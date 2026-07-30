from __future__ import annotations

import pytest

from application.evaluations import (
    RiskAuthorityGateDecisionStatus,
    RiskAuthorityGateEvidence,
    RiskAuthorityGateFailureMode,
    select_risk_authority_gate,
)
from domain.authority import (
    GateProfile,
    RiskAuthorityClassificationInput,
    RiskAuthorityClassifier,
    RiskTier,
    classify_risk_authority,
)
from domain.decision_evidence import (
    ClaimEvidenceBinding,
    DecisionEvidencePacket,
    EvidenceClaimReference,
    EvidenceReference,
    EvidenceReferenceKind,
    EvidenceRetentionRequirement,
    MaterialClaim,
    ReconstructionReference,
    ReconstructionReferenceKind,
    evidence_claim_references_from_packet,
)
from tests.helpers.risk_authority_examples import (
    authority_input_for_tier,
    outside_authority_tool_response_input,
    rag_answer_authority_input,
    recommendation_explanation_authority_input,
    runtime_evidence_authority_input,
    strategy_synthesis_authority_input,
)


def _metadata(
    classification_input: RiskAuthorityClassificationInput,
) -> dict[str, object]:
    return RiskAuthorityClassifier().classify(classification_input).to_metadata()


def _packet(
    tier: RiskTier,
    *,
    packet_id: str = "packet-1",
    output_id: str = "output-1",
    supporting_evidence_id: str = "evidence-1",
) -> DecisionEvidencePacket:
    return DecisionEvidencePacket(
        packet_id=packet_id,
        output_id=output_id,
        authority=classify_risk_authority(authority_input_for_tier(tier)),
        claims=(
            MaterialClaim(
                claim_id="claim-1",
                text="Supported material claim.",
                evidence=ClaimEvidenceBinding(
                    supporting_evidence_ids=(supporting_evidence_id,),
                ),
            ),
        ),
        evidence=(
            EvidenceReference(
                evidence_id=supporting_evidence_id,
                kind=EvidenceReferenceKind.WORKFLOW_NODE_OUTPUT,
                reconstruction_reference_ids=("workflow-node",),
                summary="Runtime node output supporting the material claim.",
            ),
        ),
        reconstruction_references=(
            ReconstructionReference(
                reference_id="workflow-node",
                kind=ReconstructionReferenceKind.WORKFLOW_NODE_OUTPUT,
                record_id="run-1:node:analysis",
            ),
        ),
        retention=EvidenceRetentionRequirement(
            retain_until="2031-07-25T00:00:00Z",
            policy_id="enhanced-provenance-5y",
        ),
    )


def _claim_reference(
    tier: RiskTier,
    *,
    packet_id: str = "packet-1",
    output_id: str = "output-1",
    supporting_evidence_id: str = "evidence-1",
) -> EvidenceClaimReference:
    return EvidenceClaimReference(
        packet_id=packet_id,
        output_id=output_id,
        claim_id="claim-1",
        risk_tier=tier,
        supporting_evidence_ids=(supporting_evidence_id,),
        reconstruction_reference_ids=("workflow-node",),
    )


@pytest.mark.parametrize(
    ("metadata", "evidence", "expected_tier", "expected_gate_profile"),
    [
        (
            _metadata(runtime_evidence_authority_input()),
            None,
            RiskTier.BASELINE,
            GateProfile.BASELINE_INTERNAL,
        ),
        (
            _metadata(rag_answer_authority_input()),
            RiskAuthorityGateEvidence(
                provenance_record_ids=("rag-doc-1",),
                decision_evidence_packets=(_packet(RiskTier.ENHANCED),),
            ),
            RiskTier.ENHANCED,
            GateProfile.ENHANCED_PROVENANCE,
        ),
        (
            _metadata(recommendation_explanation_authority_input()),
            RiskAuthorityGateEvidence(
                provenance_record_ids=("recommendation-record-1",),
                decision_evidence_packets=(_packet(RiskTier.VIGILANT),),
            ),
            RiskTier.VIGILANT,
            GateProfile.VIGILANT_DECISION_EVIDENCE,
        ),
        (
            _metadata(outside_authority_tool_response_input()),
            RiskAuthorityGateEvidence(
                provenance_record_ids=("tool-call-1",),
                decision_evidence_ids=("operator-note-1",),
            ),
            RiskTier.PROHIBITED_OUTSIDE_AUTHORITY,
            GateProfile.PROHIBITED_BOUNDARY,
        ),
    ],
)
def test_gate_selection_is_traceable_to_canonical_authority_metadata(
    metadata: dict[str, object],
    evidence: RiskAuthorityGateEvidence | None,
    expected_tier: RiskTier,
    expected_gate_profile: GateProfile,
) -> None:
    decision = select_risk_authority_gate(metadata, evidence=evidence)

    assert decision.risk_tier is expected_tier
    assert decision.gate_profile is expected_gate_profile
    assert decision.authority_metadata == metadata
    assert decision.evidence == (evidence or RiskAuthorityGateEvidence())
    assert decision.failure_mode is (
        RiskAuthorityGateFailureMode.PROHIBITED_BOUNDARY
        if expected_tier is RiskTier.PROHIBITED_OUTSIDE_AUTHORITY
        else RiskAuthorityGateFailureMode.NONE
    )


def test_capital_visible_output_cannot_select_lower_gate_than_metadata_allows() -> None:
    metadata = _metadata(recommendation_explanation_authority_input())
    metadata["risk_tier"] = "baseline"
    metadata["gate_profile"] = "baseline_internal"

    decision = select_risk_authority_gate(
        metadata,
        evidence=RiskAuthorityGateEvidence(provenance_record_ids=("record-1",)),
    )

    assert decision.status is RiskAuthorityGateDecisionStatus.FAILED
    assert decision.failure_mode is RiskAuthorityGateFailureMode.METADATA_INCONSISTENT
    assert decision.risk_tier is RiskTier.BASELINE
    assert decision.gate_profile is GateProfile.BASELINE_INTERNAL
    assert decision.expected_risk_tier is RiskTier.VIGILANT
    assert decision.expected_gate_profile is GateProfile.VIGILANT_DECISION_EVIDENCE


@pytest.mark.parametrize(
    ("metadata", "failure_mode"),
    [
        (
            _metadata(rag_answer_authority_input()),
            RiskAuthorityGateFailureMode.DECISION_EVIDENCE_REQUIRED,
        ),
        (
            _metadata(strategy_synthesis_authority_input()),
            RiskAuthorityGateFailureMode.DECISION_EVIDENCE_REQUIRED,
        ),
    ],
)
def test_missing_gate_evidence_fails_closed_for_enhanced_and_vigilant_outputs(
    metadata: dict[str, object],
    failure_mode: RiskAuthorityGateFailureMode,
) -> None:
    decision = select_risk_authority_gate(metadata)

    assert decision.status is RiskAuthorityGateDecisionStatus.FAILED
    assert decision.failure_mode is failure_mode
    assert decision.evidence == RiskAuthorityGateEvidence()
    assert decision.message


def test_enhanced_readiness_requires_complete_packet_not_only_provenance() -> None:
    decision = select_risk_authority_gate(
        _metadata(rag_answer_authority_input()),
        evidence=RiskAuthorityGateEvidence(provenance_record_ids=("rag-doc-1",)),
    )

    assert decision.status is RiskAuthorityGateDecisionStatus.FAILED
    assert (
        decision.failure_mode is RiskAuthorityGateFailureMode.DECISION_EVIDENCE_REQUIRED
    )
    assert "packet" in decision.message.lower()


def test_enhanced_readiness_rejects_reference_only_evaluation_packet_ids() -> None:
    decision = select_risk_authority_gate(
        _metadata(rag_answer_authority_input()),
        evidence=RiskAuthorityGateEvidence(
            provenance_record_ids=("case-1",),
            decision_evidence_claim_references=(
                EvidenceClaimReference(
                    packet_id="evaluation_run:run-1",
                    output_id="evaluation_case:case-1",
                    claim_id="evaluation_case:case-1",
                    risk_tier=RiskTier.ENHANCED,
                    supporting_evidence_ids=("case-1",),
                    reconstruction_reference_ids=("case-1",),
                ),
            ),
        ),
    )

    assert decision.status is RiskAuthorityGateDecisionStatus.FAILED
    assert (
        decision.failure_mode is RiskAuthorityGateFailureMode.DECISION_EVIDENCE_REQUIRED
    )
    assert "reference-only" in decision.message.lower()
    assert "packet" in decision.message.lower()


def test_vigilant_readiness_accepts_claim_reference_when_packet_backed() -> None:
    packet = _packet(RiskTier.VIGILANT)
    references = evidence_claim_references_from_packet(packet).claim_references

    decision = select_risk_authority_gate(
        _metadata(strategy_synthesis_authority_input()),
        evidence=RiskAuthorityGateEvidence(
            provenance_record_ids=("recommendation-record-1",),
            decision_evidence_packets=(packet,),
            decision_evidence_claim_references=references,
        ),
    )

    assert decision.status is RiskAuthorityGateDecisionStatus.PASSED
    assert decision.failure_mode is RiskAuthorityGateFailureMode.NONE


def test_enhanced_readiness_rejects_generic_reference_only_claim_metadata() -> None:
    decision = select_risk_authority_gate(
        _metadata(rag_answer_authority_input()),
        evidence=RiskAuthorityGateEvidence(
            provenance_record_ids=("rag-doc-1",),
            decision_evidence_claim_references=(_claim_reference(RiskTier.ENHANCED),),
        ),
    )

    assert decision.status is RiskAuthorityGateDecisionStatus.FAILED
    assert (
        decision.failure_mode is RiskAuthorityGateFailureMode.DECISION_EVIDENCE_REQUIRED
    )
    assert (
        decision.evidence.decision_evidence_claim_references[0].packet_id == "packet-1"
    )
    assert "reference-only" in decision.message.lower()
    assert "canonical" in decision.message.lower()


def test_vigilant_strategy_output_fails_closed_when_only_evidence_ids_exist() -> None:
    decision = select_risk_authority_gate(
        _metadata(strategy_synthesis_authority_input()),
        evidence=RiskAuthorityGateEvidence(
            provenance_record_ids=("strategy-case-1",),
            evaluation_run_ids=("run-1",),
            decision_evidence_ids=("evaluation_run:run-1",),
        ),
    )

    assert decision.status is RiskAuthorityGateDecisionStatus.FAILED
    assert (
        decision.failure_mode is RiskAuthorityGateFailureMode.DECISION_EVIDENCE_REQUIRED
    )
    assert "packet" in decision.message.lower()


def test_readiness_rejects_rejected_evidence_cited_as_support() -> None:
    decision = select_risk_authority_gate(
        _metadata(rag_answer_authority_input()),
        evidence=RiskAuthorityGateEvidence(
            provenance_record_ids=("rag-doc-1",),
            decision_evidence_packets=(
                _packet(
                    RiskTier.ENHANCED,
                    supporting_evidence_id="rag-context-rejected:chunk-1",
                ),
            ),
        ),
    )

    assert decision.status is RiskAuthorityGateDecisionStatus.FAILED
    assert (
        decision.failure_mode is RiskAuthorityGateFailureMode.DECISION_EVIDENCE_REQUIRED
    )
    assert "rejected" in decision.message.lower()


@pytest.mark.parametrize(
    ("expected_metadata", "expected_tier", "expected_gate_profile"),
    [
        (
            _metadata(rag_answer_authority_input()),
            RiskTier.ENHANCED,
            GateProfile.ENHANCED_PROVENANCE,
        ),
        (
            _metadata(strategy_synthesis_authority_input()),
            RiskTier.VIGILANT,
            GateProfile.VIGILANT_DECISION_EVIDENCE,
        ),
        (
            _metadata(outside_authority_tool_response_input()),
            RiskTier.PROHIBITED_OUTSIDE_AUTHORITY,
            GateProfile.PROHIBITED_BOUNDARY,
        ),
    ],
)
def test_missing_authority_metadata_fails_with_expected_non_baseline_gate(
    expected_metadata: dict[str, object],
    expected_tier: RiskTier,
    expected_gate_profile: GateProfile,
) -> None:
    decision = select_risk_authority_gate(
        None,
        expected_authority_metadata=expected_metadata,
    )

    assert decision.status is RiskAuthorityGateDecisionStatus.FAILED
    assert decision.failure_mode is RiskAuthorityGateFailureMode.METADATA_MISSING
    assert decision.risk_tier is expected_tier
    assert decision.gate_profile is expected_gate_profile
    assert decision.expected_risk_tier is expected_tier
    assert decision.expected_gate_profile is expected_gate_profile
    assert decision.authority_metadata is None


@pytest.mark.parametrize(
    ("expected_metadata", "expected_tier", "expected_gate_profile"),
    [
        (
            _metadata(rag_answer_authority_input()),
            RiskTier.ENHANCED,
            GateProfile.ENHANCED_PROVENANCE,
        ),
        (
            _metadata(strategy_synthesis_authority_input()),
            RiskTier.VIGILANT,
            GateProfile.VIGILANT_DECISION_EVIDENCE,
        ),
        (
            _metadata(outside_authority_tool_response_input()),
            RiskTier.PROHIBITED_OUTSIDE_AUTHORITY,
            GateProfile.PROHIBITED_BOUNDARY,
        ),
    ],
)
def test_malformed_authority_metadata_fails_with_expected_non_baseline_gate(
    expected_metadata: dict[str, object],
    expected_tier: RiskTier,
    expected_gate_profile: GateProfile,
) -> None:
    decision = select_risk_authority_gate(
        {"risk_tier": expected_tier.value},
        expected_authority_metadata=expected_metadata,
    )

    assert decision.status is RiskAuthorityGateDecisionStatus.FAILED
    assert decision.failure_mode is RiskAuthorityGateFailureMode.METADATA_MALFORMED
    assert decision.risk_tier is expected_tier
    assert decision.gate_profile is expected_gate_profile
    assert decision.expected_risk_tier is expected_tier
    assert decision.expected_gate_profile is expected_gate_profile
    assert decision.authority_metadata == {"risk_tier": expected_tier.value}


def test_missing_authority_metadata_passes_only_for_baseline_internal() -> None:
    expected_metadata = _metadata(runtime_evidence_authority_input())

    decision = select_risk_authority_gate(
        None,
        expected_authority_metadata=expected_metadata,
    )

    assert decision.status is RiskAuthorityGateDecisionStatus.PASSED
    assert decision.failure_mode is RiskAuthorityGateFailureMode.NONE
    assert decision.risk_tier is RiskTier.BASELINE
    assert decision.gate_profile is GateProfile.BASELINE_INTERNAL
    assert decision.expected_risk_tier is RiskTier.BASELINE
    assert decision.expected_gate_profile is GateProfile.BASELINE_INTERNAL
    assert decision.authority_metadata is None
