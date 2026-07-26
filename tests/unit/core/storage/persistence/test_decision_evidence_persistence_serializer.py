from __future__ import annotations

from core.storage.persistence.serializers import (
    DecisionEvidencePacketPersistenceSerializer,
)
from domain.authority import RiskTier, classify_risk_authority
from domain.decision_evidence import (
    ClaimEvidenceBinding,
    DecisionEvidencePacket,
    EvidenceReference,
    EvidenceReferenceKind,
    EvidenceRetentionRequirement,
    MaterialClaim,
    ReconstructionReference,
    ReconstructionReferenceKind,
)
from tests.helpers.risk_authority_examples import authority_input_for_tier


def test_packet_serializer_stores_audit_data_and_durable_reconstruction_ids() -> None:
    packet = _packet()

    record = DecisionEvidencePacketPersistenceSerializer.record_from_packet(packet)

    assert record.packet_id == "packet-1"
    assert record.output_id == "strategy-decision-1"
    assert record.risk_tier is RiskTier.ENHANCED
    assert record.authority_metadata["risk_tier"] == "enhanced"
    assert record.retention_metadata["packet_id"] == "packet-1"
    assert record.retention_metadata["output_id"] == "strategy-decision-1"
    assert record.retention_metadata["retain_until"] == "2031-07-25T00:00:00Z"
    assert record.retention_metadata["policy_id"] == "enhanced-provenance-5y"
    assert record.retention_metadata["legal_hold"] is False
    assert record.retention_metadata["risk_tier"] == "enhanced"
    assert record.retention_metadata["authority_boundary"] == {
        "canonical_owner": "rag_service",
        "source_of_truth": "presentation_output",
        "intended_sink": "rag_answer",
        "gate_profile": "enhanced_provenance",
    }
    assert record.retention_metadata["retention_basis"] == (
        "decision_evidence_packet_reconstruction"
    )
    assert record.retention_metadata["requires_reconstruction"] is True
    assert record.reconstruction_reference_ids == (
        "evidence-synthesis:completed-run",
        "evidence-synthesis:node-output",
    )
    assert not hasattr(record, "metadata")
    assert "outputs" not in record.evidence_references[0]
    assert "outputs" not in record.reconstruction_references[1]


def test_packet_serializer_round_trips_canonical_packet_audit_contract() -> None:
    packet = _packet()

    record = DecisionEvidencePacketPersistenceSerializer.record_from_packet(packet)
    reconstructed = DecisionEvidencePacketPersistenceSerializer.packet_from_record(
        record
    )

    assert reconstructed == packet


def test_packet_serializer_rejects_malformed_reconstruction_identifier_values() -> None:
    record = DecisionEvidencePacketPersistenceSerializer.record_from_packet(_packet())
    malformed = record.with_reconstruction_reference_ids(
        ("evidence-synthesis:node-output",)
    )

    try:
        DecisionEvidencePacketPersistenceSerializer.packet_from_record(malformed)
    except ValueError as exc:
        assert "reconstruction reference ids" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("malformed reconstruction identifiers were accepted")


def _packet() -> DecisionEvidencePacket:
    return DecisionEvidencePacket(
        packet_id="packet-1",
        output_id="strategy-decision-1",
        authority=classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED)),
        claims=(
            MaterialClaim(
                claim_id="claim-1",
                text="The synthesis selected a bullish strategy posture.",
                evidence=ClaimEvidenceBinding(
                    supporting_evidence_ids=("evidence-synthesis",),
                ),
            ),
        ),
        evidence=(
            EvidenceReference(
                evidence_id="evidence-synthesis",
                kind=EvidenceReferenceKind.WORKFLOW_NODE_OUTPUT,
                reconstruction_reference_ids=(
                    "evidence-synthesis:completed-run",
                    "evidence-synthesis:node-output",
                ),
                summary="Persisted strategy synthesis node output.",
            ),
        ),
        reconstruction_references=(
            ReconstructionReference(
                reference_id="evidence-synthesis:completed-run",
                kind=ReconstructionReferenceKind.COMPLETED_WORKFLOW_RUN,
                record_id="morning_report:exec-1",
                snapshot_id="run-1",
            ),
            ReconstructionReference(
                reference_id="evidence-synthesis:node-output",
                kind=ReconstructionReferenceKind.WORKFLOW_NODE_OUTPUT,
                record_id="node-output-synthesis",
                snapshot_id="morning_report:exec-1:strategy_synthesis_agent",
                content_digest="digest-1",
            ),
        ),
        retention=EvidenceRetentionRequirement(
            retain_until="2031-07-25T00:00:00Z",
            policy_id="enhanced-provenance-5y",
        ),
    )
