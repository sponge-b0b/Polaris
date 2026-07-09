from __future__ import annotations

import pytest

from core.runtime.control import WorkflowControlManager
from core.runtime.control import WorkflowControlState
from core.runtime.events import EventBus
from core.storage.persistence.postgres_completed_run_archive import (
    PostgresCompletedRunArchive,
)
from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapConfig
from core.workflow.bootstrap.workflow_bootstrap import build_workflow_runtime
from core.workflow.bootstrap.workflow_bootstrap import build_workflow_runtime_async


def bootstrap_config() -> WorkflowBootstrapConfig:
    return WorkflowBootstrapConfig(
        enable_checkpoints=False,
        enable_artifacts=False,
        enable_telemetry=False,
        enable_jsonl_telemetry=False,
        enable_observability=False,
        enable_policies=False,
        enable_governance=False,
    )


def test_build_workflow_runtime_wires_postgres_completed_run_archive() -> None:
    runtime = build_workflow_runtime(
        config=bootstrap_config(),
    )

    assert isinstance(
        runtime.archive,
        PostgresCompletedRunArchive,
    )
    assert runtime.facade.state_manager.archive is runtime.archive


def test_build_workflow_runtime_wires_default_control_manager() -> None:
    runtime = build_workflow_runtime(
        config=bootstrap_config(),
    )

    assert isinstance(
        runtime.workflow_control_manager,
        WorkflowControlManager,
    )
    assert runtime.facade.workflow_control_manager is runtime.workflow_control_manager
    assert runtime.facade.runtime_engine.control_manager is (
        runtime.workflow_control_manager
    )
    assert runtime.facade.runtime_engine.event_bus is runtime.event_bus
    assert runtime.workflow_control_manager.event_bus is runtime.event_bus
    assert runtime.facade.observability_manager is runtime.observability_manager
    assert (
        runtime.facade.runtime_engine.observability_manager
        is runtime.observability_manager
    )


def test_build_workflow_runtime_composes_replay_with_shared_components() -> None:
    config = bootstrap_config()
    config = WorkflowBootstrapConfig(
        enable_checkpoints=True,
        enable_artifacts=config.enable_artifacts,
        enable_telemetry=config.enable_telemetry,
        enable_jsonl_telemetry=config.enable_jsonl_telemetry,
        enable_observability=config.enable_observability,
        enable_policies=True,
        enable_governance=True,
    )

    runtime = build_workflow_runtime(config=config)

    assert runtime.replay_engine is not None
    assert runtime.facade.checkpoint_manager is not None
    assert runtime.replay_engine.workflow_engine is runtime.facade.workflow_engine
    assert runtime.replay_engine.checkpoint_manager is runtime.facade.checkpoint_manager
    assert runtime.replay_engine.event_bus is runtime.event_bus
    assert runtime.replay_engine.policy_engine is runtime.policy_engine
    assert runtime.replay_engine.governance_engine is runtime.governance_engine


def test_build_workflow_runtime_uses_injected_control_manager() -> None:
    event_bus = EventBus()
    control_manager = WorkflowControlManager(
        event_bus=event_bus,
    )

    runtime = build_workflow_runtime(
        config=bootstrap_config(),
        event_bus=event_bus,
        workflow_control_manager=control_manager,
    )

    assert runtime.event_bus is event_bus
    assert runtime.workflow_control_manager is control_manager
    assert runtime.facade.workflow_control_manager is control_manager
    assert runtime.facade.runtime_engine.control_manager is control_manager
    assert runtime.facade.runtime_engine.event_bus is event_bus


@pytest.mark.asyncio
async def test_build_workflow_runtime_async_uses_injected_control_manager() -> None:
    event_bus = EventBus()
    control_manager = WorkflowControlManager(
        event_bus=event_bus,
    )

    runtime = await build_workflow_runtime_async(
        config=bootstrap_config(),
        event_bus=event_bus,
        workflow_control_manager=control_manager,
    )

    await runtime.facade.pause_workflow(
        execution_id="bootstrap-execution-1",
        reason="pause from bootstrap test",
        requested_by="integration_test",
    )

    assert runtime.event_bus is event_bus
    assert runtime.workflow_control_manager is control_manager
    assert runtime.facade.workflow_control_manager is control_manager
    assert runtime.facade.runtime_engine.control_manager is control_manager
    assert (
        runtime.workflow_control_manager.get_state(
            "bootstrap-execution-1",
        )
        is WorkflowControlState.PAUSING
    )
