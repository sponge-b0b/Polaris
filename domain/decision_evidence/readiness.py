from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from domain.authority import RiskTier
from domain.decision_evidence.claim_references import EvidenceClaimReference
from domain.decision_evidence.packets import (
    DecisionEvidencePacket,
    ReconstructionReferenceKind,
)

_REJECTED_SUPPORT_ID_PREFIXES: Final[tuple[str, ...]] = (
    "rag-context-rejected:",
    "rejected:",
    "evidence-rejected:",
)
_REFERENCE_ONLY_EVALUATION_PACKET_ID_PREFIXES: Final[tuple[str, ...]] = (
    "evaluation_run:",
    "model_replacement_gate:",
)


class DecisionEvidencePacketReadinessFailureMode(StrEnum):
    """Fail-closed packet completeness reasons for authority readiness checks."""

    NONE = "none"
    PACKET_SUPPORT_MISSING = "packet_support_missing"
    RECONSTRUCTION_REFERENCES_MISSING = "reconstruction_references_missing"
    AUTHORITY_METADATA_INCONSISTENT = "authority_metadata_inconsistent"
    REJECTED_EVIDENCE_CITED = "rejected_evidence_cited"
    MATERIAL_CONFLICT_UNRESOLVED = "material_conflict_unresolved"


_Mode = DecisionEvidencePacketReadinessFailureMode


@dataclass(frozen=True, slots=True)
class DecisionEvidencePacketReadiness:
    """Completeness assessment for canonical decision evidence packet support."""

    complete: bool
    failure_mode: DecisionEvidencePacketReadinessFailureMode
    message: str
    provenance_reconstruction_complete: bool = False
    claim_support_complete: bool = False
    correctness_support_complete: bool = False
    provenance_reconstruction_failure_mode: _Mode = _Mode.NONE
    claim_support_failure_mode: _Mode = _Mode.NONE
    correctness_support_failure_mode: _Mode = _Mode.NONE
    packet_ids: tuple[str, ...] = ()
    supporting_evidence_ids: tuple[str, ...] = ()
    conflicting_evidence_ids: tuple[str, ...] = ()
    unresolved_conflicting_evidence_ids: tuple[str, ...] = ()
    reconstruction_reference_ids: tuple[str, ...] = ()
    reconstruction_reference_kinds: tuple[str, ...] = ()
    rejected_supporting_evidence_ids: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        """Whether all packet readiness dimensions are complete."""

        return self.complete


_COMPLETE_READINESS = DecisionEvidencePacketReadiness(
    complete=True,
    failure_mode=DecisionEvidencePacketReadinessFailureMode.NONE,
    message="Canonical decision evidence packet support is complete.",
    provenance_reconstruction_complete=True,
    claim_support_complete=True,
    correctness_support_complete=True,
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
    unique_conflicting_ids = _unique(collected.conflicting_evidence_ids)
    unique_unresolved_conflicting_ids = _unique(
        collected.unresolved_conflicting_evidence_ids
    )
    unique_reconstruction_ids = _unique(collected.reconstruction_reference_ids)
    unique_reconstruction_kinds = _unique(collected.reconstruction_reference_kinds)
    if unique_unresolved_conflicting_ids:
        return _readiness_failure(
            DecisionEvidencePacketReadinessFailureMode.MATERIAL_CONFLICT_UNRESOLVED,
            "Material claims cannot have unresolved conflicting evidence.",
            provenance_reconstruction_complete=bool(unique_reconstruction_ids),
            claim_support_complete=bool(unique_supporting_ids),
            correctness_support_complete=False,
            correctness_support_failure_mode=(
                DecisionEvidencePacketReadinessFailureMode.MATERIAL_CONFLICT_UNRESOLVED
            ),
            packet_ids=unique_packet_ids,
            supporting_evidence_ids=unique_supporting_ids,
            conflicting_evidence_ids=unique_conflicting_ids,
            unresolved_conflicting_evidence_ids=unique_unresolved_conflicting_ids,
            reconstruction_reference_ids=unique_reconstruction_ids,
            reconstruction_reference_kinds=unique_reconstruction_kinds,
        )
    incomplete = _incomplete_support_failure(
        readiness_gating_claim_ids=collected.readiness_gating_claim_ids,
        packet_ids=unique_packet_ids,
        supporting_evidence_ids=unique_supporting_ids,
        reconstruction_reference_ids=unique_reconstruction_ids,
        reconstruction_reference_kinds=unique_reconstruction_kinds,
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
            provenance_reconstruction_complete=bool(unique_reconstruction_ids),
            claim_support_complete=False,
            correctness_support_complete=False,
            claim_support_failure_mode=(
                DecisionEvidencePacketReadinessFailureMode.REJECTED_EVIDENCE_CITED
            ),
            correctness_support_failure_mode=(
                DecisionEvidencePacketReadinessFailureMode.REJECTED_EVIDENCE_CITED
            ),
            reconstruction_reference_ids=unique_reconstruction_ids,
            reconstruction_reference_kinds=unique_reconstruction_kinds,
            rejected_supporting_evidence_ids=rejected_supporting_ids,
        )

    return DecisionEvidencePacketReadiness(
        complete=_COMPLETE_READINESS.complete,
        failure_mode=_COMPLETE_READINESS.failure_mode,
        message=_COMPLETE_READINESS.message,
        provenance_reconstruction_complete=True,
        claim_support_complete=True,
        correctness_support_complete=True,
        packet_ids=unique_packet_ids,
        supporting_evidence_ids=unique_supporting_ids,
        conflicting_evidence_ids=unique_conflicting_ids,
        unresolved_conflicting_evidence_ids=unique_unresolved_conflicting_ids,
        reconstruction_reference_ids=unique_reconstruction_ids,
        reconstruction_reference_kinds=unique_reconstruction_kinds,
    )


@dataclass(frozen=True, slots=True)
class _CollectedPacketSupport:
    packet_ids: tuple[str, ...]
    readiness_gating_claim_ids: tuple[str, ...]
    supporting_evidence_ids: tuple[str, ...]
    conflicting_evidence_ids: tuple[str, ...]
    unresolved_conflicting_evidence_ids: tuple[str, ...]
    reconstruction_reference_ids: tuple[str, ...]
    reconstruction_reference_kinds: tuple[str, ...]


def _collect_packet_support_details(
    packets: tuple[DecisionEvidencePacket, ...],
    claim_references: tuple[EvidenceClaimReference, ...],
    *,
    required_risk_tier: RiskTier | None,
) -> _CollectedPacketSupport | DecisionEvidencePacketReadiness:
    packet_ids: list[str] = []
    readiness_gating_claim_ids: list[str] = []
    supporting_evidence_ids: list[str] = []
    conflicting_evidence_ids: list[str] = []
    unresolved_conflicting_evidence_ids: list[str] = []
    reconstruction_reference_ids: list[str] = []
    reconstruction_reference_kinds: list[str] = []
    full_packet_ids = frozenset(packet.packet_id for packet in packets)

    for packet in packets:
        if _risk_tier_mismatch(packet.risk_tier, required_risk_tier):
            return _readiness_failure(
                DecisionEvidencePacketReadinessFailureMode.AUTHORITY_METADATA_INCONSISTENT,
                "Decision evidence packet authority does not match selected risk tier.",
            )
        packet_ids.append(packet.packet_id)
        reconstruction_reference_ids.extend(packet.reconstruction_reference_ids)
        reconstruction_reference_kinds.extend(
            _canonical_reconstruction_reference_kind_values(packet)
        )
        for claim in packet.material_claims:
            readiness_gating_claim_ids.append(claim.claim_id)
            supporting_evidence_ids.extend(claim.evidence.supporting_evidence_ids)
            conflicting_evidence_ids.extend(claim.evidence.conflicting_evidence_ids)
            unresolved_conflicting_evidence_ids.extend(
                claim.evidence.unresolved_conflicting_evidence_ids
            )

    for reference in claim_references:
        if _risk_tier_mismatch(reference.risk_tier, required_risk_tier):
            return _readiness_failure(
                DecisionEvidencePacketReadinessFailureMode.AUTHORITY_METADATA_INCONSISTENT,
                (
                    "Decision evidence claim reference risk tier does not match "
                    "selected risk tier."
                ),
            )
        if _is_reference_only_evaluation_packet(reference, full_packet_ids):
            return _readiness_failure(
                DecisionEvidencePacketReadinessFailureMode.PACKET_SUPPORT_MISSING,
                (
                    "Reference-only evaluation case provenance cannot satisfy "
                    "decision evidence packet readiness."
                ),
                packet_ids=(reference.packet_id,),
                supporting_evidence_ids=reference.supporting_evidence_ids,
                reconstruction_reference_ids=reference.reconstruction_reference_ids,
                provenance_reconstruction_complete=False,
                claim_support_complete=False,
                correctness_support_complete=False,
            )
        packet_ids.append(reference.packet_id)
        reconstruction_reference_ids.extend(reference.reconstruction_reference_ids)
        if reference.material:
            readiness_gating_claim_ids.append(reference.claim_id)
            supporting_evidence_ids.extend(reference.supporting_evidence_ids)
            conflicting_evidence_ids.extend(reference.conflicting_evidence_ids)
            unresolved_conflicting_evidence_ids.extend(
                reference.unresolved_conflicting_evidence_ids
            )

    return _CollectedPacketSupport(
        packet_ids=tuple(packet_ids),
        readiness_gating_claim_ids=tuple(readiness_gating_claim_ids),
        supporting_evidence_ids=tuple(supporting_evidence_ids),
        conflicting_evidence_ids=tuple(conflicting_evidence_ids),
        unresolved_conflicting_evidence_ids=tuple(unresolved_conflicting_evidence_ids),
        reconstruction_reference_ids=tuple(reconstruction_reference_ids),
        reconstruction_reference_kinds=tuple(reconstruction_reference_kinds),
    )


def _incomplete_support_failure(
    *,
    readiness_gating_claim_ids: tuple[str, ...],
    packet_ids: tuple[str, ...],
    supporting_evidence_ids: tuple[str, ...],
    reconstruction_reference_ids: tuple[str, ...],
    reconstruction_reference_kinds: tuple[str, ...],
) -> DecisionEvidencePacketReadiness | None:
    if readiness_gating_claim_ids and not supporting_evidence_ids:
        return _readiness_failure(
            DecisionEvidencePacketReadinessFailureMode.PACKET_SUPPORT_MISSING,
            (
                "Material claims require supporting evidence from a decision "
                "evidence packet."
            ),
            provenance_reconstruction_complete=bool(reconstruction_reference_ids),
            claim_support_complete=False,
            correctness_support_complete=False,
            claim_support_failure_mode=(
                DecisionEvidencePacketReadinessFailureMode.PACKET_SUPPORT_MISSING
            ),
            packet_ids=packet_ids,
            reconstruction_reference_ids=reconstruction_reference_ids,
            reconstruction_reference_kinds=reconstruction_reference_kinds,
        )
    if not reconstruction_reference_ids:
        return _readiness_failure(
            DecisionEvidencePacketReadinessFailureMode.RECONSTRUCTION_REFERENCES_MISSING,
            "Decision evidence packet support requires reconstruction references.",
            provenance_reconstruction_complete=False,
            claim_support_complete=bool(supporting_evidence_ids),
            correctness_support_complete=True,
            provenance_reconstruction_failure_mode=(
                DecisionEvidencePacketReadinessFailureMode.RECONSTRUCTION_REFERENCES_MISSING
            ),
            packet_ids=packet_ids,
            supporting_evidence_ids=supporting_evidence_ids,
        )
    return None


def _canonical_reconstruction_reference_kind_values(
    packet: DecisionEvidencePacket,
) -> tuple[str, ...]:
    return tuple(
        _canonical_reconstruction_reference_kind_value(reference.kind)
        for reference in packet.reconstruction_references
    )


def _canonical_reconstruction_reference_kind_value(
    kind: ReconstructionReferenceKind,
) -> str:
    return kind.value


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


def _is_reference_only_evaluation_packet(
    reference: EvidenceClaimReference,
    full_packet_ids: frozenset[str],
) -> bool:
    return (
        reference.packet_id not in full_packet_ids
        and reference.packet_id.startswith(
            _REFERENCE_ONLY_EVALUATION_PACKET_ID_PREFIXES,
        )
    )


def _readiness_failure(
    failure_mode: DecisionEvidencePacketReadinessFailureMode,
    message: str,
    *,
    packet_ids: tuple[str, ...] = (),
    supporting_evidence_ids: tuple[str, ...] = (),
    conflicting_evidence_ids: tuple[str, ...] = (),
    unresolved_conflicting_evidence_ids: tuple[str, ...] = (),
    reconstruction_reference_ids: tuple[str, ...] = (),
    reconstruction_reference_kinds: tuple[str, ...] = (),
    rejected_supporting_evidence_ids: tuple[str, ...] = (),
    provenance_reconstruction_complete: bool = False,
    claim_support_complete: bool = False,
    correctness_support_complete: bool = False,
    provenance_reconstruction_failure_mode: (DecisionEvidencePacketReadinessFailureMode)
    | None = None,
    claim_support_failure_mode: (DecisionEvidencePacketReadinessFailureMode)
    | None = None,
    correctness_support_failure_mode: (DecisionEvidencePacketReadinessFailureMode)
    | None = None,
) -> DecisionEvidencePacketReadiness:
    return DecisionEvidencePacketReadiness(
        complete=False,
        failure_mode=failure_mode,
        message=message,
        provenance_reconstruction_complete=provenance_reconstruction_complete,
        claim_support_complete=claim_support_complete,
        correctness_support_complete=correctness_support_complete,
        provenance_reconstruction_failure_mode=_dimension_failure_mode(
            complete=provenance_reconstruction_complete,
            explicit_failure_mode=provenance_reconstruction_failure_mode,
            fallback_failure_mode=failure_mode,
        ),
        claim_support_failure_mode=_dimension_failure_mode(
            complete=claim_support_complete,
            explicit_failure_mode=claim_support_failure_mode,
            fallback_failure_mode=failure_mode,
        ),
        correctness_support_failure_mode=_dimension_failure_mode(
            complete=correctness_support_complete,
            explicit_failure_mode=correctness_support_failure_mode,
            fallback_failure_mode=failure_mode,
        ),
        packet_ids=packet_ids,
        supporting_evidence_ids=supporting_evidence_ids,
        conflicting_evidence_ids=conflicting_evidence_ids,
        unresolved_conflicting_evidence_ids=unresolved_conflicting_evidence_ids,
        reconstruction_reference_ids=reconstruction_reference_ids,
        reconstruction_reference_kinds=reconstruction_reference_kinds,
        rejected_supporting_evidence_ids=rejected_supporting_evidence_ids,
    )


def _dimension_failure_mode(
    *,
    complete: bool,
    explicit_failure_mode: DecisionEvidencePacketReadinessFailureMode | None,
    fallback_failure_mode: DecisionEvidencePacketReadinessFailureMode,
) -> DecisionEvidencePacketReadinessFailureMode:
    if complete:
        return DecisionEvidencePacketReadinessFailureMode.NONE
    return explicit_failure_mode or fallback_failure_mode


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
