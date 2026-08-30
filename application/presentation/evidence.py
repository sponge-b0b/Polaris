from __future__ import annotations

from collections.abc import Iterable

from application.evaluations.risk_authority_gate import (
    OutputGovernanceGateEvidence,
    RiskAuthorityGateEvidence,
)
from application.presentation.sink_decision import PresentationSinkDecision
from domain.decision_evidence import DecisionEvidencePacket, EvidenceClaimReference

PRESENTATION_SINK_DISPOSITION_METADATA_KEY = "presentation_sink_disposition"
PRESENTATION_SINK_MAY_PRESENT_METADATA_KEY = "presentation_sink_may_present"
PRESENTATION_SINK_REASONS_METADATA_KEY = "presentation_sink_reasons"
PRESENTATION_SINK_LIMITATIONS_METADATA_KEY = "presentation_sink_limitations"
PRESENTATION_SINK_GATE_FAILURE_MODE_METADATA_KEY = "presentation_sink_gate_failure_mode"


def presentation_gate_evidence(
    *,
    packets: Iterable[DecisionEvidencePacket] = (),
    claim_references: Iterable[EvidenceClaimReference] = (),
    output_governance_evidence: Iterable[OutputGovernanceGateEvidence] = (),
    rejected_evidence_ids: Iterable[str] = (),
) -> RiskAuthorityGateEvidence:
    """Adapt canonical packet evidence into the shared presentation gate contract."""

    packet_tuple = tuple(packets)
    return RiskAuthorityGateEvidence(
        provenance_record_ids=_provenance_record_ids(packet_tuple),
        decision_evidence_packets=packet_tuple,
        decision_evidence_claim_references=tuple(claim_references),
        output_governance_evidence=tuple(output_governance_evidence),
        rejected_evidence_ids=tuple(rejected_evidence_ids),
    )


def presentation_sink_decision_metadata(
    decision: PresentationSinkDecision,
) -> dict[str, object]:
    """Project one canonical sink decision into transport-safe presentation metadata."""

    return {
        PRESENTATION_SINK_DISPOSITION_METADATA_KEY: decision.disposition.value,
        PRESENTATION_SINK_MAY_PRESENT_METADATA_KEY: decision.may_present,
        PRESENTATION_SINK_REASONS_METADATA_KEY: list(decision.reasons),
        PRESENTATION_SINK_LIMITATIONS_METADATA_KEY: list(decision.limitations),
        PRESENTATION_SINK_GATE_FAILURE_MODE_METADATA_KEY: (
            decision.gate_failure_mode.value
        ),
    }


def _provenance_record_ids(
    packets: tuple[DecisionEvidencePacket, ...],
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            reference.record_id
            for packet in packets
            for reference in packet.reconstruction_references
        )
    )


__all__ = [
    "PRESENTATION_SINK_DISPOSITION_METADATA_KEY",
    "PRESENTATION_SINK_GATE_FAILURE_MODE_METADATA_KEY",
    "PRESENTATION_SINK_LIMITATIONS_METADATA_KEY",
    "PRESENTATION_SINK_MAY_PRESENT_METADATA_KEY",
    "PRESENTATION_SINK_REASONS_METADATA_KEY",
    "presentation_gate_evidence",
    "presentation_sink_decision_metadata",
]
