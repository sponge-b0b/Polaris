from __future__ import annotations

import pytest

from core.runtime.control import WorkflowControlManager, WorkflowControlState
from core.runtime.events import EventBus
from core.workflow.execution.workflow_facade import WorkflowFacade, WorkflowFacadeConfig


def facade_config() -> WorkflowFacadeConfig:
    return WorkflowFacadeConfig(
        enable_checkpoints=False,
        enable_artifacts=False,
        enable_telemetry=False,
    )


def test_workflow_facade_create_wires_default_control_manager() -> None:
    facade = WorkflowFacade.create(
        config=facade_config(),
    )

    assert isinstance(
        facade.workflow_control_manager,
        WorkflowControlManager,
    )
    assert facade.runtime_engine.control_manager is facade.workflow_control_manager
    assert facade.runtime_engine.event_bus is facade.event_bus


def test_workflow_facade_create_uses_injected_control_manager() -> None:
    event_bus = EventBus()
    control_manager = WorkflowControlManager(
        event_bus=event_bus,
    )

    facade = WorkflowFacade.create(
        event_bus=event_bus,
        workflow_control_manager=control_manager,
        config=facade_config(),
    )

    assert facade.workflow_control_manager is control_manager
    assert facade.runtime_engine.control_manager is control_manager
    assert facade.runtime_engine.event_bus is event_bus


@pytest.mark.asyncio
async def test_workflow_facade_control_methods_delegate_to_manager() -> None:
    facade = WorkflowFacade.create(
        config=facade_config(),
    )

    pause_snapshot = await facade.pause_workflow(
        execution_id="execution-1",
        reason="pause from facade",
        requested_by="unit_test",
        metadata={
            "source": "facade_test",
        },
    )

    assert pause_snapshot.state is WorkflowControlState.PAUSING
    assert pause_snapshot.reason == "pause from facade"
    assert pause_snapshot.requested_by == "unit_test"
    assert pause_snapshot.metadata["source"] == "facade_test"
    assert (
        facade.get_workflow_state(
            "execution-1",
        )
        is WorkflowControlState.PAUSING
    )

    resume_snapshot = await facade.resume_workflow(
        execution_id="execution-1",
        reason="resume from facade",
        requested_by="unit_test",
    )

    assert resume_snapshot.state is WorkflowControlState.RESUMING
    assert resume_snapshot.reason == "resume from facade"
    assert (
        facade.get_workflow_control_snapshot(
            "execution-1",
        ).requested_by
        == "unit_test"
    )

    cancel_snapshot = await facade.cancel_workflow(
        execution_id="execution-1",
        reason="cancel from facade",
        requested_by="unit_test",
    )

    assert cancel_snapshot.state is WorkflowControlState.CANCELLING
    assert cancel_snapshot.reason == "cancel from facade"
    assert (
        facade.get_workflow_state(
            "execution-1",
        )
        is WorkflowControlState.CANCELLING
    )
