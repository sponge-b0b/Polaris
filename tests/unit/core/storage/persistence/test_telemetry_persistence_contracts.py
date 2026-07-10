from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime
from datetime import timezone

import pytest

from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.telemetry import AgentMetricRecord
from core.storage.persistence.telemetry import ProviderMetricRecord
from core.storage.persistence.telemetry import TelemetryEventRecord
from core.storage.persistence.telemetry import TelemetryMetricRecord
from core.storage.persistence.telemetry import TelemetryPersistenceBundle
from core.storage.persistence.telemetry import TelemetryPersistenceResult
from core.storage.persistence.telemetry import TelemetryTraceRecord
from core.storage.persistence.telemetry import WorkflowMetricRecord
from core.storage.persistence.telemetry import new_agent_metric_id
from core.storage.persistence.telemetry import new_provider_metric_id
from core.storage.persistence.telemetry import new_telemetry_event_id
from core.storage.persistence.telemetry import new_telemetry_metric_id
from core.storage.persistence.telemetry import new_telemetry_trace_record_id
from core.storage.persistence.telemetry import new_workflow_metric_id


def test_telemetry_event_record_is_typed_immutable_and_operational() -> None:
    record = TelemetryEventRecord(
        telemetry_event_id="event-1",
        event_type="runtime.workflow.started",
        source="runtime",
        timestamp=_timestamp(),
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
        ),
        severity=" info ",
        message=" workflow started ",
        correlation_id=" corr-1 ",
        payload={"node": "start"},
        metadata={"operational": True},
    )

    assert record.source == "runtime"
    assert record.severity == "info"
    assert record.message == "workflow started"
    assert record.correlation_id == "corr-1"
    assert record.lineage.workflow_name == "morning_report"
    assert record.payload == {"node": "start"}
    assert record.metadata == {"operational": True}

    with pytest.raises(FrozenInstanceError):
        record.source = "rag"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        ("telemetry_event_id", {"telemetry_event_id": " "}),
        ("event_type", {"event_type": ""}),
        ("source", {"source": " "}),
    ],
)
def test_telemetry_event_record_validates_required_fields(
    field_name: str,
    kwargs: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "telemetry_event_id": "event-1",
        "event_type": "runtime.workflow.started",
        "source": "runtime",
        "timestamp": _timestamp(),
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        TelemetryEventRecord(**values)  # type: ignore[arg-type]


def test_generic_metric_record_preserves_dimensions_and_lineage() -> None:
    record = TelemetryMetricRecord(
        metric_id="metric-1",
        metric_name="runtime.node.duration",
        source="runtime",
        timestamp=_timestamp(),
        metric_value=1.25,
        metric_unit="seconds",
        metric_kind="histogram",
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
            node_name="macro",
        ),
        dimensions={"node_type": "analysis"},
    )

    assert record.metric_value == 1.25
    assert record.metric_unit == "seconds"
    assert record.metric_kind == "histogram"
    assert record.dimensions == {"node_type": "analysis"}
    assert record.lineage.node_name == "macro"


@pytest.mark.parametrize(
    "value",
    [float("inf"), float("-inf"), float("nan")],
)
def test_metric_records_reject_non_finite_values(
    value: float,
) -> None:
    with pytest.raises(ValueError, match="metric_value"):
        TelemetryMetricRecord(
            metric_id="metric-1",
            metric_name="runtime.node.duration",
            source="runtime",
            timestamp=_timestamp(),
            metric_value=value,
        )


def test_trace_record_validates_span_timing() -> None:
    started_at = _timestamp()
    ended_at = datetime(2026, 5, 30, 14, 1, tzinfo=timezone.utc)
    record = TelemetryTraceRecord(
        trace_record_id="trace-record-1",
        trace_id="trace-1",
        span_id="span-1",
        parent_span_id=" parent ",
        operation_name="workflow.execute",
        source="runtime",
        started_at=started_at,
        ended_at=ended_at,
        duration_seconds=60.0,
        status=" failed ",
        terminal_event_id=" terminal-event-1 ",
        exception_type=" RuntimeError ",
        exception_message=" failed operation ",
        exception_stack_trace=" traceback ",
        exception_stack_trace_truncated=True,
        attributes={"wave_index": 0},
    )

    assert record.parent_span_id == "parent"
    assert record.status == "failed"
    assert record.terminal_event_id == "terminal-event-1"
    assert record.exception_type == "RuntimeError"
    assert record.exception_message == "failed operation"
    assert record.exception_stack_trace == "traceback"
    assert record.exception_stack_trace_truncated is True
    assert record.ended_at == ended_at
    assert record.duration_seconds == 60.0

    with pytest.raises(ValueError, match="duration_seconds"):
        TelemetryTraceRecord(
            trace_record_id="trace-record-1",
            trace_id="trace-1",
            span_id="span-1",
            operation_name="workflow.execute",
            source="runtime",
            started_at=started_at,
            duration_seconds=-1.0,
        )

    with pytest.raises(ValueError, match="ended_at"):
        TelemetryTraceRecord(
            trace_record_id="trace-record-1",
            trace_id="trace-1",
            span_id="span-1",
            operation_name="workflow.execute",
            source="runtime",
            started_at=started_at,
            ended_at=datetime(2026, 5, 30, 13, tzinfo=timezone.utc),
        )


def test_workflow_agent_and_provider_metrics_validate_scope() -> None:
    workflow_metric = WorkflowMetricRecord(
        workflow_metric_id="workflow-metric-1",
        workflow_name=" morning_report ",
        execution_id=" exec-1 ",
        metric_name="duration",
        timestamp=_timestamp(),
        metric_value=2.5,
        duration_seconds=2.5,
    )
    agent_metric = AgentMetricRecord(
        agent_metric_id="agent-metric-1",
        agent_name="MacroAgent",
        agent_type="macro",
        metric_name="tokens.total",
        timestamp=_timestamp(),
        metric_value=1200.0,
        symbol=" spy ",
        universe="core",
    )
    provider_metric = ProviderMetricRecord(
        provider_metric_id="provider-metric-1",
        provider_name="FMP",
        provider_type="market_data",
        endpoint=" /quote ",
        metric_name="latency_ms",
        timestamp=_timestamp(),
        metric_value=85.0,
        status_code=200,
        success=True,
    )

    assert workflow_metric.workflow_name == "morning_report"
    assert workflow_metric.execution_id == "exec-1"
    assert agent_metric.symbol == "SPY"
    assert provider_metric.endpoint == "/quote"
    assert provider_metric.status_code == 200

    with pytest.raises(ValueError, match="status_code"):
        ProviderMetricRecord(
            provider_metric_id="provider-metric-1",
            provider_name="FMP",
            provider_type="market_data",
            metric_name="latency_ms",
            timestamp=_timestamp(),
            metric_value=85.0,
            status_code=-1,
        )


def test_telemetry_persistence_bundle_and_result_validate_state() -> None:
    event = TelemetryEventRecord(
        telemetry_event_id="event-1",
        event_type="runtime.workflow.started",
        source="runtime",
        timestamp=_timestamp(),
    )
    metric = TelemetryMetricRecord(
        metric_id="metric-1",
        metric_name="duration",
        source="runtime",
        timestamp=_timestamp(),
        metric_value=1.0,
    )
    bundle = TelemetryPersistenceBundle(
        events=(event,),
        metrics=(metric,),
    )
    success = TelemetryPersistenceResult.succeeded(
        primary_record_id=event.telemetry_event_id,
        records_persisted=2,
    )
    failure = TelemetryPersistenceResult.failed("database unavailable")

    assert bundle.events == (event,)
    assert bundle.metrics == (metric,)
    assert success.success is True
    assert success.records_persisted == 2
    assert failure.success is False

    with pytest.raises(ValueError, match="error"):
        TelemetryPersistenceResult.failed(" ")

    with pytest.raises(ValueError, match="successful"):
        TelemetryPersistenceResult(
            success=True,
            primary_record_id="event-1",
            error="unexpected",
        )

    with pytest.raises(ValueError, match="records_persisted"):
        TelemetryPersistenceResult(
            success=True,
            primary_record_id="event-1",
            records_persisted=-1,
        )


def test_telemetry_id_helpers_are_stable() -> None:
    timestamp = _timestamp()

    assert new_telemetry_event_id(
        source="runtime",
        event_type="runtime.workflow.started",
        timestamp=timestamp,
        correlation_id="corr-1",
    ) == (
        "telemetry_event:runtime:runtime.workflow.started:"
        "2026-05-30T14:00:00+00:00:corr-1"
    )
    assert (
        new_telemetry_metric_id(
            source="runtime",
            metric_name="duration",
            timestamp=timestamp,
            dimensions_key="node:macro",
        )
        == "telemetry_metric:runtime:duration:2026-05-30T14:00:00+00:00:node:macro"
    )
    assert (
        new_telemetry_trace_record_id(
            trace_id="trace-1",
            span_id="span-1",
        )
        == "telemetry_trace:trace-1:span-1"
    )
    assert (
        new_workflow_metric_id(
            workflow_name="morning_report",
            metric_name="duration",
            execution_id="exec-1",
            timestamp=timestamp,
        )
        == "workflow_metric:morning_report:duration:2026-05-30T14:00:00+00:00:exec-1"
    )
    assert (
        new_agent_metric_id(
            agent_name="MacroAgent",
            agent_type="macro",
            metric_name="tokens.total",
            timestamp=timestamp,
        )
        == "agent_metric:MacroAgent:macro:tokens.total:2026-05-30T14:00:00+00:00"
    )
    assert (
        new_provider_metric_id(
            provider_name="FMP",
            provider_type="market_data",
            metric_name="latency_ms",
            timestamp=timestamp,
        )
        == "provider_metric:FMP:market_data:latency_ms:2026-05-30T14:00:00+00:00"
    )


def _timestamp() -> datetime:
    return datetime(2026, 5, 30, 14, tzinfo=timezone.utc)
