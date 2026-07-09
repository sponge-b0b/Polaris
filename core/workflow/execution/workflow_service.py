from __future__ import annotations

from collections.abc import Mapping

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from core.runtime.checkpoints.checkpoint_manager import CheckpointManager
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.state_manager import StateManager
from core.workflow.compiler.workflow_compiler import CompiledWorkflow
from core.workflow.execution.workflow_runner import (
    WorkflowRunRequest,
    WorkflowRunResult,
    WorkflowRunner,
)
from core.workflow.models.workflow_graph_definition import WorkflowGraphDefinition
from core.workflow.registry.workflow_registry import WorkflowRegistry


@dataclass(frozen=True, slots=True)
class WorkflowSummary:
    """
    Serializable workflow summary for API / CLI / UI consumers.
    """

    workflow_name: str

    description: str = ""

    tags: tuple[str, ...] = ()

    metadata: dict[str, Any] | None = None

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "workflow_name": self.workflow_name,
            "description": self.description,
            "tags": list(self.tags),
            "metadata": dict(self.metadata or {}),
        }


class WorkflowService:
    """
    Application-facing workflow service.

    PURPOSE
    ============================================================
    Provides a stable façade for external callers:
    - API routes
    - CLI commands
    - schedulers
    - UI controllers
    - tests

    RESPONSIBILITIES
    ============================================================
    - list workflows
    - describe workflows
    - compile workflows
    - run workflows
    - run workflows from existing RuntimeContext
    - restore RuntimeContext from checkpoints
    - access completed run archive (audit/history/RAG)

    DOES NOT
    ============================================================
    - execute RuntimeNodes directly
    - compile node internals manually
    - mutate RuntimeContext
    - know live/backtest/simulation infrastructure
    """

    def __init__(
        self,
        registry: WorkflowRegistry,
        runner: WorkflowRunner,
        checkpoint_manager: CheckpointManager | None = None,
        state_manager: StateManager | None = None,
    ) -> None:
        self.registry = registry
        self.runner = runner
        self.checkpoint_manager = checkpoint_manager
        self.state_manager = state_manager

    # ========================================================
    # REGISTRATION
    # ========================================================

    def register_workflow(
        self,
        workflow_definition: WorkflowGraphDefinition,
        tags: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
        overwrite: bool = False,
    ) -> None:
        self.registry.register(
            workflow_definition=workflow_definition,
            tags=tags,
            metadata=metadata,
            overwrite=overwrite,
        )

    # ========================================================
    # DISCOVERY
    # ========================================================

    def list_workflows(
        self,
        tag: str | None = None,
    ) -> list[str]:
        return self.registry.list_workflows(
            tag=tag,
        )

    def list_workflow_summaries(
        self,
        tag: str | None = None,
    ) -> list[WorkflowSummary]:
        return [
            WorkflowSummary(
                workflow_name=entry.workflow_name,
                description=entry.description,
                tags=entry.tags,
                metadata=entry.metadata,
            )
            for entry in self.registry.list_entries(
                tag=tag,
            )
        ]

    def describe_workflow(
        self,
        workflow_name: str,
    ) -> dict[str, Any]:
        entry = self.registry.get_entry(
            workflow_name,
        )

        workflow_definition = entry.workflow_definition

        return {
            **entry.to_dict(),
            "definition": workflow_definition.to_dict(),
        }

    def workflow_exists(
        self,
        workflow_name: str,
    ) -> bool:
        return self.registry.exists(
            workflow_name,
        )

    # ========================================================
    # COMPILE
    # ========================================================

    def compile_workflow(
        self,
        workflow_name: str,
        execution_id: str | None = None,
    ) -> CompiledWorkflow:
        return self.runner.compile_only(
            workflow_name=workflow_name,
            execution_id=execution_id,
        )

    # ========================================================
    # EXECUTION
    # ========================================================

    async def run_workflow(
        self,
        workflow_name: str,
        execution_id: str | None = None,
        mode: str = "live",
        workflow_inputs: Mapping[str, Any] | None = None,
        simulation_time: datetime | None = None,
        archive_on_completion: bool = True,
        checkpoint_on_completion: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowRunResult:
        request = WorkflowRunRequest(
            workflow_name=workflow_name,
            execution_id=execution_id,
            mode=mode,
            workflow_inputs=workflow_inputs,
            simulation_time=simulation_time,
            archive_on_completion=archive_on_completion,
            checkpoint_on_completion=checkpoint_on_completion,
            metadata=metadata,
        )

        return await self.runner.run(
            request,
        )

    async def run_from_context(
        self,
        workflow_name: str,
        context: RuntimeContext,
        archive_on_completion: bool = True,
        checkpoint_on_completion: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowRunResult:
        return await self.runner.run_from_context(
            workflow_name=workflow_name,
            context=context,
            archive_on_completion=archive_on_completion,
            checkpoint_on_completion=checkpoint_on_completion,
            metadata=metadata,
        )

    # ========================================================
    # CHECKPOINT RESTORE
    # ========================================================

    async def restore_context_from_checkpoint(
        self,
        checkpoint_file: str,
    ) -> RuntimeContext:
        if self.checkpoint_manager is None:
            raise RuntimeError("CheckpointManager is not configured.")

        return await self.checkpoint_manager.restore_context(
            checkpoint_file,
        )

    # ========================================================
    # COMPLETED RUN ARCHIVE
    # ========================================================

    async def list_completed_runs(
        self,
        workflow_name: str,
    ) -> list[str]:
        """
        Lists all archived run execution IDs for a workflow.
        """
        if self.state_manager is None:
            return []
        return await self.state_manager.list_completed_runs(
            workflow_name,
        )

    async def load_completed_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> RuntimeContext | None:
        """
        Loads a completed run from archive for historical analysis.

        Returns RuntimeContext for analysis, NOT for execution recovery.
        Use restore_context_from_checkpoint() for recovery.
        """
        if self.state_manager is None:
            return None
        return await self.state_manager.load_completed_run(
            workflow_name,
            execution_id,
        )

    async def delete_completed_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> None:
        """
        Deletes a completed run from the archive.
        """

        if self.state_manager is None:
            return
        await self.state_manager.delete_completed_run(
            workflow_name,
            execution_id,
        )

    async def cleanup_completed_runs(
        self,
        max_age_days: int | None = None,
        max_count: int | None = None,
    ) -> int:
        """
        Cleans up archived runs based on retention policy.

        Returns number of runs deleted.
        """
        if self.state_manager is None:
            return 0
        return await self.state_manager.cleanup_completed_runs(
            max_age_days=max_age_days,
            max_count=max_count,
        )
