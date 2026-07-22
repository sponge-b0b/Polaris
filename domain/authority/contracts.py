from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final


class RiskTier(StrEnum):
    """Canonical consequence tier for AI-adjacent Polaris outputs."""

    BASELINE = "baseline"
    ENHANCED = "enhanced"
    VIGILANT = "vigilant"
    PROHIBITED_OUTSIDE_AUTHORITY = "prohibited_outside_authority"


class AiOutputContentType(StrEnum):
    """Stable content-family labels; content does not decide authority alone."""

    RUNTIME_EVIDENCE = "runtime_evidence"
    DURABLE_RECORD = "durable_record"
    RECOMMENDATION_EXPLANATION = "recommendation_explanation"
    RAG_ANSWER = "rag_answer"
    REPORT = "report"
    STRATEGY_SYNTHESIS = "strategy_synthesis"
    TOOL_RESPONSE = "tool_response"


class AuthorityEffect(StrEnum):
    """What an output is allowed to affect after platform classification."""

    NON_AUTHORITATIVE_INFORMATION = "non_authoritative_information"
    ADVISORY_CONTEXT = "advisory_context"
    CANONICAL_RECORD = "canonical_record"
    DETERMINISTIC_PLATFORM_DECISION = "deterministic_platform_decision"
    GOVERNANCE_DECISION = "governance_decision"
    EXECUTION_DECISION = "execution_decision"
    OUTSIDE_AUTHORITY = "outside_authority"


class CanonicalOwner(StrEnum):
    """Platform owner responsible for the classified output boundary."""

    RUNTIME = "runtime"
    WORKFLOW_OUTPUT_CURATION = "workflow_output_curation"
    APPLICATION_SERVICE = "application_service"
    RECOMMENDATION_SERVICE = "recommendation_service"
    REPORT_SERVICE = "report_service"
    RAG_SERVICE = "rag_service"
    STRATEGY_SERVICE = "strategy_service"
    GOVERNANCE_ENGINE = "governance_engine"
    EVALUATION_SERVICE = "evaluation_service"


class SourceOfTruthCategory(StrEnum):
    """Canonical Polaris source-of-truth categories."""

    RUNTIME_EVIDENCE = "runtime_evidence"
    CANONICAL_DOMAIN_RECORD = "canonical_domain_record"
    DERIVED_PROJECTION = "derived_projection"
    TELEMETRY = "telemetry"
    PRESENTATION_OUTPUT = "presentation_output"
    EXTERNAL_TRANSPORT_PAYLOAD = "external_transport_payload"


class IntendedSink(StrEnum):
    """Stable sink categories that consume classified AI-adjacent outputs."""

    INTERNAL_RUNTIME_EVIDENCE = "internal_runtime_evidence"
    DURABLE_DOMAIN_RECORD = "durable_domain_record"
    RECOMMENDATION = "recommendation"
    RAG_ANSWER = "rag_answer"
    REPORT = "report"
    GOVERNANCE_REVIEW = "governance_review"
    EVALUATION_GATE = "evaluation_gate"
    MCP_TOOL_RESPONSE = "mcp_tool_response"


class GateProfile(StrEnum):
    """Readiness/control profile selected from canonical risk metadata."""

    BASELINE_INTERNAL = "baseline_internal"
    ENHANCED_PROVENANCE = "enhanced_provenance"
    VIGILANT_DECISION_EVIDENCE = "vigilant_decision_evidence"
    PROHIBITED_BOUNDARY = "prohibited_boundary"


_GATE_PROFILE_BY_TIER: Final[dict[RiskTier, GateProfile]] = {
    RiskTier.BASELINE: GateProfile.BASELINE_INTERNAL,
    RiskTier.ENHANCED: GateProfile.ENHANCED_PROVENANCE,
    RiskTier.VIGILANT: GateProfile.VIGILANT_DECISION_EVIDENCE,
    RiskTier.PROHIBITED_OUTSIDE_AUTHORITY: GateProfile.PROHIBITED_BOUNDARY,
}

_MODEL_AUTHORITY_CLAIM_KEYS: Final[frozenset[str]] = frozenset(
    {
        "authority_effect",
        "authority_level",
        "governance_approved",
        "residual_risk_accepted",
        "risk_tier",
        "production_ready",
    }
)

_VIGILANT_AUTHORITY_EFFECTS: Final[frozenset[AuthorityEffect]] = frozenset(
    {
        AuthorityEffect.GOVERNANCE_DECISION,
        AuthorityEffect.EXECUTION_DECISION,
    }
)

_ENHANCED_SINKS: Final[frozenset[IntendedSink]] = frozenset(
    {
        IntendedSink.DURABLE_DOMAIN_RECORD,
        IntendedSink.RECOMMENDATION,
        IntendedSink.RAG_ANSWER,
        IntendedSink.REPORT,
        IntendedSink.GOVERNANCE_REVIEW,
        IntendedSink.EVALUATION_GATE,
        IntendedSink.MCP_TOOL_RESPONSE,
    }
)


@dataclass(frozen=True, slots=True)
class RiskAuthorityClassificationInput:
    """Platform-known inputs for classifying one AI-adjacent output."""

    content_type: AiOutputContentType
    authority_effect: AuthorityEffect
    canonical_owner: CanonicalOwner
    source_of_truth: SourceOfTruthCategory
    intended_sink: IntendedSink
    capital_relevant: bool = False
    durable_authority: bool = False
    externally_visible: bool = False
    governance_impact: bool = False
    evidence_sufficient: bool = True
    model_provided_metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RiskAuthorityContract:
    """Canonical risk tier and authority metadata for one output boundary."""

    risk_tier: RiskTier
    authority_effect: AuthorityEffect
    content_type: AiOutputContentType
    canonical_owner: CanonicalOwner
    source_of_truth: SourceOfTruthCategory
    intended_sink: IntendedSink
    gate_profile: GateProfile
    capital_relevant: bool = False
    durable_authority: bool = False
    externally_visible: bool = False
    governance_impact: bool = False
    evidence_sufficient: bool = True
    ignored_model_authority_claims: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        expected_gate_profile = _GATE_PROFILE_BY_TIER[self.risk_tier]
        if self.gate_profile is not expected_gate_profile:
            raise ValueError(
                "RiskAuthorityContract gate_profile must match risk_tier: "
                f"expected {expected_gate_profile.value!r} for "
                f"{self.risk_tier.value!r}, got {self.gate_profile.value!r}."
            )

    def to_metadata(self) -> dict[str, object]:
        """Serialize stable authority metadata for JSON/persistence boundaries."""

        return {
            "risk_tier": self.risk_tier.value,
            "authority_effect": self.authority_effect.value,
            "content_type": self.content_type.value,
            "canonical_owner": self.canonical_owner.value,
            "source_of_truth": self.source_of_truth.value,
            "intended_sink": self.intended_sink.value,
            "gate_profile": self.gate_profile.value,
            "capital_relevant": self.capital_relevant,
            "durable_authority": self.durable_authority,
            "externally_visible": self.externally_visible,
            "governance_impact": self.governance_impact,
            "evidence_sufficient": self.evidence_sufficient,
            "ignored_model_authority_claims": list(self.ignored_model_authority_claims),
        }


class RiskAuthorityClassifier:
    """Deterministic platform-owned classifier for risk and authority metadata."""

    def classify(
        self,
        request: RiskAuthorityClassificationInput,
    ) -> RiskAuthorityContract:
        risk_tier = _risk_tier_for(request)
        return RiskAuthorityContract(
            risk_tier=risk_tier,
            authority_effect=request.authority_effect,
            content_type=request.content_type,
            canonical_owner=request.canonical_owner,
            source_of_truth=request.source_of_truth,
            intended_sink=request.intended_sink,
            gate_profile=_GATE_PROFILE_BY_TIER[risk_tier],
            capital_relevant=request.capital_relevant,
            durable_authority=request.durable_authority,
            externally_visible=request.externally_visible,
            governance_impact=request.governance_impact,
            evidence_sufficient=request.evidence_sufficient,
            ignored_model_authority_claims=_ignored_model_authority_claims(request),
        )


def classify_risk_authority(
    request: RiskAuthorityClassificationInput,
) -> RiskAuthorityContract:
    """Convenience function for callers that do not need a classifier instance."""

    return RiskAuthorityClassifier().classify(request)


def gate_profile_for_tier(risk_tier: RiskTier) -> GateProfile:
    """Return the canonical readiness/control profile for a risk tier."""

    return _GATE_PROFILE_BY_TIER[risk_tier]


def _risk_tier_for(request: RiskAuthorityClassificationInput) -> RiskTier:
    if request.authority_effect is AuthorityEffect.OUTSIDE_AUTHORITY:
        return RiskTier.PROHIBITED_OUTSIDE_AUTHORITY
    if _requires_vigilant_controls(request):
        return RiskTier.VIGILANT
    if _requires_enhanced_controls(request):
        return RiskTier.ENHANCED
    return RiskTier.BASELINE


def _requires_vigilant_controls(request: RiskAuthorityClassificationInput) -> bool:
    if request.authority_effect in _VIGILANT_AUTHORITY_EFFECTS:
        return True
    if request.governance_impact:
        return True
    if request.capital_relevant and (
        request.externally_visible or request.durable_authority
    ):
        return True
    if not request.evidence_sufficient and (
        request.capital_relevant
        or request.durable_authority
        or request.externally_visible
        or request.governance_impact
    ):
        return True
    return False


def _requires_enhanced_controls(request: RiskAuthorityClassificationInput) -> bool:
    if request.capital_relevant:
        return True
    if request.durable_authority:
        return True
    if request.externally_visible:
        return True
    if not request.evidence_sufficient:
        return True
    if request.authority_effect in {
        AuthorityEffect.CANONICAL_RECORD,
        AuthorityEffect.DETERMINISTIC_PLATFORM_DECISION,
    }:
        return True
    if request.source_of_truth is not SourceOfTruthCategory.RUNTIME_EVIDENCE:
        return True
    return request.intended_sink in _ENHANCED_SINKS


def _ignored_model_authority_claims(
    request: RiskAuthorityClassificationInput,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            key
            for key in request.model_provided_metadata
            if key in _MODEL_AUTHORITY_CLAIM_KEYS
        )
    )
