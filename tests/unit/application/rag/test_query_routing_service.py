from __future__ import annotations

from collections import deque

import pytest

from application.rag.routing.query_routing_models import RagConversationMemory
from application.rag.routing.query_routing_models import RagConversationRole
from application.rag.routing.query_routing_models import RagConversationTurn
from application.rag.routing.query_routing_models import RagQueryComplexity
from application.rag.routing.query_routing_models import RagQueryContext
from application.rag.routing.query_routing_service import RagQueryRoutingService
from application.rag.routing.query_routing_models import RagRetrievalRoute
from application.rag.routing.query_routing_service import RagRoutingModelOutputError
from core.storage.persistence.rag import JsonObject
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from integration.providers.rag.query_routing_provider import RagQueryModelOperation
from integration.providers.rag.query_routing_provider import RagQueryModelRequest
from integration.providers.rag.query_routing_provider import RagQueryModelResult


@pytest.mark.asyncio
async def test_routes_context_free_query_directly_without_rewrite() -> None:
    provider = FakeQueryModelProvider(
        {"complexity": "low"},
        {"route": "direct_answer"},
    )

    decision = await RagQueryRoutingService(provider).route(
        RagQueryContext(request_id="route-1", query="What is diversification?")
    )

    assert decision.rewrite.standalone_query == "What is diversification?"
    assert decision.rewrite.rewritten is False
    assert decision.triage.complexity is RagQueryComplexity.LOW
    assert decision.route_selection.route is RagRetrievalRoute.DIRECT_ANSWER
    assert decision.hyde is None
    assert [request.operation for request in provider.requests] == [
        RagQueryModelOperation.ADAPTIVE_TRIAGE,
        RagQueryModelOperation.ROUTE_SELECTION,
    ]
    assert decision.persistence_metadata() == {
        "model_executions": [
            {
                "operation": "adaptive_triage",
                "configured_model": "fake-adaptive_triage-model",
                "provider_name": "fake",
                "duration_ms": 12.5,
                "success": True,
            },
            {
                "operation": "route_selection",
                "configured_model": "fake-route_selection-model",
                "provider_name": "fake",
                "duration_ms": 12.5,
                "success": True,
            },
        ]
    }


@pytest.mark.asyncio
async def test_rewrites_follow_up_and_selects_retrieval() -> None:
    provider = FakeQueryModelProvider(
        {"standalone_query": "How did SPY market breadth change this week?"},
        {"complexity": "moderate"},
        {"route": "retrieval"},
    )
    context = RagQueryContext(
        request_id="route-2",
        query="How did it change this week?",
        memory=RagConversationMemory(
            turns=(
                RagConversationTurn(
                    role=RagConversationRole.USER,
                    content="Tell me about SPY market breadth.",
                ),
                RagConversationTurn(
                    role=RagConversationRole.ASSISTANT,
                    content="SPY breadth was mixed.",
                ),
            )
        ),
    )

    decision = await RagQueryRoutingService(provider).route(context)

    assert decision.rewrite.rewritten is True
    assert decision.rewrite.standalone_query == (
        "How did SPY market breadth change this week?"
    )
    assert decision.route_selection.route is RagRetrievalRoute.RETRIEVAL
    assert decision.hyde is None
    assert [request.operation for request in provider.requests] == [
        RagQueryModelOperation.REWRITE,
        RagQueryModelOperation.ADAPTIVE_TRIAGE,
        RagQueryModelOperation.ROUTE_SELECTION,
    ]
    assert "SPY market breadth" in provider.requests[0].user_prompt
    assert "Adaptive triage complexity: moderate" in provider.requests[2].user_prompt


@pytest.mark.asyncio
async def test_deep_research_generates_hyde_expansion() -> None:
    provider = FakeQueryModelProvider(
        {"complexity": "high"},
        {"route": "deep_research"},
        {
            "hypothetical_document": (
                "A multi-source assessment compares breadth, volatility, and macro risk."
            )
        },
    )

    decision = await RagQueryRoutingService(provider).route(
        RagQueryContext(
            request_id="route-3",
            query="Assess whether the current market regime supports adding equity risk.",
        )
    )

    assert decision.triage.complexity is RagQueryComplexity.HIGH
    assert decision.route_selection.route is RagRetrievalRoute.DEEP_RESEARCH
    assert decision.hyde is not None
    assert "multi-source assessment" in decision.hyde.hypothetical_document
    assert [request.operation for request in provider.requests] == [
        RagQueryModelOperation.ADAPTIVE_TRIAGE,
        RagQueryModelOperation.ROUTE_SELECTION,
        RagQueryModelOperation.HYDE,
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"complexity": "unknown"},
        {},
        {"complexity": "moderate", "extra": True},
        {"complexity": 1},
    ],
)
async def test_invalid_triage_output_fails_closed(payload: JsonObject) -> None:
    provider = FakeQueryModelProvider(payload)

    with pytest.raises(RagRoutingModelOutputError):
        await RagQueryRoutingService(provider).route(
            RagQueryContext(request_id="route-invalid", query="Analyze SPY.")
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"route": "unsupported"},
        {},
        {"route": "retrieval", "extra": True},
        {"route": 1},
    ],
)
async def test_invalid_route_selection_output_fails_closed(
    payload: JsonObject,
) -> None:
    provider = FakeQueryModelProvider({"complexity": "moderate"}, payload)

    with pytest.raises(RagRoutingModelOutputError):
        await RagQueryRoutingService(provider).route(
            RagQueryContext(request_id="route-invalid-route", query="Analyze SPY.")
        )


@pytest.mark.asyncio
async def test_invalid_rewrite_output_fails_closed() -> None:
    provider = FakeQueryModelProvider(
        {"standalone_query": ""},
    )
    context = RagQueryContext(
        request_id="route-invalid-rewrite",
        query="What about it?",
        memory=RagConversationMemory(
            turns=(
                RagConversationTurn(
                    role=RagConversationRole.USER,
                    content="Discuss SPY breadth.",
                ),
            )
        ),
    )

    with pytest.raises(RagRoutingModelOutputError):
        await RagQueryRoutingService(provider).route(context)


@pytest.mark.asyncio
async def test_invalid_hyde_output_fails_closed() -> None:
    provider = FakeQueryModelProvider(
        {"complexity": "high"},
        {"route": "deep_research"},
        {"hypothetical_document": "", "unexpected": "value"},
    )

    with pytest.raises(RagRoutingModelOutputError):
        await RagQueryRoutingService(provider).route(
            RagQueryContext(request_id="route-invalid-hyde", query="Deep analysis.")
        )


@pytest.mark.asyncio
async def test_routing_emits_success_and_failure_telemetry() -> None:
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    telemetry = ApplicationRagTelemetry(observability_manager=observability)
    service = RagQueryRoutingService(
        FakeQueryModelProvider(
            {"complexity": "low"},
            {"route": "direct_answer"},
        ),
        telemetry=telemetry,
    )

    await service.route(
        RagQueryContext(request_id="route-telemetry", query="Define beta.")
    )

    assert [event.attributes["operation"] for event in sink.events] == [
        "rag.query_routing.route",
        "rag.query_routing.rewrite",
        "rag.query_routing.rewrite",
        "rag.query_routing.adaptive_triage",
        "rag.query_routing.adaptive_triage",
        "rag.query_routing.route_selection",
        "rag.query_routing.route_selection",
        "rag.query_routing.route",
    ]
    assert [event.event_type for event in sink.events] == [
        "application.rag.operation.started",
        "application.rag.operation.started",
        "application.rag.operation.completed",
        "application.rag.operation.started",
        "application.rag.operation.completed",
        "application.rag.operation.started",
        "application.rag.operation.completed",
        "application.rag.operation.completed",
    ]
    assert sink.events[2].attributes["model_invoked"] is False
    assert sink.events[-1].attributes["route"] == "direct_answer"
    assert sink.events[-1].attributes["hyde_generated"] is False
    assert sink.events[-1].attributes["model_operation_count"] == 2
    assert sink.events[-1].payload["model_executions"] == [
        {
            "operation": "adaptive_triage",
            "configured_model": "fake-adaptive_triage-model",
            "provider_name": "fake",
            "duration_ms": 12.5,
            "success": True,
        },
        {
            "operation": "route_selection",
            "configured_model": "fake-route_selection-model",
            "provider_name": "fake",
            "duration_ms": 12.5,
            "success": True,
        },
    ]


@pytest.mark.asyncio
async def test_direct_routing_stage_failure_emits_stage_and_route_failures() -> None:
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    service = RagQueryRoutingService(
        FakeQueryModelProvider({"complexity": "invalid"}),
        telemetry=ApplicationRagTelemetry(observability),
    )

    with pytest.raises(RagRoutingModelOutputError):
        await service.triage(
            context=RagQueryContext(
                request_id="route-stage-failure",
                query="Analyze SPY.",
            ),
            query="Analyze SPY.",
        )

    assert [event.attributes["operation"] for event in sink.events] == [
        "rag.query_routing.adaptive_triage",
        "rag.query_routing.adaptive_triage",
    ]
    assert sink.events[-1].event_type == "application.rag.operation.failed"
    assert sink.events[-1].payload["error_type"] == "RagRoutingModelOutputError"


class FakeQueryModelProvider:
    def __init__(self, *payloads: JsonObject) -> None:
        self._payloads = deque(payloads)
        self.requests: list[RagQueryModelRequest] = []

    async def generate_structured(
        self,
        request: RagQueryModelRequest,
    ) -> RagQueryModelResult:
        self.requests.append(request)
        return RagQueryModelResult(
            operation=request.operation,
            payload=self._payloads.popleft(),
            model=f"fake-{request.operation.value}-model",
            provider_name="fake",
            duration_ms=12.5,
            success=True,
        )
