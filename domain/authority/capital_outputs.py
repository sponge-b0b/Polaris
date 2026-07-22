from __future__ import annotations

from collections.abc import Mapping
from typing import Final, cast

from domain.authority.contracts import (
    AiOutputContentType,
    AuthorityEffect,
    CanonicalOwner,
    IntendedSink,
    RiskAuthorityClassificationInput,
    RiskAuthorityContract,
    SourceOfTruthCategory,
    classify_risk_authority,
)

RISK_AUTHORITY_METADATA_KEY: Final = "risk_authority"

type JsonScalar = str | int | float | bool | None
type JsonValue = (
    JsonScalar | Mapping[str, JsonValue] | tuple[JsonValue, ...] | list[JsonValue]
)


def authority_contract_metadata(
    contract: RiskAuthorityContract,
) -> dict[str, JsonValue]:
    """Wrap a classified authority contract under the canonical metadata key."""

    return {RISK_AUTHORITY_METADATA_KEY: cast(JsonValue, contract.to_metadata())}


def model_authority_claims_from_payloads(
    *payloads: Mapping[str, object],
) -> dict[str, object]:
    """Collect model-provided authority claims for deterministic ignore auditing.

    Model outputs are allowed to contain advisory narration, but they may not declare
    risk tiers, governance approval, residual-risk acceptance, or readiness. The
    classifier remains platform-owned; this helper only exposes those claims so the
    resulting contract can record which model claims were ignored.
    """

    claims: dict[str, object] = {}
    for payload in payloads:
        _collect_model_authority_claims(payload, claims)
    return claims


def trade_recommendation_runtime_authority(
    model_provided_metadata: Mapping[str, object] | None = None,
) -> RiskAuthorityContract:
    """Classify trade proposal runtime evidence before curation/persistence."""

    return _capital_runtime_authority(
        content_type=AiOutputContentType.RUNTIME_EVIDENCE,
        model_provided_metadata=model_provided_metadata,
    )


def portfolio_allocation_intent_runtime_authority(
    model_provided_metadata: Mapping[str, object] | None = None,
) -> RiskAuthorityContract:
    """Classify allocation-intent runtime evidence before curation/persistence."""

    return _capital_runtime_authority(
        content_type=AiOutputContentType.RUNTIME_EVIDENCE,
        model_provided_metadata=model_provided_metadata,
    )


def strategy_synthesis_runtime_authority(
    model_provided_metadata: Mapping[str, object] | None = None,
) -> RiskAuthorityContract:
    """Classify strategy synthesis runtime evidence before curation/persistence."""

    return _capital_runtime_authority(
        content_type=AiOutputContentType.STRATEGY_SYNTHESIS,
        model_provided_metadata=model_provided_metadata,
    )


def recommendation_record_authority(
    model_provided_metadata: Mapping[str, object] | None = None,
) -> RiskAuthorityContract:
    """Classify a durable recommendation record at the persistence boundary."""

    return classify_risk_authority(
        RiskAuthorityClassificationInput(
            content_type=AiOutputContentType.DURABLE_RECORD,
            authority_effect=AuthorityEffect.CANONICAL_RECORD,
            canonical_owner=CanonicalOwner.RECOMMENDATION_SERVICE,
            source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
            intended_sink=IntendedSink.RECOMMENDATION,
            capital_relevant=True,
            durable_authority=True,
            evidence_sufficient=True,
            model_provided_metadata=model_provided_metadata or {},
        )
    )


def recommendation_rationale_authority(
    model_provided_metadata: Mapping[str, object] | None = None,
) -> RiskAuthorityContract:
    """Classify advisory recommendation narration at the persistence boundary."""

    return classify_risk_authority(
        RiskAuthorityClassificationInput(
            content_type=AiOutputContentType.RECOMMENDATION_EXPLANATION,
            authority_effect=AuthorityEffect.ADVISORY_CONTEXT,
            canonical_owner=CanonicalOwner.RECOMMENDATION_SERVICE,
            source_of_truth=SourceOfTruthCategory.DERIVED_PROJECTION,
            intended_sink=IntendedSink.RECOMMENDATION,
            capital_relevant=True,
            durable_authority=False,
            evidence_sufficient=True,
            model_provided_metadata=model_provided_metadata or {},
        )
    )


def strategy_synthesis_decision_authority(
    model_provided_metadata: Mapping[str, object] | None = None,
) -> RiskAuthorityContract:
    """Classify a durable strategy synthesis decision record."""

    return classify_risk_authority(
        RiskAuthorityClassificationInput(
            content_type=AiOutputContentType.STRATEGY_SYNTHESIS,
            authority_effect=AuthorityEffect.DETERMINISTIC_PLATFORM_DECISION,
            canonical_owner=CanonicalOwner.STRATEGY_SERVICE,
            source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
            intended_sink=IntendedSink.DURABLE_DOMAIN_RECORD,
            capital_relevant=True,
            durable_authority=True,
            evidence_sufficient=True,
            model_provided_metadata=model_provided_metadata or {},
        )
    )


def strategy_recommendation_record_authority(
    model_provided_metadata: Mapping[str, object] | None = None,
) -> RiskAuthorityContract:
    """Classify a recommendation derived from strategy synthesis."""

    return recommendation_record_authority(model_provided_metadata)


def strategy_recommendation_rationale_authority(
    model_provided_metadata: Mapping[str, object] | None = None,
) -> RiskAuthorityContract:
    """Classify advisory strategy recommendation narration."""

    return recommendation_rationale_authority(model_provided_metadata)


def _capital_runtime_authority(
    *,
    content_type: AiOutputContentType,
    model_provided_metadata: Mapping[str, object] | None,
) -> RiskAuthorityContract:
    return classify_risk_authority(
        RiskAuthorityClassificationInput(
            content_type=content_type,
            authority_effect=AuthorityEffect.DETERMINISTIC_PLATFORM_DECISION,
            canonical_owner=CanonicalOwner.WORKFLOW_OUTPUT_CURATION,
            source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
            intended_sink=IntendedSink.DURABLE_DOMAIN_RECORD,
            capital_relevant=True,
            durable_authority=True,
            evidence_sufficient=True,
            model_provided_metadata=model_provided_metadata or {},
        )
    )


def _collect_model_authority_claims(
    payload: Mapping[str, object],
    claims: dict[str, object],
) -> None:
    for key, value in payload.items():
        text_key = str(key)
        claims[text_key] = value
        if isinstance(value, Mapping):
            nested_payload = {
                str(nested_key): nested_value
                for nested_key, nested_value in value.items()
            }
            _collect_model_authority_claims(nested_payload, claims)
