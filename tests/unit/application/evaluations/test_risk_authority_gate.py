from __future__ import annotations

import pytest

from application.evaluations import (
    RiskAuthorityGateDecisionStatus,
    RiskAuthorityGateEvidence,
    RiskAuthorityGateFailureMode,
    select_risk_authority_gate,
)
from domain.authority import (
    AiOutputContentType,
    AuthorityEffect,
    CanonicalOwner,
    GateProfile,
    IntendedSink,
    RiskAuthorityClassificationInput,
    RiskAuthorityClassifier,
    RiskTier,
    SourceOfTruthCategory,
)


def _metadata(
    classification_input: RiskAuthorityClassificationInput,
) -> dict[str, object]:
    return RiskAuthorityClassifier().classify(classification_input).to_metadata()


@pytest.mark.parametrize(
    ("metadata", "evidence", "expected_tier", "expected_gate_profile"),
    [
        (
            _metadata(
                RiskAuthorityClassificationInput(
                    content_type=AiOutputContentType.RUNTIME_EVIDENCE,
                    authority_effect=AuthorityEffect.NON_AUTHORITATIVE_INFORMATION,
                    canonical_owner=CanonicalOwner.RUNTIME,
                    source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
                    intended_sink=IntendedSink.INTERNAL_RUNTIME_EVIDENCE,
                )
            ),
            None,
            RiskTier.BASELINE,
            GateProfile.BASELINE_INTERNAL,
        ),
        (
            _metadata(
                RiskAuthorityClassificationInput(
                    content_type=AiOutputContentType.RAG_ANSWER,
                    authority_effect=AuthorityEffect.NON_AUTHORITATIVE_INFORMATION,
                    canonical_owner=CanonicalOwner.RAG_SERVICE,
                    source_of_truth=SourceOfTruthCategory.PRESENTATION_OUTPUT,
                    intended_sink=IntendedSink.RAG_ANSWER,
                    externally_visible=True,
                )
            ),
            RiskAuthorityGateEvidence(provenance_record_ids=("rag-doc-1",)),
            RiskTier.ENHANCED,
            GateProfile.ENHANCED_PROVENANCE,
        ),
        (
            _metadata(
                RiskAuthorityClassificationInput(
                    content_type=AiOutputContentType.RECOMMENDATION_EXPLANATION,
                    authority_effect=AuthorityEffect.ADVISORY_CONTEXT,
                    canonical_owner=CanonicalOwner.RECOMMENDATION_SERVICE,
                    source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
                    intended_sink=IntendedSink.RECOMMENDATION,
                    capital_relevant=True,
                    externally_visible=True,
                )
            ),
            RiskAuthorityGateEvidence(
                provenance_record_ids=("recommendation-record-1",),
                decision_evidence_ids=("model-gate-1",),
            ),
            RiskTier.VIGILANT,
            GateProfile.VIGILANT_DECISION_EVIDENCE,
        ),
        (
            _metadata(
                RiskAuthorityClassificationInput(
                    content_type=AiOutputContentType.TOOL_RESPONSE,
                    authority_effect=AuthorityEffect.OUTSIDE_AUTHORITY,
                    canonical_owner=CanonicalOwner.APPLICATION_SERVICE,
                    source_of_truth=SourceOfTruthCategory.EXTERNAL_TRANSPORT_PAYLOAD,
                    intended_sink=IntendedSink.MCP_TOOL_RESPONSE,
                    capital_relevant=True,
                    externally_visible=True,
                )
            ),
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
    metadata = _metadata(
        RiskAuthorityClassificationInput(
            content_type=AiOutputContentType.RECOMMENDATION_EXPLANATION,
            authority_effect=AuthorityEffect.ADVISORY_CONTEXT,
            canonical_owner=CanonicalOwner.RECOMMENDATION_SERVICE,
            source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
            intended_sink=IntendedSink.RECOMMENDATION,
            capital_relevant=True,
            externally_visible=True,
        )
    )
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
            _metadata(
                RiskAuthorityClassificationInput(
                    content_type=AiOutputContentType.RAG_ANSWER,
                    authority_effect=AuthorityEffect.NON_AUTHORITATIVE_INFORMATION,
                    canonical_owner=CanonicalOwner.RAG_SERVICE,
                    source_of_truth=SourceOfTruthCategory.PRESENTATION_OUTPUT,
                    intended_sink=IntendedSink.RAG_ANSWER,
                    externally_visible=True,
                )
            ),
            RiskAuthorityGateFailureMode.PROVENANCE_EVIDENCE_REQUIRED,
        ),
        (
            _metadata(
                RiskAuthorityClassificationInput(
                    content_type=AiOutputContentType.STRATEGY_SYNTHESIS,
                    authority_effect=AuthorityEffect.DETERMINISTIC_PLATFORM_DECISION,
                    canonical_owner=CanonicalOwner.STRATEGY_SERVICE,
                    source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
                    intended_sink=IntendedSink.DURABLE_DOMAIN_RECORD,
                    capital_relevant=True,
                    durable_authority=True,
                )
            ),
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
