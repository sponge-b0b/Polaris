"""Tests for the thin ``polaris_rag_status`` MCP boundary."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import cast

import pytest
from dishka import AsyncContainer
from mcp.server.fastmcp.exceptions import ToolError

from application.rag.contracts.rag_operation_models import (
    RagCanonicalProjectionReadiness,
    RagGraphProjectionReadiness,
    RagModelReadiness,
    RagProjectionReadinessResult,
    RagStatusOperationRequest,
    RagVectorProjectionReadiness,
)
from core.telemetry.collectors.telemetry_collector import TelemetryCollector
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapResult
from mcp_server.contracts.models import RagStatusRequest
from mcp_server.lifespan import McpApplicationContext
from mcp_server.settings import McpServerSettings
from mcp_server.telemetry import McpTelemetry
from mcp_server.tools.rag_status import execute_rag_status


def _credential_url(password: str) -> str:
    return "postgresql://user:" + password + "@localhost/polaris"


class _FakeStatusService:
    def __init__(
        self,
        result: RagProjectionReadinessResult | BaseException,
    ) -> None:
        self._result = result
        self.requests: list[RagStatusOperationRequest] = []

    async def status(
        self,
        request: RagStatusOperationRequest,
    ) -> RagProjectionReadinessResult:
        self.requests.append(request)
        if isinstance(self._result, BaseException):
            raise self._result
        return self._result


class _RequestContainer:
    def __init__(self, service: _FakeStatusService) -> None:
        self._service = service

    async def get(self, dependency_type: type[object]) -> object:
        assert dependency_type.__name__ == "RagStatusOperationsService"
        return self._service


class _RequestScope:
    def __init__(self, service: _FakeStatusService) -> None:
        self._container = _RequestContainer(service)
        self.closed = False

    async def __aenter__(self) -> _RequestContainer:
        return self._container

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: object,
    ) -> None:
        self.closed = True


class _ApplicationContainer:
    def __init__(self, service: _FakeStatusService) -> None:
        self._service = service
        self.scopes: list[_RequestScope] = []

    def __call__(self) -> _RequestScope:
        scope = _RequestScope(self._service)
        self.scopes.append(scope)
        return scope


def _context(
    service: _FakeStatusService,
) -> tuple[McpApplicationContext, InMemoryTelemetrySink, _ApplicationContainer]:
    sink = InMemoryTelemetrySink()
    manager = ObservabilityManager(
        collector=TelemetryCollector(sinks=(sink,)),
        enable_domain_metrics=False,
    )
    container = _ApplicationContainer(service)
    return (
        McpApplicationContext(
            container=cast(AsyncContainer, container),
            runtime=cast(WorkflowBootstrapResult, SimpleNamespace()),
            telemetry=McpTelemetry(manager),
            settings=McpServerSettings(),
        ),
        sink,
        container,
    )


@pytest.mark.asyncio
async def test_rag_status_serializes_every_ready_component() -> None:
    service = _FakeStatusService(_readiness_result())
    context, sink, container = _context(service)

    response = await execute_rag_status(
        RagStatusRequest(),
        context,
        request_id="status-request-1",
    )

    assert service.requests == [RagStatusOperationRequest(include_details=True)]
    assert response.status == "ready"
    assert response.ready is True
    assert response.canonical is not None
    assert response.canonical.document_count == 3
    assert response.canonical.graph_job_count == 2
    assert response.vector is not None
    assert response.vector.collection_name == "polaris_rag_chunks"
    assert response.vector.sparse_vector_present is True
    assert response.vector.actual_vector_size == 1024
    assert response.graph is not None
    assert response.graph.entity_count == 12
    assert response.embedding is not None
    assert response.embedding.model == "bge-m3:567m"
    assert response.embedding.dimensions == 1024
    assert response.reranker is not None
    assert response.reranker.model == "bge-reranker-large"
    assert container.scopes[0].closed is True
    assert [event.event_type for event in sink.events] == [
        "mcp.tool.started",
        "mcp.tool.completed",
    ]
    assert all(event.correlation_id == "status-request-1" for event in sink.events)
    assert sink.events[-1].attributes["result_status"] == "ready"


@pytest.mark.asyncio
async def test_rag_status_omits_dependency_details_when_not_requested() -> None:
    service = _FakeStatusService(_readiness_result())
    context, _, _ = _context(service)

    response = await execute_rag_status(
        RagStatusRequest(include_details=False),
        context,
    )

    assert service.requests == [RagStatusOperationRequest(include_details=False)]
    assert response.status == "ready"
    assert response.ready is True
    assert response.canonical is None
    assert response.vector is None
    assert response.graph is None
    assert response.embedding is None
    assert response.reranker is None


@pytest.mark.asyncio
async def test_rag_status_returns_degraded_result_and_sanitizes_dependency_errors() -> (
    None
):
    secrets = (
        _credential_url("password"),
        "http://qdrant:6333?api_key=secret",
        "neo4j://neo4j:" + "password" + "@localhost:7687",
        "Bearer embedding-secret",
        "Bearer reranker-secret",
    )
    ready = _readiness_result()
    degraded = RagProjectionReadinessResult(
        operation=ready.operation,
        status="degraded",
        message="One or more RAG projection dependencies require attention.",
        canonical=RagCanonicalProjectionReadiness(
            available=False,
            document_count=None,
            chunk_count=None,
            embedding_job_count=None,
            graph_job_count=None,
            pending_embedding_jobs=None,
            retryable_embedding_jobs=None,
            failed_embedding_jobs=None,
            error=secrets[0],
        ),
        vector=RagVectorProjectionReadiness(
            collection_name="polaris_rag_chunks",
            exists=False,
            healthy=False,
            dense_vector_present=False,
            sparse_vector_present=False,
            configured_vector_size=1024,
            actual_vector_size=None,
            vector_size_compatible=False,
            points_count=0,
            error=secrets[1],
        ),
        graph=RagGraphProjectionReadiness(
            connected=False,
            healthy=False,
            entity_count=None,
            error=secrets[2],
        ),
        embedding=RagModelReadiness(
            component="embedding",
            model="bge-m3:567m",
            ready=False,
            error=secrets[3],
        ),
        reranker=RagModelReadiness(
            component="reranker",
            model="bge-reranker-large",
            ready=False,
            error=secrets[4],
        ),
    )
    context, sink, _ = _context(_FakeStatusService(degraded))

    response = await execute_rag_status(RagStatusRequest(), context)

    assert response.status == "degraded"
    assert response.ready is False
    assert response.canonical is not None
    assert response.canonical.error == "Canonical PostgreSQL readiness check failed."
    assert response.vector is not None
    assert response.vector.error == "Vector projection readiness check failed."
    assert response.graph is not None
    assert response.graph.error == "Graph projection readiness check failed."
    assert response.embedding is not None
    assert response.embedding.error == "Embedding model readiness check failed."
    assert response.reranker is not None
    assert response.reranker.error == "Reranker readiness check failed."
    serialized = response.model_dump_json()
    assert all(secret not in serialized for secret in secrets)
    assert sink.events[-1].event_type == "mcp.tool.completed"
    assert sink.events[-1].attributes["result_status"] == "degraded"


@pytest.mark.asyncio
async def test_rag_status_sanitizes_dependency_exception_and_closes_scope() -> None:
    secret = _credential_url("password")
    service = _FakeStatusService(RuntimeError(secret))
    context, sink, container = _context(service)

    with pytest.raises(ToolError, match="Polaris RAG status request failed") as caught:
        await execute_rag_status(RagStatusRequest(), context)

    assert secret not in str(caught.value)
    assert container.scopes[0].closed is True
    assert sink.events[-1].event_type == "mcp.tool.failed"
    assert sink.events[-1].attributes["failure_category"] == "application"
    assert sink.events[-1].attributes["error_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_rag_status_preserves_cancellation_and_closes_scope() -> None:
    service = _FakeStatusService(asyncio.CancelledError())
    context, sink, container = _context(service)

    with pytest.raises(asyncio.CancelledError):
        await execute_rag_status(RagStatusRequest(), context)

    assert container.scopes[0].closed is True
    assert sink.events[-1].event_type == "mcp.tool.failed"
    assert sink.events[-1].attributes["failure_category"] == "cancelled"


def _readiness_result() -> RagProjectionReadinessResult:
    return RagProjectionReadinessResult(
        operation="rag.status",
        status="ready",
        message="RAG projections and model dependencies are ready.",
        canonical=RagCanonicalProjectionReadiness(
            available=True,
            document_count=3,
            chunk_count=8,
            embedding_job_count=5,
            graph_job_count=2,
            pending_embedding_jobs=1,
            retryable_embedding_jobs=0,
            failed_embedding_jobs=0,
        ),
        vector=RagVectorProjectionReadiness(
            collection_name="polaris_rag_chunks",
            exists=True,
            healthy=True,
            dense_vector_present=True,
            sparse_vector_present=True,
            configured_vector_size=1024,
            actual_vector_size=1024,
            vector_size_compatible=True,
            points_count=8,
            status="green",
        ),
        graph=RagGraphProjectionReadiness(
            connected=True,
            healthy=True,
            entity_count=12,
        ),
        embedding=RagModelReadiness(
            component="embedding",
            model="bge-m3:567m",
            ready=True,
            dimensions=1024,
        ),
        reranker=RagModelReadiness(
            component="reranker",
            model="bge-reranker-large",
            ready=True,
        ),
    )


def test_rag_status_is_registered_as_read_only_idempotent_tool() -> None:
    from mcp_server.server import server

    tools = {tool.name: tool for tool in server._tool_manager.list_tools()}

    tool = tools["polaris_rag_status"]
    assert tool.annotations is not None
    assert tool.annotations.readOnlyHint is True
    assert tool.annotations.destructiveHint is False
    assert tool.annotations.idempotentHint is True
    assert tool.annotations.openWorldHint is False
    assert tool.fn_metadata.output_model is not None
    assert tool.fn_metadata.output_model.__name__ == "RagStatusResponse"
