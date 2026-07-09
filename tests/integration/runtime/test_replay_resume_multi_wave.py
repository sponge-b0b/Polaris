from __future__ import annotations

from pathlib import Path

import pytest

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.replay.replay_engine import ReplayEngine
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.workflow.bootstrap.workflow_bootstrap import (
    WorkflowBootstrapConfig,
    build_workflow_runtime_async,
)
from core.workflow.models.workflow_graph_definition import (
    WorkflowGraphDefinition,
)
from core.workflow.models.workflow_node_definition import (
    WorkflowNodeDefinition,
)


class ReplayWaveOneNode(RuntimeNode):
    node_name = "replay_wave_one_node"
    node_type = "test.replay.wave_one"
    node_version = "1.0.0"

    parallel_safe = True

    run_count = 0

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        ReplayWaveOneNode.run_count += 1

        return RuntimeNodeOutput.success_output(
            outputs={
                "wave": 0,
                "value": "wave_one_complete",
                "run_count": ReplayWaveOneNode.run_count,
            },
        )


class ReplayWaveTwoNode(RuntimeNode):
    node_name = "replay_wave_two_node"
    node_type = "test.replay.wave_two"
    node_version = "1.0.0"

    parallel_safe = True

    run_count = 0

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        ReplayWaveTwoNode.run_count += 1

        assert "wave_one" in context.node_outputs

        return RuntimeNodeOutput.success_output(
            outputs={
                "wave": 1,
                "value": "wave_two_complete",
                "run_count": ReplayWaveTwoNode.run_count,
            },
        )


class ReplayWaveThreeNode(RuntimeNode):
    node_name = "replay_wave_three_node"
    node_type = "test.replay.wave_three"
    node_version = "1.0.0"

    parallel_safe = True

    run_count = 0

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        ReplayWaveThreeNode.run_count += 1

        assert "wave_two" in context.node_outputs

        return RuntimeNodeOutput.success_output(
            outputs={
                "wave": 2,
                "value": "wave_three_complete",
                "run_count": ReplayWaveThreeNode.run_count,
            },
        )


class ReplayMultiWaveWorkflow(WorkflowGraphDefinition):
    @property
    def workflow_name(
        self,
    ) -> str:
        return "replay_multi_wave_workflow"

    @property
    def workflow_description(
        self,
    ) -> str:
        return "Integration workflow for replay resume from wave checkpoint."

    def build_graph(
        self,
    ) -> list[WorkflowNodeDefinition]:
        return [
            WorkflowNodeDefinition(
                name="wave_one",
                node_type=ReplayWaveOneNode,
                dependencies=(),
                enabled=True,
                tags=("test", "replay"),
            ),
            WorkflowNodeDefinition(
                name="wave_two",
                node_type=ReplayWaveTwoNode,
                dependencies=("wave_one",),
                enabled=True,
                tags=("test", "replay"),
            ),
            WorkflowNodeDefinition(
                name="wave_three",
                node_type=ReplayWaveThreeNode,
                dependencies=("wave_two",),
                enabled=True,
                tags=("test", "replay"),
            ),
        ]


@pytest.mark.asyncio
async def test_replay_resume_from_wave_checkpoint_skips_completed_nodes(
    tmp_path: Path,
) -> None:
    ReplayWaveOneNode.run_count = 0
    ReplayWaveTwoNode.run_count = 0
    ReplayWaveThreeNode.run_count = 0

    checkpoint_dir = tmp_path / "checkpoints"
    artifact_dir = tmp_path / "artifacts"

    runtime = await build_workflow_runtime_async(
        config=WorkflowBootstrapConfig(
            checkpoint_dir=str(checkpoint_dir),
            artifact_dir=str(artifact_dir),
            enable_checkpoints=True,
            enable_artifacts=True,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
            checkpoint_on_wave_completion=True,
        ),
        workflow_definitions=[
            ReplayMultiWaveWorkflow(),
        ],
    )

    first_result = await runtime.facade.run_workflow(
        workflow_name="replay_multi_wave_workflow",
        mode="simulation",
        archive_on_completion=False,
        checkpoint_on_completion=False,
    )

    assert first_result.success is True

    assert ReplayWaveOneNode.run_count == 1
    assert ReplayWaveTwoNode.run_count == 1
    assert ReplayWaveThreeNode.run_count == 1

    checkpoints = sorted(
        checkpoint_dir.glob("*.json"),
    )

    assert len(checkpoints) >= 3

    wave_zero_checkpoint = _checkpoint_for_wave(
        checkpoints=checkpoints,
        wave_index=0,
    )

    compiled_workflow = runtime.facade.compile_workflow(
        workflow_name="replay_multi_wave_workflow",
        execution_id=first_result.execution_id,
    )

    assert runtime.facade.checkpoint_manager is not None

    replay_engine = ReplayEngine(
        workflow_engine=runtime.facade.workflow_engine,
        checkpoint_manager=runtime.facade.checkpoint_manager,
        event_bus=runtime.facade.event_bus,
    )

    replay_result = await replay_engine.replay_from_checkpoint(
        compiled_workflow=compiled_workflow,
        checkpoint_file=wave_zero_checkpoint,
        archive_on_completion=False,
        checkpoint_on_completion=False,
        resume_from_checkpoint_position=True,
    )

    assert replay_result.success is True
    assert replay_result.error_message is None
    assert replay_result.final_context is not None

    assert ReplayWaveOneNode.run_count == 1
    assert ReplayWaveTwoNode.run_count == 2
    assert ReplayWaveThreeNode.run_count == 2

    final_context = replay_result.final_context

    assert "wave_one" in final_context.node_outputs
    assert "wave_two" in final_context.node_outputs
    assert "wave_three" in final_context.node_outputs

    metadata = replay_result.metadata or {}

    assert metadata["resume_from_checkpoint_position"] is True
    assert metadata["remaining_node_count"] == 2
    assert metadata["remaining_wave_count"] == 2
    assert "wave_one" in metadata["completed_nodes"]


def _checkpoint_for_wave(
    checkpoints: list[Path],
    wave_index: int,
) -> Path:
    target = f"_wave_{wave_index}.json"

    for checkpoint in checkpoints:
        if checkpoint.name.endswith(
            target,
        ):
            return checkpoint

    raise AssertionError(
        f"No checkpoint found for wave {wave_index}. "
        f"Available checkpoints: {[path.name for path in checkpoints]}"
    )
