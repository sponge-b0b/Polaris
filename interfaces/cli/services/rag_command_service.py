from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from application.rag.contracts.rag_context import RagRetrievalFilters, RagSource
from application.rag.contracts.rag_operation_models import (
    RagIngestOperationRequest,
    RagOperationResult,
    RagProcessEmbeddingsOperationRequest,
    RagProcessGraphOperationRequest,
    RagProjectionReadinessResult,
    RagRebuildProjectionOperationRequest,
    RagStatusOperationRequest,
)
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from application.rag.operations.rag_embedding_operations import (
    RagEmbeddingJobOperationsService,
)
from application.rag.operations.rag_ingestion_operations import (
    RagIngestionOperationsService,
)
from application.rag.operations.rag_projection_operations import (
    RagProjectionOperationsService,
)
from application.rag.operations.rag_status_operations import RagStatusOperationsService
from application.rag.rag_service import RagService
from core.bootstrap.di_providers import application_request_scope

logger = logging.getLogger(__name__)


class RagServicePort(Protocol):
    async def run(
        self,
        request: RagRequest,
    ) -> RagResult: ...


class RagIngestionOperationsPort(Protocol):
    async def ingest(
        self,
        request: RagIngestOperationRequest,
    ) -> RagOperationResult: ...


class RagEmbeddingOperationsPort(Protocol):
    async def process_embeddings(
        self,
        request: RagProcessEmbeddingsOperationRequest,
    ) -> RagOperationResult: ...


class RagProjectionOperationsPort(Protocol):
    async def process_graph(
        self,
        request: RagProcessGraphOperationRequest,
    ) -> RagOperationResult: ...

    async def rebuild(
        self,
        request: RagRebuildProjectionOperationRequest,
    ) -> RagOperationResult: ...


class RagStatusOperationsPort(Protocol):
    async def status(
        self,
        request: RagStatusOperationRequest,
    ) -> RagProjectionReadinessResult: ...


RagServiceContextFactory = Callable[[], AbstractAsyncContextManager[RagServicePort]]
RagIngestionContextFactory = Callable[
    [], AbstractAsyncContextManager[RagIngestionOperationsPort]
]
RagEmbeddingContextFactory = Callable[
    [], AbstractAsyncContextManager[RagEmbeddingOperationsPort]
]
RagProjectionContextFactory = Callable[
    [], AbstractAsyncContextManager[RagProjectionOperationsPort]
]
RagStatusContextFactory = Callable[
    [], AbstractAsyncContextManager[RagStatusOperationsPort]
]


@dataclass(
    frozen=True,
    slots=True,
)
class RagAskCommandRequest:
    """
    CLI-facing request for a platform-native RAG question.
    """

    query: str
    symbols: tuple[str, ...] = ()
    source_types: tuple[str, ...] = ()
    source_tables: tuple[str, ...] = ()
    agent_names: tuple[str, ...] = ()
    report_types: tuple[str, ...] = ()
    workflow_name: str | None = None
    execution_id: str | None = None
    runtime_id: str | None = None
    as_of_start: datetime | None = None
    as_of_end: datetime | None = None
    route: str = "hybrid"
    top_k: int = 8
    allow_web: bool = False
    requester: str = "polaris_cli"


@dataclass(
    frozen=True,
    slots=True,
)
class RagAskCommandResult:
    """
    CLI-facing result that always carries renderable output.
    """

    success: bool
    result: RagResult | None = None
    error: str | None = None


class RagCommandService:
    """Thin CLI service that delegates RAG commands to application services."""

    def __init__(
        self,
        service: RagServicePort | None = None,
        service_context_factory: RagServiceContextFactory | None = None,
        ingestion_service: RagIngestionOperationsPort | None = None,
        ingestion_context_factory: RagIngestionContextFactory | None = None,
        embedding_service: RagEmbeddingOperationsPort | None = None,
        embedding_context_factory: RagEmbeddingContextFactory | None = None,
        projection_service: RagProjectionOperationsPort | None = None,
        projection_context_factory: RagProjectionContextFactory | None = None,
        status_service: RagStatusOperationsPort | None = None,
        status_context_factory: RagStatusContextFactory | None = None,
    ) -> None:
        self._service = service
        self._service_context_factory = (
            service_context_factory or default_rag_service_context
        )
        self._ingestion_service = ingestion_service
        self._ingestion_context_factory = (
            ingestion_context_factory or default_rag_ingestion_context
        )
        self._embedding_service = embedding_service
        self._embedding_context_factory = (
            embedding_context_factory or default_rag_embedding_context
        )
        self._projection_service = projection_service
        self._projection_context_factory = (
            projection_context_factory or default_rag_projection_context
        )
        self._status_service = status_service
        self._status_context_factory = (
            status_context_factory or default_rag_status_context
        )

    async def ask(
        self,
        request: RagAskCommandRequest,
    ) -> RagAskCommandResult:
        try:
            rag_request = _rag_request_from_command_request(request)
            logger.info(
                "Running RAG CLI query.",
                extra={"route": request.route, "top_k": request.top_k},
            )
            result = await self._run_rag_request(rag_request)
        except Exception as exc:
            logger.exception("RAG CLI query failed.")
            return RagAskCommandResult(success=False, error=str(exc))
        return RagAskCommandResult(
            success=result.status != "failed",
            result=result,
            error=result.error,
        )

    async def ingest(
        self,
        request: RagIngestOperationRequest,
    ) -> RagOperationResult:
        return await _run_operation(
            self._ingestion_service,
            self._ingestion_context_factory,
            lambda service: service.ingest(request),
        )

    async def process_embeddings(
        self,
        request: RagProcessEmbeddingsOperationRequest,
    ) -> RagOperationResult:
        return await _run_operation(
            self._embedding_service,
            self._embedding_context_factory,
            lambda service: service.process_embeddings(request),
        )

    async def process_graph(
        self,
        request: RagProcessGraphOperationRequest,
    ) -> RagOperationResult:
        return await _run_operation(
            self._projection_service,
            self._projection_context_factory,
            lambda service: service.process_graph(request),
        )

    async def rebuild(
        self,
        request: RagRebuildProjectionOperationRequest,
    ) -> RagOperationResult:
        return await _run_operation(
            self._projection_service,
            self._projection_context_factory,
            lambda service: service.rebuild(request),
        )

    async def status(self) -> RagProjectionReadinessResult:
        return await _run_status_operation(
            self._status_service,
            self._status_context_factory,
            lambda service: service.status(RagStatusOperationRequest()),
        )

    async def _run_rag_request(self, request: RagRequest) -> RagResult:
        if self._service is not None:
            return await self._service.run(request)
        async with self._service_context_factory() as service:
            return await service.run(request)


async def _run_operation[RagOperationDependency](
    service: RagOperationDependency | None,
    context_factory: Callable[[], AbstractAsyncContextManager[RagOperationDependency]],
    callback: Callable[[RagOperationDependency], Awaitable[RagOperationResult]],
) -> RagOperationResult:
    if service is not None:
        return await callback(service)
    async with context_factory() as resolved_service:
        return await callback(resolved_service)


async def _run_status_operation[RagOperationDependency](
    service: RagOperationDependency | None,
    context_factory: Callable[[], AbstractAsyncContextManager[RagOperationDependency]],
    callback: Callable[
        [RagOperationDependency], Awaitable[RagProjectionReadinessResult]
    ],
) -> RagProjectionReadinessResult:
    if service is not None:
        return await callback(service)
    async with context_factory() as resolved_service:
        return await callback(resolved_service)


@asynccontextmanager
async def _default_rag_dependency_context[RagDependency](
    dependency_type: type[RagDependency],
) -> AsyncIterator[RagDependency]:
    """Resolve one request-scoped dependency from canonical composition."""

    async with application_request_scope() as request_container:
        yield await request_container.get(
            dependency_type,
        )


@asynccontextmanager
async def default_rag_service_context() -> AsyncIterator[RagServicePort]:
    """Resolve the canonical request-scoped RAG service."""

    async with _default_rag_dependency_context(RagService) as service:
        yield service


@asynccontextmanager
async def default_rag_ingestion_context() -> AsyncIterator[RagIngestionOperationsPort]:
    async with _default_rag_dependency_context(
        RagIngestionOperationsService
    ) as service:
        yield service


@asynccontextmanager
async def default_rag_embedding_context() -> AsyncIterator[RagEmbeddingOperationsPort]:
    async with _default_rag_dependency_context(
        RagEmbeddingJobOperationsService
    ) as service:
        yield service


@asynccontextmanager
async def default_rag_projection_context() -> AsyncIterator[
    RagProjectionOperationsPort
]:
    async with _default_rag_dependency_context(
        RagProjectionOperationsService
    ) as service:
        yield service


@asynccontextmanager
async def default_rag_status_context() -> AsyncIterator[RagStatusOperationsPort]:
    async with _default_rag_dependency_context(RagStatusOperationsService) as service:
        yield service


def _rag_request_from_command_request(
    request: RagAskCommandRequest,
) -> RagRequest:
    filters = RagRetrievalFilters(
        source_tables=request.source_tables,
        source_types=request.source_types,
        symbols=request.symbols,
        workflow_name=request.workflow_name,
        execution_id=request.execution_id,
        runtime_id=request.runtime_id,
        agent_names=request.agent_names,
        report_types=request.report_types,
        as_of_start=request.as_of_start,
        as_of_end=request.as_of_end,
    )
    return RagRequest(
        query=request.query,
        filters=filters,
        route=request.route,
        top_k=request.top_k,
        allow_web=request.allow_web,
        requester=request.requester,
        workflow_name=request.workflow_name,
        execution_id=request.execution_id,
        metadata={
            "source": "polaris_cli",
            "command": "rag ask",
        },
    )


def render_rag_ask_result(
    command_result: RagAskCommandResult,
) -> str:
    """
    Render RAG command output for humans without truncating model responses.
    """

    if command_result.result is None:
        return _render_command_failure(
            command_result.error or "RAG query failed.",
        )

    result = command_result.result
    lines = [
        "RAG Answer",
        f"Query ID: {result.query_id}",
        f"Status: {result.status}",
        f"Route: {result.route}",
        f"Top K: {result.request.top_k}",
    ]
    if result.confidence_score is not None:
        lines.append(
            f"Confidence: {result.confidence_score}",
        )
    if result.error:
        lines.append(
            f"Error: {result.error}",
        )

    lines.extend(
        [
            "",
            "Question:",
            result.request.normalized_query,
            "",
            "Answer:",
            result.answer_text,
        ]
    )

    if result.citations:
        lines.extend(
            [
                "",
                "Citations:",
            ]
        )
        for index, source in enumerate(
            result.citations,
            start=1,
        ):
            lines.append(
                _format_citation(
                    index,
                    source,
                )
            )

    return "\n".join(
        lines,
    )


def render_rag_operation_result(
    result: RagOperationResult,
) -> str:
    """
    Render a RAG operational command result for humans.
    """

    lines = [
        "RAG Operation",
        f"Operation: {result.operation}",
        f"Status: {result.status}",
        f"Success: {result.success}",
        f"Dry run: {result.dry_run}",
        f"Records processed: {result.records_processed}",
        "",
        "Message:",
        result.message,
    ]
    if result.error and result.error != result.message:
        lines.extend(
            [
                "",
                "Error:",
                result.error,
            ]
        )
    if result.details:
        lines.extend(
            [
                "",
                "Details:",
            ]
        )
        for detail in result.details:
            lines.append(
                f"- {detail.name}: {detail.value}",
            )

    return "\n".join(
        lines,
    )


def render_rag_projection_readiness(
    result: RagProjectionReadinessResult,
) -> str:
    """Render typed RAG projection readiness diagnostics."""

    canonical = result.canonical
    vector = result.vector
    graph = result.graph
    lines = [
        "RAG Projection Readiness",
        f"Status: {result.status}",
        f"Ready: {result.ready}",
        "",
        "Canonical PostgreSQL Records",
        f"- Available: {canonical.available}",
        f"- Documents: {_display_value(canonical.document_count)}",
        f"- Chunks: {_display_value(canonical.chunk_count)}",
        f"- Embedding jobs: {_display_value(canonical.embedding_job_count)}",
        f"- Graph jobs: {_display_value(canonical.graph_job_count)}",
        f"- Pending embedding jobs: {_display_value(canonical.pending_embedding_jobs)}",
        f"- Retryable embedding jobs: "
        f"{_display_value(canonical.retryable_embedding_jobs)}",
        f"- Failed embedding jobs: {_display_value(canonical.failed_embedding_jobs)}",
        "",
        "Qdrant Projection",
        f"- Collection: {vector.collection_name}",
        f"- Exists: {vector.exists}",
        f"- Healthy: {vector.healthy}",
        f"- Named dense vector: {vector.dense_vector_present}",
        f"- Named sparse vector: {vector.sparse_vector_present}",
        f"- Configured dimensions: {vector.configured_vector_size}",
        f"- Actual dimensions: {_display_value(vector.actual_vector_size)}",
        f"- Dimension compatible: {vector.vector_size_compatible}",
        f"- Points: {vector.points_count}",
        "",
        "Neo4j Projection",
        f"- Connected: {graph.connected}",
        f"- Healthy: {graph.healthy}",
        f"- Entities: {_display_value(graph.entity_count)}",
        "",
        "Model Dependencies",
        f"- Embedding ({result.embedding.model}): {result.embedding.ready}",
        f"- Embedding dimensions: {_display_value(result.embedding.dimensions)}",
        f"- Reranker ({result.reranker.model}): {result.reranker.ready}",
    ]
    for label, error in (
        ("PostgreSQL", canonical.error),
        ("Qdrant", vector.error),
        ("Neo4j", graph.error),
        ("Embedding", result.embedding.error),
        ("Reranker", result.reranker.error),
    ):
        if error:
            lines.append(f"- {label} error: {error}")
    lines.extend(("", "Summary", result.message))
    return "\n".join(lines)


def _display_value(value: object | None) -> str:
    return "unavailable" if value is None else str(value)


def _render_command_failure(
    error: str,
) -> str:
    return "\n".join(
        [
            "RAG Answer",
            "Status: failed",
            f"Error: {error}",
        ]
    )


def _format_citation(
    index: int,
    source: RagSource,
) -> str:
    source_table = source.source_table
    source_id = source.source_id
    title = source.title
    chunk_id = source.chunk_id
    section_name = source.section_name
    generated_at = source.generated_at

    suffix_parts: list[str] = []
    if chunk_id:
        suffix_parts.append(
            f"chunk={chunk_id}",
        )
    if section_name:
        suffix_parts.append(
            f"section={section_name}",
        )
    if generated_at:
        suffix_parts.append(
            f"generated_at={generated_at.isoformat()}",
        )

    suffix = ""
    if suffix_parts:
        suffix = f" ({'; '.join(suffix_parts)})"

    return f"[{index}] {title} — {source_table}:{source_id}{suffix}"
