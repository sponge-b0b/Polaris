from __future__ import annotations

from datetime import UTC, datetime, timedelta

from application.persistence.telemetry.telemetry_event_mapper import (
    TelemetryPersistenceMapper,
)
from core.telemetry.events.telemetry_event import TelemetryEvent, TelemetryEventLevel
from core.telemetry.events.telemetry_exception_details import (
    TelemetryExceptionDetails,
)


def test_mapper_maps_workflow_completed_event_to_event_and_workflow_metric() -> None:
    timestamp = datetime(2026, 1, 2, 14, 30, tzinfo=UTC)
    event = TelemetryEvent(
        event_type="runtime.workflow.completed",
        source="runtime.engine",
        timestamp=timestamp,
        level=TelemetryEventLevel.INFO,
        workflow_id="morning_report",
        execution_id="exec-123",
        runtime_id="runtime-456",
        node_name="finalize_report",
        correlation_id="corr-789",
        trace_id="trace-1",
        span_id="span-1",
        parent_span_id="workflow-span-1",
        duration_seconds=12.345678,
        success=True,
        attributes={
            "message": "workflow completed",
        },
        payload={
            "record_count": 4,
        },
    )

    bundle = TelemetryPersistenceMapper().map_event(
        event,
    )

    assert len(bundle.events) == 1
    telemetry_event = bundle.events[0]
    assert telemetry_event.telemetry_event_id == event.event_id
    assert telemetry_event.event_type == "runtime.workflow.completed"
    assert telemetry_event.source == "runtime.engine"
    assert telemetry_event.severity == "info"
    assert telemetry_event.message == "workflow completed"
    assert telemetry_event.correlation_id == "corr-789"
    assert telemetry_event.trace_id == "trace-1"
    assert telemetry_event.span_id == "span-1"
    assert telemetry_event.lineage.workflow_name == "morning_report"
    assert telemetry_event.lineage.execution_id == "exec-123"
    assert telemetry_event.metadata["duration_seconds"] == 12.345678
    assert telemetry_event.payload["record_count"] == 4

    assert len(bundle.workflow_metrics) == 1
    workflow_metric = bundle.workflow_metrics[0]
    assert workflow_metric.workflow_name == "morning_report"
    assert workflow_metric.metric_name == "workflow.duration_seconds"
    assert workflow_metric.metric_value == 12.345678
    assert workflow_metric.metric_unit == "seconds"
    assert workflow_metric.status == "succeeded"
    assert workflow_metric.execution_id == "exec-123"
    assert workflow_metric.runtime_id == "runtime-456"
    assert workflow_metric.node_name == "finalize_report"

    assert len(bundle.traces) == 1
    trace = bundle.traces[0]
    assert trace.trace_id == "trace-1"
    assert trace.span_id == "span-1"
    assert trace.parent_span_id == "workflow-span-1"
    assert trace.operation_name == "runtime.workflow"
    assert trace.started_at == timestamp - timedelta(seconds=12.345678)
    assert trace.ended_at == timestamp
    assert trace.duration_seconds == 12.345678
    assert trace.status == "succeeded"
    assert trace.terminal_event_id == event.event_id


def test_mapper_maps_provider_call_event_to_provider_metric() -> None:
    timestamp = datetime(2026, 1, 2, 14, 31, tzinfo=UTC)
    event = TelemetryEvent(
        event_type="integration.provider.call",
        source="integration.provider",
        timestamp=timestamp,
        workflow_id="morning_report",
        execution_id="exec-123",
        correlation_id="corr-789",
        duration_seconds=0.876543,
        success=False,
        attributes={
            "provider_name": "alpaca",
            "provider_type": "portfolio",
            "endpoint": "get_portfolio_history",
            "status_code": 503,
        },
    )

    bundle = TelemetryPersistenceMapper().map_event(
        event,
    )

    assert len(bundle.provider_metrics) == 1
    provider_metric = bundle.provider_metrics[0]
    assert provider_metric.provider_name == "alpaca"
    assert provider_metric.provider_type == "portfolio"
    assert provider_metric.metric_name == "integration.provider.duration_seconds"
    assert provider_metric.metric_value == 0.876543
    assert provider_metric.metric_unit == "seconds"
    assert provider_metric.endpoint == "get_portfolio_history"
    assert provider_metric.status_code == 503
    assert provider_metric.success is False
    assert provider_metric.correlation_id == "corr-789"
    assert provider_metric.lineage.workflow_name == "morning_report"
    assert provider_metric.lineage.execution_id == "exec-123"


def test_mapper_maps_agent_signal_event_to_agent_metric() -> None:
    timestamp = datetime(2026, 1, 2, 14, 32, tzinfo=UTC)
    event = TelemetryEvent(
        event_type="intelligence.agent.signal",
        source="intelligence.agent",
        timestamp=timestamp,
        workflow_id="morning_report",
        execution_id="exec-123",
        node_name="technical_agent",
        correlation_id="corr-789",
        attributes={
            "agent_name": "technical_agent",
            "agent_type": "technical",
            "confidence": 0.812345,
            "model_name": "local-rule-engine",
            "symbol": "spy",
            "universe": "core_watchlist",
        },
    )

    bundle = TelemetryPersistenceMapper().map_event(
        event,
    )

    assert len(bundle.agent_metrics) == 1
    agent_metric = bundle.agent_metrics[0]
    assert agent_metric.agent_name == "technical_agent"
    assert agent_metric.agent_type == "technical"
    assert agent_metric.metric_name == "intelligence.agent.confidence"
    assert agent_metric.metric_value == 0.812345
    assert agent_metric.metric_unit == "ratio"
    assert agent_metric.model_name == "local-rule-engine"
    assert agent_metric.symbol == "SPY"
    assert agent_metric.universe == "core_watchlist"
    assert agent_metric.correlation_id == "corr-789"
    assert agent_metric.lineage.workflow_name == "morning_report"
    assert agent_metric.lineage.execution_id == "exec-123"


def test_mapper_assembles_start_and_failed_events_for_one_canonical_span() -> None:
    started_at = datetime(2026, 1, 2, 14, 30, tzinfo=UTC)
    started = TelemetryEvent(
        event_id="event-started",
        event_type="application.service.started",
        source="application.service",
        timestamp=started_at,
        trace_id="trace-1",
        span_id="span-1",
        parent_span_id="parent-1",
    )
    failed = TelemetryEvent(
        event_id="event-failed",
        event_type="application.service.failed",
        source="application.service",
        timestamp=started_at + timedelta(seconds=0.5),
        duration_seconds=0.5,
        success=False,
        exception_details=TelemetryExceptionDetails(
            exception_type="RuntimeError",
            message="service failed",
            stack_trace="traceback",
            stack_trace_truncated=False,
        ),
        trace_id="trace-1",
        span_id="span-1",
        parent_span_id="parent-1",
    )

    started_bundle = TelemetryPersistenceMapper().map_event(started)
    failed_bundle = TelemetryPersistenceMapper().map_event(failed)

    assert started_bundle.events[0].telemetry_event_id == "event-started"
    assert failed_bundle.events[0].telemetry_event_id == "event-failed"
    assert (
        started_bundle.traces[0].trace_record_id
        == failed_bundle.traces[0].trace_record_id
    )
    assert started_bundle.traces[0].operation_name == "application.service"
    assert started_bundle.traces[0].started_at == started_at
    assert started_bundle.traces[0].ended_at is None
    assert started_bundle.traces[0].status == "running"

    terminal_trace = failed_bundle.traces[0]
    assert terminal_trace.operation_name == "application.service"
    assert terminal_trace.started_at == started_at
    assert terminal_trace.ended_at == started_at + timedelta(seconds=0.5)
    assert terminal_trace.status == "failed"
    assert terminal_trace.terminal_event_id == "event-failed"
    assert terminal_trace.exception_type == "RuntimeError"
    assert terminal_trace.exception_message == "service failed"
    assert terminal_trace.exception_stack_trace == "traceback"
    assert terminal_trace.exception_stack_trace_truncated is False


def test_mapper_persists_typed_exception_in_event_payload_and_message() -> None:
    event = TelemetryEvent(
        event_id="event-failed",
        event_type="application.service.failed",
        source="application.service",
        level=TelemetryEventLevel.ERROR,
        trace_id="trace-1",
        span_id="span-1",
        success=False,
        exception_details=TelemetryExceptionDetails(
            exception_type="RuntimeError",
            message="password=super-secret provider failed",
            stack_trace="token=super-secret traceback",
        ),
        payload={"attempt": 2},
    )

    record = TelemetryPersistenceMapper().map_event(event).events[0]

    assert record.telemetry_event_id == "event-failed"
    assert record.trace_id == "trace-1"
    assert record.span_id == "span-1"
    assert record.message == "password=[REDACTED] provider failed"
    assert record.payload == {
        "attempt": 2,
        "exception_details": {
            "exception_type": "RuntimeError",
            "message": "password=[REDACTED] provider failed",
            "stack_trace": "token=[REDACTED] traceback",
            "stack_trace_truncated": False,
        },
    }


def test_mapper_prefers_explicit_event_message_over_exception_message() -> None:
    event = TelemetryEvent(
        event_type="application.service.failed",
        source="application.service",
        attributes={"message": "service execution failed"},
        exception_details=TelemetryExceptionDetails(
            exception_type="RuntimeError",
            message="provider failed",
            stack_trace="traceback",
        ),
    )

    record = TelemetryPersistenceMapper().map_event(event).events[0]

    assert record.message == "service execution failed"
    assert record.payload["exception_details"] == {
        "exception_type": "RuntimeError",
        "message": "provider failed",
        "stack_trace": "traceback",
        "stack_trace_truncated": False,
    }
