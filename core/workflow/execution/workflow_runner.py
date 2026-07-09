from __future__ import annotations

from collections.abc import Mapping

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from core.runtime.state.runtime_context import RuntimeContext
from core.workflow.compiler.workflow_compiler import CompiledWorkflow
from core.workflow.compiler.workflow_compiler import WorkflowCompiler
from core.workflow.execution.workflow_engine import WorkflowEngine
from core.workflow.execution.workflow_engine import WorkflowExecutionResult
from core.workflow.registry.workflow_registry import WorkflowRegistry


@dataclass(frozen=True, slots=True)
class WorkflowRunRequest:
    """
    Immutable workflow run request.
    """

    workflow_name: str

    execution_id: str | None = None

    mode: str = "live"

    workflow_inputs: Mapping[str, Any] | None = None

    simulation_time: datetime | None = None

    archive_on_completion: bool = True

    checkpoint_on_completion: bool = False

    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class WorkflowRunResult:
    """
    Immutable workflow runner result.
    """

    success: bool

    workflow_name: str

    execution_id: str

    compiled_workflow: CompiledWorkflow

    execution_result: WorkflowExecutionResult

    metadata: dict[str, Any] | None = None

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "success": self.success,
            "workflow_name": self.workflow_name,
            "execution_id": self.execution_id,
            "compiled_workflow": self.compiled_workflow.to_dict(),
            "execution_result": self.execution_result.to_dict(),
            "metadata": dict(self.metadata or {}),
        }


class WorkflowRunner:
    """
    High-level workflow execution façade.

    PURPOSE
    ============================================================
    Coordinates:
    - workflow lookup
    - workflow compilation
    - workflow execution

    USED BY
    ============================================================
    - CLI
    - API routes
    - schedulers
    - tests
    - future service layer

    DOES NOT
    ============================================================
    - execute RuntimeNodes directly
    - mutate RuntimeContext
    - manage RuntimeContext directly
    - know live/backtest implementation details
    """

    def __init__(
        self,
        registry: WorkflowRegistry,
        compiler: WorkflowCompiler,
        workflow_engine: WorkflowEngine,
    ) -> None:
        self.registry = registry
        self.compiler = compiler
        self.workflow_engine = workflow_engine

    # ========================================================
    # RUN BY NAME
    # ========================================================

    async def run(
        self,
        request: WorkflowRunRequest,
    ) -> WorkflowRunResult:
        """
        Lookup, compile, and execute a workflow by name.
        """

        if not request.workflow_name.strip():
            raise ValueError("workflow_name cannot be empty.")

        execution_id = request.execution_id or self._generate_execution_id()

        workflow_definition = self.registry.get(
            request.workflow_name,
        )

        compiled_workflow = self.compiler.compile(
            workflow_definition=workflow_definition,
            execution_id=execution_id,
        )

        execution_result = await self.workflow_engine.execute(
            compiled_workflow=compiled_workflow,
            workflow_inputs=request.workflow_inputs,
            mode=request.mode,
            simulation_time=request.simulation_time,
            archive_on_completion=request.archive_on_completion,
            checkpoint_on_completion=request.checkpoint_on_completion,
        )

        return WorkflowRunResult(
            success=execution_result.success,
            workflow_name=compiled_workflow.workflow_name,
            execution_id=execution_result.execution_id,
            compiled_workflow=compiled_workflow,
            execution_result=execution_result,
            metadata=dict(request.metadata or {}),
        )

    # ========================================================
    # RUN FROM EXISTING CONTEXT
    # ========================================================

    async def run_from_context(
        self,
        workflow_name: str,
        context: RuntimeContext,
        archive_on_completion: bool = True,
        checkpoint_on_completion: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowRunResult:
        """
        Compile workflow and execute from an existing RuntimeContext.

        Used for:
        - recovery
        - controlled re-entry
        - test harnesses
        """

        workflow_definition = self.registry.get(
            workflow_name,
        )

        compiled_workflow = self.compiler.compile(
            workflow_definition=workflow_definition,
            execution_id=context.execution_id,
        )

        execution_result = await self.workflow_engine.execute_from_context(
            compiled_workflow=compiled_workflow,
            context=context,
            archive_on_completion=archive_on_completion,
            checkpoint_on_completion=checkpoint_on_completion,
        )

        return WorkflowRunResult(
            success=execution_result.success,
            workflow_name=compiled_workflow.workflow_name,
            execution_id=execution_result.execution_id,
            compiled_workflow=compiled_workflow,
            execution_result=execution_result,
            metadata=dict(metadata or {}),
        )

    # ========================================================
    # COMPILE ONLY
    # ========================================================

    def compile_only(
        self,
        workflow_name: str,
        execution_id: str | None = None,
    ) -> CompiledWorkflow:
        """
        Compile workflow without executing it.
        """

        workflow_definition = self.registry.get(
            workflow_name,
        )

        return self.compiler.compile(
            workflow_definition=workflow_definition,
            execution_id=execution_id or self._generate_execution_id(),
        )

    # ========================================================
    # HELPERS
    # ========================================================

    def _generate_execution_id(
        self,
    ) -> str:
        return uuid4().hex
