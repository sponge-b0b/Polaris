from __future__ import annotations

from dataclasses import dataclass

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.workflow.models.workflow_execution_plan import (
    ExecutionPlanNode,
    WorkflowExecutionPlan,
)


@dataclass(frozen=True, slots=True)
class RuntimeExecutionLocation:
    """Typed location for one workflow, wave, or node execution boundary."""

    context: RuntimeContext
    execution_plan: WorkflowExecutionPlan
    wave_index: int | None = None
    plan_node: ExecutionPlanNode | None = None

    @property
    def node_name(self) -> str | None:
        if self.plan_node is None:
            return None
        return self.plan_node.name

    def with_context(
        self,
        context: RuntimeContext,
    ) -> RuntimeExecutionLocation:
        return RuntimeExecutionLocation(
            context=context,
            execution_plan=self.execution_plan,
            wave_index=self.wave_index,
            plan_node=self.plan_node,
        )

    def for_wave(
        self,
        wave_index: int,
    ) -> RuntimeExecutionLocation:
        return RuntimeExecutionLocation(
            context=self.context,
            execution_plan=self.execution_plan,
            wave_index=wave_index,
        )

    def for_node(
        self,
        plan_node: ExecutionPlanNode,
        *,
        context: RuntimeContext | None = None,
    ) -> RuntimeExecutionLocation:
        return RuntimeExecutionLocation(
            context=context or self.context,
            execution_plan=self.execution_plan,
            wave_index=self.wave_index,
            plan_node=plan_node,
        )


@dataclass(frozen=True, slots=True)
class RuntimeNodeInvocation:
    """Complete typed input required to invoke one registered runtime node."""

    node: RuntimeNode
    location: RuntimeExecutionLocation


@dataclass(frozen=True, slots=True)
class RuntimeNodeExecutionResult:
    """Final output and operation location for one runtime node attempt."""

    output: RuntimeNodeOutput
    location: RuntimeExecutionLocation
