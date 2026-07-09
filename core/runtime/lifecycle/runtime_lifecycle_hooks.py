from __future__ import annotations

from typing import Protocol

from core.runtime.artifacts.artifact_ref import ArtifactRef
from core.runtime.events.runtime_events import RuntimeEvent
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.workflow.models.workflow_execution_plan import (
    ExecutionPlanNode,
    ExecutionWave,
    WorkflowExecutionPlan,
)


class RuntimeLifecycleHook(Protocol):
    """
    Runtime lifecycle hook contract.

    Hooks are optional infrastructure extensions for:
    - telemetry
    - tracing
    - metrics
    - audit logging
    - plugin observers
    - artifact lifecycle monitoring
    """

    # ========================================================
    # WORKFLOW LIFECYCLE
    # ========================================================

    async def before_workflow_execute(
        self,
        context: RuntimeContext,
        execution_plan: WorkflowExecutionPlan,
    ) -> None: ...

    async def after_workflow_execute(
        self,
        context: RuntimeContext,
        execution_plan: WorkflowExecutionPlan,
    ) -> None: ...

    # ========================================================
    # WAVE LIFECYCLE
    # ========================================================

    async def before_wave_execute(
        self,
        context: RuntimeContext,
        execution_plan: WorkflowExecutionPlan,
        wave: ExecutionWave,
    ) -> None: ...

    async def after_wave_execute(
        self,
        context: RuntimeContext,
        execution_plan: WorkflowExecutionPlan,
        wave: ExecutionWave,
    ) -> None: ...

    # ========================================================
    # NODE LIFECYCLE
    # ========================================================

    async def before_node_execute(
        self,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
    ) -> None: ...

    async def after_node_execute(
        self,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
        output: RuntimeNodeOutput,
    ) -> None: ...

    # ========================================================
    # ARTIFACT LIFECYCLE
    # ========================================================

    async def on_artifact_persisted(
        self,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
        artifact_name: str,
        artifact_ref: ArtifactRef,
    ) -> None: ...

    async def on_artifact_failed(
        self,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
        artifact_name: str,
        error: Exception,
    ) -> None: ...

    # ========================================================
    # EVENT LIFECYCLE
    # ========================================================

    async def on_runtime_event(
        self,
        event: RuntimeEvent,
    ) -> None: ...


class NoOpRuntimeLifecycleHook:
    """
    No-op lifecycle hook implementation.

    Useful as:
    - default hook
    - test fixture
    - base class for partial hook implementations
    """

    async def before_workflow_execute(
        self,
        context: RuntimeContext,
        execution_plan: WorkflowExecutionPlan,
    ) -> None:
        return None

    async def after_workflow_execute(
        self,
        context: RuntimeContext,
        execution_plan: WorkflowExecutionPlan,
    ) -> None:
        return None

    async def before_wave_execute(
        self,
        context: RuntimeContext,
        execution_plan: WorkflowExecutionPlan,
        wave: ExecutionWave,
    ) -> None:
        return None

    async def after_wave_execute(
        self,
        context: RuntimeContext,
        execution_plan: WorkflowExecutionPlan,
        wave: ExecutionWave,
    ) -> None:
        return None

    async def before_node_execute(
        self,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
    ) -> None:
        return None

    async def after_node_execute(
        self,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
        output: RuntimeNodeOutput,
    ) -> None:
        return None

    async def on_artifact_persisted(
        self,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
        artifact_name: str,
        artifact_ref: ArtifactRef,
    ) -> None:
        return None

    async def on_artifact_failed(
        self,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
        artifact_name: str,
        error: Exception,
    ) -> None:
        return None

    async def on_runtime_event(
        self,
        event: RuntimeEvent,
    ) -> None:
        return None
