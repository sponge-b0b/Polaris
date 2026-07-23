from __future__ import annotations

import asyncio

import pytest

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.control import WorkflowControlManager, WorkflowControlState
from core.runtime.events import EventBus, RuntimeEvent, RuntimeEventType
from core.runtime.execution.runtime_engine import RuntimeEngine
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.workflow.models.workflow_execution_plan import (
    ExecutionPlanNode,
    ExecutionWave,
    WorkflowExecutionPlan,
)


class BoundaryControlledRuntimeNode(RuntimeNode):
    node_name = "first_node"
    node_type = "integration_test"

    def __init__(
        self,
        started: asyncio.Event,
        release: asyncio.Event,
        executed_nodes: list[str],
    ) -> None:
        self._started = started
        self._release = release
        self._executed_nodes = executed_nodes

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        self._executed_nodes.append(
            self.node_name,
        )
        self._started.set()
        await self._release.wait()
        return RuntimeNodeOutput.success_output(
            outputs={
                "released": True,
            },
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
        workflow_id="cancel_workflow",
        execution_id="execution-1",
    )


def build_two_wave_plan() -> WorkflowExecutionPlan:
    return WorkflowExecutionPlan(
        workflow_name="cancel_workflow",
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


async def wait_for_control_state(
    control_manager: WorkflowControlManager,
    state: WorkflowControlState,
) -> None:
    for _ in range(20):
        if (
            control_manager.get_state(
                "execution-1",
            )
            is state
        ):
            return
        await asyncio.sleep(
            0,
        )

    raise AssertionError(f"Workflow did not reach {state.value} state.")


def assert_cancelled_workflow_output(
    result: RuntimeContext,
) -> None:
    assert RuntimeEngine.CANCELLED_WORKFLOW_OUTPUT_NAME in result.node_outputs

    cancelled_output = result.node_outputs[RuntimeEngine.CANCELLED_WORKFLOW_OUTPUT_NAME]
    assert isinstance(
        cancelled_output,
        dict,
    )
    assert cancelled_output["success"] is False
    assert cancelled_output["skipped"] is False
    assert cancelled_output["stop_propagation"] is True
    assert cancelled_output["errors"] == []

    outputs = cancelled_output["outputs"]
    assert outputs["cancelled"] is True
    assert outputs["status"] == WorkflowControlState.CANCELLED.value
    assert outputs["reason"] == "external cancel before next wave"
    assert outputs["requested_by"] == "integration_test"
    assert outputs["cancel_boundary"] == "after_node"
    assert outputs["wave_index"] == 0
    assert outputs["node_name"] == "first_node"

    metadata = cancelled_output["execution_metadata"]
    assert metadata["node_name"] == RuntimeEngine.CANCELLED_WORKFLOW_OUTPUT_NAME
    assert metadata["cancelled"] is True
    assert metadata["status"] == WorkflowControlState.CANCELLED.value
    assert metadata["cancel_boundary"] == "after_node"
    assert metadata["wave_index"] == 0
    assert metadata["cancelled_node_name"] == "first_node"


@pytest.mark.asyncio
async def test_runtime_workflow_cancels_before_next_wave() -> None:
    event_bus, events = create_event_collector()
    control_manager = WorkflowControlManager(
        event_bus=event_bus,
    )
    engine = RuntimeEngine(
        control_manager=control_manager,
    )

    first_node_started = asyncio.Event()
    first_node_release = asyncio.Event()
    executed_nodes: list[str] = []

    engine.register_many(
        {
            "first_node": BoundaryControlledRuntimeNode(
                started=first_node_started,
                release=first_node_release,
                executed_nodes=executed_nodes,
            ),
            "second_node": RecordingRuntimeNode(
                node_name="second_node",
                executed_nodes=executed_nodes,
            ),
        }
    )

    execution_task = asyncio.create_task(
        engine.execute(
            context=build_context(),
            execution_plan=build_two_wave_plan(),
        )
    )

    await asyncio.wait_for(
        first_node_started.wait(),
        timeout=1.0,
    )

    await control_manager.request_cancel(
        "execution-1",
        reason="external cancel before next wave",
        requested_by="integration_test",
    )

    first_node_release.set()

    result = await asyncio.wait_for(
        execution_task,
        timeout=1.0,
    )

    assert result.errors == []
    assert executed_nodes == [
        "first_node",
    ]
    assert "second_node" not in result.node_outputs
    assert_cancelled_workflow_output(
        result,
    )

    await wait_for_control_state(
        control_manager=control_manager,
        state=WorkflowControlState.CANCELLED,
    )

    snapshot = control_manager.get_snapshot(
        "execution-1",
    )
    assert snapshot.state is WorkflowControlState.CANCELLED
    assert snapshot.reason == "external cancel before next wave"
    assert snapshot.requested_by == "integration_test"
    assert snapshot.metadata["workflow_id"] == "cancel_workflow"
    assert snapshot.metadata["runtime_id"] == "runtime-1"
    assert snapshot.metadata["cancelled"] is True
    assert snapshot.metadata["status"] == WorkflowControlState.CANCELLED.value
    assert snapshot.metadata["cancel_boundary"] == "after_node"
    assert snapshot.metadata["wave_index"] == 0
    assert snapshot.metadata["node_name"] == "first_node"

    event_types = [event.event_type for event in events]
    assert RuntimeEventType.WORKFLOW_PROGRESS_CANCELLING in event_types
    assert RuntimeEventType.WORKFLOW_PROGRESS_CANCELLED in event_types
    assert RuntimeEventType.WORKFLOW_PROGRESS_COMPLETED not in event_types
    assert RuntimeEventType.WORKFLOW_PROGRESS_FAILED not in event_types
