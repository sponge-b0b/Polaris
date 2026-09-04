from __future__ import annotations

import pytest

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.control import WorkflowControlState
from core.runtime.events import EventBus, RuntimeEvent, RuntimeEventType
from core.runtime.execution.runtime_engine import RuntimeEngine
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.workflow.models.workflow_execution_plan import (
    ExecutionPlanNode,
    ExecutionWave,
    WorkflowExecutionPlan,
)


class RecordingRuntimeNode(RuntimeNode):
    node_type = "integration_test"

    def __init__(
        self,
        node_name: str,
        executed_nodes: list[str],
    ) -> None:
        self.node_name = node_name
        self._executed_nodes = executed_nodes

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        self._executed_nodes.append(
            self.node_name,
        )
        return RuntimeNodeOutput.success_output(
            outputs={
                "recorded": self.node_name,
            },
        )


def build_context() -> RuntimeContext:
    return RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="progress_workflow",
        execution_id="execution-1",
    )


def build_two_wave_plan() -> WorkflowExecutionPlan:
    return WorkflowExecutionPlan(
        workflow_name="progress_workflow",
        execution_id="execution-1",
        nodes={
            "first_node": ExecutionPlanNode(
                name="first_node",
                node_type="integration_test",
                max_retries=0,
            ),
            "second_node": ExecutionPlanNode(
                name="second_node",
                node_type="integration_test",
                dependencies=("first_node",),
                max_retries=0,
            ),
        },
        waves=(
            ExecutionWave(
                index=0,
                nodes=("first_node",),
            ),
            ExecutionWave(
                index=1,
                nodes=("second_node",),
            ),
        ),
    )


def create_event_collector() -> tuple[EventBus, list[RuntimeEvent]]:
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


def external_progress_events(
    events: list[RuntimeEvent],
) -> list[RuntimeEvent]:
    progress_event_types = {
        RuntimeEventType.WORKFLOW_PROGRESS_STARTED,
        RuntimeEventType.WORKFLOW_PROGRESS_RUNNING,
        RuntimeEventType.WORKFLOW_PROGRESS_COMPLETED,
        RuntimeEventType.WAVE_PROGRESS_STARTED,
        RuntimeEventType.WAVE_PROGRESS_COMPLETED,
        RuntimeEventType.NODE_PROGRESS_STARTED,
        RuntimeEventType.NODE_PROGRESS_RUNNING,
        RuntimeEventType.NODE_PROGRESS_COMPLETED,
    }
    return [event for event in events if event.event_type in progress_event_types]


@pytest.mark.asyncio
async def test_runtime_workflow_emits_ordered_external_progress_events() -> None:
    event_bus, events = create_event_collector()
    engine = RuntimeEngine(
        event_bus=event_bus,
    )
    executed_nodes: list[str] = []

    engine.register_many(
        {
            "first_node": RecordingRuntimeNode(
                node_name="first_node",
                executed_nodes=executed_nodes,
            ),
            "second_node": RecordingRuntimeNode(
                node_name="second_node",
                executed_nodes=executed_nodes,
            ),
        }
    )

    result = await engine.execute(
        context=build_context(),
        execution_plan=build_two_wave_plan(),
    )

    progress_events = external_progress_events(
        events,
    )

    assert result.errors == []
    assert executed_nodes == [
        "first_node",
        "second_node",
    ]
    assert (
        engine.control_manager.get_state(
            "execution-1",
        )
        is WorkflowControlState.COMPLETED
    )

    assert [event.event_type for event in progress_events] == [
        RuntimeEventType.WORKFLOW_PROGRESS_STARTED,
        RuntimeEventType.WORKFLOW_PROGRESS_RUNNING,
        RuntimeEventType.WAVE_PROGRESS_STARTED,
        RuntimeEventType.NODE_PROGRESS_STARTED,
        RuntimeEventType.NODE_PROGRESS_RUNNING,
        RuntimeEventType.NODE_PROGRESS_COMPLETED,
        RuntimeEventType.WAVE_PROGRESS_COMPLETED,
        RuntimeEventType.WAVE_PROGRESS_STARTED,
        RuntimeEventType.NODE_PROGRESS_STARTED,
        RuntimeEventType.NODE_PROGRESS_RUNNING,
        RuntimeEventType.NODE_PROGRESS_COMPLETED,
        RuntimeEventType.WAVE_PROGRESS_COMPLETED,
        RuntimeEventType.WORKFLOW_PROGRESS_COMPLETED,
    ]

    for event in progress_events:
        assert event.execution_id == "execution-1"
        assert event.workflow_id == "progress_workflow"
        assert event.runtime_id == "runtime-1"
        assert event.payload["execution_id"] == "execution-1"
        assert event.payload["workflow_id"] == "progress_workflow"
        assert event.payload["workflow_name"] == "progress_workflow"
        assert event.payload["runtime_id"] == "runtime-1"
        assert event.payload["timestamp"]

    node_progress = [
        event
        for event in progress_events
        if event.event_type
        in {
            RuntimeEventType.NODE_PROGRESS_STARTED,
            RuntimeEventType.NODE_PROGRESS_RUNNING,
            RuntimeEventType.NODE_PROGRESS_COMPLETED,
        }
    ]
    assert [
        (
            event.event_type,
            event.node_name,
            event.wave_index,
            event.payload["node_type"],
        )
        for event in node_progress
    ] == [
        (
            RuntimeEventType.NODE_PROGRESS_STARTED,
            "first_node",
            0,
            "integration_test",
        ),
        (
            RuntimeEventType.NODE_PROGRESS_RUNNING,
            "first_node",
            0,
            "integration_test",
        ),
        (
            RuntimeEventType.NODE_PROGRESS_COMPLETED,
            "first_node",
            0,
            "integration_test",
        ),
        (
            RuntimeEventType.NODE_PROGRESS_STARTED,
            "second_node",
            1,
            "integration_test",
        ),
        (
            RuntimeEventType.NODE_PROGRESS_RUNNING,
            "second_node",
            1,
            "integration_test",
        ),
        (
            RuntimeEventType.NODE_PROGRESS_COMPLETED,
            "second_node",
            1,
            "integration_test",
        ),
    ]

    wave_progress = [
        event
        for event in progress_events
        if event.event_type
        in {
            RuntimeEventType.WAVE_PROGRESS_STARTED,
            RuntimeEventType.WAVE_PROGRESS_COMPLETED,
        }
    ]
    assert [
        (
            event.event_type,
            event.wave_index,
            event.payload["wave_nodes"],
        )
        for event in wave_progress
    ] == [
        (
            RuntimeEventType.WAVE_PROGRESS_STARTED,
            0,
            ["first_node"],
        ),
        (
            RuntimeEventType.WAVE_PROGRESS_COMPLETED,
            0,
            ["first_node"],
        ),
        (
            RuntimeEventType.WAVE_PROGRESS_STARTED,
            1,
            ["second_node"],
        ),
        (
            RuntimeEventType.WAVE_PROGRESS_COMPLETED,
            1,
            ["second_node"],
        ),
    ]

    workflow_started = progress_events[0]
    workflow_completed = progress_events[-1]

    assert workflow_started.payload["state"] == WorkflowControlState.PENDING.value
    assert workflow_completed.payload["state"] == WorkflowControlState.COMPLETED.value
    assert workflow_completed.is_terminal is True
