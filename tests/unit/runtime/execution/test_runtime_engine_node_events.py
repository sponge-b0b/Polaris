from __future__ import annotations

import asyncio

import pytest

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.control import WorkflowControlManager
from core.runtime.events import EventBus, RuntimeEvent, RuntimeEventType
from core.runtime.execution.runtime_engine import RuntimeEngine
from core.runtime.lifecycle.runtime_lifecycle_manager import RuntimeLifecycleManager
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.runtime.telemetry.runtime_telemetry import (
    InMemoryRuntimeTelemetrySink,
    RuntimeTelemetry,
    RuntimeTelemetryEventType,
)
from core.runtime.telemetry.runtime_telemetry_hook import RuntimeTelemetryHook
from core.workflow.models.workflow_execution_plan import (
    ExecutionPlanNode,
    ExecutionWave,
    WorkflowExecutionPlan,
)


class SuccessfulRuntimeNode(RuntimeNode):
    node_name = "retry_node"
    node_type = "test"

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        return RuntimeNodeOutput.success_output(
            outputs={
                "ok": True,
            },
        )


class RetryRuntimeNode(RuntimeNode):
    node_name = "retry_node"
    node_type = "test"

    def __init__(
        self,
    ) -> None:
        self.attempts = 0
        self.attempt_traces: list[tuple[str, str, str | None]] = []

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        assert context.trace_context is not None
        self.attempt_traces.append(
            (
                context.trace_context.trace_id,
                context.trace_context.span_id,
                context.trace_context.parent_span_id,
            )
        )
        self.attempts += 1
        if self.attempts == 1:
            return RuntimeNodeOutput.failure_output(
                errors=[
                    {
                        "node_name": self.node_name,
                        "error_type": "TransientFailure",
                        "message": "retry me",
                    }
                ],
            )

        return RuntimeNodeOutput.success_output(
            outputs={
                "attempts": self.attempts,
            },
        )


def build_context(
    execution_id: str = "execution-1",
) -> RuntimeContext:
    return RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="unit_workflow",
        execution_id=execution_id,
    )


def collect_events() -> tuple[EventBus, list[RuntimeEvent]]:
    event_bus = EventBus()
    events: list[RuntimeEvent] = []

    async def collect(
        event: RuntimeEvent,
    ) -> None:
        events.append(
            event,
        )

    event_bus.subscribe_all(
        collect,
    )
    return event_bus, events


@pytest.mark.asyncio
async def test_runtime_engine_emits_events_for_disabled_and_dependency_skipped_nodes() -> (  # noqa: E501 - descriptive pytest node id
    None
):
    event_bus, events = collect_events()
    engine = RuntimeEngine(
        control_manager=WorkflowControlManager(
            event_bus=event_bus,
        ),
    )
    engine.register(
        "dependent_node",
        SuccessfulRuntimeNode(),
    )
    plan = WorkflowExecutionPlan(
        workflow_name="unit_workflow",
        execution_id="execution-1",
        nodes={
            "disabled_node": ExecutionPlanNode(
                name="disabled_node",
                node_type="test",
                enabled=False,
                max_retries=0,
            ),
            "dependent_node": ExecutionPlanNode(
                name="dependent_node",
                node_type="test",
                dependencies=("disabled_node",),
                max_retries=0,
            ),
        },
        waves=(
            ExecutionWave(
                index=0,
                nodes=("disabled_node",),
            ),
            ExecutionWave(
                index=1,
                nodes=("dependent_node",),
            ),
        ),
    )

    result = await engine.execute(
        context=build_context(),
        execution_plan=plan,
    )

    assert result.node_outputs["disabled_node"]["skipped"] is True
    assert result.node_outputs["dependent_node"]["skipped"] is True
    assert result.trace_context is not None

    skipped_events = [
        event for event in events if event.event_type is RuntimeEventType.NODE_SKIPPED
    ]
    skipped_progress_events = [
        event
        for event in events
        if event.event_type is RuntimeEventType.NODE_PROGRESS_SKIPPED
    ]

    assert [event.node_name for event in skipped_events] == [
        "disabled_node",
        "dependent_node",
    ]
    assert [event.payload["reason"] for event in skipped_events] == [
        "node_disabled",
        "dependency_failed",
    ]
    assert [event.node_name for event in skipped_progress_events] == [
        "disabled_node",
        "dependent_node",
    ]
    assert [event.payload["reason"] for event in skipped_progress_events] == [
        "node_disabled",
        "dependency_failed",
    ]
    assert all(event.payload["skipped"] is True for event in skipped_progress_events)
    for event in skipped_events + skipped_progress_events:
        assert event.payload["trace_id"] == result.trace_context.trace_id
        assert event.payload["span_id"] != result.trace_context.span_id
        assert event.payload["parent_span_id"] == result.trace_context.span_id
        assert event.metadata["trace_id"] == result.trace_context.trace_id
        assert event.metadata["parent_span_id"] == result.trace_context.span_id


@pytest.mark.asyncio
async def test_runtime_engine_emits_events_for_missing_registered_node() -> None:
    event_bus, events = collect_events()
    engine = RuntimeEngine(
        control_manager=WorkflowControlManager(
            event_bus=event_bus,
        ),
    )
    plan = WorkflowExecutionPlan(
        workflow_name="unit_workflow",
        execution_id="execution-1",
        nodes={
            "missing_node": ExecutionPlanNode(
                name="missing_node",
                node_type="test",
                max_retries=0,
            ),
        },
        waves=(
            ExecutionWave(
                index=0,
                nodes=("missing_node",),
            ),
        ),
    )

    result = await engine.execute(
        context=build_context(),
        execution_plan=plan,
    )

    assert result.node_outputs["missing_node"]["success"] is False
    assert result.errors[0]["error_type"] == "NodeRegistrationError"
    assert result.trace_context is not None

    node_failed = next(
        event for event in events if event.event_type is RuntimeEventType.NODE_FAILED
    )
    progress_failed = next(
        event
        for event in events
        if event.event_type is RuntimeEventType.NODE_PROGRESS_FAILED
    )

    assert node_failed.node_name == "missing_node"
    assert node_failed.wave_index == 0
    assert node_failed.payload["error_type"] == "NodeRegistrationError"
    assert progress_failed.node_name == "missing_node"
    assert progress_failed.wave_index == 0
    assert progress_failed.payload["success"] is False
    assert progress_failed.payload["error_count"] == 1
    for event in (node_failed, progress_failed):
        assert event.payload["trace_id"] == result.trace_context.trace_id
        assert event.payload["span_id"] != result.trace_context.span_id
        assert event.payload["parent_span_id"] == result.trace_context.span_id
        assert event.metadata["trace_id"] == result.trace_context.trace_id
        assert event.metadata["parent_span_id"] == result.trace_context.span_id


@pytest.mark.asyncio
async def test_runtime_engine_emits_retrying_event_before_retry_attempt() -> None:
    event_bus, events = collect_events()
    telemetry_sink = InMemoryRuntimeTelemetrySink()
    lifecycle_manager = RuntimeLifecycleManager(
        hooks=[RuntimeTelemetryHook(RuntimeTelemetry(sinks=[telemetry_sink]))]
    )
    engine = RuntimeEngine(
        control_manager=WorkflowControlManager(
            event_bus=event_bus,
        ),
        lifecycle_manager=lifecycle_manager,
    )
    node = RetryRuntimeNode()
    engine.register(
        "retry_node",
        node,
    )
    plan = WorkflowExecutionPlan(
        workflow_name="unit_workflow",
        execution_id="execution-1",
        nodes={
            "retry_node": ExecutionPlanNode(
                name="retry_node",
                node_type="test",
                max_retries=1,
                metadata={
                    "retry_backoff_seconds": 0.0,
                },
            ),
        },
        waves=(
            ExecutionWave(
                index=0,
                nodes=("retry_node",),
            ),
        ),
    )

    result = await engine.execute(
        context=build_context(),
        execution_plan=plan,
    )

    retrying_event = next(
        event for event in events if event.event_type is RuntimeEventType.NODE_RETRYING
    )

    assert node.attempts == 2
    assert result.node_outputs["retry_node"]["success"] is True
    assert result.trace_context is not None
    assert retrying_event.node_name == "retry_node"
    assert retrying_event.wave_index == 0
    assert retrying_event.payload["attempt"] == 1
    assert retrying_event.payload["next_attempt"] == 2
    assert retrying_event.payload["max_attempts"] == 2
    assert retrying_event.payload["error_count"] == 1
    assert retrying_event.payload["errors"][0]["error_type"] == "TransientFailure"
    assert retrying_event.payload["trace_id"] == result.trace_context.trace_id
    assert retrying_event.payload["span_id"] != result.trace_context.span_id
    assert retrying_event.payload["parent_span_id"] == result.trace_context.span_id
    assert retrying_event.metadata["trace_id"] == result.trace_context.trace_id
    assert retrying_event.metadata["parent_span_id"] == result.trace_context.span_id
    assert len(node.attempt_traces) == 2
    first_trace, second_trace = node.attempt_traces
    assert first_trace[0] == result.trace_context.trace_id
    assert second_trace[0] == result.trace_context.trace_id
    assert first_trace[1] != second_trace[1]
    assert first_trace[2] == result.trace_context.span_id
    assert second_trace[2] == result.trace_context.span_id
    assert retrying_event.payload["span_id"] == first_trace[1]
    attempt_lifecycle_events = [
        event
        for event in telemetry_sink.events
        if event.node_name == "retry_node"
        and event.event_type
        in {
            RuntimeTelemetryEventType.NODE_STARTED,
            RuntimeTelemetryEventType.NODE_FAILED,
            RuntimeTelemetryEventType.NODE_COMPLETED,
        }
    ]
    assert [event.event_type for event in attempt_lifecycle_events] == [
        RuntimeTelemetryEventType.NODE_STARTED,
        RuntimeTelemetryEventType.NODE_FAILED,
        RuntimeTelemetryEventType.NODE_STARTED,
        RuntimeTelemetryEventType.NODE_COMPLETED,
    ]
    assert [event.payload["span_id"] for event in attempt_lifecycle_events] == [
        first_trace[1],
        first_trace[1],
        second_trace[1],
        second_trace[1],
    ]


class TimedOutRuntimeNode(RuntimeNode):
    node_name = "timed_out_node"
    node_type = "test"

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        await asyncio.sleep(1.0)
        return RuntimeNodeOutput.success_output(outputs={"unexpected": True})


class CancelledRuntimeNode(RuntimeNode):
    node_name = "cancelled_node"
    node_type = "test"

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        raise asyncio.CancelledError


@pytest.mark.asyncio
async def test_runtime_timeout_retains_node_trace_and_one_terminal_lifecycle_event() -> (  # noqa: E501 - descriptive pytest node id
    None
):
    telemetry_sink = InMemoryRuntimeTelemetrySink()
    lifecycle_manager = RuntimeLifecycleManager(
        hooks=[RuntimeTelemetryHook(RuntimeTelemetry(sinks=[telemetry_sink]))]
    )
    engine = RuntimeEngine(lifecycle_manager=lifecycle_manager)
    engine.register("timed_out_node", TimedOutRuntimeNode())
    plan = WorkflowExecutionPlan(
        workflow_name="unit_workflow",
        execution_id="execution-timeout",
        nodes={
            "timed_out_node": ExecutionPlanNode(
                name="timed_out_node",
                node_type="test",
                max_retries=0,
                timeout_seconds=0.001,
            )
        },
        waves=(ExecutionWave(index=0, nodes=("timed_out_node",)),),
    )

    result = await engine.execute(
        context=build_context(execution_id="execution-timeout"),
        execution_plan=plan,
    )

    terminal_events = [
        event
        for event in telemetry_sink.events
        if event.event_type is RuntimeTelemetryEventType.NODE_FAILED
        and event.node_name == "timed_out_node"
    ]
    assert len(terminal_events) == 1
    terminal_event = terminal_events[0]
    assert result.trace_context is not None
    assert terminal_event.payload["errors"][0]["error_type"] == "TimeoutError"
    assert terminal_event.payload["trace_id"] == result.trace_context.trace_id
    assert terminal_event.payload["span_id"] != result.trace_context.span_id
    assert terminal_event.payload["parent_span_id"] == result.trace_context.span_id


@pytest.mark.asyncio
async def test_runtime_wave_propagates_node_task_cancellation() -> None:
    engine = RuntimeEngine()
    engine.register("cancelled_node", CancelledRuntimeNode())
    plan = WorkflowExecutionPlan(
        workflow_name="unit_workflow",
        execution_id="execution-cancelled-task",
        nodes={
            "cancelled_node": ExecutionPlanNode(
                name="cancelled_node",
                node_type="test",
                max_retries=0,
            )
        },
        waves=(ExecutionWave(index=0, nodes=("cancelled_node",)),),
    )

    with pytest.raises(asyncio.CancelledError):
        await engine.execute(
            context=build_context(execution_id="execution-cancelled-task"),
            execution_plan=plan,
        )
