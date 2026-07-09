from __future__ import annotations

import pytest

from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.emitters.telemetry_emitter import TelemetryEmitter
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from core.telemetry.tracing.trace_context import TraceContext


def test_telemetry_context_from_trace_context_carries_trace_identity() -> None:
    trace_context = TraceContext(
        trace_id="trace-1",
        span_id="span-1",
        parent_span_id="parent-1",
        workflow_id="workflow-1",
        execution_id="execution-1",
        runtime_id="runtime-1",
        node_name="node-1",
        correlation_id="correlation-1",
        attributes={
            "trace_source": "workflow",
        },
    )

    context = TelemetryContext.from_trace_context(
        trace_context,
        tags=("runtime",),
        attributes={
            "layer": "test",
        },
    )

    assert context.workflow_id == "workflow-1"
    assert context.execution_id == "execution-1"
    assert context.runtime_id == "runtime-1"
    assert context.node_name == "node-1"
    assert context.correlation_id == "correlation-1"
    assert context.tags == ("runtime",)
    assert context.trace_id == "trace-1"
    assert context.span_id == "span-1"
    assert context.parent_span_id == "parent-1"
    assert context.attributes == {
        "trace_source": "workflow",
        "layer": "test",
    }


def test_telemetry_context_merged_attributes_includes_canonical_trace_fields() -> None:
    context = TelemetryContext(
        attributes={
            "component": "service",
            "trace_id": "stale-trace",
        },
        trace_id="trace-1",
        span_id="span-1",
        parent_span_id="parent-1",
    )

    attributes = context.merged_attributes(
        {
            "operation": "analyze",
            "span_id": "stale-span",
        }
    )

    assert attributes == {
        "component": "service",
        "operation": "analyze",
        "trace_id": "trace-1",
        "span_id": "span-1",
        "parent_span_id": "parent-1",
    }


def test_telemetry_context_round_trips_to_trace_context() -> None:
    context = TelemetryContext(
        workflow_id="workflow-1",
        execution_id="execution-1",
        runtime_id="runtime-1",
        node_name="node-1",
        correlation_id="correlation-1",
        attributes={
            "component": "runtime",
        },
        trace_id="trace-1",
        span_id="span-1",
        parent_span_id="parent-1",
    )

    trace_context = context.to_trace_context()

    assert trace_context is not None
    assert trace_context.trace_id == "trace-1"
    assert trace_context.span_id == "span-1"
    assert trace_context.parent_span_id == "parent-1"
    assert trace_context.workflow_id == "workflow-1"
    assert trace_context.execution_id == "execution-1"
    assert trace_context.runtime_id == "runtime-1"
    assert trace_context.node_name == "node-1"
    assert trace_context.correlation_id == "correlation-1"
    assert trace_context.attributes == {
        "component": "runtime",
    }


def test_telemetry_context_without_trace_identity_does_not_create_trace_context() -> (
    None
):
    assert TelemetryContext().to_trace_context() is None


def test_telemetry_context_child_operation_creates_distinct_child_identity() -> None:
    parent = TelemetryContext(
        workflow_id="workflow-1",
        trace_id="trace-1",
        span_id="parent-span",
        attributes={"component": "runtime"},
    )

    child = parent.child_operation(
        attributes={"operation_kind": "provider_call"},
    )

    assert child.trace_id == "trace-1"
    assert child.span_id is not None
    assert child.span_id != "parent-span"
    assert child.parent_span_id == "parent-span"
    assert child.attributes == {
        "component": "runtime",
        "operation_kind": "provider_call",
    }


def test_telemetry_context_child_operation_creates_root_when_untraced() -> None:
    child = TelemetryContext(
        correlation_id="correlation-1",
        tags=("standalone",),
    ).child_operation(
        attributes={"operation_kind": "provider_call"},
    )

    assert child.trace_id is not None
    assert child.span_id is not None
    assert child.parent_span_id is None
    assert child.correlation_id == "correlation-1"
    assert child.tags == ("standalone",)
    assert child.attributes == {"operation_kind": "provider_call"}


@pytest.mark.asyncio
async def test_observability_manager_trace_context_emits_trace_attributes() -> None:
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(
        sink,
    )
    trace_context = observability_manager.create_trace_context(
        workflow_id="workflow-1",
        execution_id="execution-1",
        runtime_id="runtime-1",
        node_name="node-1",
        correlation_id="correlation-1",
        attributes={
            "component": "runtime",
        },
    )

    await observability_manager.info(
        event_type="runtime.workflow.started",
        source="runtime",
        trace_context=trace_context,
    )

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.workflow_id == "workflow-1"
    assert event.execution_id == "execution-1"
    assert event.runtime_id == "runtime-1"
    assert event.node_name == "node-1"
    assert event.correlation_id == "correlation-1"
    assert event.trace_id == trace_context.trace_id
    assert event.span_id == trace_context.span_id
    assert event.parent_span_id == trace_context.parent_span_id
    assert event.attributes["component"] == "runtime"
    assert event.attributes["trace_id"] == trace_context.trace_id
    assert event.attributes["span_id"] == trace_context.span_id


@pytest.mark.asyncio
async def test_telemetry_emitter_emits_trace_attributes_from_telemetry_context() -> (
    None
):
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(
        sink,
    )
    emitter = TelemetryEmitter(
        observability_manager=observability_manager,
        source="test",
    )

    await emitter.emit(
        event_type="test.event",
        context=TelemetryContext(
            workflow_id="workflow-1",
            trace_id="trace-1",
            span_id="span-1",
            parent_span_id="parent-1",
        ),
    )

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.workflow_id == "workflow-1"
    assert event.trace_id == "trace-1"
    assert event.span_id == "span-1"
    assert event.parent_span_id == "parent-1"
    assert event.attributes["trace_id"] == "trace-1"
    assert event.attributes["span_id"] == "span-1"
    assert event.attributes["parent_span_id"] == "parent-1"
