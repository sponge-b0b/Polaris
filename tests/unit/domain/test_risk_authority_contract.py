from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from domain.authority import (
    AiOutputContentType,
    AuthorityEffect,
    CanonicalOwner,
    GateProfile,
    IntendedSink,
    RiskAuthorityClassificationInput,
    RiskAuthorityClassifier,
    RiskAuthorityContract,
    RiskTier,
    SourceOfTruthCategory,
    reclassify_risk_authority_contract,
    risk_authority_contract_from_metadata,
)
from tests.helpers.risk_authority_examples import (
    advisory_tool_response_authority_input,
    outside_authority_tool_response_input,
    rag_answer_authority_input,
    recommendation_explanation_authority_input,
    recommendation_record_authority_input,
    report_presentation_authority_input,
    runtime_evidence_authority_input,
    strategy_synthesis_authority_input,
)


def classify(
    classification_input: RiskAuthorityClassificationInput,
) -> RiskAuthorityContract:
    return RiskAuthorityClassifier().classify(classification_input)


def test_internal_runtime_evidence_is_baseline_and_immutable() -> None:
    contract = classify(runtime_evidence_authority_input())

    assert contract.risk_tier is RiskTier.BASELINE
    assert contract.gate_profile is GateProfile.BASELINE_INTERNAL
    assert contract.authority_effect is AuthorityEffect.NON_AUTHORITATIVE_INFORMATION
    assert contract.content_type is AiOutputContentType.RUNTIME_EVIDENCE
    with pytest.raises(FrozenInstanceError):
        contract.risk_tier = RiskTier.VIGILANT  # type: ignore[misc]


def test_durable_domain_records_escalate_beyond_baseline() -> None:
    contract = classify(recommendation_record_authority_input())

    assert contract.risk_tier is RiskTier.ENHANCED
    assert contract.gate_profile is GateProfile.ENHANCED_PROVENANCE
    assert contract.source_of_truth is SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD


def test_capital_relevant_external_recommendations_are_vigilant() -> None:
    contract = classify(recommendation_explanation_authority_input())

    assert contract.risk_tier is RiskTier.VIGILANT
    assert contract.gate_profile is GateProfile.VIGILANT_DECISION_EVIDENCE


@pytest.mark.parametrize(
    (
        "classification_input",
        "expected_tier",
        "expected_owner",
        "expected_sink",
    ),
    [
        (
            rag_answer_authority_input(),
            RiskTier.ENHANCED,
            CanonicalOwner.RAG_SERVICE,
            IntendedSink.RAG_ANSWER,
        ),
        (
            report_presentation_authority_input(),
            RiskTier.ENHANCED,
            CanonicalOwner.REPORT_SERVICE,
            IntendedSink.REPORT,
        ),
        (
            strategy_synthesis_authority_input(),
            RiskTier.VIGILANT,
            CanonicalOwner.STRATEGY_SERVICE,
            IntendedSink.DURABLE_DOMAIN_RECORD,
        ),
        (
            advisory_tool_response_authority_input(),
            RiskTier.VIGILANT,
            CanonicalOwner.APPLICATION_SERVICE,
            IntendedSink.MCP_TOOL_RESPONSE,
        ),
    ],
)
def test_representative_ai_output_families_receive_authority_metadata(
    classification_input: RiskAuthorityClassificationInput,
    expected_tier: RiskTier,
    expected_owner: CanonicalOwner,
    expected_sink: IntendedSink,
) -> None:
    contract = classify(classification_input)

    assert contract.risk_tier is expected_tier
    assert contract.canonical_owner is expected_owner
    assert contract.intended_sink is expected_sink
    assert contract.content_type is classification_input.content_type
    assert contract.authority_effect is classification_input.authority_effect


def test_prohibited_outside_authority_selects_prohibited_boundary_gate() -> None:
    contract = classify(outside_authority_tool_response_input())

    assert contract.risk_tier is RiskTier.PROHIBITED_OUTSIDE_AUTHORITY
    assert contract.gate_profile is GateProfile.PROHIBITED_BOUNDARY


def test_model_metadata_cannot_self_promote_or_downgrade_authority() -> None:
    contract = classify(
        recommendation_explanation_authority_input(
            model_provided_metadata={
                "risk_tier": "baseline",
                "authority_effect": "governance_decision",
                "production_ready": True,
                "governance_approved": True,
                "residual_risk_accepted": True,
            },
        )
    )

    assert contract.risk_tier is RiskTier.VIGILANT
    assert contract.authority_effect is AuthorityEffect.ADVISORY_CONTEXT
    assert contract.gate_profile is GateProfile.VIGILANT_DECISION_EVIDENCE
    assert contract.ignored_model_authority_claims == (
        "authority_effect",
        "governance_approved",
        "production_ready",
        "residual_risk_accepted",
        "risk_tier",
    )


def test_contract_metadata_is_boundary_safe_and_uses_stable_values() -> None:
    contract = classify(rag_answer_authority_input())

    assert contract.to_metadata() == {
        "risk_tier": "enhanced",
        "authority_effect": "non_authoritative_information",
        "content_type": "rag_answer",
        "canonical_owner": "rag_service",
        "source_of_truth": "presentation_output",
        "intended_sink": "rag_answer",
        "gate_profile": "enhanced_provenance",
        "capital_relevant": False,
        "durable_authority": False,
        "externally_visible": True,
        "governance_impact": False,
        "evidence_sufficient": True,
        "ignored_model_authority_claims": [],
    }


def test_contract_metadata_round_trips_through_canonical_parser() -> None:
    contract = classify(report_presentation_authority_input())

    parsed_contract = risk_authority_contract_from_metadata(contract.to_metadata())

    assert parsed_contract == contract
    assert (
        reclassify_risk_authority_contract(parsed_contract).risk_tier
        is RiskTier.ENHANCED
    )


def test_contract_metadata_parser_rejects_malformed_boundary_values() -> None:
    metadata = classify(rag_answer_authority_input()).to_metadata()
    metadata["evidence_sufficient"] = "yes"

    with pytest.raises(ValueError, match="risk_authority.evidence_sufficient"):
        risk_authority_contract_from_metadata(metadata)
