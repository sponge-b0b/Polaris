from __future__ import annotations

from core.runtime.telemetry.runtime_telemetry import RuntimeTelemetryEvent
from core.runtime.telemetry.runtime_telemetry import RuntimeTelemetryEventType
from core.telemetry.attribution.telemetry_attribution import TelemetryAttribution
from core.telemetry.attribution.telemetry_attribution import (
    TelemetryAttributionManager,
)
from core.telemetry.contracts import TelemetryEvent as ExportedTelemetryEvent
from core.telemetry.events.telemetry_exception_details import (
    MAX_TELEMETRY_EXCEPTION_MESSAGE_CHARACTERS,
)
from core.telemetry.events.telemetry_exception_details import (
    MAX_TELEMETRY_EXCEPTION_TYPE_CHARACTERS,
)
from core.telemetry.events.telemetry_exception_details import (
    MAX_TELEMETRY_STACK_TRACE_CHARACTERS,
)
from core.telemetry.events.telemetry_exception_details import (
    TELEMETRY_EXCEPTION_TEXT_TRUNCATION_MARKER,
)
from core.telemetry.events.telemetry_exception_details import (
    TELEMETRY_STACK_TRACE_TRUNCATION_MARKER,
)
from core.telemetry.events.telemetry_exception_details import (
    TelemetryExceptionDetails,
)
from core.telemetry.events.telemetry_event import TelemetryEvent
from core.telemetry.events.telemetry_event import TelemetryEventLevel
from core.telemetry.sinks.runtime_telemetry_sink import CoreTelemetryRuntimeSink
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink


def test_contract_package_exports_canonical_telemetry_event() -> None:
    assert ExportedTelemetryEvent is TelemetryEvent


def test_telemetry_event_round_trip_preserves_identity_trace_and_exception() -> None:
    exception_details = TelemetryExceptionDetails(
        exception_type="RuntimeError",
        message="provider unavailable",
        stack_trace="Traceback: provider unavailable",
    )
    event = TelemetryEvent(
        event_id="event-1",
        event_type="integration.provider.failed",
        source="integration",
        level=TelemetryEventLevel.ERROR,
        workflow_id="workflow-1",
        execution_id="execution-1",
        runtime_id="runtime-1",
        node_name="technical_node",
        correlation_id="correlation-1",
        trace_id="trace-1",
        span_id="span-1",
        parent_span_id="parent-1",
        success=False,
        error_count=1,
        exception_details=exception_details,
        attributes={"provider": "yfinance"},
        payload={"operation": "get_market_data"},
    )

    restored = TelemetryEvent.from_dict(event.to_dict())

    assert restored == event


def test_historical_event_deserialization_supplies_new_fields() -> None:
    restored = TelemetryEvent.from_dict(
        {
            "event_type": "runtime.workflow.completed",
            "source": "runtime",
            "level": "info",
            "attributes": {
                "trace_id": "legacy-trace",
                "span_id": "legacy-span",
                "parent_span_id": "legacy-parent",
            },
            "payload": {},
        }
    )

    assert restored.event_id
    assert restored.trace_id == "legacy-trace"
    assert restored.span_id == "legacy-span"
    assert restored.parent_span_id == "legacy-parent"
    assert restored.exception_details is None


def test_exception_details_sanitize_and_bound_stack_trace() -> None:
    try:
        raise RuntimeError(
            "password=super-secret "
            + ("failure context " * MAX_TELEMETRY_STACK_TRACE_CHARACTERS)
        )
    except RuntimeError as error:
        details = TelemetryExceptionDetails.from_exception(error)

    assert details.exception_type == "RuntimeError"
    assert "super-secret" not in details.message
    assert "super-secret" not in details.stack_trace
    assert details.stack_trace_truncated is True
    assert len(details.stack_trace) == MAX_TELEMETRY_STACK_TRACE_CHARACTERS
    assert details.stack_trace.endswith(TELEMETRY_STACK_TRACE_TRUNCATION_MARKER)


def test_exception_details_direct_construction_is_sanitized_and_bounded() -> None:
    details = TelemetryExceptionDetails(
        exception_type="X" * (MAX_TELEMETRY_EXCEPTION_TYPE_CHARACTERS * 2),
        message=(
            "password=super-secret "
            + ("failure context " * MAX_TELEMETRY_EXCEPTION_MESSAGE_CHARACTERS)
        ),
        stack_trace=(
            "token=super-secret "
            + ("trace context " * MAX_TELEMETRY_STACK_TRACE_CHARACTERS)
        ),
    )

    assert len(details.exception_type) == MAX_TELEMETRY_EXCEPTION_TYPE_CHARACTERS
    assert len(details.message) == MAX_TELEMETRY_EXCEPTION_MESSAGE_CHARACTERS
    assert details.message.endswith(TELEMETRY_EXCEPTION_TEXT_TRUNCATION_MARKER)
    assert len(details.stack_trace) == MAX_TELEMETRY_STACK_TRACE_CHARACTERS
    assert details.stack_trace.endswith(TELEMETRY_STACK_TRACE_TRUNCATION_MARKER)
    assert details.stack_trace_truncated is True
    assert "super-secret" not in details.message
    assert "super-secret" not in details.stack_trace


def test_attribution_preserves_canonical_event_fields() -> None:
    exception_details = TelemetryExceptionDetails(
        exception_type="ValueError",
        message="invalid response",
        stack_trace="traceback",
    )
    event = TelemetryEvent(
        event_id="event-1",
        event_type="test.failed",
        source="test",
        trace_id="trace-1",
        span_id="span-1",
        parent_span_id="parent-1",
        exception_details=exception_details,
    )

    attributed = TelemetryAttributionManager().apply(
        event,
        TelemetryAttribution(
            source="test",
            workflow_id="workflow-1",
        ),
    )

    assert attributed.event_id == "event-1"
    assert attributed.workflow_id == "workflow-1"
    assert attributed.trace_id == "trace-1"
    assert attributed.span_id == "span-1"
    assert attributed.parent_span_id == "parent-1"
    assert attributed.exception_details is exception_details


async def test_runtime_event_conversion_promotes_trace_identity() -> None:
    sink = InMemoryTelemetrySink()
    runtime_sink = CoreTelemetryRuntimeSink(sink=sink)

    await runtime_sink.emit(
        RuntimeTelemetryEvent(
            event_type=RuntimeTelemetryEventType.NODE_COMPLETED,
            workflow_id="workflow-1",
            execution_id="execution-1",
            runtime_id="runtime-1",
            node_name="node-1",
            payload={
                "trace_id": "trace-1",
                "span_id": "span-1",
                "parent_span_id": "parent-1",
                "correlation_id": "correlation-1",
            },
        )
    )

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.event_id
    assert event.trace_id == "trace-1"
    assert event.span_id == "span-1"
    assert event.parent_span_id == "parent-1"
    assert event.correlation_id == "correlation-1"
