from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar

from core.storage.persistence.claim_evidence_links import (
    ClaimEvidenceLinkRecordProtocol,
)
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
class _MaterialClaimEvidenceBindingKey:
    claim_target_id: str
    packet_id: str
    packet_claim_id: str


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

    async def validated_packets_for_references(
        self,
        references: Sequence[EvidenceClaimReference],
    ) -> tuple[DecisionEvidencePacket, ...]:
        """Return canonical packets after validating every supplied claim reference."""

        packets_by_id: dict[str, DecisionEvidencePacket] = {}
        for reference in references:
            packet = packets_by_id.get(reference.packet_id)
            if packet is None:
                packet = await self._validated_packet(reference.packet_id)
                packets_by_id[reference.packet_id] = packet
            canonical = _canonical_reference_for_claim(packet, reference.claim_id)
            _assert_reference_matches_canonical(
                reference=reference,
                canonical=canonical,
            )
        return tuple(packets_by_id.values())

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
        packet = await self._validated_packet(reference.packet_id)
        canonical = _canonical_reference_for_claim(
            packet,
            reference.claim_id,
        )
        _assert_reference_matches_canonical(
            reference=reference,
            canonical=canonical,
        )
        return canonical

    async def _validated_packet(self, packet_id: str) -> DecisionEvidencePacket:
        packet = await self._packet_reader.reconstruct_packet(packet_id)
        if packet.packet_id != packet_id:
            raise ClaimEvidenceBindingError(
                "decision evidence packet reader returned substituted packet "
                f"{packet.packet_id!r} for reference {packet_id!r}."
            )
        return packet


def has_material_claim_references(
    targets: Sequence[_ClaimEvidenceBindingTarget],
) -> bool:
    """Return whether any binding target carries readiness-gating material refs."""

    return bool(_required_material_claim_binding_keys(targets))


def ensure_material_claim_evidence_links_bound(
    *,
    targets: Sequence[_ClaimEvidenceBindingTarget],
    links: Iterable[ClaimEvidenceLinkRecordProtocol],
    boundary_name: str,
) -> None:
    """Fail closed when material target refs lack matching durable link records."""

    required_references_by_key = _required_material_claim_references_by_key(targets)
    required_keys = frozenset(required_references_by_key)
    link_records = tuple(links)
    material_link_keys = _material_claim_link_keys(link_records)
    unexpected_keys = material_link_keys - required_keys
    if unexpected_keys:
        unexpected = _first_sorted_key(unexpected_keys)
        raise ClaimEvidenceBindingError(
            f"{boundary_name} received unexpected material decision-evidence "
            f"packet binding for target {unexpected.claim_target_id!r}, "
            f"packet {unexpected.packet_id!r}, claim "
            f"{unexpected.packet_claim_id!r}."
        )

    if not required_keys:
        return

    missing_keys = required_keys - material_link_keys
    if missing_keys:
        missing = _first_sorted_key(missing_keys)
        raise ClaimEvidenceBindingError(
            f"{boundary_name} material claim {missing.packet_claim_id!r} on "
            f"target {missing.claim_target_id!r} lacks required "
            "decision-evidence packet binding."
        )

    for link in link_records:
        if not link.material:
            continue
        expected = required_references_by_key[
            _MaterialClaimEvidenceBindingKey(
                claim_target_id=link.claim_target_id,
                packet_id=link.packet_id,
                packet_claim_id=link.packet_claim_id,
            )
        ]
        _assert_material_link_matches_required_reference(
            link=link,
            reference=expected,
            boundary_name=boundary_name,
        )


def _assert_material_link_matches_required_reference(
    *,
    link: ClaimEvidenceLinkRecordProtocol,
    reference: EvidenceClaimReference,
    boundary_name: str,
) -> None:
    if link.risk_tier is not reference.risk_tier:
        raise ClaimEvidenceBindingError(
            f"{boundary_name} material claim {link.packet_claim_id!r} risk_tier "
            "does not match required canonical claim reference."
        )
    if link.supporting_evidence_ids != reference.supporting_evidence_ids:
        raise ClaimEvidenceBindingError(
            f"{boundary_name} material claim {link.packet_claim_id!r} "
            "supporting evidence does not match required canonical claim reference."
        )
    if link.reconstruction_reference_ids != reference.reconstruction_reference_ids:
        raise ClaimEvidenceBindingError(
            f"{boundary_name} material claim {link.packet_claim_id!r} "
            "reconstruction references do not match required canonical claim reference."
        )
    if link.uncertainty_ids != reference.uncertainty_ids:
        raise ClaimEvidenceBindingError(
            f"{boundary_name} material claim {link.packet_claim_id!r} "
            "uncertainty references do not match required canonical claim reference."
        )
    if link.limitation_ids != reference.limitation_ids:
        raise ClaimEvidenceBindingError(
            f"{boundary_name} material claim {link.packet_claim_id!r} "
            "limitation references do not match required canonical claim reference."
        )


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


def _required_material_claim_binding_keys(
    targets: Sequence[_ClaimEvidenceBindingTarget],
) -> frozenset[_MaterialClaimEvidenceBindingKey]:
    return frozenset(_required_material_claim_references_by_key(targets))


def _required_material_claim_references_by_key(
    targets: Sequence[_ClaimEvidenceBindingTarget],
) -> dict[_MaterialClaimEvidenceBindingKey, EvidenceClaimReference]:
    references_by_key: dict[
        _MaterialClaimEvidenceBindingKey, EvidenceClaimReference
    ] = {}
    for target in targets:
        for reference in target.claim_references:
            if not reference.material:
                continue
            key = _MaterialClaimEvidenceBindingKey(
                claim_target_id=target.claim_target_id,
                packet_id=reference.packet_id,
                packet_claim_id=reference.claim_id,
            )
            existing = references_by_key.get(key)
            if existing is not None and existing != reference:
                raise ClaimEvidenceBindingError(
                    "material claim references for target "
                    f"{target.claim_target_id!r}, packet {reference.packet_id!r}, "
                    f"claim {reference.claim_id!r} contain conflicting canonical "
                    "evidence bindings."
                )
            references_by_key[key] = reference
    return references_by_key


def _material_claim_link_keys(
    links: Sequence[ClaimEvidenceLinkRecordProtocol],
) -> frozenset[_MaterialClaimEvidenceBindingKey]:
    return frozenset(
        _MaterialClaimEvidenceBindingKey(
            claim_target_id=link.claim_target_id,
            packet_id=link.packet_id,
            packet_claim_id=link.packet_claim_id,
        )
        for link in links
        if link.material
    )


def _first_sorted_key(
    keys: frozenset[_MaterialClaimEvidenceBindingKey],
) -> _MaterialClaimEvidenceBindingKey:
    return sorted(
        keys,
        key=lambda key: (key.claim_target_id, key.packet_id, key.packet_claim_id),
    )[0]


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
    _assert_reference_identity_matches_canonical(
        reference=reference,
        canonical=canonical,
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
    if reference.materiality is not canonical.materiality:
        raise ClaimEvidenceBindingError(
            f"claim {reference.claim_id!r} materiality does not match canonical packet."
        )
    if reference.supporting_evidence_ids != canonical.supporting_evidence_ids:
        raise ClaimEvidenceBindingError(
            f"claim {reference.claim_id!r} supporting evidence does not match "
            "canonical packet."
        )
    if reference.conflicting_evidence_ids != canonical.conflicting_evidence_ids:
        raise ClaimEvidenceBindingError(
            f"claim {reference.claim_id!r} conflicting evidence does not match "
            "canonical packet."
        )
    _assert_unresolved_conflicts_match(reference=reference, canonical=canonical)
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


def _assert_reference_identity_matches_canonical(
    *,
    reference: EvidenceClaimReference,
    canonical: EvidenceClaimReference,
) -> None:
    if reference.packet_version != canonical.packet_version:
        raise ClaimEvidenceBindingError(
            f"claim {reference.claim_id!r} packet_version does not match "
            "canonical packet."
        )
    if reference.output_id != canonical.output_id:
        raise ClaimEvidenceBindingError(
            f"claim {reference.claim_id!r} output_id does not match canonical packet."
        )


def _assert_unresolved_conflicts_match(
    *,
    reference: EvidenceClaimReference,
    canonical: EvidenceClaimReference,
) -> None:
    if (
        reference.unresolved_conflicting_evidence_ids
        != canonical.unresolved_conflicting_evidence_ids
    ):
        raise ClaimEvidenceBindingError(
            f"claim {reference.claim_id!r} unresolved conflicting evidence does "
            "not match canonical packet."
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
    "ensure_material_claim_evidence_links_bound",
    "has_material_claim_references",
    "RecommendationClaimEvidenceBindingTarget",
    "ReportClaimEvidenceBindingTarget",
]
