from __future__ import annotations

from datetime import datetime
from datetime import timezone

import pytest

from core.runtime.events import RuntimeEvent
from core.runtime.events import RuntimeEventType
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.runtime.telemetry.runtime_telemetry import InMemoryRuntimeTelemetrySink
from core.runtime.telemetry.runtime_telemetry import RuntimeTelemetry
from core.runtime.telemetry.runtime_telemetry import RuntimeTelemetryEventType
from core.runtime.telemetry.runtime_telemetry_hook import RuntimeTelemetryHook
from core.telemetry.tracing.trace_context import TraceContext
from core.workflow.models.workflow_execution_plan import ExecutionPlanNode
from core.workflow.models.workflow_execution_plan import ExecutionWave
from core.workflow.models.workflow_execution_plan import WorkflowExecutionPlan


@pytest.mark.asyncio
async def test_workflow_lifecycle_telemetry_carries_root_trace_context() -> None:
    sink = InMemoryRuntimeTelemetrySink()
    hook = RuntimeTelemetryHook(
        telemetry=RuntimeTelemetry(
            sinks=[
                sink,
            ],
        ),
    )
    trace_context = TraceContext(
        trace_id="trace-1",
        span_id="span-1",
        workflow_id="morning_report",
        execution_id="execution-1",
        runtime_id="runtime-1",
    )
    context = RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="execution-1",
        trace_context=trace_context,
    )
    execution_plan = WorkflowExecutionPlan(
        workflow_name="morning_report",
        execution_id="execution-1",
        nodes={
            "node-1": ExecutionPlanNode(
                name="node-1",
                node_type="test",
            ),
        },
        waves=(
            ExecutionWave(
                index=0,
                nodes=("node-1",),
            ),
        ),
    )

    await hook.before_workflow_execute(
        context=context,
        execution_plan=execution_plan,
    )
    await hook.after_workflow_execute(
        context=context,
        execution_plan=execution_plan,
    )

    assert [event.event_type for event in sink.events] == [
        RuntimeTelemetryEventType.WORKFLOW_STARTED,
        RuntimeTelemetryEventType.WORKFLOW_COMPLETED,
    ]
    assert sink.events[0].payload["trace_id"] == "trace-1"
    assert sink.events[0].payload["span_id"] == "span-1"
    assert sink.events[1].payload["trace_id"] == "trace-1"
    assert sink.events[1].payload["span_id"] == "span-1"


@pytest.mark.asyncio
async def test_wave_lifecycle_telemetry_carries_root_trace_context() -> None:
    sink = InMemoryRuntimeTelemetrySink()
    hook = RuntimeTelemetryHook(
        telemetry=RuntimeTelemetry(
            sinks=[
                sink,
            ],
        ),
    )
    trace_context = TraceContext(
        trace_id="trace-1",
        span_id="span-1",
        workflow_id="morning_report",
        execution_id="execution-1",
        runtime_id="runtime-1",
    )
    context = RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="execution-1",
        trace_context=trace_context,
    )
    execution_plan = WorkflowExecutionPlan(
        workflow_name="morning_report",
        execution_id="execution-1",
        nodes={},
        waves=(),
    )
    wave = ExecutionWave(
        index=0,
        nodes=("node-1",),
    )

    await hook.before_wave_execute(context, execution_plan, wave)
    await hook.after_wave_execute(context, execution_plan, wave)

    assert [event.event_type for event in sink.events] == [
        RuntimeTelemetryEventType.WAVE_STARTED,
        RuntimeTelemetryEventType.WAVE_COMPLETED,
    ]
    for event in sink.events:
        assert event.payload["trace_id"] == "trace-1"
        assert event.payload["span_id"] == "span-1"


@pytest.mark.asyncio
async def test_node_lifecycle_telemetry_carries_child_trace_context() -> None:
    sink = InMemoryRuntimeTelemetrySink()
    hook = RuntimeTelemetryHook(
        telemetry=RuntimeTelemetry(
            sinks=[
                sink,
            ],
        ),
    )
    root_trace_context = TraceContext(
        trace_id="trace-1",
        span_id="root-span",
        workflow_id="morning_report",
        execution_id="execution-1",
        runtime_id="runtime-1",
    )
    child_trace_context = root_trace_context.child(
        node_name="node-1",
        attributes={
            "node_type": "test",
            "trace_scope": "runtime_node",
        },
    )
    context = RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="execution-1",
        trace_context=child_trace_context,
    )
    plan_node = ExecutionPlanNode(
        name="node-1",
        node_type="test",
    )

    await hook.before_node_execute(
        context=context,
        plan_node=plan_node,
    )
    await hook.after_node_execute(
        context=context,
        plan_node=plan_node,
        output=RuntimeNodeOutput.success_output(
            outputs={
                "ok": True,
            },
            execution_metadata={
                "wave_index": 0,
            },
        ),
    )

    assert [event.event_type for event in sink.events] == [
        RuntimeTelemetryEventType.NODE_STARTED,
        RuntimeTelemetryEventType.NODE_COMPLETED,
    ]

    for event in sink.events:
        assert event.payload["trace_id"] == "trace-1"
        assert event.payload["span_id"] == child_trace_context.span_id
        assert event.payload["parent_span_id"] == "root-span"


@pytest.mark.asyncio
async def test_runtime_telemetry_hook_maps_workflow_control_events() -> None:
    sink = InMemoryRuntimeTelemetrySink()
    hook = RuntimeTelemetryHook(
        telemetry=RuntimeTelemetry(
            sinks=[
                sink,
            ],
        ),
    )

    await hook.on_runtime_event(
        RuntimeEvent(
            event_type=RuntimeEventType.WORKFLOW_PROGRESS_PAUSING,
            workflow_id="morning_report",
            execution_id="execution-1",
            runtime_id="runtime-1",
            payload={
                "state": "pausing",
                "reason": "operator requested pause",
                "requested_by": "cli",
            },
        )
    )
    await hook.on_runtime_event(
        RuntimeEvent(
            event_type=RuntimeEventType.WORKFLOW_PROGRESS_PAUSED,
            workflow_id="morning_report",
            execution_id="execution-1",
            runtime_id="runtime-1",
            payload={
                "state": "paused",
            },
        )
    )
    await hook.on_runtime_event(
        RuntimeEvent(
            event_type=RuntimeEventType.WORKFLOW_PROGRESS_RESUMING,
            workflow_id="morning_report",
            execution_id="execution-1",
            runtime_id="runtime-1",
            payload={
                "state": "resuming",
                "reason": "operator requested resume",
                "requested_by": "cli",
            },
        )
    )
    await hook.on_runtime_event(
        RuntimeEvent(
            event_type=RuntimeEventType.WORKFLOW_PROGRESS_RESUMED,
            workflow_id="morning_report",
            execution_id="execution-1",
            runtime_id="runtime-1",
            payload={
                "state": "running",
                "previous_state": "resuming",
            },
        )
    )
    await hook.on_runtime_event(
        RuntimeEvent(
            event_type=RuntimeEventType.WORKFLOW_PROGRESS_CANCELLING,
            workflow_id="morning_report",
            execution_id="execution-1",
            runtime_id="runtime-1",
            payload={
                "state": "cancelling",
                "reason": "operator requested cancel",
                "requested_by": "cli",
            },
        )
    )
    await hook.on_runtime_event(
        RuntimeEvent(
            event_type=RuntimeEventType.WORKFLOW_PROGRESS_CANCELLED,
            workflow_id="morning_report",
            execution_id="execution-1",
            runtime_id="runtime-1",
            payload={
                "state": "cancelled",
            },
        )
    )

    assert [event.event_type for event in sink.events] == [
        RuntimeTelemetryEventType.WORKFLOW_CONTROL_PAUSE_REQUESTED,
        RuntimeTelemetryEventType.WORKFLOW_CONTROL_PAUSED,
        RuntimeTelemetryEventType.WORKFLOW_CONTROL_RESUME_REQUESTED,
        RuntimeTelemetryEventType.WORKFLOW_CONTROL_RESUMED,
        RuntimeTelemetryEventType.WORKFLOW_CONTROL_CANCEL_REQUESTED,
        RuntimeTelemetryEventType.WORKFLOW_CONTROL_CANCELLED,
    ]

    pause_requested = sink.events[0]
    assert pause_requested.workflow_id == "morning_report"
    assert pause_requested.execution_id == "execution-1"
    assert pause_requested.runtime_id == "runtime-1"
    assert pause_requested.success is None
    assert pause_requested.error_count == 0
    assert (
        pause_requested.payload["runtime_event"]["payload"]["reason"]
        == "operator requested pause"
    )

    cancelled = sink.events[-1]
    assert cancelled.success is True
    assert cancelled.error_count == 0


@pytest.mark.asyncio
async def test_runtime_telemetry_hook_maps_workflow_progress_events() -> None:
    sink = InMemoryRuntimeTelemetrySink()
    hook = RuntimeTelemetryHook(
        telemetry=RuntimeTelemetry(
            sinks=[
                sink,
            ],
        ),
    )
    timestamp = datetime(
        2026,
        5,
        26,
        tzinfo=timezone.utc,
    )

    await hook.on_runtime_event(
        RuntimeEvent(
            event_type=RuntimeEventType.WORKFLOW_PROGRESS_STARTED,
            workflow_id="morning_report",
            execution_id="execution-1",
            runtime_id="runtime-1",
            timestamp=timestamp,
            metadata={
                "trace_id": "trace-1",
                "span_id": "span-1",
            },
        )
    )
    await hook.on_runtime_event(
        RuntimeEvent(
            event_type=RuntimeEventType.WAVE_PROGRESS_COMPLETED,
            workflow_id="morning_report",
            execution_id="execution-1",
            runtime_id="runtime-1",
            timestamp=timestamp,
            wave_index=2,
            payload={
                "wave_nodes": [
                    "macro_node",
                ],
            },
        )
    )
    await hook.on_runtime_event(
        RuntimeEvent(
            event_type=RuntimeEventType.NODE_PROGRESS_COMPLETED,
            workflow_id="morning_report",
            execution_id="execution-1",
            runtime_id="runtime-1",
            timestamp=timestamp,
            node_name="macro_node",
            wave_index=2,
            payload={
                "success": True,
                "error_count": 0,
            },
        )
    )
    await hook.on_runtime_event(
        RuntimeEvent(
            event_type=RuntimeEventType.NODE_PROGRESS_SKIPPED,
            workflow_id="morning_report",
            execution_id="execution-1",
            runtime_id="runtime-1",
            timestamp=timestamp,
            node_name="skipped_node",
            wave_index=3,
            payload={
                "success": False,
                "skipped": True,
                "reason": "dependency_failed",
                "error_count": 0,
            },
        )
    )

    assert [event.event_type for event in sink.events] == [
        RuntimeTelemetryEventType.WORKFLOW_PROGRESS_STARTED,
        RuntimeTelemetryEventType.WAVE_PROGRESS_COMPLETED,
        RuntimeTelemetryEventType.NODE_PROGRESS_COMPLETED,
        RuntimeTelemetryEventType.NODE_PROGRESS_SKIPPED,
    ]

    workflow_started = sink.events[0]
    assert workflow_started.payload["trace_id"] == "trace-1"
    assert workflow_started.payload["span_id"] == "span-1"

    node_completed = sink.events[-2]
    assert node_completed.timestamp == timestamp
    assert node_completed.node_name == "macro_node"
    assert node_completed.wave_index == 2
    assert node_completed.success is True
    assert node_completed.error_count == 0
    assert node_completed.payload["runtime_event"]["payload"]["success"] is True

    node_skipped = sink.events[-1]
    assert node_skipped.node_name == "skipped_node"
    assert node_skipped.wave_index == 3
    assert node_skipped.success is False
    assert node_skipped.error_count == 0
    assert (
        node_skipped.payload["runtime_event"]["payload"]["reason"]
        == "dependency_failed"
    )


@pytest.mark.asyncio
async def test_runtime_telemetry_hook_maps_failed_progress_as_error() -> None:
    sink = InMemoryRuntimeTelemetrySink()
    hook = RuntimeTelemetryHook(
        telemetry=RuntimeTelemetry(
            sinks=[
                sink,
            ],
        ),
    )

    await hook.on_runtime_event(
        RuntimeEvent(
            event_type=RuntimeEventType.NODE_PROGRESS_FAILED,
            workflow_id="morning_report",
            execution_id="execution-1",
            runtime_id="runtime-1",
            node_name="macro_node",
            wave_index=1,
            payload={
                "success": False,
                "error_count": 3,
            },
        )
    )

    assert len(sink.events) == 1
    telemetry_event = sink.events[0]
    assert telemetry_event.event_type is RuntimeTelemetryEventType.NODE_PROGRESS_FAILED
    assert telemetry_event.success is False
    assert telemetry_event.error_count == 3
    assert telemetry_event.node_name == "macro_node"
    assert telemetry_event.wave_index == 1


@pytest.mark.asyncio
async def test_runtime_telemetry_hook_skips_lifecycle_equivalent_runtime_events() -> (
    None
):
    sink = InMemoryRuntimeTelemetrySink()
    hook = RuntimeTelemetryHook(
        telemetry=RuntimeTelemetry(
            sinks=[
                sink,
            ],
        ),
    )

    await hook.on_runtime_event(
        RuntimeEvent(
            event_type=RuntimeEventType.WORKFLOW_STARTED,
            workflow_id="morning_report",
            execution_id="execution-1",
            runtime_id="runtime-1",
        )
    )
    await hook.on_runtime_event(
        RuntimeEvent(
            event_type=RuntimeEventType.NODE_COMPLETED,
            workflow_id="morning_report",
            execution_id="execution-1",
            runtime_id="runtime-1",
            node_name="macro_node",
            payload={
                "success": True,
            },
        )
    )
    await hook.on_runtime_event(
        RuntimeEvent(
            event_type=RuntimeEventType.WORKFLOW_PROGRESS_STARTED,
            workflow_id="morning_report",
            execution_id="execution-1",
            runtime_id="runtime-1",
        )
    )

    assert [event.event_type for event in sink.events] == [
        RuntimeTelemetryEventType.WORKFLOW_PROGRESS_STARTED,
    ]
