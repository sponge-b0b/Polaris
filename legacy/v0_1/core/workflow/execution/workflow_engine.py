from __future__ import annotations

import logging
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from core.runtime.checkpoints.checkpoint_manager import CheckpointManager
from core.runtime.events.event_bus import EventBus
from core.runtime.events.runtime_events import RuntimeEvent, RuntimeEventType
from core.runtime.execution.runtime_engine import RuntimeEngine
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.state_manager import StateManager
from core.workflow.compiler.workflow_compiler import CompiledWorkflow

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class WorkflowExecutionResult:
    """
    Immutable workflow execution result.
    """

    success: bool
    workflow_name: str
    execution_id: str
    runtime_id: str
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    final_context: RuntimeContext
    error_message: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "success": self.success,
            "workflow_name": self.workflow_name,
            "execution_id": self.execution_id,
            "runtime_id": self.runtime_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "final_context": self.final_context.to_dict(),
            "error_message": self.error_message,
            "metadata": deepcopy(self.metadata or {}),
        }


class WorkflowEngine:
    """
    Canonical workflow orchestration engine.

    Coordinates:
    - RuntimeContext creation
    - RuntimeNode registration
    - RuntimeEngine execution
    - workflow lifecycle events
    - persistence/checkpoint coordination
    """

    def __init__(
        self,
        runtime_engine: RuntimeEngine,
        state_manager: StateManager,
        event_bus: EventBus | None = None,
        checkpoint_manager: CheckpointManager | None = None,
    ) -> None:
        self.runtime_engine = runtime_engine
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.checkpoint_manager = checkpoint_manager

    # ========================================================
    # EXECUTE NEW CONTEXT
    # ========================================================

    async def execute(
        self,
        compiled_workflow: CompiledWorkflow,
        workflow_inputs: Mapping[str, Any] | None = None,
        mode: str = "live",
        simulation_time: datetime | None = None,
        archive_on_completion: bool = True,
        checkpoint_on_completion: bool = False,
    ) -> WorkflowExecutionResult:
        compiled_workflow.execution_plan.validate()

        context = self.state_manager.create_context(
            workflow_id=compiled_workflow.workflow_name,
            mode=mode,
            workflow_inputs=workflow_inputs,
            simulation_time=simulation_time,
            execution_id=compiled_workflow.execution_plan.execution_id,
        )

        return await self.execute_from_context(
            compiled_workflow=compiled_workflow,
            context=context,
            archive_on_completion=archive_on_completion,
            checkpoint_on_completion=checkpoint_on_completion,
        )

    # ========================================================
    # EXECUTE EXISTING CONTEXT
    # ========================================================

    async def execute_from_context(
        self,
        compiled_workflow: CompiledWorkflow,
        context: RuntimeContext,
        archive_on_completion: bool = True,
        checkpoint_on_completion: bool = False,
    ) -> WorkflowExecutionResult:
        self._validate_context_workflow_match(
            compiled_workflow=compiled_workflow,
            context=context,
        )

        compiled_workflow.execution_plan.validate()

        started_at = datetime.now(
            UTC,
        )

        self.runtime_engine.register_many(
            compiled_workflow.runtime_nodes,
            clear_existing=True,
        )

        await self._emit(
            RuntimeEvent(
                event_type=RuntimeEventType.WORKFLOW_STARTED,
                execution_id=context.execution_id,
                workflow_id=context.workflow_id,
                runtime_id=context.runtime_id,
                payload={
                    "workflow_name": compiled_workflow.workflow_name,
                    "node_count": compiled_workflow.execution_plan.total_nodes(),
                    "wave_count": compiled_workflow.execution_plan.total_waves(),
                },
            )
        )

        try:
            final_context = await self.runtime_engine.execute(
                context=context,
                execution_plan=compiled_workflow.execution_plan,
            )

            completed_at = datetime.now(
                UTC,
            )

            success = not bool(
                final_context.errors,
            )

            if archive_on_completion:
                await self._archive_context_safe(
                    context=final_context,
                )

            if checkpoint_on_completion:
                await self._save_checkpoint_safe(
                    context=final_context,
                    checkpoint_name=(
                        f"{compiled_workflow.workflow_name}_"
                        f"{final_context.execution_id}_completed"
                    ),
                    compiled_workflow=compiled_workflow,
                )

            await self._emit(
                RuntimeEvent(
                    event_type=(
                        RuntimeEventType.WORKFLOW_COMPLETED
                        if success
                        else RuntimeEventType.WORKFLOW_FAILED
                    ),
                    execution_id=final_context.execution_id,
                    workflow_id=final_context.workflow_id,
                    runtime_id=final_context.runtime_id,
                    payload={
                        "workflow_name": compiled_workflow.workflow_name,
                        "success": success,
                        "error_count": len(final_context.errors),
                    },
                )
            )

            return WorkflowExecutionResult(
                success=success,
                workflow_name=compiled_workflow.workflow_name,
                execution_id=final_context.execution_id,
                runtime_id=final_context.runtime_id,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=(completed_at - started_at).total_seconds(),
                final_context=final_context,
                error_message=(None if success else "Workflow completed with errors."),
                metadata=self._build_result_metadata(
                    compiled_workflow=compiled_workflow,
                    context=final_context,
                ),
            )

        except Exception as exc:
            completed_at = datetime.now(
                UTC,
            )

            failed_context = self._append_context_error(
                context=context,
                error={
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                    "started_at": started_at.isoformat(),
                    "completed_at": completed_at.isoformat(),
                    "timestamp": completed_at.isoformat(),
                },
            )

            if archive_on_completion:
                await self._archive_context_safe(
                    context=failed_context,
                )

            if checkpoint_on_completion:
                await self._save_checkpoint_safe(
                    context=failed_context,
                    checkpoint_name=(
                        f"{compiled_workflow.workflow_name}_"
                        f"{failed_context.execution_id}_failed"
                    ),
                    compiled_workflow=compiled_workflow,
                )

            await self._emit(
                RuntimeEvent(
                    event_type=RuntimeEventType.WORKFLOW_FAILED,
                    execution_id=failed_context.execution_id,
                    workflow_id=failed_context.workflow_id,
                    runtime_id=failed_context.runtime_id,
                    payload={
                        "workflow_name": compiled_workflow.workflow_name,
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    },
                )
            )

            return WorkflowExecutionResult(
                success=False,
                workflow_name=compiled_workflow.workflow_name,
                execution_id=failed_context.execution_id,
                runtime_id=failed_context.runtime_id,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=(completed_at - started_at).total_seconds(),
                final_context=failed_context,
                error_message=str(exc),
                metadata={
                    **self._build_result_metadata(
                        compiled_workflow=compiled_workflow,
                        context=failed_context,
                    ),
                    "error_type": type(exc).__name__,
                },
            )

    # ========================================================
    # VALIDATION
    # ========================================================

    def _validate_context_workflow_match(
        self,
        compiled_workflow: CompiledWorkflow,
        context: RuntimeContext,
    ) -> None:
        if context.workflow_id != compiled_workflow.workflow_name:
            raise ValueError(
                "RuntimeContext workflow_id does not match "
                "CompiledWorkflow workflow_name. "
                f"context.workflow_id={context.workflow_id}, "
                f"compiled_workflow.workflow_name="
                f"{compiled_workflow.workflow_name}"
            )

    # ========================================================
    # INTERNAL HELPERS
    # ========================================================

    async def _emit(
        self,
        event: RuntimeEvent,
    ) -> None:
        if self.event_bus is None:
            return

        await self.event_bus.emit(
            event,
        )

    async def _archive_context_safe(
        self,
        context: RuntimeContext,
    ) -> None:
        try:
            await self.state_manager.archive_completed_run(
                context,
            )
        except Exception:
            logger.exception(
                "Completed workflow run archival failed.",
                extra={
                    "workflow_id": context.workflow_id,
                    "execution_id": context.execution_id,
                    "runtime_id": context.runtime_id,
                },
            )
            return

    async def _save_checkpoint_safe(
        self,
        context: RuntimeContext,
        checkpoint_name: str,
        compiled_workflow: CompiledWorkflow,
    ) -> None:
        if self.checkpoint_manager is None:
            return

        try:
            completed_nodes = self._completed_nodes(
                context,
            )

            failed_nodes = self._failed_nodes(
                context,
            )

            skipped_nodes = self._skipped_nodes(
                context,
            )

            wave_index = self._latest_completed_wave_index(
                compiled_workflow=compiled_workflow,
                context=context,
            )

            await self.checkpoint_manager.save_checkpoint(
                context=context,
                checkpoint_name=checkpoint_name,
                wave_index=wave_index,
                completed_nodes=tuple(completed_nodes),
                failed_nodes=tuple(failed_nodes),
                skipped_nodes=tuple(skipped_nodes),
                metadata={
                    "workflow_name": compiled_workflow.workflow_name,
                    "node_count": compiled_workflow.execution_plan.total_nodes(),
                    "wave_count": compiled_workflow.execution_plan.total_waves(),
                    "context_version": context.context_version,
                    "checkpoint_reason": "workflow_completion",
                },
            )
        except Exception:
            return

    def _append_context_error(
        self,
        context: RuntimeContext,
        error: dict[str, Any],
    ) -> RuntimeContext:
        return context.add_error(
            error,
        )

    def _build_result_metadata(
        self,
        compiled_workflow: CompiledWorkflow,
        context: RuntimeContext,
    ) -> dict[str, Any]:
        return {
            "mode": context.mode,
            "context_version": context.context_version,
            "node_count": compiled_workflow.execution_plan.total_nodes(),
            "wave_count": compiled_workflow.execution_plan.total_waves(),
            "checkpoint_wave_index": self._latest_completed_wave_index(
                compiled_workflow=compiled_workflow,
                context=context,
            ),
            "completed_nodes": self._completed_nodes(
                context,
            ),
            "failed_nodes": self._failed_nodes(
                context,
            ),
            "skipped_nodes": self._skipped_nodes(
                context,
            ),
        }

    # ========================================================
    # EXECUTION POSITION HELPERS
    # ========================================================

    def _completed_nodes(
        self,
        context: RuntimeContext,
    ) -> list[str]:
        return sorted(
            node_name
            for node_name, output in context.node_outputs.items()
            if (
                isinstance(output, dict)
                and output.get("success") is True
                and output.get("skipped") is not True
            )
        )

    def _failed_nodes(
        self,
        context: RuntimeContext,
    ) -> list[str]:
        return sorted(
            node_name
            for node_name, output in context.node_outputs.items()
            if (
                isinstance(output, dict)
                and output.get("success") is False
                and output.get("skipped") is not True
            )
        )

    def _skipped_nodes(
        self,
        context: RuntimeContext,
    ) -> list[str]:
        return sorted(
            node_name
            for node_name, output in context.node_outputs.items()
            if (isinstance(output, dict) and output.get("skipped") is True)
        )

    def _latest_completed_wave_index(
        self,
        compiled_workflow: CompiledWorkflow,
        context: RuntimeContext,
    ) -> int:
        latest_wave_index = 0

        completed_or_terminal_nodes = set(
            self._completed_nodes(context)
            + self._failed_nodes(context)
            + self._skipped_nodes(context)
        )

        for wave in compiled_workflow.execution_plan.waves:
            if all(
                node_name in completed_or_terminal_nodes for node_name in wave.nodes
            ):
                latest_wave_index = wave.index

        return latest_wave_index
