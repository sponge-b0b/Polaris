from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import Final, cast


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


@dataclass(frozen=True, slots=True)
class RiskAuthorityDecisionProfile:
    """Canonical gate requirements selected for one risk tier."""

    risk_tier: RiskTier
    gate_profile: GateProfile
    requires_provenance_evidence: bool = False
    requires_decision_evidence: bool = False
    prohibits_boundary: bool = False


_DECISION_PROFILE_BY_TIER: Final[dict[RiskTier, RiskAuthorityDecisionProfile]] = {
    RiskTier.BASELINE: RiskAuthorityDecisionProfile(
        risk_tier=RiskTier.BASELINE,
        gate_profile=GateProfile.BASELINE_INTERNAL,
    ),
    RiskTier.ENHANCED: RiskAuthorityDecisionProfile(
        risk_tier=RiskTier.ENHANCED,
        gate_profile=GateProfile.ENHANCED_PROVENANCE,
        requires_provenance_evidence=True,
    ),
    RiskTier.VIGILANT: RiskAuthorityDecisionProfile(
        risk_tier=RiskTier.VIGILANT,
        gate_profile=GateProfile.VIGILANT_DECISION_EVIDENCE,
        requires_provenance_evidence=True,
        requires_decision_evidence=True,
    ),
    RiskTier.PROHIBITED_OUTSIDE_AUTHORITY: RiskAuthorityDecisionProfile(
        risk_tier=RiskTier.PROHIBITED_OUTSIDE_AUTHORITY,
        gate_profile=GateProfile.PROHIBITED_BOUNDARY,
        prohibits_boundary=True,
    ),
}

_GATE_PROFILE_BY_TIER: Final[dict[RiskTier, GateProfile]] = {
    risk_tier: profile.gate_profile
    for risk_tier, profile in _DECISION_PROFILE_BY_TIER.items()
}

_MODEL_AUTHORITY_CLAIM_KEYS: Final[frozenset[str]] = frozenset(
    {
        "authority_effect",
        "authority_level",
        "governance_approved",
        "residual_risk_accepted",
        "risk_tier",
        "production_ready",
        "governance_required",
        "requires_governance",
        "skip_governance",
    }
)

type AuthorityClaimPattern = tuple[str, re.Pattern[str]]

_MODEL_AUTHORITY_CLAIM_PATTERNS: Final[tuple[AuthorityClaimPattern, ...]] = (
    ("authority_effect", re.compile(r"(?i)\bauthority[-_ ]effect\b")),
    ("authority_level", re.compile(r"(?i)\b(?:authoritative|authority[-_ ]level)\b")),
    ("governance_approved", re.compile(r"(?i)\bgovernance[-_ ]approved\b")),
    ("production_ready", re.compile(r"(?i)\bproduction[-_ ]ready\b")),
    ("residual_risk_accepted", re.compile(r"(?i)\bresidual[-_ ]risk[-_ ]accepted\b")),
    ("risk_tier", re.compile(r"(?i)\brisk[-_ ]tier\b")),
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


@dataclass(frozen=True, slots=True)
class RiskAuthorityValidation:
    """Canonical validation result for coerced authority metadata."""

    contract: RiskAuthorityContract
    expected_contract: RiskAuthorityContract

    @property
    def platform_consistent(self) -> bool:
        """Whether metadata matches the platform-owned risk classification."""

        return (
            self.contract.risk_tier is self.expected_contract.risk_tier
            and self.contract.gate_profile is self.expected_contract.gate_profile
        )

    @property
    def selected_profile(self) -> RiskAuthorityDecisionProfile:
        """Profile requested by the supplied metadata."""

        return risk_authority_decision_profile_for_tier(self.contract.risk_tier)

    @property
    def expected_profile(self) -> RiskAuthorityDecisionProfile:
        """Profile required by the platform-owned classification."""

        return risk_authority_decision_profile_for_tier(
            self.expected_contract.risk_tier,
        )


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

    return risk_authority_decision_profile_for_tier(risk_tier).gate_profile


def risk_authority_decision_profile_for_tier(
    risk_tier: RiskTier,
) -> RiskAuthorityDecisionProfile:
    """Return the canonical decision requirements for a risk tier."""

    return _DECISION_PROFILE_BY_TIER[risk_tier]


def model_authority_claim_keys_from_text(
    text: str,
    *,
    extra_patterns: Sequence[AuthorityClaimPattern] = (),
) -> tuple[str, ...]:
    """Detect model-text claims that must not self-promote output authority."""

    return tuple(
        claim_key
        for claim_key, pattern in (*_MODEL_AUTHORITY_CLAIM_PATTERNS, *extra_patterns)
        if pattern.search(text)
    )


def risk_authority_contract_from_metadata(
    raw_authority_metadata: Mapping[str, object],
) -> RiskAuthorityContract:
    """Deserialize stable authority metadata into the canonical typed contract."""

    ignored_claims = _optional_string_tuple(
        raw_authority_metadata,
        "ignored_model_authority_claims",
    )
    try:
        return RiskAuthorityContract(
            risk_tier=_required_enum(
                raw_authority_metadata,
                "risk_tier",
                RiskTier,
            ),
            authority_effect=_required_enum(
                raw_authority_metadata,
                "authority_effect",
                AuthorityEffect,
            ),
            content_type=_required_enum(
                raw_authority_metadata,
                "content_type",
                AiOutputContentType,
            ),
            canonical_owner=_required_enum(
                raw_authority_metadata,
                "canonical_owner",
                CanonicalOwner,
            ),
            source_of_truth=_required_enum(
                raw_authority_metadata,
                "source_of_truth",
                SourceOfTruthCategory,
            ),
            intended_sink=_required_enum(
                raw_authority_metadata,
                "intended_sink",
                IntendedSink,
            ),
            gate_profile=_required_enum(
                raw_authority_metadata,
                "gate_profile",
                GateProfile,
            ),
            capital_relevant=_required_bool(
                raw_authority_metadata,
                "capital_relevant",
            ),
            durable_authority=_required_bool(
                raw_authority_metadata,
                "durable_authority",
            ),
            externally_visible=_required_bool(
                raw_authority_metadata,
                "externally_visible",
            ),
            governance_impact=_required_bool(
                raw_authority_metadata,
                "governance_impact",
            ),
            evidence_sufficient=_required_bool(
                raw_authority_metadata,
                "evidence_sufficient",
            ),
            ignored_model_authority_claims=ignored_claims,
        )
    except KeyError as exc:
        raise ValueError("risk_authority field is invalid.") from exc


def coerce_risk_authority_contract(
    raw_authority_metadata: object,
) -> RiskAuthorityContract:
    """Coerce boundary metadata or an existing contract into the typed contract."""

    if isinstance(raw_authority_metadata, RiskAuthorityContract):
        return raw_authority_metadata
    if not isinstance(raw_authority_metadata, Mapping):
        raise ValueError("risk_authority must be a metadata object.")
    return risk_authority_contract_from_metadata(
        cast(Mapping[str, object], raw_authority_metadata),
    )


def validate_risk_authority_metadata(
    raw_authority_metadata: object,
) -> RiskAuthorityValidation:
    """Coerce metadata and recompute the platform-owned authority profile."""

    contract = coerce_risk_authority_contract(raw_authority_metadata)
    return RiskAuthorityValidation(
        contract=contract,
        expected_contract=reclassify_risk_authority_contract(contract),
    )


def reclassify_risk_authority_contract(
    contract: RiskAuthorityContract,
) -> RiskAuthorityContract:
    """Recompute tier and gate from immutable contract attributes."""

    return classify_risk_authority(
        RiskAuthorityClassificationInput(
            content_type=contract.content_type,
            authority_effect=contract.authority_effect,
            canonical_owner=contract.canonical_owner,
            source_of_truth=contract.source_of_truth,
            intended_sink=contract.intended_sink,
            capital_relevant=contract.capital_relevant,
            durable_authority=contract.durable_authority,
            externally_visible=contract.externally_visible,
            governance_impact=contract.governance_impact,
            evidence_sufficient=contract.evidence_sufficient,
        )
    )


def _required_enum[TEnum: Enum](
    metadata: Mapping[str, object],
    key: str,
    enum_type: type[TEnum],
) -> TEnum:
    value = _required_value(
        metadata,
        key,
    )
    if isinstance(
        value,
        enum_type,
    ):
        return value
    if isinstance(value, str):
        cleaned_value = value.strip().lower()
        try:
            return enum_type(cleaned_value)
        except ValueError as exc:
            raise ValueError(
                f"risk_authority.{key} has unsupported value {value!r}.",
            ) from exc
    raise ValueError(f"risk_authority.{key} must be a string.")


def _required_bool(
    metadata: Mapping[str, object],
    key: str,
) -> bool:
    value = _required_value(
        metadata,
        key,
    )
    if not isinstance(value, bool):
        raise ValueError(f"risk_authority.{key} must be a boolean.")
    return value


def _optional_string_tuple(
    metadata: Mapping[str, object],
    key: str,
) -> tuple[str, ...]:
    value = metadata.get(
        key,
        (),
    )
    if not isinstance(
        value,
        Sequence,
    ) or isinstance(
        value,
        str,
    ):
        raise ValueError(f"risk_authority.{key} must be a list of strings.")
    values = tuple(value)
    if not all(isinstance(item, str) for item in values):
        raise ValueError(f"risk_authority.{key} must be a list of strings.")
    return values


def _required_value(
    metadata: Mapping[str, object],
    key: str,
) -> object:
    if key not in metadata:
        raise ValueError(f"risk_authority.{key} is required.")
    return metadata[key]


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
