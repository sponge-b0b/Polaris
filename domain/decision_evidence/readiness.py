from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from domain.authority import RiskTier
from domain.decision_evidence.claim_references import EvidenceClaimReference
from domain.decision_evidence.packets import DecisionEvidencePacket

_REJECTED_SUPPORT_ID_PREFIXES: Final[tuple[str, ...]] = (
    "rag-context-rejected:",
    "rejected:",
    "evidence-rejected:",
)


class DecisionEvidencePacketReadinessFailureMode(StrEnum):
    """Fail-closed packet completeness reasons for authority readiness checks."""

    NONE = "none"
    PACKET_SUPPORT_MISSING = "packet_support_missing"
    RECONSTRUCTION_REFERENCES_MISSING = "reconstruction_references_missing"
    AUTHORITY_METADATA_INCONSISTENT = "authority_metadata_inconsistent"
    REJECTED_EVIDENCE_CITED = "rejected_evidence_cited"


@dataclass(frozen=True, slots=True)
class DecisionEvidencePacketReadiness:
    """Completeness assessment for canonical decision evidence packet support."""

    complete: bool
    failure_mode: DecisionEvidencePacketReadinessFailureMode
    message: str
    packet_ids: tuple[str, ...] = ()
    supporting_evidence_ids: tuple[str, ...] = ()
    reconstruction_reference_ids: tuple[str, ...] = ()
    rejected_supporting_evidence_ids: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        """Whether canonical packet support is complete for readiness."""

        return self.complete


_COMPLETE_READINESS = DecisionEvidencePacketReadiness(
    complete=True,
    failure_mode=DecisionEvidencePacketReadinessFailureMode.NONE,
    message="Canonical decision evidence packet support is complete.",
)


def assess_decision_evidence_packet_readiness(
    *,
    packets: Iterable[DecisionEvidencePacket] = (),
    claim_references: Iterable[EvidenceClaimReference] = (),
    rejected_evidence_ids: Iterable[str] = (),
    required_risk_tier: RiskTier | None = None,
) -> DecisionEvidencePacketReadiness:
    """Assess whether Enhanced/Vigilant output has complete packet support.

    The inputs are the canonical full packet model and its reference-only claim
    bindings used by presentation boundaries. Legacy provenance IDs are
    intentionally ignored because they cannot prove support, reconstruction, or
    rejected-evidence status.
    """

    packet_tuple = tuple(packets)
    reference_tuple = tuple(claim_references)
    explicit_rejected_ids = frozenset(_clean_identifier_tuple(rejected_evidence_ids))
    if not packet_tuple and not reference_tuple:
        return _readiness_failure(
            DecisionEvidencePacketReadinessFailureMode.PACKET_SUPPORT_MISSING,
            "Complete decision evidence packet support is required.",
        )

    collected = _collect_packet_support_details(
        packet_tuple,
        reference_tuple,
        required_risk_tier=required_risk_tier,
    )
    if isinstance(collected, DecisionEvidencePacketReadiness):
        return collected

    unique_packet_ids = _unique(collected.packet_ids)
    unique_supporting_ids = _unique(collected.supporting_evidence_ids)
    unique_reconstruction_ids = _unique(collected.reconstruction_reference_ids)
    incomplete = _incomplete_support_failure(
        packet_ids=unique_packet_ids,
        supporting_evidence_ids=unique_supporting_ids,
        reconstruction_reference_ids=unique_reconstruction_ids,
    )
    if incomplete is not None:
        return incomplete

    rejected_supporting_ids = _rejected_supporting_ids(
        unique_supporting_ids,
        explicit_rejected_ids=explicit_rejected_ids,
    )
    if rejected_supporting_ids:
        return _readiness_failure(
            DecisionEvidencePacketReadinessFailureMode.REJECTED_EVIDENCE_CITED,
            "Rejected evidence cannot be cited as supporting packet evidence.",
            packet_ids=unique_packet_ids,
            supporting_evidence_ids=unique_supporting_ids,
            reconstruction_reference_ids=unique_reconstruction_ids,
            rejected_supporting_evidence_ids=rejected_supporting_ids,
        )

    return DecisionEvidencePacketReadiness(
        complete=_COMPLETE_READINESS.complete,
        failure_mode=_COMPLETE_READINESS.failure_mode,
        message=_COMPLETE_READINESS.message,
        packet_ids=unique_packet_ids,
        supporting_evidence_ids=unique_supporting_ids,
        reconstruction_reference_ids=unique_reconstruction_ids,
    )


@dataclass(frozen=True, slots=True)
class _CollectedPacketSupport:
    packet_ids: tuple[str, ...]
    supporting_evidence_ids: tuple[str, ...]
    reconstruction_reference_ids: tuple[str, ...]


def _collect_packet_support_details(
    packets: tuple[DecisionEvidencePacket, ...],
    claim_references: tuple[EvidenceClaimReference, ...],
    *,
    required_risk_tier: RiskTier | None,
) -> _CollectedPacketSupport | DecisionEvidencePacketReadiness:
    packet_ids: list[str] = []
    supporting_evidence_ids: list[str] = []
    reconstruction_reference_ids: list[str] = []

    for packet in packets:
        if _risk_tier_mismatch(packet.risk_tier, required_risk_tier):
            return _readiness_failure(
                DecisionEvidencePacketReadinessFailureMode.AUTHORITY_METADATA_INCONSISTENT,
                "Decision evidence packet authority does not match selected risk tier.",
            )
        packet_ids.append(packet.packet_id)
        reconstruction_reference_ids.extend(packet.reconstruction_reference_ids)
        for claim in packet.material_claims:
            supporting_evidence_ids.extend(claim.evidence.supporting_evidence_ids)

    for reference in claim_references:
        if _risk_tier_mismatch(reference.risk_tier, required_risk_tier):
            return _readiness_failure(
                DecisionEvidencePacketReadinessFailureMode.AUTHORITY_METADATA_INCONSISTENT,
                (
                    "Decision evidence claim reference risk tier does not match "
                    "selected risk tier."
                ),
            )
        packet_ids.append(reference.packet_id)
        reconstruction_reference_ids.extend(reference.reconstruction_reference_ids)
        if reference.material:
            supporting_evidence_ids.extend(reference.supporting_evidence_ids)

    return _CollectedPacketSupport(
        packet_ids=tuple(packet_ids),
        supporting_evidence_ids=tuple(supporting_evidence_ids),
        reconstruction_reference_ids=tuple(reconstruction_reference_ids),
    )


def _incomplete_support_failure(
    *,
    packet_ids: tuple[str, ...],
    supporting_evidence_ids: tuple[str, ...],
    reconstruction_reference_ids: tuple[str, ...],
) -> DecisionEvidencePacketReadiness | None:
    if not supporting_evidence_ids:
        return _readiness_failure(
            DecisionEvidencePacketReadinessFailureMode.PACKET_SUPPORT_MISSING,
            (
                "Material claims require supporting evidence from a decision "
                "evidence packet."
            ),
            packet_ids=packet_ids,
            reconstruction_reference_ids=reconstruction_reference_ids,
        )
    if not reconstruction_reference_ids:
        return _readiness_failure(
            DecisionEvidencePacketReadinessFailureMode.RECONSTRUCTION_REFERENCES_MISSING,
            "Decision evidence packet support requires reconstruction references.",
            packet_ids=packet_ids,
            supporting_evidence_ids=supporting_evidence_ids,
        )
    return None


def _rejected_supporting_ids(
    supporting_evidence_ids: tuple[str, ...],
    *,
    explicit_rejected_ids: frozenset[str],
) -> tuple[str, ...]:
    return tuple(
        evidence_id
        for evidence_id in supporting_evidence_ids
        if evidence_id in explicit_rejected_ids or _has_rejected_prefix(evidence_id)
    )


def _risk_tier_mismatch(
    observed_risk_tier: RiskTier,
    required_risk_tier: RiskTier | None,
) -> bool:
    return (
        required_risk_tier is not None and observed_risk_tier is not required_risk_tier
    )


def _readiness_failure(
    failure_mode: DecisionEvidencePacketReadinessFailureMode,
    message: str,
    *,
    packet_ids: tuple[str, ...] = (),
    supporting_evidence_ids: tuple[str, ...] = (),
    reconstruction_reference_ids: tuple[str, ...] = (),
    rejected_supporting_evidence_ids: tuple[str, ...] = (),
) -> DecisionEvidencePacketReadiness:
    return DecisionEvidencePacketReadiness(
        complete=False,
        failure_mode=failure_mode,
        message=message,
        packet_ids=packet_ids,
        supporting_evidence_ids=supporting_evidence_ids,
        reconstruction_reference_ids=reconstruction_reference_ids,
        rejected_supporting_evidence_ids=rejected_supporting_evidence_ids,
    )


def _clean_identifier_tuple(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(value.strip() for value in values if value.strip())


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _has_rejected_prefix(evidence_id: str) -> bool:
    return evidence_id.startswith(_REJECTED_SUPPORT_ID_PREFIXES)


__all__ = [
    "DecisionEvidencePacketReadiness",
    "DecisionEvidencePacketReadinessFailureMode",
    "assess_decision_evidence_packet_readiness",
]
