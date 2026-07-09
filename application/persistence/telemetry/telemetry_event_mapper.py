from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from math import isfinite
from typing import Any

from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.lineage import JsonValue
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.telemetry import AgentMetricRecord
from core.storage.persistence.telemetry import ProviderMetricRecord
from core.storage.persistence.telemetry import TelemetryEventRecord
from core.storage.persistence.telemetry import TelemetryPersistenceBundle
from core.storage.persistence.telemetry import TelemetryTraceRecord
from core.storage.persistence.telemetry import WorkflowMetricRecord
from core.storage.persistence.telemetry import new_agent_metric_id
from core.storage.persistence.telemetry import new_provider_metric_id
from core.storage.persistence.telemetry import new_telemetry_trace_record_id
from core.storage.persistence.telemetry import new_workflow_metric_id
from core.telemetry.events.telemetry_event import TelemetryEvent
from core.telemetry.tracing.operation_lifecycle import (
    is_terminal_operation_event,
)
from core.telemetry.tracing.operation_lifecycle import resolve_operation_name

_WORKFLOW_STARTED_EVENT = "runtime.workflow.started"
_WORKFLOW_COMPLETED_EVENT = "runtime.workflow.completed"
_WORKFLOW_FAILED_EVENT = "runtime.workflow.failed"
_PROVIDER_CALL_EVENT = "integration.provider.call"
_AGENT_SIGNAL_EVENT = "intelligence.agent.signal"


@dataclass(
    frozen=True,
    slots=True,
)
class TelemetryPersistenceMapper:
    """
    Convert core telemetry events into optional persistence records.

    The mapper is intentionally application-layer glue: JSONL runtime telemetry
    remains the default, while PostgreSQL persistence can opt into these typed
    records when a retention/volume policy enables it.
    """

    def map_event(
        self,
        event: TelemetryEvent,
    ) -> TelemetryPersistenceBundle:
        lineage = _lineage_from_event(
            event,
        )
        telemetry_record = _map_telemetry_event_record(
            event,
            lineage=lineage,
        )
        workflow_metric = _map_workflow_metric(
            event,
        )
        provider_metric = _map_provider_metric(
            event,
            lineage=lineage,
        )
        agent_metric = _map_agent_metric(
            event,
            lineage=lineage,
        )
        trace_record = _map_trace_record(
            event,
            lineage=lineage,
        )

        return TelemetryPersistenceBundle(
            events=(telemetry_record,),
            traces=_optional_tuple(trace_record),
            workflow_metrics=_optional_tuple(workflow_metric),
            agent_metrics=_optional_tuple(agent_metric),
            provider_metrics=_optional_tuple(provider_metric),
        )


def _map_telemetry_event_record(
    event: TelemetryEvent,
    *,
    lineage: PersistenceLineage,
) -> TelemetryEventRecord:
    trace_id = event.trace_id
    span_id = event.span_id
    exception_details = event.exception_details
    message = _lookup_text(
        event,
        "message",
    )
    if message is None and exception_details is not None:
        message = exception_details.message or None

    return TelemetryEventRecord(
        telemetry_event_id=event.event_id,
        event_type=event.event_type,
        source=event.source,
        timestamp=event.timestamp,
        lineage=lineage,
        severity=event.level.value,
        message=message,
        correlation_id=event.correlation_id,
        trace_id=trace_id,
        span_id=span_id,
        payload=_event_payload(event),
        metadata={
            "duration_seconds": event.duration_seconds,
            "success": event.success,
            "error_count": event.error_count,
            "tags": event.tags,
            "attributes": _to_json_object(event.attributes),
        },
    )


def _map_workflow_metric(
    event: TelemetryEvent,
) -> WorkflowMetricRecord | None:
    if event.event_type not in {
        _WORKFLOW_STARTED_EVENT,
        _WORKFLOW_COMPLETED_EVENT,
        _WORKFLOW_FAILED_EVENT,
    }:
        return None

    workflow_name = event.workflow_id
    if workflow_name is None:
        return None

    metric_name = "workflow.executions.total"
    metric_value = 1.0
    metric_unit = "count"
    duration_seconds = _valid_duration(event.duration_seconds)

    if duration_seconds is not None and event.event_type in {
        _WORKFLOW_COMPLETED_EVENT,
        _WORKFLOW_FAILED_EVENT,
    }:
        metric_name = "workflow.duration_seconds"
        metric_value = duration_seconds
        metric_unit = "seconds"

    if event.event_type == _WORKFLOW_FAILED_EVENT:
        status = "failed"
    elif event.success is False:
        status = "failed"
    elif event.event_type == _WORKFLOW_STARTED_EVENT:
        status = "started"
    else:
        status = "succeeded"

    return WorkflowMetricRecord(
        workflow_metric_id=new_workflow_metric_id(
            workflow_name=workflow_name,
            metric_name=metric_name,
            timestamp=event.timestamp,
            execution_id=event.execution_id,
        ),
        workflow_name=workflow_name,
        metric_name=metric_name,
        timestamp=event.timestamp,
        metric_value=metric_value,
        execution_id=event.execution_id,
        runtime_id=event.runtime_id,
        node_name=event.node_name,
        metric_unit=metric_unit,
        status=status,
        duration_seconds=duration_seconds,
        metadata=_event_metadata(event),
    )


def _map_provider_metric(
    event: TelemetryEvent,
    *,
    lineage: PersistenceLineage,
) -> ProviderMetricRecord | None:
    if event.event_type != _PROVIDER_CALL_EVENT:
        return None

    provider_name = _lookup_text(event, "provider_name") or "unknown_provider"
    provider_type = _lookup_text(event, "provider_type") or event.source
    duration_seconds = _valid_duration(event.duration_seconds)
    metric_name = "integration.provider.calls.total"
    metric_value = 1.0
    metric_unit = "count"
    if duration_seconds is not None:
        metric_name = "integration.provider.duration_seconds"
        metric_value = duration_seconds
        metric_unit = "seconds"

    return ProviderMetricRecord(
        provider_metric_id=new_provider_metric_id(
            provider_name=provider_name,
            provider_type=provider_type,
            metric_name=metric_name,
            timestamp=event.timestamp,
        ),
        provider_name=provider_name,
        provider_type=provider_type,
        metric_name=metric_name,
        timestamp=event.timestamp,
        metric_value=metric_value,
        lineage=lineage,
        metric_unit=metric_unit,
        endpoint=_lookup_text(event, "endpoint") or _lookup_text(event, "operation"),
        status_code=_lookup_int(event, "status_code"),
        success=event.success,
        correlation_id=event.correlation_id,
        metadata=_event_metadata(event),
    )


def _map_agent_metric(
    event: TelemetryEvent,
    *,
    lineage: PersistenceLineage,
) -> AgentMetricRecord | None:
    if event.event_type != _AGENT_SIGNAL_EVENT:
        return None

    agent_name = _lookup_text(event, "agent_name") or event.node_name
    if agent_name is None:
        agent_name = "unknown_agent"
    agent_type = _lookup_text(event, "agent_type") or event.source
    confidence = _lookup_float(event, "confidence")
    metric_name = "intelligence.agent.signals.total"
    metric_value = 1.0
    metric_unit = "count"
    if confidence is not None:
        metric_name = "intelligence.agent.confidence"
        metric_value = confidence
        metric_unit = "ratio"

    return AgentMetricRecord(
        agent_metric_id=new_agent_metric_id(
            agent_name=agent_name,
            agent_type=agent_type,
            metric_name=metric_name,
            timestamp=event.timestamp,
        ),
        agent_name=agent_name,
        agent_type=agent_type,
        metric_name=metric_name,
        timestamp=event.timestamp,
        metric_value=metric_value,
        lineage=lineage,
        metric_unit=metric_unit,
        model_name=_lookup_text(event, "model_name"),
        symbol=_lookup_text(event, "symbol"),
        universe=_lookup_text(event, "universe"),
        correlation_id=event.correlation_id,
        metadata=_event_metadata(event),
    )


def _map_trace_record(
    event: TelemetryEvent,
    *,
    lineage: PersistenceLineage,
) -> TelemetryTraceRecord | None:
    trace_id = event.trace_id
    span_id = event.span_id
    if trace_id is None or span_id is None:
        return None

    duration_seconds = _valid_duration(event.duration_seconds)
    terminal = is_terminal_operation_event(event)
    started_at = event.timestamp
    if duration_seconds is not None:
        started_at = event.timestamp - timedelta(seconds=duration_seconds)

    status = _trace_status(event, terminal=terminal)
    exception_details = event.exception_details

    return TelemetryTraceRecord(
        trace_record_id=new_telemetry_trace_record_id(
            trace_id=trace_id,
            span_id=span_id,
        ),
        trace_id=trace_id,
        span_id=span_id,
        operation_name=resolve_operation_name(event),
        source=event.source,
        started_at=started_at,
        lineage=lineage,
        parent_span_id=event.parent_span_id,
        ended_at=event.timestamp if terminal else None,
        duration_seconds=duration_seconds if terminal else None,
        status=status,
        correlation_id=event.correlation_id,
        terminal_event_id=event.event_id if terminal else None,
        exception_type=(
            exception_details.exception_type if exception_details is not None else None
        ),
        exception_message=(
            exception_details.message if exception_details is not None else None
        ),
        exception_stack_trace=(
            exception_details.stack_trace if exception_details is not None else None
        ),
        exception_stack_trace_truncated=(
            exception_details.stack_trace_truncated
            if exception_details is not None
            else False
        ),
        attributes=_to_json_object(event.attributes),
        metadata=_event_metadata(event),
    )


def _trace_status(
    event: TelemetryEvent,
    *,
    terminal: bool,
) -> str:
    if not terminal:
        return "running"
    if event.event_type.endswith(".cancelled"):
        return "cancelled"
    if event.success is False or event.error_count > 0 or event.exception_details:
        return "failed"
    return "succeeded"


def _lineage_from_event(
    event: TelemetryEvent,
) -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name=event.workflow_id,
        execution_id=event.execution_id,
        runtime_id=event.runtime_id,
        node_name=event.node_name,
    )


def _event_payload(
    event: TelemetryEvent,
) -> JsonObject:
    payload: dict[str, JsonValue] = dict(_to_json_object(event.payload))
    if event.exception_details is not None:
        payload["exception_details"] = _to_json_object(
            event.exception_details.to_dict()
        )
    return payload


def _event_metadata(
    event: TelemetryEvent,
) -> JsonObject:
    return {
        "duration_seconds": event.duration_seconds,
        "success": event.success,
        "error_count": event.error_count,
        "tags": event.tags,
        "payload": _to_json_object(event.payload),
        "attributes": _to_json_object(event.attributes),
    }


def _lookup_text(
    event: TelemetryEvent,
    key: str,
) -> str | None:
    value = _lookup(event, key)
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _lookup_float(
    event: TelemetryEvent,
    key: str,
) -> float | None:
    value = _lookup(event, key)
    if value is None:
        return None
    if not isinstance(value, str | int | float):
        return None
    try:
        numeric_value = float(value)
    except ValueError:
        return None
    if not isfinite(numeric_value):
        return None
    return numeric_value


def _lookup_int(
    event: TelemetryEvent,
    key: str,
) -> int | None:
    value = _lookup(event, key)
    if value is None:
        return None
    if not isinstance(value, str | int | float):
        return None
    try:
        numeric_value = int(value)
    except ValueError:
        return None
    if numeric_value < 0:
        return None
    return numeric_value


def _lookup(
    event: TelemetryEvent,
    key: str,
) -> object | None:
    if key in event.attributes:
        return event.attributes[key]
    if key in event.payload:
        return event.payload[key]
    return None


def _valid_duration(
    duration_seconds: float | None,
) -> float | None:
    if duration_seconds is None:
        return None
    if not isfinite(duration_seconds):
        return None
    if duration_seconds < 0.0:
        return None
    return duration_seconds


def _optional_tuple(
    record: object | None,
) -> tuple[Any, ...]:
    if record is None:
        return ()
    return (record,)


def _to_json_object(
    values: Mapping[str, Any],
) -> JsonObject:
    return {str(key): _to_json_value(value) for key, value in values.items()}


def _to_json_value(
    value: Any,
) -> JsonValue:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Mapping):
        return {
            str(key): _to_json_value(nested_value)
            for key, nested_value in value.items()
        }
    if isinstance(value, tuple | list):
        return tuple(_to_json_value(nested_value) for nested_value in value)
    return str(value)
