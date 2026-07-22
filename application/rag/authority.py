from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import replace
from enum import StrEnum
from typing import Final, cast

from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from application.rag.security.rag_security import safe_grounding_failure_answer
from core.storage.persistence.rag import JsonObject
from domain.authority import (
    RISK_AUTHORITY_METADATA_KEY,
    AiOutputContentType,
    AuthorityEffect,
    CanonicalOwner,
    IntendedSink,
    RiskAuthorityClassificationInput,
    SourceOfTruthCategory,
    authority_contract_metadata,
    classify_risk_authority,
    model_authority_claims_from_payloads,
)

RAG_AUTHORITY_REQUEST_METADATA_KEY: Final = "rag_authority"
RAG_AUTHORITY_FAILURE_MODE_METADATA_KEY: Final = "rag_authority_failure_mode"
RAG_AUTHORITY_FAIL_CLOSED_METADATA_KEY: Final = "rag_authority_fail_closed"
RAG_ANSWER_BOUNDARY_METADATA_KEY: Final = "rag_answer_boundary"
RETRIEVED_EVIDENCE_BOUNDARY_METADATA_KEY: Final = "retrieved_evidence_boundary"
RAG_AUTHORITY_EVIDENCE_METADATA_KEY: Final = "rag_authority_evidence"

_RAG_ANSWER_BOUNDARY: Final = "presentation_output_not_durable_financial_advice"
_RETRIEVED_EVIDENCE_BOUNDARY: Final = (
    "retrieved_context_is_runtime_evidence_not_canonical_domain_record"
)
_AUTHORITY_METADATA_KEYS: Final[frozenset[str]] = frozenset(
    {
        RISK_AUTHORITY_METADATA_KEY,
        RAG_AUTHORITY_FAILURE_MODE_METADATA_KEY,
        RAG_AUTHORITY_FAIL_CLOSED_METADATA_KEY,
        RAG_ANSWER_BOUNDARY_METADATA_KEY,
        RETRIEVED_EVIDENCE_BOUNDARY_METADATA_KEY,
        RAG_AUTHORITY_EVIDENCE_METADATA_KEY,
    }
)
_EXTERNAL_AUDIENCES: Final[frozenset[str]] = frozenset(
    {"client", "customer", "external", "mcp", "partner", "public", "tool"}
)
_STALE_OR_SUBSTITUTED_FLAGS: Final[frozenset[str]] = frozenset(
    {
        "evidence_stale",
        "evidence_substituted",
        "retrieval_substituted",
        "source_stale",
        "source_substituted",
        "stale",
        "stale_evidence",
        "substituted_evidence",
    }
)
_CITATION_TOKEN = re.compile(r"\[([A-Za-z0-9][A-Za-z0-9_-]*)\]")
_AUTHORITY_CLAIM_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("authority_effect", re.compile(r"(?i)\bauthority[-_ ]effect\b")),
    ("authority_level", re.compile(r"(?i)\b(?:authoritative|authority[-_ ]level)\b")),
    ("governance_approved", re.compile(r"(?i)\bgovernance[-_ ]approved\b")),
    ("production_ready", re.compile(r"(?i)\bproduction[-_ ]ready\b")),
    ("residual_risk_accepted", re.compile(r"(?i)\bresidual[-_ ]risk[-_ ]accepted\b")),
    ("risk_tier", re.compile(r"(?i)\brisk[-_ ]tier\b")),
)


class RagAuthorityFailureMode(StrEnum):
    """Platform-owned failure modes for classified RAG answer boundaries."""

    NONE = "none"
    UNSUPPORTED_EVIDENCE = "unsupported_evidence"
    CITATION_SPOOFING = "citation_spoofing"
    STALE_OR_SUBSTITUTED_EVIDENCE = "stale_or_substituted_evidence"
    MODEL_AUTHORITY_CLAIM = "model_authority_claim"
    OUTSIDE_AUTHORITY = "outside_authority"


def classify_rag_result_authority(
    *,
    request: RagRequest,
    result: RagResult,
) -> RagResult:
    """Attach canonical authority metadata and fail closed on unsafe RAG answers."""

    authority_request = _authority_request_metadata(request)
    intended_sink = _enum_from_metadata(
        authority_request,
        "intended_sink",
        IntendedSink,
        IntendedSink.RAG_ANSWER,
    )
    authority_effect = _enum_from_metadata(
        authority_request,
        "authority_effect",
        AuthorityEffect,
        AuthorityEffect.NON_AUTHORITATIVE_INFORMATION,
    )
    source_of_truth = _enum_from_metadata(
        authority_request,
        "source_of_truth",
        SourceOfTruthCategory,
        SourceOfTruthCategory.PRESENTATION_OUTPUT,
    )

    external = _externally_visible(authority_request, intended_sink)
    capital_relevant = _bool_metadata(authority_request, "capital_relevant", False)
    durable_authority = _durable_authority(
        authority_request,
        intended_sink,
        authority_effect,
    )
    governance_impact = _bool_metadata(authority_request, "governance_impact", False)

    existing_failure_mode = _existing_failure_mode(result.metadata)
    original_metadata = _strip_authority_metadata(result.metadata)
    answer_authority_claims = _authority_claims_from_answer_text(result.answer_text)
    provider_authority_claims = _provider_authority_claims(original_metadata)
    model_authority_claims = {
        **provider_authority_claims,
        **{claim: True for claim in answer_authority_claims},
    }

    failure_mode = existing_failure_mode or _failure_mode(
        result=result,
        allowed_citation_ids=_allowed_citation_ids(result),
        answer_authority_claims=answer_authority_claims,
        authority_effect=authority_effect,
    )
    evidence_sufficient = _evidence_sufficient(result, failure_mode)

    contract = classify_risk_authority(
        RiskAuthorityClassificationInput(
            content_type=AiOutputContentType.RAG_ANSWER,
            authority_effect=authority_effect,
            canonical_owner=CanonicalOwner.RAG_SERVICE,
            source_of_truth=source_of_truth,
            intended_sink=intended_sink,
            capital_relevant=capital_relevant,
            durable_authority=durable_authority,
            externally_visible=external,
            governance_impact=governance_impact,
            evidence_sufficient=evidence_sufficient,
            model_provided_metadata=model_authority_claims,
        )
    )
    metadata = _authority_metadata(
        base_metadata=original_metadata,
        contract_metadata=authority_contract_metadata(contract),
        failure_mode=failure_mode,
        result=result,
    )

    if _should_fail_closed(result, failure_mode):
        return replace(
            result,
            answer_text=safe_grounding_failure_answer(),
            status="no_results",
            citations=(),
            confidence_score=None,
            error=None,
            metadata=metadata,
        )
    return replace(result, metadata=metadata)


def _authority_request_metadata(request: RagRequest) -> Mapping[str, object]:
    metadata = request.metadata.get(RAG_AUTHORITY_REQUEST_METADATA_KEY)
    if isinstance(metadata, Mapping):
        return {str(key): value for key, value in metadata.items()}
    return {}


def _strip_authority_metadata(metadata: JsonObject) -> JsonObject:
    return {
        key: value
        for key, value in metadata.items()
        if key not in _AUTHORITY_METADATA_KEYS
    }


def _existing_failure_mode(metadata: JsonObject) -> RagAuthorityFailureMode | None:
    value = metadata.get(RAG_AUTHORITY_FAILURE_MODE_METADATA_KEY)
    if not isinstance(value, str):
        return None
    try:
        failure_mode = RagAuthorityFailureMode(value)
    except ValueError:
        return None
    if failure_mode is RagAuthorityFailureMode.NONE:
        return None
    return failure_mode


def _enum_from_metadata[T: StrEnum](
    metadata: Mapping[str, object],
    key: str,
    enum_type: type[T],
    default: T,
) -> T:
    value = metadata.get(key)
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        try:
            return enum_type(value.strip())
        except ValueError:
            return default
    return default


def _externally_visible(
    metadata: Mapping[str, object],
    intended_sink: IntendedSink,
) -> bool:
    if _bool_metadata(metadata, "externally_visible", False):
        return True
    audience = metadata.get("audience")
    if isinstance(audience, str) and audience.strip().lower() in _EXTERNAL_AUDIENCES:
        return True
    return intended_sink is IntendedSink.MCP_TOOL_RESPONSE and _bool_metadata(
        metadata, "tool_response_external", False
    )


def _durable_authority(
    metadata: Mapping[str, object],
    intended_sink: IntendedSink,
    authority_effect: AuthorityEffect,
) -> bool:
    if _bool_metadata(metadata, "durable_authority", False):
        return True
    if intended_sink is IntendedSink.DURABLE_DOMAIN_RECORD:
        return True
    return authority_effect in {
        AuthorityEffect.CANONICAL_RECORD,
        AuthorityEffect.DETERMINISTIC_PLATFORM_DECISION,
        AuthorityEffect.GOVERNANCE_DECISION,
        AuthorityEffect.EXECUTION_DECISION,
    }


def _bool_metadata(
    metadata: Mapping[str, object],
    key: str,
    default: bool,
) -> bool:
    value = metadata.get(key)
    if isinstance(value, bool):
        return value
    return default


def _failure_mode(
    *,
    result: RagResult,
    allowed_citation_ids: tuple[str, ...],
    answer_authority_claims: tuple[str, ...],
    authority_effect: AuthorityEffect,
) -> RagAuthorityFailureMode:
    if authority_effect is AuthorityEffect.OUTSIDE_AUTHORITY:
        return RagAuthorityFailureMode.OUTSIDE_AUTHORITY
    if result.status != "answered":
        return RagAuthorityFailureMode.UNSUPPORTED_EVIDENCE
    if _has_stale_or_substituted_evidence(result.contexts):
        return RagAuthorityFailureMode.STALE_OR_SUBSTITUTED_EVIDENCE
    if _spoofed_citation_ids(result.answer_text, allowed_citation_ids):
        return RagAuthorityFailureMode.CITATION_SPOOFING
    if answer_authority_claims:
        return RagAuthorityFailureMode.MODEL_AUTHORITY_CLAIM
    return RagAuthorityFailureMode.NONE


def _evidence_sufficient(
    result: RagResult,
    failure_mode: RagAuthorityFailureMode,
) -> bool:
    return (
        result.status == "answered"
        and bool(result.citations)
        and failure_mode is RagAuthorityFailureMode.NONE
    )


def _should_fail_closed(
    result: RagResult,
    failure_mode: RagAuthorityFailureMode,
) -> bool:
    return (
        result.status == "answered" and failure_mode is not RagAuthorityFailureMode.NONE
    )


def _allowed_citation_ids(result: RagResult) -> tuple[str, ...]:
    citation_ids = result.metadata.get("citation_ids")
    if isinstance(citation_ids, Sequence) and not isinstance(
        citation_ids, (str, bytes, bytearray)
    ):
        cleaned = tuple(str(citation_id) for citation_id in citation_ids if citation_id)
        if cleaned:
            return cleaned
    return tuple(f"C{index}" for index, _ in enumerate(result.contexts, start=1))


def _spoofed_citation_ids(
    answer_text: str,
    allowed_citation_ids: tuple[str, ...],
) -> tuple[str, ...]:
    if not allowed_citation_ids:
        return ()
    allowed = set(allowed_citation_ids)
    return tuple(
        dict.fromkeys(
            citation_id
            for citation_id in _CITATION_TOKEN.findall(answer_text)
            if citation_id not in allowed
        )
    )


def _has_stale_or_substituted_evidence(
    contexts: tuple[RagRetrievedContext, ...],
) -> bool:
    return any(
        _metadata_has_stale_or_substituted_flag(context.metadata)
        or _metadata_has_stale_or_substituted_flag(context.source.metadata)
        for context in contexts
    )


def _metadata_has_stale_or_substituted_flag(metadata: Mapping[str, object]) -> bool:
    for key, value in metadata.items():
        normalized_key = str(key).strip().lower()
        if normalized_key in _STALE_OR_SUBSTITUTED_FLAGS and value is not False:
            return True
        if normalized_key == "source_status" and isinstance(value, str):
            if value.strip().lower() in {"stale", "substituted"}:
                return True
    return False


def _authority_claims_from_answer_text(answer_text: str) -> tuple[str, ...]:
    return tuple(
        claim
        for claim, pattern in _AUTHORITY_CLAIM_PATTERNS
        if pattern.search(answer_text)
    )


def _provider_authority_claims(metadata: JsonObject) -> dict[str, object]:
    provider_metadata = metadata.get("provider_metadata")
    if not isinstance(provider_metadata, Mapping):
        return {}
    return model_authority_claims_from_payloads(provider_metadata)


def _authority_metadata(
    *,
    base_metadata: JsonObject,
    contract_metadata: Mapping[str, object],
    failure_mode: RagAuthorityFailureMode,
    result: RagResult,
) -> JsonObject:
    return cast(
        JsonObject,
        {
            **base_metadata,
            **contract_metadata,
            RAG_AUTHORITY_FAILURE_MODE_METADATA_KEY: failure_mode.value,
            RAG_AUTHORITY_FAIL_CLOSED_METADATA_KEY: (
                failure_mode is not RagAuthorityFailureMode.NONE
            ),
            RAG_ANSWER_BOUNDARY_METADATA_KEY: _RAG_ANSWER_BOUNDARY,
            RETRIEVED_EVIDENCE_BOUNDARY_METADATA_KEY: _RETRIEVED_EVIDENCE_BOUNDARY,
            RAG_AUTHORITY_EVIDENCE_METADATA_KEY: {
                "context_count": len(result.contexts),
                "citation_count": len(result.citations),
                "citation_ids": list(_allowed_citation_ids(result)),
            },
        },
    )
