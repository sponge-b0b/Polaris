from __future__ import annotations

import asyncio

import pytest

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.control import WorkflowControlManager
from core.runtime.events import EventBus
from core.runtime.execution.runtime_engine import RuntimeEngine
from core.runtime.lifecycle.runtime_lifecycle_manager import RuntimeLifecycleManager
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.runtime.telemetry.runtime_telemetry import RuntimeTelemetry
from core.runtime.telemetry.runtime_telemetry_hook import RuntimeTelemetryHook
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.runtime_telemetry_sink import CoreTelemetryRuntimeSink
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from core.workflow.models.workflow_execution_plan import ExecutionPlanNode
from core.workflow.models.workflow_execution_plan import ExecutionWave
from core.workflow.models.workflow_execution_plan import WorkflowExecutionPlan


class BaselineRuntimeNode(RuntimeNode):
    node_name = "baseline_node"
    node_type = "baseline_test"

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        assert context.trace_context is not None

        return RuntimeNodeOutput.success_output(
            outputs={
                "baseline": True,
                "trace_id": context.trace_context.trace_id,
                "span_id": context.trace_context.span_id,
                "parent_span_id": context.trace_context.parent_span_id,
            },
        )


def build_baseline_plan() -> WorkflowExecutionPlan:
    return WorkflowExecutionPlan(
        workflow_name="telemetry_baseline_workflow",
        execution_id="telemetry-baseline-execution",
        nodes={
            "baseline_node": ExecutionPlanNode(
                name="baseline_node",
                node_type="baseline_test",
                max_retries=0,
            ),
        },
        waves=(
            ExecutionWave(
                index=0,
                nodes=("baseline_node",),
            ),
        ),
    )


def build_observed_runtime() -> tuple[RuntimeEngine, InMemoryTelemetrySink]:
    telemetry_sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(
        telemetry_sink,
    )

    runtime_telemetry = RuntimeTelemetry(
        sinks=[
            CoreTelemetryRuntimeSink(
                sink=observability,
            ),
        ],
    )
    lifecycle_manager = RuntimeLifecycleManager(
        hooks=[
            RuntimeTelemetryHook(
                telemetry=runtime_telemetry,
            ),
        ],
    )
    event_bus = EventBus()
    event_bus.subscribe_lifecycle_manager(
        lifecycle_manager,
    )

    engine = RuntimeEngine(
        lifecycle_manager=lifecycle_manager,
        event_bus=event_bus,
        observability_manager=observability,
    )
    engine.register(
        "baseline_node",
        BaselineRuntimeNode(),
    )

    return engine, telemetry_sink


@pytest.mark.asyncio
async def test_runtime_lifecycle_and_progress_telemetry_reach_observability() -> None:
    engine, telemetry_sink = build_observed_runtime()

    result = await engine.execute(
        context=RuntimeContext(
            runtime_id="telemetry-baseline-runtime",
            workflow_id="telemetry_baseline_workflow",
            execution_id="telemetry-baseline-execution",
        ),
        execution_plan=build_baseline_plan(),
    )

    assert result.errors == []
    assert result.trace_context is not None
    assert result.trace_context.workflow_id == "telemetry_baseline_workflow"
    assert result.trace_context.execution_id == "telemetry-baseline-execution"
    assert result.trace_context.runtime_id == "telemetry-baseline-runtime"
    node_output = result.node_outputs["baseline_node"]["outputs"]
    assert node_output["trace_id"] == result.trace_context.trace_id
    assert node_output["span_id"] != result.trace_context.span_id
    assert node_output["parent_span_id"] == result.trace_context.span_id

    event_types = [event.event_type for event in telemetry_sink.events]

    assert "runtime.workflow.started" in event_types
    assert "runtime.workflow.completed" in event_types
    assert "runtime.wave.started" in event_types
    assert "runtime.wave.completed" in event_types
    assert "runtime.node.started" in event_types
    assert "runtime.node.completed" in event_types
    assert "workflow_progress.workflow_started" in event_types
    assert "workflow_progress.workflow_running" in event_types
    assert "workflow_progress.workflow_completed" in event_types
    assert "workflow_progress.wave_started" in event_types
    assert "workflow_progress.wave_completed" in event_types
    assert "workflow_progress.node_started" in event_types
    assert "workflow_progress.node_running" in event_types
    assert "workflow_progress.node_completed" in event_types

    workflow_started = next(
        event
        for event in telemetry_sink.events
        if event.event_type == "runtime.workflow.started"
    )
    workflow_completed = next(
        event
        for event in telemetry_sink.events
        if event.event_type == "runtime.workflow.completed"
    )
    assert workflow_started.payload["trace_id"] == result.trace_context.trace_id
    assert workflow_completed.payload["trace_id"] == result.trace_context.trace_id
    assert workflow_started.payload["span_id"] == result.trace_context.span_id
    assert workflow_completed.payload["span_id"] == result.trace_context.span_id

    node_started = next(
        event
        for event in telemetry_sink.events
        if event.event_type == "runtime.node.started"
    )
    node_completed = next(
        event
        for event in telemetry_sink.events
        if event.event_type == "runtime.node.completed"
    )

    assert node_started.payload["trace_id"] == result.trace_context.trace_id
    assert node_completed.payload["trace_id"] == result.trace_context.trace_id
    assert node_started.payload["span_id"] != result.trace_context.span_id
    assert node_completed.payload["span_id"] == node_started.payload["span_id"]
    assert node_started.payload["parent_span_id"] == result.trace_context.span_id
    assert node_completed.payload["parent_span_id"] == result.trace_context.span_id

    progress_started = next(
        event
        for event in telemetry_sink.events
        if event.event_type == "workflow_progress.workflow_started"
    )
    assert (
        progress_started.payload["runtime_event"]["payload"]["trace_id"]
        == result.trace_context.trace_id
    )

    progress_node_running = next(
        event
        for event in telemetry_sink.events
        if event.event_type == "workflow_progress.node_running"
    )
    progress_node_completed = next(
        event
        for event in telemetry_sink.events
        if event.event_type == "workflow_progress.node_completed"
    )
    assert (
        progress_node_running.payload["runtime_event"]["payload"]["trace_id"]
        == result.trace_context.trace_id
    )
    assert (
        progress_node_completed.payload["runtime_event"]["payload"]["trace_id"]
        == result.trace_context.trace_id
    )
    assert (
        progress_node_running.payload["runtime_event"]["payload"]["span_id"]
        == node_started.payload["span_id"]
    )
    assert (
        progress_node_completed.payload["runtime_event"]["payload"]["span_id"]
        == node_started.payload["span_id"]
    )
    assert (
        progress_node_running.payload["runtime_event"]["payload"]["parent_span_id"]
        == result.trace_context.span_id
    )
    assert (
        progress_node_completed.payload["runtime_event"]["payload"]["parent_span_id"]
        == result.trace_context.span_id
    )

    node_completed = next(
        event
        for event in telemetry_sink.events
        if event.event_type == "runtime.node.completed"
    )
    assert node_completed.workflow_id == "telemetry_baseline_workflow"
    assert node_completed.execution_id == "telemetry-baseline-execution"
    assert node_completed.runtime_id == "telemetry-baseline-runtime"
    assert node_completed.node_name == "baseline_node"
    assert node_completed.success is True
    assert node_completed.error_count == 0


@pytest.mark.asyncio
async def test_workflow_control_telemetry_reaches_observability() -> None:
    telemetry_sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(
        telemetry_sink,
    )

    runtime_telemetry = RuntimeTelemetry(
        sinks=[
            CoreTelemetryRuntimeSink(
                sink=observability,
            ),
        ],
    )
    lifecycle_manager = RuntimeLifecycleManager(
        hooks=[
            RuntimeTelemetryHook(
                telemetry=runtime_telemetry,
            ),
        ],
    )
    event_bus = EventBus()
    event_bus.subscribe_lifecycle_manager(
        lifecycle_manager,
    )
    control_manager = WorkflowControlManager(
        event_bus=event_bus,
    )

    await control_manager.mark_running(
        "telemetry-control-execution",
        metadata={
            "workflow_id": "telemetry_control_workflow",
            "runtime_id": "telemetry-control-runtime",
        },
    )
    await control_manager.request_pause(
        "telemetry-control-execution",
        reason="baseline pause",
        requested_by="test",
    )
    wait_task = asyncio.create_task(
        control_manager.wait_if_paused(
            "telemetry-control-execution",
        ),
    )
    await asyncio.sleep(
        0,
    )
    await control_manager.request_resume(
        "telemetry-control-execution",
        reason="baseline resume",
        requested_by="test",
    )
    await asyncio.wait_for(
        wait_task,
        timeout=1.0,
    )
    await control_manager.request_cancel(
        "telemetry-control-execution",
        reason="baseline cancel",
        requested_by="test",
    )
    await control_manager.mark_cancelled(
        "telemetry-control-execution",
    )

    event_types = [event.event_type for event in telemetry_sink.events]

    assert "workflow_control.state_changed" in event_types
    assert "workflow_progress.workflow_running" in event_types
    assert "workflow_control.pause_requested" in event_types
    assert "workflow_control.paused" in event_types
    assert "workflow_control.resume_requested" in event_types
    assert "workflow_control.resumed" in event_types
    assert "workflow_control.cancel_requested" in event_types
    assert "workflow_control.cancelled" in event_types

    cancelled = telemetry_sink.events[-1]
    assert cancelled.event_type == "workflow_control.cancelled"
    assert cancelled.workflow_id == "telemetry_control_workflow"
    assert cancelled.execution_id == "telemetry-control-execution"
    assert cancelled.runtime_id == "telemetry-control-runtime"
    assert cancelled.success is True
    assert cancelled.error_count == 0
