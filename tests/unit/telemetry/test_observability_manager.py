from __future__ import annotations

import pytest

from core.telemetry.events.telemetry_event import TelemetryEvent
from core.telemetry.events.telemetry_event import TelemetryEventLevel
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink


@pytest.mark.asyncio
async def test_observability_manager_correlates_events_and_records_metrics() -> None:
    sink = InMemoryTelemetrySink()
    manager = ObservabilityManager()
    manager.add_sink(sink)
    trace = manager.create_trace_context(
        workflow_id="workflow-1",
        execution_id="execution-1",
        runtime_id="runtime-1",
        node_name="node-1",
        correlation_id="correlation-1",
        attributes={"scope": "test"},
    )

    await manager.info(
        event_type="test.started",
        source="test",
        trace_context=trace,
    )
    await manager.error(
        event_type="test.failed",
        source="test",
        trace_context=trace,
        payload={"reason": "expected"},
    )
    await manager.emit(
        TelemetryEvent(
            event_type="test.duration",
            source="test",
            level=TelemetryEventLevel.INFO,
            duration_seconds=0.25,
            success=True,
        )
    )

    assert len(sink.events) == 3
    started = sink.events[0]
    assert started.workflow_id == "workflow-1"
    assert started.execution_id == "execution-1"
    assert started.runtime_id == "runtime-1"
    assert started.node_name == "node-1"
    assert started.correlation_id == "correlation-1"
    assert started.attributes["scope"] == "test"
    assert started.attributes["trace_id"] == trace.trace_id
    assert started.attributes["span_id"] == trace.span_id

    points = manager.metrics_store.points()
    names = [point.name for point in points]
    assert names.count("telemetry.events.total") == 3
    assert "telemetry.events.errors" in names
    assert "telemetry.event.duration_seconds" in names


def test_observability_manager_delegates_sink_lifecycle() -> None:
    class LifecycleSink(InMemoryTelemetrySink):
        def __init__(self) -> None:
            super().__init__()
            self.flush_count = 0
            self.shutdown_count = 0

        def force_flush(self) -> None:
            self.flush_count += 1

        def shutdown(self) -> None:
            self.shutdown_count += 1

    sink = LifecycleSink()
    manager = ObservabilityManager()
    manager.add_sink(sink)

    manager.force_flush()
    manager.shutdown()

    assert sink.flush_count == 1
    assert sink.shutdown_count == 1


@pytest.mark.asyncio
async def test_observability_manager_exposes_collector_sink_failure_metric() -> None:
    class FailingSink:
        async def emit(self, event: TelemetryEvent) -> None:
            del event
            raise RuntimeError("expected sink failure")

    manager = ObservabilityManager()
    manager.add_sink(FailingSink())

    await manager.emit(
        TelemetryEvent(
            event_type="test.failed",
            source="test",
        )
    )

    failure_points = [
        point
        for point in manager.metrics_store.points()
        if point.name == "telemetry.sink.failures"
    ]
    assert len(failure_points) == 1
    assert failure_points[0].attributes == {
        "component_name": "FailingSink",
        "operation": "emit",
        "outcome": "failed",
    }
