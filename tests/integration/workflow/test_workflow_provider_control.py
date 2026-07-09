from __future__ import annotations

import pytest

from dishka import make_container

from core.bootstrap.workflow_providers import WorkflowInfrastructureProvider
from core.runtime.control import WorkflowControlManager
from core.runtime.control import WorkflowControlState
from core.runtime.events import EventBus
from core.storage.persistence.completed_run_archive import CompletedRunArchive
from core.storage.persistence.postgres_completed_run_archive import (
    PostgresCompletedRunArchive,
)
from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapResult
from core.workflow.execution.workflow_facade import WorkflowFacade


def test_workflow_provider_resolves_postgres_completed_run_archive() -> None:
    container = make_container(
        WorkflowInfrastructureProvider(),
    )

    archive = container.get(
        CompletedRunArchive,
    )
    facade = container.get(
        WorkflowFacade,
    )

    assert isinstance(
        archive,
        PostgresCompletedRunArchive,
    )
    assert facade.state_manager.archive is archive


def test_workflow_provider_exposes_one_bootstrapped_runtime_graph() -> None:
    container = make_container(WorkflowInfrastructureProvider())

    runtime = container.get(WorkflowBootstrapResult)

    assert container.get(WorkflowFacade) is runtime.facade
    assert container.get(EventBus) is runtime.event_bus
    assert container.get(WorkflowControlManager) is runtime.workflow_control_manager
    assert container.get(CompletedRunArchive) is runtime.archive


def test_workflow_provider_resolves_control_manager_with_event_bus() -> None:
    container = make_container(
        WorkflowInfrastructureProvider(),
    )

    event_bus = container.get(
        EventBus,
    )
    control_manager = container.get(
        WorkflowControlManager,
    )

    assert isinstance(
        control_manager,
        WorkflowControlManager,
    )
    assert control_manager.event_bus is event_bus


@pytest.mark.asyncio
async def test_workflow_provider_wires_control_manager_into_facade() -> None:
    container = make_container(
        WorkflowInfrastructureProvider(),
    )

    control_manager = container.get(
        WorkflowControlManager,
    )
    event_bus = container.get(
        EventBus,
    )
    facade = container.get(
        WorkflowFacade,
    )

    await facade.pause_workflow(
        execution_id="dishka-execution-1",
        reason="pause from dishka provider test",
        requested_by="integration_test",
    )

    assert facade.workflow_control_manager is control_manager
    assert facade.runtime_engine.control_manager is control_manager
    assert facade.event_bus is event_bus
    assert facade.runtime_engine.event_bus is event_bus
    assert (
        control_manager.get_state(
            "dishka-execution-1",
        )
        is WorkflowControlState.PAUSING
    )
