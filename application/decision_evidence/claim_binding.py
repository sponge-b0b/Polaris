from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar

from core.storage.persistence.recommendations import (
    RecommendationClaimEvidenceLinkRecord,
    new_recommendation_claim_evidence_link_id,
)
from core.storage.persistence.reports import (
    ReportClaimEvidenceLinkRecord,
    new_report_claim_evidence_link_id,
)
from domain.decision_evidence import (
    DecisionEvidencePacket,
    DecisionEvidencePacketValidationError,
    EvidenceClaimReference,
    evidence_claim_references_from_packet,
)


class ClaimEvidenceBindingError(ValueError):
    """Raised when a generated claim cannot be safely bound to packet evidence."""


class DecisionEvidencePacketReader(Protocol):
    """Read boundary for canonical decision evidence packets."""

    async def reconstruct_packet(self, packet_id: str) -> DecisionEvidencePacket:
        """Reconstruct and validate one canonical packet by id."""


class _ClaimEvidenceBindingTarget(Protocol):
    """Common claim-binding fields shared by report and recommendation targets."""

    @property
    def claim_target_id(self) -> str: ...

    @property
    def claim_references(self) -> tuple[EvidenceClaimReference, ...]: ...


_ClaimEvidenceBindingTargetT = TypeVar(
    "_ClaimEvidenceBindingTargetT",
    bound=_ClaimEvidenceBindingTarget,
)
_ClaimEvidenceLinkT = TypeVar("_ClaimEvidenceLinkT")
_ClaimEvidenceLinkFactory = Callable[
    [_ClaimEvidenceBindingTargetT, EvidenceClaimReference],
    _ClaimEvidenceLinkT,
]


@dataclass(frozen=True, slots=True)
class ReportClaimEvidenceBindingTarget:
    """Generated report section or bullet claim needing durable evidence links."""

    claim_target_id: str
    claim_references: tuple[EvidenceClaimReference, ...]
    section_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "claim_target_id",
            _clean_identifier(self.claim_target_id, "claim_target_id"),
        )
        object.__setattr__(
            self,
            "section_id",
            _clean_optional_identifier(self.section_id, "section_id"),
        )
        object.__setattr__(
            self,
            "claim_references",
            _claim_reference_tuple(self.claim_references),
        )


@dataclass(frozen=True, slots=True)
class RecommendationClaimEvidenceBindingTarget:
    """One recommendation rationale or nested claim target requiring durable links."""

    claim_target_id: str
    claim_references: tuple[EvidenceClaimReference, ...]
    rationale_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "claim_target_id",
            _clean_identifier(self.claim_target_id, "claim_target_id"),
        )
        object.__setattr__(
            self,
            "rationale_id",
            _clean_optional_identifier(self.rationale_id, "rationale_id"),
        )
        object.__setattr__(
            self,
            "claim_references",
            _claim_reference_tuple(self.claim_references),
        )


class DecisionEvidenceClaimBindingService:
    """Bind generated report/recommendation claims to canonical packet claims.

    The service does not persist records itself. It reconstructs canonical
    packets through the packet reader so stale, missing, or substituted sources
    fail closed before presentation records are committed.
    """

    def __init__(self, packet_reader: DecisionEvidencePacketReader) -> None:
        self._packet_reader = packet_reader

    async def bind_report_claims(
        self,
        *,
        report_id: str,
        targets: Sequence[ReportClaimEvidenceBindingTarget],
    ) -> tuple[ReportClaimEvidenceLinkRecord, ...]:
        clean_report_id = _clean_identifier(report_id, "report_id")
        return await self._bind_claim_links(
            targets=targets,
            make_link=lambda target, canonical: _report_claim_evidence_link(
                report_id=clean_report_id,
                target=target,
                canonical=canonical,
            ),
        )

    async def bind_recommendation_claims(
        self,
        *,
        recommendation_id: str,
        targets: Sequence[RecommendationClaimEvidenceBindingTarget],
    ) -> tuple[RecommendationClaimEvidenceLinkRecord, ...]:
        clean_recommendation_id = _clean_identifier(
            recommendation_id,
            "recommendation_id",
        )
        return await self._bind_claim_links(
            targets=targets,
            make_link=lambda target, canonical: _recommendation_claim_evidence_link(
                recommendation_id=clean_recommendation_id,
                target=target,
                canonical=canonical,
            ),
        )

    async def _bind_claim_links(
        self,
        *,
        targets: Sequence[_ClaimEvidenceBindingTargetT],
        make_link: _ClaimEvidenceLinkFactory[
            _ClaimEvidenceBindingTargetT,
            _ClaimEvidenceLinkT,
        ],
    ) -> tuple[_ClaimEvidenceLinkT, ...]:
        links: list[_ClaimEvidenceLinkT] = []
        for target in targets:
            for reference in target.claim_references:
                canonical = await self._validated_reference(reference)
                links.append(make_link(target, canonical))
        return tuple(links)

    async def _validated_reference(
        self,
        reference: EvidenceClaimReference,
    ) -> EvidenceClaimReference:
        packet = await self._packet_reader.reconstruct_packet(reference.packet_id)
        if packet.packet_id != reference.packet_id:
            raise ClaimEvidenceBindingError(
                "decision evidence packet reader returned substituted packet "
                f"{packet.packet_id!r} for reference {reference.packet_id!r}."
            )
        canonical = _canonical_reference_for_claim(
            packet,
            reference.claim_id,
        )
        _assert_reference_matches_canonical(
            reference=reference,
            canonical=canonical,
        )
        return canonical


def _report_claim_evidence_link(
    *,
    report_id: str,
    target: ReportClaimEvidenceBindingTarget,
    canonical: EvidenceClaimReference,
) -> ReportClaimEvidenceLinkRecord:
    return ReportClaimEvidenceLinkRecord(
        link_id=new_report_claim_evidence_link_id(
            report_id=report_id,
            section_id=target.section_id,
            claim_target_id=target.claim_target_id,
            packet_id=canonical.packet_id,
            packet_claim_id=canonical.claim_id,
        ),
        report_id=report_id,
        section_id=target.section_id,
        claim_target_id=target.claim_target_id,
        packet_id=canonical.packet_id,
        packet_claim_id=canonical.claim_id,
        risk_tier=canonical.risk_tier,
        material=canonical.material,
        supporting_evidence_ids=canonical.supporting_evidence_ids,
        reconstruction_reference_ids=canonical.reconstruction_reference_ids,
        uncertainty_ids=canonical.uncertainty_ids,
        limitation_ids=canonical.limitation_ids,
    )


def _recommendation_claim_evidence_link(
    *,
    recommendation_id: str,
    target: RecommendationClaimEvidenceBindingTarget,
    canonical: EvidenceClaimReference,
) -> RecommendationClaimEvidenceLinkRecord:
    return RecommendationClaimEvidenceLinkRecord(
        link_id=new_recommendation_claim_evidence_link_id(
            recommendation_id=recommendation_id,
            rationale_id=target.rationale_id,
            claim_target_id=target.claim_target_id,
            packet_id=canonical.packet_id,
            packet_claim_id=canonical.claim_id,
        ),
        recommendation_id=recommendation_id,
        rationale_id=target.rationale_id,
        claim_target_id=target.claim_target_id,
        packet_id=canonical.packet_id,
        packet_claim_id=canonical.claim_id,
        risk_tier=canonical.risk_tier,
        material=canonical.material,
        supporting_evidence_ids=canonical.supporting_evidence_ids,
        reconstruction_reference_ids=canonical.reconstruction_reference_ids,
        uncertainty_ids=canonical.uncertainty_ids,
        limitation_ids=canonical.limitation_ids,
    )


def _canonical_reference_for_claim(
    packet: DecisionEvidencePacket,
    claim_id: str,
) -> EvidenceClaimReference:
    references = evidence_claim_references_from_packet(packet, claim_ids=(claim_id,))
    if not references.claim_references:
        raise ClaimEvidenceBindingError(
            f"decision evidence packet {packet.packet_id!r} does not contain "
            f"claim {claim_id!r}."
        )
    if len(references.claim_references) > 1:
        raise ClaimEvidenceBindingError(
            f"decision evidence packet {packet.packet_id!r} contains duplicate "
            f"claim {claim_id!r}."
        )
    return references.claim_references[0]


def _assert_reference_matches_canonical(
    *,
    reference: EvidenceClaimReference,
    canonical: EvidenceClaimReference,
) -> None:
    if reference.output_id != canonical.output_id:
        raise ClaimEvidenceBindingError(
            f"claim {reference.claim_id!r} output_id does not match canonical packet."
        )
    if reference.risk_tier is not canonical.risk_tier:
        raise ClaimEvidenceBindingError(
            f"claim {reference.claim_id!r} risk_tier does not match canonical packet."
        )
    if reference.material is not canonical.material:
        raise ClaimEvidenceBindingError(
            f"claim {reference.claim_id!r} material flag does not match "
            "canonical packet."
        )
    if reference.supporting_evidence_ids != canonical.supporting_evidence_ids:
        raise ClaimEvidenceBindingError(
            f"claim {reference.claim_id!r} supporting evidence does not match "
            "canonical packet."
        )
    if reference.reconstruction_reference_ids != canonical.reconstruction_reference_ids:
        raise ClaimEvidenceBindingError(
            f"claim {reference.claim_id!r} reconstruction references do not match "
            "canonical packet."
        )
    if reference.uncertainty_ids != canonical.uncertainty_ids:
        raise ClaimEvidenceBindingError(
            f"claim {reference.claim_id!r} uncertainty references do not match "
            "canonical packet."
        )
    if reference.limitation_ids != canonical.limitation_ids:
        raise ClaimEvidenceBindingError(
            f"claim {reference.claim_id!r} limitation references do not match "
            "canonical packet."
        )


def _claim_reference_tuple(
    references: Iterable[EvidenceClaimReference],
) -> tuple[EvidenceClaimReference, ...]:
    clean_references = tuple(references)
    if not clean_references:
        raise DecisionEvidencePacketValidationError(
            "claim evidence binding targets require at least one "
            "EvidenceClaimReference entry."
        )
    for reference in clean_references:
        if not isinstance(reference, EvidenceClaimReference):
            raise DecisionEvidencePacketValidationError(
                "claim evidence binding targets require EvidenceClaimReference entries."
            )
    return clean_references


def _clean_identifier(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{label} cannot be empty.")
    return cleaned


def _clean_optional_identifier(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _clean_identifier(value, label)


__all__ = [
    "ClaimEvidenceBindingError",
    "DecisionEvidenceClaimBindingService",
    "DecisionEvidencePacketReader",
    "RecommendationClaimEvidenceBindingTarget",
    "ReportClaimEvidenceBindingTarget",
]
