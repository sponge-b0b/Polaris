from __future__ import annotations

from collections.abc import Mapping

from domain.authority import (
    AiOutputContentType,
    AuthorityEffect,
    CanonicalOwner,
    IntendedSink,
    RiskAuthorityClassificationInput,
    RiskTier,
    SourceOfTruthCategory,
    classify_risk_authority,
)


def authority_metadata_for_tier(
    tier: RiskTier,
    *,
    evidence_sufficient: bool = True,
) -> dict[str, object]:
    return classify_risk_authority(
        authority_input_for_tier(
            tier,
            evidence_sufficient=evidence_sufficient,
        )
    ).to_metadata()


def authority_input_for_tier(
    tier: RiskTier,
    *,
    evidence_sufficient: bool = True,
) -> RiskAuthorityClassificationInput:
    if tier is RiskTier.BASELINE:
        return runtime_evidence_authority_input(
            evidence_sufficient=evidence_sufficient,
        )
    if tier is RiskTier.ENHANCED:
        return rag_answer_authority_input(
            evidence_sufficient=evidence_sufficient,
        )
    if tier is RiskTier.VIGILANT:
        return recommendation_explanation_authority_input(
            evidence_sufficient=evidence_sufficient,
        )
    return outside_authority_tool_response_input(
        evidence_sufficient=evidence_sufficient,
    )


def runtime_evidence_authority_input(
    *,
    evidence_sufficient: bool = True,
    model_provided_metadata: Mapping[str, object] | None = None,
) -> RiskAuthorityClassificationInput:
    return _authority_input(
        content_type=AiOutputContentType.RUNTIME_EVIDENCE,
        authority_effect=AuthorityEffect.NON_AUTHORITATIVE_INFORMATION,
        canonical_owner=CanonicalOwner.RUNTIME,
        source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
        intended_sink=IntendedSink.INTERNAL_RUNTIME_EVIDENCE,
        evidence_sufficient=evidence_sufficient,
        model_provided_metadata=model_provided_metadata,
    )


def rag_answer_authority_input(
    *,
    externally_visible: bool = True,
    evidence_sufficient: bool = True,
    model_provided_metadata: Mapping[str, object] | None = None,
) -> RiskAuthorityClassificationInput:
    return _authority_input(
        content_type=AiOutputContentType.RAG_ANSWER,
        authority_effect=AuthorityEffect.NON_AUTHORITATIVE_INFORMATION,
        canonical_owner=CanonicalOwner.RAG_SERVICE,
        source_of_truth=SourceOfTruthCategory.PRESENTATION_OUTPUT,
        intended_sink=IntendedSink.RAG_ANSWER,
        externally_visible=externally_visible,
        evidence_sufficient=evidence_sufficient,
        model_provided_metadata=model_provided_metadata,
    )


def report_presentation_authority_input(
    *,
    externally_visible: bool = True,
    evidence_sufficient: bool = True,
    model_provided_metadata: Mapping[str, object] | None = None,
) -> RiskAuthorityClassificationInput:
    return _authority_input(
        AiOutputContentType.REPORT,
        AuthorityEffect.ADVISORY_CONTEXT,
        CanonicalOwner.REPORT_SERVICE,
        SourceOfTruthCategory.PRESENTATION_OUTPUT,
        IntendedSink.REPORT,
        externally_visible=externally_visible,
        evidence_sufficient=evidence_sufficient,
        model_provided_metadata=model_provided_metadata,
    )


def strategy_synthesis_authority_input(
    *,
    evidence_sufficient: bool = True,
    model_provided_metadata: Mapping[str, object] | None = None,
) -> RiskAuthorityClassificationInput:
    return _authority_input(
        AiOutputContentType.STRATEGY_SYNTHESIS,
        AuthorityEffect.DETERMINISTIC_PLATFORM_DECISION,
        CanonicalOwner.STRATEGY_SERVICE,
        SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
        IntendedSink.DURABLE_DOMAIN_RECORD,
        capital_relevant=True,
        durable_authority=True,
        evidence_sufficient=evidence_sufficient,
        model_provided_metadata=model_provided_metadata,
    )


def recommendation_record_authority_input(
    *,
    evidence_sufficient: bool = True,
    model_provided_metadata: Mapping[str, object] | None = None,
) -> RiskAuthorityClassificationInput:
    return _authority_input(
        content_type=AiOutputContentType.RECOMMENDATION_EXPLANATION,
        authority_effect=AuthorityEffect.CANONICAL_RECORD,
        canonical_owner=CanonicalOwner.RECOMMENDATION_SERVICE,
        source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
        intended_sink=IntendedSink.DURABLE_DOMAIN_RECORD,
        durable_authority=True,
        evidence_sufficient=evidence_sufficient,
        model_provided_metadata=model_provided_metadata,
    )


def recommendation_explanation_authority_input(
    *,
    evidence_sufficient: bool = True,
    model_provided_metadata: Mapping[str, object] | None = None,
) -> RiskAuthorityClassificationInput:
    return _authority_input(
        content_type=AiOutputContentType.RECOMMENDATION_EXPLANATION,
        authority_effect=AuthorityEffect.ADVISORY_CONTEXT,
        canonical_owner=CanonicalOwner.RECOMMENDATION_SERVICE,
        source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
        intended_sink=IntendedSink.RECOMMENDATION,
        capital_relevant=True,
        externally_visible=True,
        evidence_sufficient=evidence_sufficient,
        model_provided_metadata=model_provided_metadata,
    )


def advisory_tool_response_authority_input(
    *,
    evidence_sufficient: bool = True,
    model_provided_metadata: Mapping[str, object] | None = None,
) -> RiskAuthorityClassificationInput:
    return _authority_input(
        content_type=AiOutputContentType.TOOL_RESPONSE,
        authority_effect=AuthorityEffect.ADVISORY_CONTEXT,
        canonical_owner=CanonicalOwner.APPLICATION_SERVICE,
        source_of_truth=SourceOfTruthCategory.EXTERNAL_TRANSPORT_PAYLOAD,
        intended_sink=IntendedSink.MCP_TOOL_RESPONSE,
        capital_relevant=True,
        externally_visible=True,
        evidence_sufficient=evidence_sufficient,
        model_provided_metadata=model_provided_metadata,
    )


def outside_authority_tool_response_input(
    *,
    evidence_sufficient: bool = True,
    model_provided_metadata: Mapping[str, object] | None = None,
) -> RiskAuthorityClassificationInput:
    return _authority_input(
        content_type=AiOutputContentType.TOOL_RESPONSE,
        authority_effect=AuthorityEffect.OUTSIDE_AUTHORITY,
        canonical_owner=CanonicalOwner.APPLICATION_SERVICE,
        source_of_truth=SourceOfTruthCategory.EXTERNAL_TRANSPORT_PAYLOAD,
        intended_sink=IntendedSink.MCP_TOOL_RESPONSE,
        capital_relevant=True,
        externally_visible=True,
        evidence_sufficient=evidence_sufficient,
        model_provided_metadata=model_provided_metadata,
    )


def workflow_curation_authority_input(
    *,
    evidence_sufficient: bool = True,
    model_provided_metadata: Mapping[str, object] | None = None,
) -> RiskAuthorityClassificationInput:
    return _authority_input(
        content_type=AiOutputContentType.DURABLE_RECORD,
        authority_effect=AuthorityEffect.CANONICAL_RECORD,
        canonical_owner=CanonicalOwner.WORKFLOW_OUTPUT_CURATION,
        source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
        intended_sink=IntendedSink.DURABLE_DOMAIN_RECORD,
        durable_authority=True,
        evidence_sufficient=evidence_sufficient,
        model_provided_metadata=model_provided_metadata,
    )


def insufficient_runtime_evidence_authority_input() -> RiskAuthorityClassificationInput:
    return runtime_evidence_authority_input(evidence_sufficient=False)


def _authority_input(
    content_type: AiOutputContentType,
    authority_effect: AuthorityEffect,
    canonical_owner: CanonicalOwner,
    source_of_truth: SourceOfTruthCategory,
    intended_sink: IntendedSink,
    *,
    capital_relevant: bool = False,
    durable_authority: bool = False,
    externally_visible: bool = False,
    governance_impact: bool = False,
    evidence_sufficient: bool = True,
    model_provided_metadata: Mapping[str, object] | None = None,
) -> RiskAuthorityClassificationInput:
    return RiskAuthorityClassificationInput(
        content_type=content_type,
        authority_effect=authority_effect,
        canonical_owner=canonical_owner,
        source_of_truth=source_of_truth,
        intended_sink=intended_sink,
        capital_relevant=capital_relevant,
        durable_authority=durable_authority,
        externally_visible=externally_visible,
        governance_impact=governance_impact,
        evidence_sufficient=evidence_sufficient,
        model_provided_metadata=model_provided_metadata or {},
    )
