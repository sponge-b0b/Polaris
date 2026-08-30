"""Thin MCP boundary for the canonical Polaris RAG application service."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import cast

from mcp.server.fastmcp.exceptions import ToolError
from pydantic import JsonValue

from application.presentation.evidence import (
    PRESENTATION_SINK_DISPOSITION_METADATA_KEY,
    PRESENTATION_SINK_LIMITATIONS_METADATA_KEY,
    PRESENTATION_SINK_MAY_PRESENT_METADATA_KEY,
)
from application.presentation.sink_decision import PresentationSinkDisposition
from application.rag.contracts.rag_context import RagRetrievalFilters, RagSource
from application.rag.contracts.rag_context import (
    RagRetrievedContext as DomainRagRetrievedContext,
)
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from application.rag.rag_service import RagService
from domain.authority import RISK_AUTHORITY_METADATA_KEY
from mcp_server.contracts.models import (
    RagAskRequest,
    RagAskResponse,
    RagCitation,
    RagReflectionScores,
    RagRetrievedContext,
)
from mcp_server.lifespan import McpApplicationContext
from mcp_server.request_scope import mcp_dependency_scope
from mcp_server.telemetry import McpToolFailureCategory

logger = logging.getLogger(__name__)

_TOOL_NAME = "polaris_rag_ask"
_SAFE_FAILURE_MESSAGE = "Polaris RAG request failed."
_SAFE_PRESENTATION_MESSAGE = (
    "Polaris RAG response is unavailable for external presentation."
)


class McpRagPolicyError(ValueError):
    """Safe validation failure raised by the MCP RAG boundary."""


async def execute_rag_ask(
    request: RagAskRequest,
    application_context: McpApplicationContext,
    *,
    request_id: str | None = None,
) -> RagAskResponse:
    """Validate, delegate, and serialize one canonical RAG request."""

    invocation = await application_context.telemetry.tool_started(
        tool_name=_TOOL_NAME,
        transport=application_context.settings.transport,
        request_id=request_id,
        top_k=request.top_k,
    )
    try:
        _validate_request_policy(request, application_context)
        rag_request = _to_rag_request(request, request_id=invocation.request_id)
        async with mcp_dependency_scope(application_context, RagService) as service:
            result = await service.run(rag_request)
        response = _to_response(result, include_contexts=request.include_contexts)
    except asyncio.CancelledError as exc:
        await application_context.telemetry.tool_failed(
            invocation,
            failure_category=McpToolFailureCategory.CANCELLED,
            error=exc,
        )
        raise
    except McpRagPolicyError as exc:
        await application_context.telemetry.tool_failed(
            invocation,
            failure_category=McpToolFailureCategory.VALIDATION,
            error=exc,
        )
        logger.warning(
            "MCP RAG request rejected by boundary policy.",
            extra={"request_id": invocation.request_id},
        )
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        await application_context.telemetry.tool_failed(
            invocation,
            failure_category=McpToolFailureCategory.APPLICATION,
            error=exc,
        )
        logger.error(
            "MCP RAG request failed.",
            extra={
                "request_id": invocation.request_id,
                "error_type": type(exc).__name__,
            },
        )
        raise ToolError(_SAFE_FAILURE_MESSAGE) from exc

    await application_context.telemetry.tool_completed(
        invocation,
        result_status=response.status,
    )
    return response


def _validate_request_policy(
    request: RagAskRequest,
    application_context: McpApplicationContext,
) -> None:
    settings = application_context.settings
    if len(request.query) > settings.max_query_characters:
        raise McpRagPolicyError(
            f"query cannot exceed {settings.max_query_characters} characters.",
        )
    if request.top_k > settings.max_top_k:
        raise McpRagPolicyError(f"top_k cannot exceed {settings.max_top_k}.")
    if request.allow_web and not settings.allow_web:
        raise McpRagPolicyError("Web retrieval is disabled for this MCP server.")


def _to_rag_request(request: RagAskRequest, *, request_id: str) -> RagRequest:
    return RagRequest(
        query=request.query,
        filters=RagRetrievalFilters(
            source_tables=request.source_tables,
            source_types=request.source_types,
            symbols=request.symbols,
            workflow_name=request.workflow_name,
            execution_id=request.execution_id,
            runtime_id=request.runtime_id,
            agent_names=request.agent_names,
            agent_types=request.agent_types,
            report_types=request.report_types,
            regimes=request.regimes,
            as_of_start=request.as_of_start,
            as_of_end=request.as_of_end,
        ),
        route="hybrid",
        top_k=request.top_k,
        allow_web=request.allow_web,
        requester="polaris_mcp",
        metadata={
            "source": "polaris_mcp",
            "tool": _TOOL_NAME,
        },
        request_id=request_id,
    )


_PresentationState = tuple[
    PresentationSinkDisposition,
    bool,
    tuple[str, ...],
]


def _to_response(result: RagResult, *, include_contexts: bool) -> RagAskResponse:
    presentation = _presentation_state(result.metadata)

    if result.status == "failed":
        return _response_from_result(
            result,
            include_contexts=False,
            presentation=presentation,
            answer_text=_SAFE_FAILURE_MESSAGE,
            status="failed",
            error=_SAFE_FAILURE_MESSAGE,
            include_claim_content=False,
        )

    if result.status == "answered":
        if presentation is None:
            return _response_from_result(
                result,
                include_contexts=False,
                presentation=None,
                answer_text=_SAFE_PRESENTATION_MESSAGE,
                status="failed",
                error=_SAFE_PRESENTATION_MESSAGE,
                include_claim_content=False,
            )

        disposition, may_present, _ = presentation
        if not may_present or disposition not in {
            PresentationSinkDisposition.ELIGIBLE,
            PresentationSinkDisposition.DEGRADED,
        }:
            return _response_from_result(
                result,
                include_contexts=False,
                presentation=presentation,
                answer_text=_SAFE_PRESENTATION_MESSAGE,
                status="no_results",
                error=None,
                include_claim_content=False,
            )

    return _response_from_result(
        result,
        include_contexts=include_contexts,
        presentation=presentation,
        answer_text=result.answer_text,
        status=result.status,
        error=result.error,
        include_claim_content=True,
    )


def _response_from_result(
    result: RagResult,
    *,
    include_contexts: bool,
    presentation: _PresentationState | None,
    answer_text: str,
    status: str,
    error: str | None,
    include_claim_content: bool,
) -> RagAskResponse:
    disposition = presentation[0].value if presentation is not None else None
    may_present = presentation[1] if presentation is not None else None
    limitations = presentation[2] if presentation is not None else ()

    return RagAskResponse(
        query_id=result.query_id,
        answer_text=answer_text,
        status=status,
        route=result.route,
        authority_metadata=_risk_authority_metadata(result.metadata),
        presentation_disposition=disposition,
        presentation_may_present=may_present,
        presentation_limitations=limitations,
        citations=(
            tuple(_to_citation(source) for source in result.citations)
            if include_claim_content
            else ()
        ),
        contexts=(
            tuple(_to_context(context) for context in result.contexts)
            if include_claim_content and include_contexts
            else None
        ),
        confidence_score=(result.confidence_score if include_claim_content else None),
        grounding_score=(result.grounding_score if include_claim_content else None),
        utility_score=result.utility_score if include_claim_content else None,
        injection_detected=result.injection_detected,
        reflection_scores=(
            None
            if not include_claim_content or result.reflection_scores is None
            else RagReflectionScores(
                retrieval_necessity=result.reflection_scores.retrieval_necessity,
                source_relevance=result.reflection_scores.source_relevance,
                answer_support=result.reflection_scores.answer_support,
                usefulness=result.reflection_scores.usefulness,
            )
        ),
        corrective_actions=(
            tuple(action.value for action in result.corrective_actions)
            if include_claim_content
            else ()
        ),
        error=error,
        generated_at=result.generated_at,
    )


def _presentation_state(
    metadata: Mapping[str, object],
) -> _PresentationState | None:
    raw_disposition = metadata.get(PRESENTATION_SINK_DISPOSITION_METADATA_KEY)
    raw_may_present = metadata.get(PRESENTATION_SINK_MAY_PRESENT_METADATA_KEY)
    raw_limitations = metadata.get(
        PRESENTATION_SINK_LIMITATIONS_METADATA_KEY,
        (),
    )

    if not isinstance(raw_disposition, str):
        return None
    if not isinstance(raw_may_present, bool):
        return None
    if not isinstance(raw_limitations, Sequence) or isinstance(
        raw_limitations,
        str | bytes | bytearray,
    ):
        return None
    if any(not isinstance(item, str) or not item.strip() for item in raw_limitations):
        return None

    try:
        disposition = PresentationSinkDisposition(raw_disposition)
    except ValueError:
        return None

    return (
        disposition,
        raw_may_present,
        tuple(cast(str, item) for item in raw_limitations),
    )


def _to_citation(source: RagSource) -> RagCitation:
    return RagCitation(
        source_table=source.source_table,
        source_id=source.source_id,
        source_type=source.source_type,
        document_id=source.document_id,
        title=source.title,
        chunk_id=source.chunk_id,
        section_name=source.section_name,
        generated_at=source.generated_at,
        workflow_name=source.workflow_name,
        execution_id=source.execution_id,
        metadata=_boundary_metadata(source.metadata),
    )


def _to_context(context: DomainRagRetrievedContext) -> RagRetrievedContext:
    return RagRetrievedContext(
        context_id=context.context_id,
        text=context.text,
        source=_to_citation(context.source),
        score=context.score,
        rank=context.rank,
        retrieval_route=context.retrieval_route,
        metadata=_boundary_metadata(context.metadata),
    )


def _risk_authority_metadata(
    metadata: Mapping[str, object],
) -> dict[str, JsonValue]:
    authority_metadata = metadata.get(RISK_AUTHORITY_METADATA_KEY)
    if not isinstance(authority_metadata, Mapping):
        return {}
    return _boundary_metadata(authority_metadata)


def _boundary_metadata(
    metadata: Mapping[str, object],
) -> dict[str, JsonValue]:
    return cast(dict[str, JsonValue], deepcopy(dict(metadata)))


__all__ = ["execute_rag_ask"]
