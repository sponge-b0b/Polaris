from __future__ import annotations

from typing import Any

import pytest

from core.runtime.policies.policy import BaseRuntimePolicy
from core.runtime.policies.policy_engine import PolicyEngine
from core.runtime.policies.policy_registry import PolicyRegistry
from core.runtime.policies.policy_result import PolicyResult
from core.runtime.replay.replay_engine import ReplayEngine
from core.workflow.bootstrap.workflow_bootstrap import (
    WorkflowBootstrapConfig,
    build_workflow_runtime,
)


class DenyWorkflowReplayPolicy(BaseRuntimePolicy):
    policy_name = "deny_workflow_replay"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> PolicyResult:
        if (context or {}).get("policy_phase") == "workflow_replay_preflight":
            return PolicyResult.deny(
                policy_name=self.policy_name,
                message="Workflow replay denied by test policy.",
                reason="replay_blocked",
            )
        return PolicyResult.allow(policy_name=self.policy_name)


@pytest.mark.asyncio
async def test_checkpoint_replay_resumes_successfully(
    tmp_path,
) -> None:
    checkpoint_dir = tmp_path / "checkpoints"
    artifact_dir = tmp_path / "artifacts"

    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            checkpoint_dir=str(checkpoint_dir),
            artifact_dir=str(artifact_dir),
            enable_checkpoints=True,
            enable_artifacts=True,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
            checkpoint_on_wave_completion=True,
        ),
    )

    load_result = await runtime.facade.load_plugins_from_dir(
        plugin_dir="plugins/example_market_plugin",
        recursive=False,
        overwrite=True,
        register_workflows=True,
    )

    assert load_result.success is True

    run_result = await runtime.facade.run_workflow(
        workflow_name="example_plugin_workflow",
        mode="simulation",
        archive_on_completion=False,
        checkpoint_on_completion=True,
    )

    assert run_result.success is True

    checkpoints = sorted(
        checkpoint_dir.glob("*.json"),
    )

    assert checkpoints

    compiled_workflow = runtime.facade.compile_workflow(
        workflow_name="example_plugin_workflow",
        execution_id=run_result.execution_id,
    )

    assert runtime.facade.checkpoint_manager is not None

    replay_engine = ReplayEngine(
        workflow_engine=runtime.facade.workflow_engine,
        checkpoint_manager=runtime.facade.checkpoint_manager,
        event_bus=runtime.facade.event_bus,
    )

    replay_result = await replay_engine.replay_from_checkpoint(
        compiled_workflow=compiled_workflow,
        checkpoint_file=checkpoints[-1],
        archive_on_completion=False,
        checkpoint_on_completion=False,
        resume_from_checkpoint_position=True,
    )

    assert replay_result.success is True
    assert replay_result.error_message is None
    assert replay_result.final_context is not None

    assert replay_result.workflow_id == "example_plugin_workflow"
    assert replay_result.execution_id == run_result.execution_id

    metadata = replay_result.metadata or {}

    assert metadata["resume_from_checkpoint_position"] is True
    assert "plugin_market_node" in metadata["completed_nodes"]


@pytest.mark.asyncio
async def test_checkpoint_replay_is_policy_governed(
    tmp_path,
) -> None:
    checkpoint_dir = tmp_path / "checkpoints"
    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            checkpoint_dir=str(checkpoint_dir),
            artifact_dir=str(tmp_path / "artifacts"),
            enable_checkpoints=True,
            enable_artifacts=True,
            enable_policies=True,
            enable_governance=False,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
        ),
    )
    load_result = await runtime.facade.load_plugins_from_dir(
        plugin_dir="plugins/example_market_plugin",
        recursive=False,
        overwrite=True,
        register_workflows=True,
    )
    assert load_result.success is True
    run_result = await runtime.facade.run_workflow(
        workflow_name="example_plugin_workflow",
        mode="simulation",
        archive_on_completion=False,
        checkpoint_on_completion=True,
    )
    checkpoints = sorted(checkpoint_dir.glob("*.json"))
    assert checkpoints
    compiled_workflow = runtime.facade.compile_workflow(
        workflow_name="example_plugin_workflow",
        execution_id=run_result.execution_id,
    )
    assert runtime.facade.checkpoint_manager is not None
    replay_engine = ReplayEngine(
        workflow_engine=runtime.facade.workflow_engine,
        checkpoint_manager=runtime.facade.checkpoint_manager,
        event_bus=runtime.facade.event_bus,
        policy_engine=PolicyEngine(
            registry=PolicyRegistry(policies=[DenyWorkflowReplayPolicy()])
        ),
    )

    replay_result = await replay_engine.replay_from_checkpoint(
        compiled_workflow=compiled_workflow,
        checkpoint_file=checkpoints[-1],
        archive_on_completion=False,
        checkpoint_on_completion=False,
    )

    assert replay_result.success is False
    assert replay_result.error_message is not None
    assert "replay_blocked" in replay_result.error_message
    assert replay_result.final_context is None
