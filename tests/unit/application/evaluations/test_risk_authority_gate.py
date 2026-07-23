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
)
from tests.helpers.risk_authority_examples import (
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
            RiskAuthorityGateEvidence(provenance_record_ids=("rag-doc-1",)),
            RiskTier.ENHANCED,
            GateProfile.ENHANCED_PROVENANCE,
        ),
        (
            _metadata(recommendation_explanation_authority_input()),
            RiskAuthorityGateEvidence(
                provenance_record_ids=("recommendation-record-1",),
                decision_evidence_ids=("model-gate-1",),
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
            RiskAuthorityGateFailureMode.PROVENANCE_EVIDENCE_REQUIRED,
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
