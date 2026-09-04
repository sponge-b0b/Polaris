from __future__ import annotations

from datetime import UTC, datetime

from core.database.models.telemetry import (
    AgentMetricModel,
    ProviderMetricModel,
    TelemetryEventModel,
    TelemetryMetricModel,
    TelemetryTraceModel,
    WorkflowMetricModel,
)
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.serializers.telemetry_persistence_serializer import (
    TelemetryPersistenceSerializer,
)
from core.storage.persistence.telemetry import (
    AgentMetricRecord,
    ProviderMetricRecord,
    TelemetryEventRecord,
    TelemetryMetricRecord,
    TelemetryTraceRecord,
    WorkflowMetricRecord,
)


def test_telemetry_serializer_converts_event_records() -> None:
    record = _event()

    values = TelemetryPersistenceSerializer.event_values(record)
    round_trip = TelemetryPersistenceSerializer.event_from_model(
        TelemetryEventModel(**values)
    )

    assert values["telemetry_event_id"] == "event-1"
    assert values["payload"] == {
        "status": "failed",
        "exception_details": {
            "exception_type": "RuntimeError",
            "message": "provider failed",
            "stack_trace": "traceback",
            "stack_trace_truncated": False,
        },
    }
    assert values["metadata_payload"] == {"source": "unit-test"}
    assert values["workflow_name"] == "morning_report"
    assert round_trip == record


def test_telemetry_serializer_converts_generic_metric_records() -> None:
    record = _metric()

    values = TelemetryPersistenceSerializer.metric_values(record)
    round_trip = TelemetryPersistenceSerializer.metric_from_model(
        TelemetryMetricModel(**values)
    )

    assert values["metric_id"] == "metric-1"
    assert values["dimensions"] == {"phase": "node"}
    assert values["metadata_payload"] == {"source": "unit-test"}
    assert values["correlation_id"] == "corr-1"
    assert round_trip == record


def test_telemetry_serializer_converts_trace_records() -> None:
    record = _trace()

    values = TelemetryPersistenceSerializer.trace_values(record)
    round_trip = TelemetryPersistenceSerializer.trace_from_model(
        TelemetryTraceModel(**values)
    )

    assert values["trace_record_id"] == "trace-record-1"
    assert values["trace_id"] == "trace-1"
    assert values["span_id"] == "span-1"
    assert values["terminal_event_id"] == "event-terminal-1"
    assert values["exception_type"] == "RuntimeError"
    assert values["exception_message"] == "provider failed"
    assert values["exception_stack_trace"] == "traceback"
    assert values["exception_stack_trace_truncated"] is False
    assert values["attributes"] == {"node": "macro"}
    assert values["metadata_payload"] == {"source": "unit-test"}
    assert round_trip == record


def test_telemetry_serializer_converts_workflow_metrics() -> None:
    record = _workflow_metric()

    values = TelemetryPersistenceSerializer.workflow_metric_values(record)
    round_trip = TelemetryPersistenceSerializer.workflow_metric_from_model(
        WorkflowMetricModel(**values)
    )

    assert values["workflow_metric_id"] == "workflow-metric-1"
    assert values["workflow_name"] == "morning_report"
    assert values["duration_seconds"] == 3.5
    assert values["metadata_payload"] == {"source": "unit-test"}
    assert round_trip == record


def test_telemetry_serializer_converts_agent_metrics() -> None:
    record = _agent_metric()

    values = TelemetryPersistenceSerializer.agent_metric_values(record)
    round_trip = TelemetryPersistenceSerializer.agent_metric_from_model(
        AgentMetricModel(**values)
    )

    assert values["agent_metric_id"] == "agent-metric-1"
    assert values["agent_name"] == "MacroAgent"
    assert values["symbol"] == "SPY"
    assert values["metadata_payload"] == {"source": "unit-test"}
    assert round_trip == record


def test_telemetry_serializer_converts_provider_metrics() -> None:
    record = _provider_metric()

    values = TelemetryPersistenceSerializer.provider_metric_values(record)
    round_trip = TelemetryPersistenceSerializer.provider_metric_from_model(
        ProviderMetricModel(**values)
    )

    assert values["provider_metric_id"] == "provider-metric-1"
    assert values["provider_name"] == "fred"
    assert values["endpoint"] == "series/observations"
    assert values["success"] is True
    assert values["metadata_payload"] == {"source": "unit-test"}
    assert round_trip == record


def _timestamp() -> datetime:
    return datetime(2026, 6, 1, 12, tzinfo=UTC)


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="macro",
    )


def _event() -> TelemetryEventRecord:
    return TelemetryEventRecord(
        telemetry_event_id="event-1",
        event_type="workflow_control.pause_requested",
        source="runtime",
        timestamp=_timestamp(),
        lineage=_lineage(),
        severity="info",
        message="Pause requested.",
        correlation_id="corr-1",
        trace_id="trace-1",
        span_id="span-1",
        payload={
            "status": "failed",
            "exception_details": {
                "exception_type": "RuntimeError",
                "message": "provider failed",
                "stack_trace": "traceback",
                "stack_trace_truncated": False,
            },
        },
        metadata={"source": "unit-test"},
    )


def _metric() -> TelemetryMetricRecord:
    return TelemetryMetricRecord(
        metric_id="metric-1",
        metric_name="runtime.node.duration",
        source="runtime",
        timestamp=_timestamp(),
        metric_value=1.25,
        lineage=_lineage(),
        metric_unit="seconds",
        metric_kind="duration",
        correlation_id="corr-1",
        dimensions={"phase": "node"},
        metadata={"source": "unit-test"},
    )


def _trace() -> TelemetryTraceRecord:
    return TelemetryTraceRecord(
        trace_record_id="trace-record-1",
        trace_id="trace-1",
        span_id="span-1",
        operation_name="execute_node",
        source="runtime",
        started_at=_timestamp(),
        lineage=_lineage(),
        parent_span_id="parent-span",
        ended_at=datetime(2026, 6, 1, 12, 0, 1, tzinfo=UTC),
        duration_seconds=1.0,
        status="failed",
        correlation_id="corr-1",
        terminal_event_id="event-terminal-1",
        exception_type="RuntimeError",
        exception_message="provider failed",
        exception_stack_trace="traceback",
        exception_stack_trace_truncated=False,
        attributes={"node": "macro"},
        metadata={"source": "unit-test"},
    )


def _workflow_metric() -> WorkflowMetricRecord:
    return WorkflowMetricRecord(
        workflow_metric_id="workflow-metric-1",
        workflow_name="morning_report",
        metric_name="workflow.duration",
        timestamp=_timestamp(),
        metric_value=3.5,
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="macro",
        metric_unit="seconds",
        status="succeeded",
        duration_seconds=3.5,
        metadata={"source": "unit-test"},
    )


def _agent_metric() -> AgentMetricRecord:
    return AgentMetricRecord(
        agent_metric_id="agent-metric-1",
        agent_name="MacroAgent",
        agent_type="macro",
        metric_name="agent.tokens",
        timestamp=_timestamp(),
        metric_value=100.0,
        lineage=_lineage(),
        metric_unit="tokens",
        model_name="gpt-test",
        symbol="spy",
        universe="us_equities",
        correlation_id="corr-1",
        metadata={"source": "unit-test"},
    )


def _provider_metric() -> ProviderMetricRecord:
    return ProviderMetricRecord(
        provider_metric_id="provider-metric-1",
        provider_name="fred",
        provider_type="macro",
        metric_name="provider.latency",
        timestamp=_timestamp(),
        metric_value=0.25,
        lineage=_lineage(),
        metric_unit="seconds",
        endpoint="series/observations",
        status_code=200,
        success=True,
        correlation_id="corr-1",
        metadata={"source": "unit-test"},
    )
