"""Thin MCP boundary for canonical Polaris RAG readiness operations."""

from __future__ import annotations

import asyncio
import logging

from mcp.server.fastmcp.exceptions import ToolError

from application.rag.contracts.rag_operation_models import (
    RagCanonicalProjectionReadiness,
    RagGraphProjectionReadiness,
    RagProjectionReadinessResult,
    RagStatusOperationRequest,
    RagVectorProjectionReadiness,
)
from application.rag.contracts.rag_operation_models import (
    RagModelReadiness as DomainModelReadiness,
)
from application.rag.operations.rag_status_operations import RagStatusOperationsService
from mcp_server.contracts.models import (
    RagCanonicalReadiness,
    RagGraphReadiness,
    RagModelReadiness,
    RagStatusRequest,
    RagStatusResponse,
    RagVectorReadiness,
)
from mcp_server.lifespan import McpApplicationContext
from mcp_server.request_scope import mcp_dependency_scope
from mcp_server.telemetry import McpToolFailureCategory

logger = logging.getLogger(__name__)

_TOOL_NAME = "polaris_rag_status"
_SAFE_FAILURE_MESSAGE = "Polaris RAG status request failed."
_COMPONENT_ERRORS = {
    "canonical": "Canonical PostgreSQL readiness check failed.",
    "vector": "Vector projection readiness check failed.",
    "graph": "Graph projection readiness check failed.",
    "embedding": "Embedding model readiness check failed.",
    "reranker": "Reranker readiness check failed.",
}


async def execute_rag_status(
    request: RagStatusRequest,
    application_context: McpApplicationContext,
    *,
    request_id: str | None = None,
) -> RagStatusResponse:
    """Delegate one readiness request and serialize a safe typed response."""

    invocation = await application_context.telemetry.tool_started(
        tool_name=_TOOL_NAME,
        transport=application_context.settings.transport,
        request_id=request_id,
    )
    try:
        async with mcp_dependency_scope(
            application_context,
            RagStatusOperationsService,
        ) as service:
            result = await service.status(
                RagStatusOperationRequest(include_details=request.include_details)
            )
        response = _to_response(result, include_details=request.include_details)
    except asyncio.CancelledError as exc:
        await application_context.telemetry.tool_failed(
            invocation,
            failure_category=McpToolFailureCategory.CANCELLED,
            error=exc,
        )
        raise
    except Exception as exc:
        await application_context.telemetry.tool_failed(
            invocation,
            failure_category=McpToolFailureCategory.APPLICATION,
            error=exc,
        )
        logger.error(
            "MCP RAG status request failed.",
            extra={
                "request_id": invocation.request_id,
                "error_type": type(exc).__name__,
            },
        )
        raise ToolError(_SAFE_FAILURE_MESSAGE) from exc

    await application_context.telemetry.tool_completed(
        invocation,
        result_status=result.status,
    )
    return response


def _to_response(
    result: RagProjectionReadinessResult,
    *,
    include_details: bool,
) -> RagStatusResponse:
    if not include_details:
        return RagStatusResponse(
            status=result.status,
            message=result.message,
            ready=result.ready,
        )

    return RagStatusResponse(
        status=result.status,
        message=result.message,
        ready=result.ready,
        canonical=_canonical_readiness(result.canonical),
        vector=_vector_readiness(result.vector),
        graph=_graph_readiness(result.graph),
        embedding=_model_readiness(result.embedding),
        reranker=_model_readiness(result.reranker),
    )


def _canonical_readiness(
    readiness: RagCanonicalProjectionReadiness,
) -> RagCanonicalReadiness:
    return RagCanonicalReadiness(
        available=readiness.available,
        document_count=readiness.document_count,
        chunk_count=readiness.chunk_count,
        embedding_job_count=readiness.embedding_job_count,
        graph_job_count=readiness.graph_job_count,
        pending_embedding_jobs=readiness.pending_embedding_jobs,
        retryable_embedding_jobs=readiness.retryable_embedding_jobs,
        failed_embedding_jobs=readiness.failed_embedding_jobs,
        error=_safe_component_error("canonical", readiness.error),
    )


def _vector_readiness(readiness: RagVectorProjectionReadiness) -> RagVectorReadiness:
    return RagVectorReadiness(
        collection_name=readiness.collection_name,
        exists=readiness.exists,
        healthy=readiness.healthy,
        dense_vector_present=readiness.dense_vector_present,
        sparse_vector_present=readiness.sparse_vector_present,
        configured_vector_size=readiness.configured_vector_size,
        actual_vector_size=readiness.actual_vector_size,
        vector_size_compatible=readiness.vector_size_compatible,
        points_count=readiness.points_count,
        status=readiness.status,
        error=_safe_component_error("vector", readiness.error),
    )


def _graph_readiness(readiness: RagGraphProjectionReadiness) -> RagGraphReadiness:
    return RagGraphReadiness(
        connected=readiness.connected,
        healthy=readiness.healthy,
        entity_count=readiness.entity_count,
        error=_safe_component_error("graph", readiness.error),
    )


def _model_readiness(readiness: DomainModelReadiness) -> RagModelReadiness:
    return RagModelReadiness(
        component=readiness.component,
        model=readiness.model,
        ready=readiness.ready,
        dimensions=readiness.dimensions,
        error=_safe_component_error(readiness.component, readiness.error),
    )


def _safe_component_error(component: str, error: str | None) -> str | None:
    if error is None:
        return None
    return _COMPONENT_ERRORS.get(component, "RAG dependency readiness check failed.")


__all__ = ["execute_rag_status"]
