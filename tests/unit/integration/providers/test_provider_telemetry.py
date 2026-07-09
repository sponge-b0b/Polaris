from __future__ import annotations

import asyncio

from typing import Any

import pytest

from core.telemetry.context import get_active_telemetry_context
from core.telemetry.context import telemetry_context_scope
from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from core.telemetry.events.telemetry_event import TelemetryEventLevel
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from integration.providers.news.backtest_news_provider import (
    BacktestNewsProvider,
)
from integration.providers.provider_telemetry import record_provider_call


class FakeNewsProvider:
    async def get_financial_news(
        self,
        query: str,
        sort_by: str = "publishedAt",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return [
            {
                "title": query,
                "sort_by": sort_by,
                "limit": limit,
            }
        ]

    async def get_market_news(
        self,
        symbol: str = "SPY",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return [
            {
                "symbol": symbol,
                "limit": limit,
            }
        ]


class FailingNewsProvider(FakeNewsProvider):
    async def get_market_news(
        self,
        symbol: str = "SPY",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        raise RuntimeError("provider failed")


async def successful_provider_call() -> str:
    return "ok"


async def failing_provider_call() -> str:
    raise RuntimeError("provider failed")


def build_telemetry() -> tuple[IntegrationTelemetry, InMemoryTelemetrySink]:
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(
        sink,
    )

    return IntegrationTelemetry(
        observability_manager=observability_manager,
    ), sink


@pytest.mark.asyncio
async def test_provider_telemetry_records_success() -> None:
    telemetry, sink = build_telemetry()
    provider = BacktestNewsProvider(
        news_provider=FakeNewsProvider(),
        telemetry=telemetry,
    )

    result = await provider.get_market_news(
        symbol="SPY",
        limit=5,
    )

    assert result == [
        {
            "symbol": "SPY",
            "limit": 5,
        }
    ]

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.event_type == "integration.provider.call"
    assert event.success is True
    assert event.attributes["provider_name"] == "BacktestNewsProvider"
    assert event.attributes["operation"] == "get_market_news"


@pytest.mark.asyncio
async def test_provider_telemetry_records_failure() -> None:
    telemetry, sink = build_telemetry()
    provider = BacktestNewsProvider(
        news_provider=FailingNewsProvider(),
        telemetry=telemetry,
    )

    with pytest.raises(
        RuntimeError,
        match="provider failed",
    ):
        await provider.get_market_news()

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.event_type == "integration.provider.call"
    assert event.success is False
    assert event.error_count == 1
    assert event.payload["error_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_record_provider_call_uses_active_telemetry_context() -> None:
    telemetry, sink = build_telemetry()
    context = TelemetryContext(
        workflow_id="workflow-1",
        execution_id="execution-1",
        runtime_id="runtime-1",
        node_name="news_node",
        correlation_id="correlation-1",
        tags=("morning_report",),
        attributes={
            "service_name": "news_service",
        },
        trace_id="trace-1",
        span_id="provider-span-1",
        parent_span_id="node-span-1",
    )

    observed_context: TelemetryContext | None = None

    async def observed_provider_call() -> str:
        nonlocal observed_context
        observed_context = get_active_telemetry_context()
        return "ok"

    with telemetry_context_scope(
        context,
    ):
        result = await record_provider_call(
            telemetry=telemetry,
            provider_name="BacktestNewsProvider",
            operation="get_market_news",
            call=observed_provider_call,
        )

    assert result == "ok"
    assert len(sink.events) == 1

    event = sink.events[0]
    assert event.event_type == "integration.provider.call"
    assert event.workflow_id == "workflow-1"
    assert event.execution_id == "execution-1"
    assert event.runtime_id == "runtime-1"
    assert event.node_name == "news_node"
    assert event.correlation_id == "correlation-1"
    assert event.tags == ("morning_report",)
    assert event.attributes["service_name"] == "news_service"
    assert event.attributes["trace_id"] == "trace-1"
    assert observed_context is not None
    assert event.attributes["span_id"] == observed_context.span_id
    assert event.attributes["span_id"] != "provider-span-1"
    assert event.attributes["parent_span_id"] == "provider-span-1"
    assert event.attributes["operation_kind"] == "provider_call"
    assert event.attributes["provider_name"] == "BacktestNewsProvider"
    assert event.attributes["operation"] == "get_market_news"
    assert event.payload["provider_name"] == "BacktestNewsProvider"
    assert event.payload["operation"] == "get_market_news"
    assert event.payload["success"] is True


@pytest.mark.asyncio
async def test_record_provider_call_accepts_explicit_context() -> None:
    telemetry, sink = build_telemetry()
    active_context = TelemetryContext(
        workflow_id="active-workflow",
        trace_id="active-trace",
        span_id="active-span",
        parent_span_id="active-parent-span",
    )
    explicit_context = TelemetryContext(
        workflow_id="explicit-workflow",
        execution_id="explicit-execution",
        trace_id="explicit-trace",
        span_id="explicit-span",
        parent_span_id="explicit-parent-span",
    )

    with telemetry_context_scope(
        active_context,
    ):
        result = await record_provider_call(
            telemetry=telemetry,
            provider_name="BacktestNewsProvider",
            operation="get_market_news",
            call=successful_provider_call,
            context=explicit_context,
        )

    assert result == "ok"
    event = sink.events[0]
    assert event.workflow_id == "explicit-workflow"
    assert event.execution_id == "explicit-execution"
    assert event.attributes["trace_id"] == "explicit-trace"
    assert event.attributes["span_id"] != "explicit-span"
    assert event.attributes["parent_span_id"] == "explicit-span"
    assert event.attributes["operation_kind"] == "provider_call"


@pytest.mark.asyncio
async def test_record_provider_call_failure_uses_active_context_and_metrics() -> None:
    telemetry, sink = build_telemetry()
    context = TelemetryContext(
        workflow_id="workflow-2",
        execution_id="execution-2",
        runtime_id="runtime-2",
        node_name="provider_node",
        correlation_id="correlation-2",
        trace_id="trace-2",
        span_id="provider-span-2",
        parent_span_id="node-span-2",
    )

    with pytest.raises(
        RuntimeError,
        match="provider failed",
    ):
        with telemetry_context_scope(
            context,
        ):
            await record_provider_call(
                telemetry=telemetry,
                provider_name="BacktestNewsProvider",
                operation="get_market_news",
                call=failing_provider_call,
            )

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.event_type == "integration.provider.call"
    assert event.level == TelemetryEventLevel.ERROR
    assert event.success is False
    assert event.error_count == 1
    assert event.workflow_id == "workflow-2"
    assert event.execution_id == "execution-2"
    assert event.runtime_id == "runtime-2"
    assert event.node_name == "provider_node"
    assert event.correlation_id == "correlation-2"
    assert event.attributes["trace_id"] == "trace-2"
    assert event.attributes["span_id"] != "provider-span-2"
    assert event.attributes["parent_span_id"] == "provider-span-2"
    assert event.attributes["operation_kind"] == "provider_call"
    assert event.payload["provider_name"] == "BacktestNewsProvider"
    assert event.payload["operation"] == "get_market_news"
    assert event.payload["success"] is False
    assert event.payload["error_type"] == "RuntimeError"
    assert event.payload["error_message"] == "provider failed"
    assert event.exception_details is not None
    assert event.exception_details.exception_type == "RuntimeError"
    assert event.exception_details.message == "provider failed"
    assert "raise RuntimeError" in event.exception_details.stack_trace

    metric_names = {
        point.name for point in telemetry.observability_manager.metrics_store.points()
    }
    assert "integration.provider.calls.total" in metric_names
    assert "integration.provider.calls.failed" in metric_names
    assert "integration.provider.duration_seconds" in metric_names


@pytest.mark.asyncio
async def test_record_provider_call_records_cancellation_separately() -> None:
    telemetry, sink = build_telemetry()

    async def cancelled_provider_call() -> str:
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await record_provider_call(
            telemetry=telemetry,
            provider_name="BacktestNewsProvider",
            operation="get_market_news",
            call=cancelled_provider_call,
        )

    event = sink.events[0]
    assert event.event_type == "integration.provider.cancelled"
    assert event.level == TelemetryEventLevel.WARNING
    assert event.success is False
    assert event.error_count == 0
    assert event.attributes["outcome"] == "cancelled"
    metric_names = {
        point.name for point in telemetry.observability_manager.metrics_store.points()
    }
    assert "integration.provider.calls.total" in metric_names
    assert "integration.provider.calls.cancelled" in metric_names
    assert "integration.provider.calls.failed" not in metric_names
    assert "integration.provider.duration_seconds" in metric_names
