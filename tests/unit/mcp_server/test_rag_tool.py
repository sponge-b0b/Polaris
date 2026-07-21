"""Tests for the thin ``polaris_rag_ask`` MCP boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast

import pytest
from dishka import AsyncContainer
from mcp.server.fastmcp.exceptions import ToolError

from application.rag.contracts.rag_context import (
    RagRetrievedContext as DomainRagContext,
)
from application.rag.contracts.rag_context import RagSource
from application.rag.contracts.rag_quality_models import RagCorrectiveAction
from application.rag.contracts.rag_quality_models import (
    RagReflectionScores as DomainScores,
)
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from core.telemetry.collectors.telemetry_collector import TelemetryCollector
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapResult
from mcp_server.contracts.models import RagAskRequest
from mcp_server.lifespan import McpApplicationContext
from mcp_server.settings import McpServerSettings
from mcp_server.telemetry import McpTelemetry
from mcp_server.tools.rag import execute_rag_ask


def _credential_url(password: str) -> str:
    return "postgresql://user:" + password + "@localhost/polaris"


_GENERATED_AT = datetime(2026, 7, 8, 12, 0, tzinfo=UTC)


class _FakeRagService:
    def __init__(self, result_factory: object) -> None:
        self._result_factory = result_factory
        self.requests: list[RagRequest] = []

    async def run(self, request: RagRequest) -> RagResult:
        self.requests.append(request)
        result_factory = cast("_ResultFactory", self._result_factory)
        return result_factory(request)


class _ResultFactory:
    def __call__(self, request: RagRequest) -> RagResult: ...


class _RequestContainer:
    def __init__(self, service: _FakeRagService) -> None:
        self._service = service

    async def get(self, dependency_type: type[object]) -> object:
        assert dependency_type.__name__ == "RagService"
        return self._service


class _RequestScope:
    def __init__(self, service: _FakeRagService) -> None:
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
    def __init__(self, service: _FakeRagService) -> None:
        self._service = service
        self.scopes: list[_RequestScope] = []

    def __call__(self) -> _RequestScope:
        scope = _RequestScope(self._service)
        self.scopes.append(scope)
        return scope


def _context(
    service: _FakeRagService,
    *,
    settings: McpServerSettings | None = None,
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
            settings=settings or McpServerSettings(),
        ),
        sink,
        container,
    )


def _answered(request: RagRequest) -> RagResult:
    return RagResult(
        query_id=request.request_id,
        request=request,
        answer_text=(
            "Full answer with all material details.\nSecond paragraph retained."
        ),
        status="answered",
        route=request.route,
        generated_at=_GENERATED_AT,
    )


@pytest.mark.asyncio
async def test_rag_ask_maps_all_supported_filters_and_correlates_request() -> None:
    service = _FakeRagService(_answered)
    context, sink, container = _context(service)
    request = RagAskRequest(
        query="Explain market risk",
        symbols=("SPY",),
        source_types=("report",),
        source_tables=("morning_reports",),
        agent_names=("risk_agent",),
        agent_types=("risk",),
        report_types=("morning_report",),
        regimes=("volatile",),
        workflow_name="morning_report",
        execution_id="execution-1",
        runtime_id="runtime-1",
        as_of_start=datetime(2026, 7, 1, tzinfo=UTC),
        as_of_end=datetime(2026, 7, 8, tzinfo=UTC),
        top_k=12,
    )

    response = await execute_rag_ask(request, context, request_id="mcp-request-1")

    assert len(service.requests) == 1
    rag_request = service.requests[0]
    assert rag_request.request_id == "mcp-request-1"
    assert rag_request.route == "hybrid"
    assert rag_request.requester == "polaris_mcp"
    assert rag_request.top_k == 12
    assert rag_request.filters.source_tables == ("morning_reports",)
    assert rag_request.filters.source_types == ("report",)
    assert rag_request.filters.symbols == ("SPY",)
    assert rag_request.filters.agent_names == ("risk_agent",)
    assert rag_request.filters.agent_types == ("risk",)
    assert rag_request.filters.report_types == ("morning_report",)
    assert rag_request.filters.regimes == ("volatile",)
    assert rag_request.filters.workflow_name == "morning_report"
    assert rag_request.filters.execution_id == "execution-1"
    assert rag_request.filters.runtime_id == "runtime-1"
    assert rag_request.filters.as_of_start == request.as_of_start
    assert rag_request.filters.as_of_end == request.as_of_end
    assert response.answer_text.endswith("Second paragraph retained.")
    assert container.scopes[0].closed is True
    assert [event.event_type for event in sink.events] == [
        "mcp.tool.started",
        "mcp.tool.completed",
    ]
    assert all(event.correlation_id == "mcp-request-1" for event in sink.events)


@pytest.mark.asyncio
async def test_rag_ask_denies_web_before_resolving_service() -> None:
    service = _FakeRagService(_answered)
    context, sink, container = _context(service)

    with pytest.raises(ToolError, match="Web retrieval is disabled"):
        await execute_rag_ask(
            RagAskRequest(query="Search the web", allow_web=True),
            context,
        )

    assert service.requests == []
    assert container.scopes == []
    assert sink.events[-1].attributes["failure_category"] == "validation"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rag_ask_request", "message"),
    (
        (RagAskRequest(query="12345"), "query cannot exceed 4 characters"),
        (RagAskRequest(query="risk", top_k=3), "top_k cannot exceed 2"),
    ),
)
async def test_rag_ask_enforces_query_and_top_k_limits(
    rag_ask_request: RagAskRequest,
    message: str,
) -> None:
    service = _FakeRagService(_answered)
    context, _, _ = _context(
        service,
        settings=McpServerSettings(max_query_characters=4, max_top_k=2),
    )

    with pytest.raises(ToolError, match=message):
        await execute_rag_ask(rag_ask_request, context)

    assert service.requests == []


@pytest.mark.asyncio
async def test_rag_ask_sanitizes_failed_canonical_result() -> None:
    secret = _credential_url("password")

    def failed(request: RagRequest) -> RagResult:
        return RagResult.failed(request=request, error=secret)

    service = _FakeRagService(failed)
    context, sink, _ = _context(service)

    response = await execute_rag_ask(RagAskRequest(query="risk"), context)

    assert response.status == "failed"
    assert response.answer_text == "Polaris RAG request failed."
    assert response.error == "Polaris RAG request failed."
    assert secret not in response.model_dump_json()
    assert sink.events[-1].event_type == "mcp.tool.completed"
    assert sink.events[-1].attributes["result_status"] == "failed"


@pytest.mark.asyncio
@pytest.mark.parametrize("include_contexts", (False, True))
async def test_rag_ask_preserves_citations_security_scores_and_optional_contexts(
    include_contexts: bool,
) -> None:
    source = RagSource(
        source_table="strategy_recommendations",
        source_id="recommendation-1",
        source_type="strategy_recommendation",
        document_id="document-1",
        title="Strategy Recommendation",
        chunk_id="chunk-1",
        section_name="Risk",
        generated_at=_GENERATED_AT,
        workflow_name="morning_report",
        execution_id="execution-1",
        metadata={"symbol": "SPY"},
    )
    retrieved_context = DomainRagContext(
        context_id="context-1",
        text="Complete retrieved evidence.",
        source=source,
        score=0.91,
        rank=0,
        retrieval_route="hybrid",
        metadata={"engine": "vector_graph"},
    )

    def result_factory(request: RagRequest) -> RagResult:
        return RagResult(
            query_id=request.request_id,
            request=request,
            answer_text="Complete grounded answer.",
            status="answered",
            route=request.route,
            contexts=(retrieved_context,),
            citations=(source,),
            confidence_score=0.92,
            grounding_score=0.93,
            utility_score=0.94,
            injection_detected=True,
            reflection_scores=DomainScores(
                retrieval_necessity=0.8,
                source_relevance=0.9,
                answer_support=0.95,
                usefulness=0.85,
            ),
            corrective_actions=(RagCorrectiveAction.DISCARD_WEAK_CONTEXT,),
            generated_at=_GENERATED_AT,
        )

    context, _, _ = _context(_FakeRagService(result_factory))

    response = await execute_rag_ask(
        RagAskRequest(query="risk", include_contexts=include_contexts),
        context,
    )

    assert response.citations[0].document_id == "document-1"
    assert response.citations[0].metadata == {"symbol": "SPY"}
    assert response.injection_detected is True
    assert response.grounding_score == pytest.approx(0.93)
    assert response.reflection_scores is not None
    assert response.reflection_scores.answer_support == pytest.approx(0.95)
    assert response.corrective_actions == ("discard_weak_context",)
    if include_contexts:
        assert response.contexts is not None
        assert response.contexts[0].text == "Complete retrieved evidence."
    else:
        assert response.contexts is None


@pytest.mark.asyncio
async def test_rag_ask_excludes_reasoning_traces_from_mcp_boundary() -> None:
    source = RagSource(
        source_table="curated_rag_documents",
        source_id="report-1",
        source_type="morning_report",
        document_id="document-1",
        title="Morning Report",
        metadata={
            "symbol": "SPY",
            "reasoning_trace": "private source reasoning",
        },
    )
    retrieved_context = DomainRagContext(
        context_id="context-1",
        text="<think>private context reasoning</think>\nRetrieved source evidence.",
        source=source,
        score=0.91,
        rank=0,
        retrieval_route="hybrid",
    )

    def result_factory(request: RagRequest) -> RagResult:
        return RagResult(
            query_id=request.request_id,
            request=request,
            answer_text="<think>private answer reasoning</think>\nGrounded answer.",
            status="answered",
            route=request.route,
            contexts=(retrieved_context,),
            citations=(source,),
            generated_at=_GENERATED_AT,
        )

    context, _, _ = _context(_FakeRagService(result_factory))

    response = await execute_rag_ask(
        RagAskRequest(query="risk", include_contexts=True),
        context,
    )

    assert response.answer_text == "Grounded answer."
    assert response.citations[0].metadata == {"symbol": "SPY"}
    assert response.contexts is not None
    assert response.contexts[0].text == "Retrieved source evidence."
    serialized = response.model_dump_json()
    assert "private answer reasoning" not in serialized
    assert "private context reasoning" not in serialized
    assert "private source reasoning" not in serialized
