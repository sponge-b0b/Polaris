from __future__ import annotations

import pytest

from core.runtime.telemetry.runtime_telemetry import (
    RuntimeTelemetry,
    RuntimeTelemetryEvent,
    RuntimeTelemetryEventType,
)
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)
from core.telemetry.sinks.runtime_telemetry_sink import (
    CoreTelemetryRuntimeSink,
)
from core.telemetry.sinks.telemetry_sink import (
    InMemoryTelemetrySink,
)


@pytest.mark.asyncio
async def test_runtime_telemetry_flows_into_observability_pipeline() -> None:
    core_sink = InMemoryTelemetrySink()

    observability = ObservabilityManager()

    observability.add_sink(
        core_sink,
    )

    runtime_telemetry = RuntimeTelemetry()

    runtime_telemetry.add_sink(
        CoreTelemetryRuntimeSink(
            sink=observability,
        )
    )

    await runtime_telemetry.emit(
        RuntimeTelemetryEvent(
            event_type=RuntimeTelemetryEventType.WORKFLOW_COMPLETED,
            workflow_id="test_workflow",
            execution_id="test_execution",
            runtime_id="test_runtime",
            success=True,
            error_count=0,
            payload={
                "message": "workflow completed",
            },
        )
    )

    assert len(core_sink.events) == 1

    event = core_sink.events[0]

    assert event.event_type == "runtime.workflow.completed"
    assert event.source == "runtime"
    assert event.workflow_id == "test_workflow"
    assert event.execution_id == "test_execution"
    assert event.runtime_id == "test_runtime"
    assert event.success is True
    assert event.error_count == 0
    assert event.payload["message"] == "workflow completed"

    metrics = observability.metrics_store.to_dict()

    assert metrics["counters"]
    assert any(key.startswith("telemetry.events.total") for key in metrics["counters"])
