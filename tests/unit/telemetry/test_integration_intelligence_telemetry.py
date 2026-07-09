from __future__ import annotations

import pytest

from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from core.telemetry.emitters.intelligence_telemetry import (
    IntelligenceTelemetry,
)
from core.telemetry.events.telemetry_event import TelemetryEventLevel
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink


def build_observability() -> tuple[ObservabilityManager, InMemoryTelemetrySink]:
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(
        sink,
    )

    return observability_manager, sink


@pytest.mark.asyncio
async def test_integration_telemetry_emits_provider_call() -> None:
    observability_manager, sink = build_observability()
    telemetry = IntegrationTelemetry(
        observability_manager=observability_manager,
    )

    await telemetry.emit_provider_call(
        provider_name="LiveNewsProvider",
        operation="get_market_news",
        context=TelemetryContext(
            workflow_id="workflow-1",
            execution_id="execution-1",
            runtime_id="runtime-1",
            node_name="provider_node",
            correlation_id="correlation-1",
            trace_id="trace-1",
            span_id="provider-span-1",
            parent_span_id="node-span-1",
        ),
        duration_seconds=0.25,
        success=True,
    )

    assert len(sink.events) == 1

    event = sink.events[0]
    assert event.event_type == "integration.provider.call"
    assert event.source == "integration"
    assert event.level == TelemetryEventLevel.INFO
    assert event.workflow_id == "workflow-1"
    assert event.execution_id == "execution-1"
    assert event.runtime_id == "runtime-1"
    assert event.node_name == "provider_node"
    assert event.correlation_id == "correlation-1"
    assert event.success is True
    assert event.duration_seconds == 0.25
    assert event.attributes["trace_id"] == "trace-1"
    assert event.attributes["span_id"] == "provider-span-1"
    assert event.attributes["parent_span_id"] == "node-span-1"
    assert event.attributes["provider_name"] == "LiveNewsProvider"
    assert event.attributes["operation"] == "get_market_news"


@pytest.mark.asyncio
async def test_intelligence_telemetry_emits_agent_signal() -> None:
    observability_manager, sink = build_observability()
    telemetry = IntelligenceTelemetry(
        observability_manager=observability_manager,
    )

    await telemetry.emit_agent_signal(
        agent_name="technical_agent",
        signal_name="technical.analysis_signal",
        confidence=0.73,
        context=TelemetryContext(
            workflow_id="workflow-2",
            execution_id="execution-2",
            runtime_id="runtime-2",
            node_name="technical_agent",
            correlation_id="correlation-2",
            trace_id="trace-2",
            span_id="agent-span-2",
            parent_span_id="node-span-2",
        ),
        payload={
            "directional_score": 0.42,
            "regime": "risk_on",
        },
    )

    assert len(sink.events) == 1

    event = sink.events[0]
    assert event.event_type == "intelligence.agent.signal"
    assert event.source == "intelligence"
    assert event.level == TelemetryEventLevel.INFO
    assert event.workflow_id == "workflow-2"
    assert event.execution_id == "execution-2"
    assert event.runtime_id == "runtime-2"
    assert event.node_name == "technical_agent"
    assert event.correlation_id == "correlation-2"
    assert event.success is True
    assert event.attributes["trace_id"] == "trace-2"
    assert event.attributes["span_id"] == "agent-span-2"
    assert event.attributes["parent_span_id"] == "node-span-2"
    assert event.attributes["agent_name"] == "technical_agent"
    assert event.attributes["signal_name"] == "technical.analysis_signal"
    assert event.attributes["confidence"] == 0.73
    assert event.payload["directional_score"] == 0.42
    assert event.payload["regime"] == "risk_on"


@pytest.mark.asyncio
async def test_intelligence_telemetry_emits_degraded_warning_with_exception() -> None:
    observability_manager, sink = build_observability()
    telemetry = IntelligenceTelemetry(observability_manager=observability_manager)

    await telemetry.emit_agent_degraded(
        agent_name="technical_agent",
        reason="llm_inference_failure",
        error=RuntimeError("model unavailable"),
        context=TelemetryContext(node_name="technical_agent"),
    )

    event = sink.events[0]
    assert event.event_type == "intelligence.agent.degraded"
    assert event.level == TelemetryEventLevel.WARNING
    assert event.success is True
    assert event.attributes["agent_name"] == "technical_agent"
    assert event.attributes["reason"] == "llm_inference_failure"
    assert event.exception_details is not None
    assert event.exception_details.exception_type == "RuntimeError"
