from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.runtime.checkpoints.checkpoint_manager import CheckpointManager
from core.runtime.checkpoints.runtime_checkpoint import RuntimeCheckpoint
from core.runtime.events.event_bus import EventBus
from core.runtime.events.runtime_events import RuntimeEvent, RuntimeEventType
from core.runtime.governance.governance_engine import GovernanceEngine
from core.runtime.policies.policy_engine import PolicyEngine
from core.runtime.state.runtime_context import RuntimeContext
from core.workflow.compiler.workflow_compiler import CompiledWorkflow
from core.workflow.execution.workflow_engine import WorkflowEngine
from core.workflow.models.workflow_execution_plan import (
    ExecutionPlanNode,
    ExecutionWave,
    WorkflowExecutionPlan,
)


@dataclass(frozen=True, slots=True)
class ReplayResult:
    success: bool
    workflow_id: str
    execution_id: str
    replay_started_at: datetime
    replay_completed_at: datetime
    duration_seconds: float
    final_context: RuntimeContext | None = None
    error_message: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "replay_started_at": self.replay_started_at.isoformat(),
            "replay_completed_at": self.replay_completed_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "final_context": (
                self.final_context.to_dict() if self.final_context is not None else None
            ),
            "error_message": self.error_message,
            "metadata": deepcopy(self.metadata or {}),
        }


class ReplayEngine:
    """
    Canonical deterministic replay engine.

    Replays a compiled workflow from a persisted RuntimeCheckpoint.

    Supports resume-from-wave by compiling a replay-only execution plan
    that contains only unfinished nodes after the checkpoint position.
    """

    def __init__(
        self,
        workflow_engine: WorkflowEngine,
        checkpoint_manager: CheckpointManager,
        event_bus: EventBus | None = None,
        policy_engine: PolicyEngine | None = None,
        governance_engine: GovernanceEngine | None = None,
    ) -> None:
        self.workflow_engine = workflow_engine
        self.checkpoint_manager = checkpoint_manager
        self.event_bus = event_bus
        self.policy_engine = policy_engine
        self.governance_engine = governance_engine

    async def replay_from_checkpoint(
        self,
        compiled_workflow: CompiledWorkflow,
        checkpoint_file: str | Path,
        archive_on_completion: bool = True,
        checkpoint_on_completion: bool = False,
        resume_from_checkpoint_position: bool = True,
        retry_failed_nodes: bool = True,
    ) -> ReplayResult:
        started_at = datetime.now(UTC)

        try:
            await self._require_replay_allowed(
                compiled_workflow=compiled_workflow,
                checkpoint_file=checkpoint_file,
                archive_on_completion=archive_on_completion,
                checkpoint_on_completion=checkpoint_on_completion,
                resume_from_checkpoint_position=resume_from_checkpoint_position,
                retry_failed_nodes=retry_failed_nodes,
            )
            checkpoint = await self.load_runtime_checkpoint(
                checkpoint_file=checkpoint_file,
            )

            context = self._require_context(
                checkpoint=checkpoint,
            )

            replay_workflow = (
                self._build_resumed_compiled_workflow(
                    compiled_workflow=compiled_workflow,
                    checkpoint=checkpoint,
                    context=context,
                    retry_failed_nodes=retry_failed_nodes,
                )
                if resume_from_checkpoint_position
                else compiled_workflow
            )

            await self._emit(
                RuntimeEvent(
                    event_type=RuntimeEventType.REPLAY_STARTED,
                    execution_id=context.execution_id,
                    workflow_id=context.workflow_id,
                    runtime_id=context.runtime_id,
                    payload={
                        "checkpoint_id": checkpoint.checkpoint_id,
                        "checkpoint_file": str(checkpoint_file),
                        "source_wave_index": checkpoint.wave_index,
                        "resume_from_checkpoint_position": (
                            resume_from_checkpoint_position
                        ),
                        "retry_failed_nodes": retry_failed_nodes,
                        "remaining_node_count": (
                            replay_workflow.execution_plan.total_nodes()
                        ),
                        "remaining_wave_count": (
                            replay_workflow.execution_plan.total_waves()
                        ),
                    },
                )
            )

            if replay_workflow.execution_plan.total_nodes() == 0:
                completed_at = datetime.now(UTC)

                await self._emit(
                    RuntimeEvent(
                        event_type=RuntimeEventType.REPLAY_COMPLETED,
                        execution_id=context.execution_id,
                        workflow_id=context.workflow_id,
                        runtime_id=context.runtime_id,
                        payload={
                            "checkpoint_id": checkpoint.checkpoint_id,
                            "success": True,
                            "no_remaining_nodes": True,
                        },
                    )
                )

                return ReplayResult(
                    success=True,
                    workflow_id=context.workflow_id,
                    execution_id=context.execution_id,
                    replay_started_at=started_at,
                    replay_completed_at=completed_at,
                    duration_seconds=(completed_at - started_at).total_seconds(),
                    final_context=context,
                    error_message=None,
                    metadata={
                        "checkpoint_id": checkpoint.checkpoint_id,
                        "checkpoint_file": str(checkpoint_file),
                        "source_wave_index": checkpoint.wave_index,
                        "completed_nodes": list(checkpoint.completed_nodes),
                        "failed_nodes": list(checkpoint.failed_nodes),
                        "skipped_nodes": list(checkpoint.skipped_nodes),
                        "resume_from_checkpoint_position": (
                            resume_from_checkpoint_position
                        ),
                        "retry_failed_nodes": retry_failed_nodes,
                        "remaining_node_count": 0,
                        "remaining_wave_count": 0,
                        "no_remaining_nodes": True,
                    },
                )

            workflow_result = await self.workflow_engine.execute_from_context(
                compiled_workflow=replay_workflow,
                context=context,
                archive_on_completion=archive_on_completion,
                checkpoint_on_completion=checkpoint_on_completion,
            )

            completed_at = datetime.now(UTC)

            await self._emit(
                RuntimeEvent(
                    event_type=RuntimeEventType.REPLAY_COMPLETED,
                    execution_id=context.execution_id,
                    workflow_id=context.workflow_id,
                    runtime_id=context.runtime_id,
                    payload={
                        "checkpoint_id": checkpoint.checkpoint_id,
                        "success": workflow_result.success,
                    },
                )
            )

            return ReplayResult(
                success=workflow_result.success,
                workflow_id=context.workflow_id,
                execution_id=context.execution_id,
                replay_started_at=started_at,
                replay_completed_at=completed_at,
                duration_seconds=(completed_at - started_at).total_seconds(),
                final_context=workflow_result.final_context,
                error_message=workflow_result.error_message,
                metadata={
                    "checkpoint_id": checkpoint.checkpoint_id,
                    "checkpoint_file": str(checkpoint_file),
                    "source_wave_index": checkpoint.wave_index,
                    "completed_nodes": list(checkpoint.completed_nodes),
                    "failed_nodes": list(checkpoint.failed_nodes),
                    "skipped_nodes": list(checkpoint.skipped_nodes),
                    "resume_from_checkpoint_position": resume_from_checkpoint_position,
                    "retry_failed_nodes": retry_failed_nodes,
                    "remaining_node_count": (
                        replay_workflow.execution_plan.total_nodes()
                    ),
                    "remaining_wave_count": (
                        replay_workflow.execution_plan.total_waves()
                    ),
                },
            )

        except Exception as exc:
            completed_at = datetime.now(UTC)

            await self._emit(
                RuntimeEvent(
                    event_type=RuntimeEventType.REPLAY_FAILED,
                    execution_id=compiled_workflow.execution_plan.execution_id,
                    workflow_id=compiled_workflow.workflow_name,
                    payload={
                        "checkpoint_file": str(checkpoint_file),
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    },
                )
            )

            return ReplayResult(
                success=False,
                workflow_id=compiled_workflow.workflow_name,
                execution_id=compiled_workflow.execution_plan.execution_id,
                replay_started_at=started_at,
                replay_completed_at=completed_at,
                duration_seconds=(completed_at - started_at).total_seconds(),
                final_context=None,
                error_message=str(exc),
                metadata={
                    "checkpoint_file": str(checkpoint_file),
                    "error_type": type(exc).__name__,
                },
            )

    async def _require_replay_allowed(
        self,
        *,
        compiled_workflow: CompiledWorkflow,
        checkpoint_file: str | Path,
        archive_on_completion: bool,
        checkpoint_on_completion: bool,
        resume_from_checkpoint_position: bool,
        retry_failed_nodes: bool,
    ) -> None:
        subject = {
            "operation": "replay_from_checkpoint",
            "workflow_name": compiled_workflow.workflow_name,
            "execution_id": compiled_workflow.execution_plan.execution_id,
            "checkpoint_file": str(checkpoint_file),
            "archive_on_completion": archive_on_completion,
            "checkpoint_on_completion": checkpoint_on_completion,
            "resume_from_checkpoint_position": resume_from_checkpoint_position,
            "retry_failed_nodes": retry_failed_nodes,
        }
        if self.governance_engine is not None:
            await self.governance_engine.require_allowed(
                subject=subject,
                context={
                    "governance_phase": "workflow_replay_preflight",
                    "workflow_name": compiled_workflow.workflow_name,
                    "execution_id": compiled_workflow.execution_plan.execution_id,
                },
            )
        if self.policy_engine is not None:
            await self.policy_engine.require_allowed(
                subject=subject,
                context={
                    "policy_phase": "workflow_replay_preflight",
                    "workflow_name": compiled_workflow.workflow_name,
                    "execution_id": compiled_workflow.execution_plan.execution_id,
                },
            )

    async def load_runtime_checkpoint(
        self,
        checkpoint_file: str | Path,
    ) -> RuntimeCheckpoint:
        payload = await self.checkpoint_manager.load_checkpoint(
            checkpoint_file=checkpoint_file,
        )

        return RuntimeCheckpoint.from_dict(
            payload,
        )

    def _build_resumed_compiled_workflow(
        self,
        compiled_workflow: CompiledWorkflow,
        checkpoint: RuntimeCheckpoint,
        context: RuntimeContext,
        retry_failed_nodes: bool,
    ) -> CompiledWorkflow:
        original_plan = compiled_workflow.execution_plan

        excluded_nodes = set(checkpoint.completed_nodes)
        excluded_nodes.update(checkpoint.skipped_nodes)

        if not retry_failed_nodes:
            excluded_nodes.update(checkpoint.failed_nodes)

        start_wave_index = checkpoint.wave_index + 1

        remaining_wave_node_names: list[tuple[int, tuple[str, ...]]] = []

        for wave in original_plan.waves:
            if wave.index < start_wave_index:
                continue

            node_names = tuple(
                node_name for node_name in wave.nodes if node_name not in excluded_nodes
            )

            if node_names:
                remaining_wave_node_names.append(
                    (
                        wave.index,
                        node_names,
                    )
                )

        remaining_node_names = {
            node_name
            for _, node_names in remaining_wave_node_names
            for node_name in node_names
        }

        # If there is nothing left to run, create a valid empty replay plan.
        if not remaining_node_names:
            resumed_plan = WorkflowExecutionPlan(
                workflow_name=original_plan.workflow_name,
                execution_id=context.execution_id,
                nodes={},
                waves=(),
                metadata={
                    **dict(original_plan.metadata),
                    "replay": True,
                    "resume_from_wave_index": start_wave_index,
                    "source_checkpoint_id": checkpoint.checkpoint_id,
                    "no_remaining_nodes": True,
                },
            )

            return CompiledWorkflow(
                workflow_name=compiled_workflow.workflow_name,
                execution_graph=compiled_workflow.execution_graph,
                execution_plan=resumed_plan,
                runtime_nodes={},
                metadata={
                    **dict(compiled_workflow.metadata),
                    "replay": True,
                    "source_checkpoint_id": checkpoint.checkpoint_id,
                },
            )

        resumed_nodes: dict[str, ExecutionPlanNode] = {}

        for node_name in remaining_node_names:
            original_node = original_plan.get_node(
                node_name,
            )

            resumed_nodes[node_name] = ExecutionPlanNode(
                name=original_node.name,
                node_type=original_node.node_type,
                dependencies=tuple(
                    dependency
                    for dependency in original_node.dependencies
                    if dependency in remaining_node_names
                ),
                enabled=original_node.enabled,
                max_retries=original_node.max_retries,
                timeout_seconds=original_node.timeout_seconds,
                parallel_safe=original_node.parallel_safe,
                metadata={
                    **dict(original_node.metadata),
                    "replay": True,
                    "original_dependencies": list(
                        original_node.dependencies,
                    ),
                },
            )

        resumed_waves = tuple(
            ExecutionWave(
                index=index,
                nodes=node_names,
            )
            for index, (_, node_names) in enumerate(remaining_wave_node_names)
        )

        resumed_plan = WorkflowExecutionPlan(
            workflow_name=original_plan.workflow_name,
            execution_id=context.execution_id,
            nodes=resumed_nodes,
            waves=resumed_waves,
            metadata={
                **dict(original_plan.metadata),
                "replay": True,
                "resume_from_wave_index": start_wave_index,
                "source_checkpoint_id": checkpoint.checkpoint_id,
                "source_checkpoint_wave_index": checkpoint.wave_index,
                "excluded_nodes": sorted(excluded_nodes),
            },
        )

        resumed_plan.validate()

        resumed_runtime_nodes = {
            node_name: runtime_node
            for node_name, runtime_node in compiled_workflow.runtime_nodes.items()
            if node_name in remaining_node_names
        }

        return CompiledWorkflow(
            workflow_name=compiled_workflow.workflow_name,
            execution_graph=compiled_workflow.execution_graph,
            execution_plan=resumed_plan,
            runtime_nodes=resumed_runtime_nodes,
            metadata={
                **dict(compiled_workflow.metadata),
                "replay": True,
                "source_checkpoint_id": checkpoint.checkpoint_id,
                "resume_from_wave_index": start_wave_index,
            },
        )

    def _require_context(
        self,
        checkpoint: RuntimeCheckpoint,
    ) -> RuntimeContext:
        if checkpoint.runtime_context is None:
            raise ValueError(
                f"Checkpoint '{checkpoint.checkpoint_id}' "
                "does not contain a runtime context."
            )

        return checkpoint.runtime_context

    async def _emit(
        self,
        event: RuntimeEvent,
    ) -> None:
        if self.event_bus is None:
            return

        await self.event_bus.emit(
            event,
        )
