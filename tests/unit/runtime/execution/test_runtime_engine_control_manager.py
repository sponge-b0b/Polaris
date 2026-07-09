from __future__ import annotations

import asyncio
import pytest

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.control import WorkflowControlManager
from core.runtime.control import WorkflowControlState
from core.runtime.events import EventBus
from core.runtime.events import RuntimeEvent
from core.runtime.events import RuntimeEventType
from core.runtime.execution.runtime_engine import RuntimeEngine
from core.runtime.lifecycle.runtime_lifecycle_hooks import NoOpRuntimeLifecycleHook
from core.runtime.lifecycle.runtime_lifecycle_manager import RuntimeLifecycleManager
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.workflow.models.workflow_execution_plan import ExecutionPlanNode
from core.workflow.models.workflow_execution_plan import ExecutionWave
from core.workflow.models.workflow_execution_plan import WorkflowExecutionPlan


class SuccessfulRuntimeNode(RuntimeNode):
    node_name = "test_node"
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


class FailingRuntimeNode(RuntimeNode):
    node_name = "test_node"
    node_type = "test"

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        return RuntimeNodeOutput.failure_output(
            errors=[
                {
                    "node_name": self.node_name,
                    "error_type": "TestFailure",
                    "message": "node failed",
                }
            ],
        )


def build_context(
    execution_id: str = "execution-1",
) -> RuntimeContext:
    return RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="unit_workflow",
        execution_id=execution_id,
    )


def build_plan(
    execution_id: str = "execution-1",
) -> WorkflowExecutionPlan:
    return WorkflowExecutionPlan(
        workflow_name="unit_workflow",
        execution_id=execution_id,
        nodes={
            "test_node": ExecutionPlanNode(
                name="test_node",
                node_type="test",
                max_retries=0,
            ),
        },
        waves=(
            ExecutionWave(
                index=0,
                nodes=("test_node",),
            ),
        ),
    )


def test_runtime_engine_creates_default_control_manager() -> None:
    engine = RuntimeEngine()

    assert isinstance(
        engine.control_manager,
        WorkflowControlManager,
    )


def test_runtime_engine_uses_injected_control_manager() -> None:
    control_manager = WorkflowControlManager()

    engine = RuntimeEngine(
        control_manager=control_manager,
    )

    assert engine.control_manager is control_manager


@pytest.mark.asyncio
async def test_runtime_engine_marks_control_state_completed_after_successful_execution() -> (
    None
):
    control_manager = WorkflowControlManager()
    engine = RuntimeEngine(
        control_manager=control_manager,
    )
    engine.register(
        "test_node",
        SuccessfulRuntimeNode(),
    )

    result = await engine.execute(
        context=build_context(),
        execution_plan=build_plan(),
    )

    snapshot = control_manager.get_snapshot(
        "execution-1",
    )

    assert snapshot.state is WorkflowControlState.COMPLETED
    assert snapshot.reason is None
    assert snapshot.metadata["workflow_id"] == "unit_workflow"
    assert snapshot.metadata["workflow_name"] == "unit_workflow"
    assert snapshot.metadata["runtime_id"] == "runtime-1"
    assert snapshot.metadata["total_waves"] == 1
    assert snapshot.metadata["total_nodes"] == 1
    assert snapshot.metadata["context_version"] == result.context_version
    assert result.trace_context is not None
    assert snapshot.metadata["trace_id"] == result.trace_context.trace_id
    assert snapshot.metadata["span_id"] == result.trace_context.span_id


@pytest.mark.asyncio
async def test_runtime_engine_marks_control_state_failed_after_failed_node_output() -> (
    None
):
    control_manager = WorkflowControlManager()
    engine = RuntimeEngine(
        control_manager=control_manager,
    )
    engine.register(
        "test_node",
        FailingRuntimeNode(),
    )

    result = await engine.execute(
        context=build_context(),
        execution_plan=build_plan(),
    )

    snapshot = control_manager.get_snapshot(
        "execution-1",
    )

    assert result.errors == [
        {
            "node_name": "test_node",
            "error_type": "TestFailure",
            "message": "node failed",
        }
    ]
    assert snapshot.state is WorkflowControlState.FAILED
    assert snapshot.reason == "workflow execution completed with failures"
    assert snapshot.metadata["workflow_id"] == "unit_workflow"
    assert snapshot.metadata["runtime_id"] == "runtime-1"
    assert snapshot.metadata["context_version"] == result.context_version


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


@pytest.mark.asyncio
async def test_runtime_engine_emits_success_progress_events() -> None:
    event_bus, events = create_event_collector()
    control_manager = WorkflowControlManager(
        event_bus=event_bus,
    )
    engine = RuntimeEngine(
        control_manager=control_manager,
    )
    engine.register(
        "test_node",
        SuccessfulRuntimeNode(),
    )

    await engine.execute(
        context=build_context(),
        execution_plan=build_plan(),
    )

    event_types = [event.event_type for event in events]

    assert engine.event_bus is event_bus
    assert RuntimeEventType.WORKFLOW_PROGRESS_STARTED in event_types
    assert RuntimeEventType.WAVE_PROGRESS_STARTED in event_types
    assert RuntimeEventType.NODE_PROGRESS_STARTED in event_types
    assert RuntimeEventType.NODE_PROGRESS_RUNNING in event_types
    assert RuntimeEventType.NODE_PROGRESS_COMPLETED in event_types
    assert RuntimeEventType.WAVE_PROGRESS_COMPLETED in event_types

    node_completed = next(
        event
        for event in events
        if event.event_type is RuntimeEventType.NODE_PROGRESS_COMPLETED
    )
    assert node_completed.execution_id == "execution-1"
    assert node_completed.workflow_id == "unit_workflow"
    assert node_completed.runtime_id == "runtime-1"
    assert node_completed.node_name == "test_node"
    assert node_completed.wave_index == 0
    assert node_completed.payload["workflow_name"] == "unit_workflow"
    assert node_completed.payload["node_type"] == "test"
    assert node_completed.payload["success"] is True
    assert node_completed.payload["state"] == WorkflowControlState.RUNNING.value
    assert node_completed.metadata["context_version"] == 1

    wave_completed = next(
        event
        for event in events
        if event.event_type is RuntimeEventType.WAVE_PROGRESS_COMPLETED
    )
    assert wave_completed.payload["wave_nodes"] == [
        "test_node",
    ]
    assert wave_completed.payload["context_version"] == 1


@pytest.mark.asyncio
async def test_runtime_engine_emits_failed_progress_events() -> None:
    event_bus, events = create_event_collector()
    control_manager = WorkflowControlManager(
        event_bus=event_bus,
    )
    engine = RuntimeEngine(
        control_manager=control_manager,
    )
    engine.register(
        "test_node",
        FailingRuntimeNode(),
    )

    await engine.execute(
        context=build_context(),
        execution_plan=build_plan(),
    )

    event_types = [event.event_type for event in events]

    assert RuntimeEventType.NODE_PROGRESS_FAILED in event_types
    assert RuntimeEventType.WAVE_PROGRESS_FAILED in event_types

    node_failed = next(
        event
        for event in events
        if event.event_type is RuntimeEventType.NODE_PROGRESS_FAILED
    )
    assert node_failed.node_name == "test_node"
    assert node_failed.wave_index == 0
    assert node_failed.payload["success"] is False
    assert node_failed.payload["error_count"] == 1

    wave_failed = next(
        event
        for event in events
        if event.event_type is RuntimeEventType.WAVE_PROGRESS_FAILED
    )
    assert wave_failed.wave_index == 0
    assert wave_failed.payload["wave_nodes"] == [
        "test_node",
    ]


class PauseRequestRuntimeNode(RuntimeNode):
    node_name = "pause_node"
    node_type = "test"

    def __init__(
        self,
        control_manager: WorkflowControlManager,
        executed_nodes: list[str],
    ) -> None:
        self._control_manager = control_manager
        self._executed_nodes = executed_nodes

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        self._executed_nodes.append(
            self.node_name,
        )
        await self._control_manager.request_pause(
            context.execution_id,
            reason="pause before next wave",
            requested_by="unit_test",
        )
        return RuntimeNodeOutput.success_output()


class RecordingRuntimeNode(RuntimeNode):
    node_type = "test"

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
        return RuntimeNodeOutput.success_output()


def build_two_wave_plan(
    execution_id: str = "execution-1",
) -> WorkflowExecutionPlan:
    return WorkflowExecutionPlan(
        workflow_name="unit_workflow",
        execution_id=execution_id,
        nodes={
            "pause_node": ExecutionPlanNode(
                name="pause_node",
                node_type="test",
                max_retries=0,
            ),
            "second_node": ExecutionPlanNode(
                name="second_node",
                node_type="test",
                dependencies=("pause_node",),
                max_retries=0,
            ),
        },
        waves=(
            ExecutionWave(
                index=0,
                nodes=("pause_node",),
            ),
            ExecutionWave(
                index=1,
                nodes=("second_node",),
            ),
        ),
    )


@pytest.mark.asyncio
async def test_runtime_engine_waits_if_pause_is_requested_before_next_wave() -> None:
    control_manager = WorkflowControlManager()
    executed_nodes: list[str] = []
    engine = RuntimeEngine(
        control_manager=control_manager,
    )
    engine.register_many(
        {
            "pause_node": PauseRequestRuntimeNode(
                control_manager=control_manager,
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

    for _ in range(10):
        if (
            control_manager.get_state(
                "execution-1",
            )
            is WorkflowControlState.PAUSED
        ):
            break
        await asyncio.sleep(
            0,
        )

    assert (
        control_manager.get_state(
            "execution-1",
        )
        is WorkflowControlState.PAUSED
    )
    assert executed_nodes == [
        "pause_node",
    ]
    assert execution_task.done() is False

    await control_manager.request_resume(
        "execution-1",
        reason="resume next wave",
        requested_by="unit_test",
    )

    await asyncio.wait_for(
        execution_task,
        timeout=1.0,
    )

    assert executed_nodes == [
        "pause_node",
        "second_node",
    ]
    assert (
        control_manager.get_state(
            "execution-1",
        )
        is WorkflowControlState.COMPLETED
    )


class CancelRequestRuntimeNode(RuntimeNode):
    node_name = "cancel_node"
    node_type = "test"

    def __init__(
        self,
        control_manager: WorkflowControlManager,
        executed_nodes: list[str],
    ) -> None:
        self._control_manager = control_manager
        self._executed_nodes = executed_nodes

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        self._executed_nodes.append(
            self.node_name,
        )
        await self._control_manager.request_cancel(
            context.execution_id,
            reason="cancel before next wave",
            requested_by="unit_test",
        )
        return RuntimeNodeOutput.success_output()


def build_cancel_two_wave_plan(
    execution_id: str = "execution-1",
) -> WorkflowExecutionPlan:
    return WorkflowExecutionPlan(
        workflow_name="unit_workflow",
        execution_id=execution_id,
        nodes={
            "cancel_node": ExecutionPlanNode(
                name="cancel_node",
                node_type="test",
                max_retries=0,
            ),
            "second_node": ExecutionPlanNode(
                name="second_node",
                node_type="test",
                dependencies=("cancel_node",),
                max_retries=0,
            ),
        },
        waves=(
            ExecutionWave(
                index=0,
                nodes=("cancel_node",),
            ),
            ExecutionWave(
                index=1,
                nodes=("second_node",),
            ),
        ),
    )


def assert_cancelled_workflow_output(
    result: RuntimeContext,
    *,
    reason: str,
    requested_by: str,
    cancel_boundary: str,
    wave_index: int,
    node_name: str,
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
    assert outputs["reason"] == reason
    assert outputs["requested_by"] == requested_by
    assert outputs["cancel_boundary"] == cancel_boundary
    assert outputs["wave_index"] == wave_index
    assert outputs["node_name"] == node_name

    metadata = cancelled_output["execution_metadata"]
    assert metadata["node_name"] == RuntimeEngine.CANCELLED_WORKFLOW_OUTPUT_NAME
    assert metadata["cancelled"] is True
    assert metadata["status"] == WorkflowControlState.CANCELLED.value
    assert metadata["cancel_boundary"] == cancel_boundary
    assert metadata["wave_index"] == wave_index
    assert metadata["cancelled_node_name"] == node_name


@pytest.mark.asyncio
async def test_runtime_engine_cancels_before_next_wave_when_cancel_requested() -> None:
    control_manager = WorkflowControlManager()
    executed_nodes: list[str] = []
    engine = RuntimeEngine(
        control_manager=control_manager,
    )
    engine.register_many(
        {
            "cancel_node": CancelRequestRuntimeNode(
                control_manager=control_manager,
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
        execution_plan=build_cancel_two_wave_plan(),
    )

    snapshot = control_manager.get_snapshot(
        "execution-1",
    )

    assert result.errors == []
    assert executed_nodes == [
        "cancel_node",
    ]
    assert "second_node" not in result.node_outputs
    assert_cancelled_workflow_output(
        result,
        reason="cancel before next wave",
        requested_by="unit_test",
        cancel_boundary="after_node",
        wave_index=0,
        node_name="cancel_node",
    )
    assert snapshot.state is WorkflowControlState.CANCELLED
    assert snapshot.reason == "cancel before next wave"
    assert snapshot.requested_by == "unit_test"
    assert snapshot.metadata["cancelled"] is True
    assert snapshot.metadata["status"] == WorkflowControlState.CANCELLED.value
    assert snapshot.metadata["cancel_boundary"] == "after_node"
    assert snapshot.metadata["wave_index"] == 0
    assert snapshot.metadata["node_name"] == "cancel_node"


class RequestControlBeforeFirstNodeHook(NoOpRuntimeLifecycleHook):
    def __init__(
        self,
        control_manager: WorkflowControlManager,
        command: str,
    ) -> None:
        self._control_manager = control_manager
        self._command = command
        self._requested = False

    async def before_node_execute(
        self,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
    ) -> None:
        if self._requested or plan_node.name != "first_node":
            return

        self._requested = True
        if self._command == "pause":
            await self._control_manager.request_pause(
                context.execution_id,
                reason="pause before next node",
                requested_by="unit_test",
            )
            return

        await self._control_manager.request_cancel(
            context.execution_id,
            reason="cancel before next node",
            requested_by="unit_test",
        )


def build_same_wave_plan(
    execution_id: str = "execution-1",
) -> WorkflowExecutionPlan:
    return WorkflowExecutionPlan(
        workflow_name="unit_workflow",
        execution_id=execution_id,
        nodes={
            "first_node": ExecutionPlanNode(
                name="first_node",
                node_type="test",
                max_retries=0,
            ),
            "second_node": ExecutionPlanNode(
                name="second_node",
                node_type="test",
                max_retries=0,
            ),
        },
        waves=(
            ExecutionWave(
                index=0,
                nodes=(
                    "first_node",
                    "second_node",
                ),
            ),
        ),
    )


@pytest.mark.asyncio
async def test_runtime_engine_waits_if_pause_is_requested_before_next_node() -> None:
    control_manager = WorkflowControlManager()
    executed_nodes: list[str] = []
    lifecycle_manager = RuntimeLifecycleManager(
        hooks=(
            RequestControlBeforeFirstNodeHook(
                control_manager=control_manager,
                command="pause",
            ),
        )
    )
    engine = RuntimeEngine(
        lifecycle_manager=lifecycle_manager,
        control_manager=control_manager,
    )
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

    execution_task = asyncio.create_task(
        engine.execute(
            context=build_context(),
            execution_plan=build_same_wave_plan(),
        )
    )

    for _ in range(10):
        if (
            control_manager.get_state(
                "execution-1",
            )
            is WorkflowControlState.PAUSED
        ):
            break
        await asyncio.sleep(
            0,
        )

    assert (
        control_manager.get_state(
            "execution-1",
        )
        is WorkflowControlState.PAUSED
    )
    assert "second_node" not in executed_nodes
    assert execution_task.done() is False

    await control_manager.request_resume(
        "execution-1",
        reason="resume next node",
        requested_by="unit_test",
    )

    await asyncio.wait_for(
        execution_task,
        timeout=1.0,
    )

    assert executed_nodes == [
        "first_node",
        "second_node",
    ]
    assert (
        control_manager.get_state(
            "execution-1",
        )
        is WorkflowControlState.COMPLETED
    )


@pytest.mark.asyncio
async def test_runtime_engine_cancels_before_next_node_when_cancel_requested() -> None:
    control_manager = WorkflowControlManager()
    executed_nodes: list[str] = []
    lifecycle_manager = RuntimeLifecycleManager(
        hooks=(
            RequestControlBeforeFirstNodeHook(
                control_manager=control_manager,
                command="cancel",
            ),
        )
    )
    engine = RuntimeEngine(
        lifecycle_manager=lifecycle_manager,
        control_manager=control_manager,
    )
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
        execution_plan=build_same_wave_plan(),
    )

    snapshot = control_manager.get_snapshot(
        "execution-1",
    )

    assert result.errors == []
    assert executed_nodes == [
        "first_node",
    ]
    assert "second_node" not in result.node_outputs
    assert_cancelled_workflow_output(
        result,
        reason="cancel before next node",
        requested_by="unit_test",
        cancel_boundary="before_node",
        wave_index=0,
        node_name="second_node",
    )
    assert snapshot.state is WorkflowControlState.CANCELLED
    assert snapshot.reason == "cancel before next node"
    assert snapshot.requested_by == "unit_test"
    assert snapshot.metadata["cancelled"] is True
    assert snapshot.metadata["status"] == WorkflowControlState.CANCELLED.value
    assert snapshot.metadata["cancel_boundary"] == "before_node"
    assert snapshot.metadata["wave_index"] == 0
    assert snapshot.metadata["node_name"] == "second_node"
