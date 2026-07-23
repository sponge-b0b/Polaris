from __future__ import annotations

import pytest

from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.emitters.application_service_telemetry import (
    ApplicationServiceTelemetry,
)
from core.telemetry.events.telemetry_event import TelemetryEventLevel
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink


@pytest.mark.asyncio
async def test_application_service_telemetry_emits_service_started() -> None:
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()

    observability_manager.add_sink(
        sink,
    )

    telemetry = ApplicationServiceTelemetry(
        observability_manager=observability_manager,
    )

    await telemetry.emit_service_started(
        service_name="TechnicalService",
        request_name="TechnicalAnalysisRequest",
        correlation_id="corr-1",
        attributes={
            "symbol": "SPY",
        },
        payload={
            "days": 365,
        },
    )

    assert len(sink.events) == 1

    event = sink.events[0]

    assert event.event_type == "application.service.started"
    assert event.source == "application"
    assert event.level == TelemetryEventLevel.INFO
    assert event.success is None
    assert event.correlation_id == "corr-1"
    assert event.attributes["service_name"] == "TechnicalService"
    assert event.attributes["request_name"] == "TechnicalAnalysisRequest"
    assert "operation" not in event.attributes
    assert event.attributes["symbol"] == "SPY"
    assert event.payload["service_name"] == "TechnicalService"
    assert "operation" not in event.payload
    assert event.payload["days"] == 365


@pytest.mark.asyncio
async def test_application_service_telemetry_emits_service_completed() -> None:
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()

    observability_manager.add_sink(
        sink,
    )

    telemetry = ApplicationServiceTelemetry(
        observability_manager=observability_manager,
    )

    await telemetry.emit_service_completed(
        service_name="TechnicalService",
        request_name="TechnicalAnalysisRequest",
        duration_seconds=1.25,
        attributes={
            "symbol": "SPY",
        },
        payload={
            "technical_score": 0.42,
        },
    )

    assert len(sink.events) == 1

    event = sink.events[0]

    assert event.event_type == "application.service.completed"
    assert event.level == TelemetryEventLevel.INFO
    assert event.success is True
    assert event.duration_seconds == 1.25
    assert event.error_count == 0
    assert event.attributes["symbol"] == "SPY"
    assert event.payload["technical_score"] == 0.42


@pytest.mark.asyncio
async def test_application_service_telemetry_emits_service_failed_with_exception() -> (
    None
):
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()

    observability_manager.add_sink(
        sink,
    )

    telemetry = ApplicationServiceTelemetry(
        observability_manager=observability_manager,
    )

    error = RuntimeError(
        "provider failed",
    )

    await telemetry.emit_service_failed(
        service_name="TechnicalService",
        request_name="TechnicalAnalysisRequest",
        error=error,
        duration_seconds=0.75,
        attributes={
            "symbol": "SPY",
        },
    )

    assert len(sink.events) == 1

    event = sink.events[0]

    assert event.event_type == "application.service.failed"
    assert event.level == TelemetryEventLevel.ERROR
    assert event.success is False
    assert event.error_count == 1
    assert event.duration_seconds == 0.75
    assert event.payload["error_type"] == "RuntimeError"
    assert event.payload["error_message"] == "provider failed"
    assert event.attributes["symbol"] == "SPY"
    assert event.exception_details is not None
    assert event.exception_details.exception_type == "RuntimeError"
    assert event.exception_details.message == "provider failed"


@pytest.mark.asyncio
async def test_application_service_telemetry_emits_service_failed_with_string_error() -> (  # noqa: E501
    None
):
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()

    observability_manager.add_sink(
        sink,
    )

    telemetry = ApplicationServiceTelemetry(
        observability_manager=observability_manager,
    )

    await telemetry.emit_service_failed(
        service_name="TechnicalService",
        request_name="TechnicalAnalysisRequest",
        error="missing data",
    )

    assert len(sink.events) == 1

    event = sink.events[0]

    assert event.event_type == "application.service.failed"
    assert event.level == TelemetryEventLevel.ERROR
    assert event.success is False
    assert event.error_count == 1
    assert event.payload["error_type"] == "ApplicationServiceError"
    assert event.payload["error_message"] == "missing data"
    assert event.exception_details is None


@pytest.mark.asyncio
async def test_application_service_telemetry_emits_trace_context_attributes() -> None:
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()

    observability_manager.add_sink(
        sink,
    )

    telemetry = ApplicationServiceTelemetry(
        observability_manager=observability_manager,
    )
    context = TelemetryContext(
        workflow_id="workflow-1",
        execution_id="execution-1",
        runtime_id="runtime-1",
        node_name="technical_node",
        correlation_id="correlation-1",
        trace_id="trace-1",
        span_id="node-span-1",
        parent_span_id="workflow-span-1",
        tags=("morning_report",),
    )

    await telemetry.emit_service_completed(
        service_name="TechnicalService",
        request_name="TechnicalAnalysisRequest",
        duration_seconds=1.25,
        context=context,
    )

    assert len(sink.events) == 1

    event = sink.events[0]
    assert event.event_type == "application.service.completed"
    assert event.workflow_id == "workflow-1"
    assert event.execution_id == "execution-1"
    assert event.runtime_id == "runtime-1"
    assert event.node_name == "technical_node"
    assert event.correlation_id == "correlation-1"
    assert event.tags == ("morning_report",)
    assert event.trace_id == "trace-1"
    assert event.span_id == "node-span-1"
    assert event.parent_span_id == "workflow-span-1"
    assert event.attributes["trace_id"] == "trace-1"
    assert event.attributes["span_id"] == "node-span-1"
    assert event.attributes["parent_span_id"] == "workflow-span-1"


@pytest.mark.asyncio
async def test_application_service_telemetry_emits_service_cancelled() -> None:
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(sink)
    telemetry = ApplicationServiceTelemetry(
        observability_manager=observability_manager,
    )

    await telemetry.emit_service_cancelled(
        service_name="TechnicalService",
        request_name="TechnicalAnalysisRequest",
        duration_seconds=0.5,
    )

    event = sink.events[0]
    assert event.event_type == "application.service.cancelled"
    assert event.level == TelemetryEventLevel.WARNING
    assert event.success is False
    assert event.error_count == 0
    assert event.attributes["outcome"] == "cancelled"
    assert event.payload["outcome"] == "cancelled"
    metric_names = {
        point.name for point in observability_manager.metrics_store.points()
    }
    assert "application.service.calls.cancelled" in metric_names
    assert "application.service.calls.failed" not in metric_names
    assert "application.service.duration_seconds" in metric_names


@pytest.mark.asyncio
async def test_application_service_telemetry_emits_configuration_failure() -> None:
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(sink)
    telemetry = ApplicationServiceTelemetry(
        observability_manager=observability_manager,
    )

    await telemetry.emit_service_configuration_failed(
        service_name="TechnicalService",
        request_name="TechnicalAnalysisRequest",
        validation_errors=("max_attempts must be at least 1.",),
        attributes={"max_attempts": 0},
    )

    event = sink.events[0]
    assert event.event_type == "application.service.configuration_failed"
    assert event.level == TelemetryEventLevel.ERROR
    assert event.success is False
    assert event.error_count == 1
    assert event.exception_details is None
    assert event.attributes["max_attempts"] == 0
    assert event.payload["error_type"] == "ServiceRunnerConfigurationError"
    assert event.payload["validation_errors"] == ["max_attempts must be at least 1."]


@pytest.mark.asyncio
async def test_application_service_telemetry_emits_retry_scheduled() -> None:
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(sink)
    telemetry = ApplicationServiceTelemetry(
        observability_manager=observability_manager,
    )

    await telemetry.emit_service_retry_scheduled(
        service_name="TechnicalService",
        request_name="TechnicalAnalysisRequest",
        attempt=1,
        next_attempt=2,
        maximum_attempts=3,
        backoff_seconds=0.25,
        reason="temporary failure",
        error_type="RuntimeError",
    )

    event = sink.events[0]
    assert event.event_type == "application.service.retry_scheduled"
    assert event.level == TelemetryEventLevel.WARNING
    assert event.success is None
    assert event.error_count == 0
    assert event.exception_details is None
    assert event.payload["attempt"] == 1
    assert event.payload["next_attempt"] == 2
    assert event.payload["maximum_attempts"] == 3
    assert event.payload["backoff_seconds"] == 0.25
    assert event.payload["reason"] == "temporary failure"
    assert event.payload["error_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_application_service_telemetry_emits_degraded_success() -> None:
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(sink)
    telemetry = ApplicationServiceTelemetry(
        observability_manager=observability_manager,
    )

    await telemetry.emit_service_degraded(
        service_name="NewsService",
        request_name="NewsAnalysisRequest",
        duration_seconds=0.5,
        payload={"degradation_count": 1},
    )

    event = sink.events[0]
    assert event.event_type == "application.service.degraded"
    assert event.level == TelemetryEventLevel.WARNING
    assert event.success is True
    assert event.error_count == 0
    assert event.duration_seconds == 0.5
    assert event.payload["degradation_count"] == 1
