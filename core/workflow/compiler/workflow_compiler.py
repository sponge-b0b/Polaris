from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.execution.execution_graph import (
    ExecutionGraph,
    NodeDescriptor,
)
from core.runtime.factory.runtime_node_factory import RuntimeNodeFactory
from core.workflow.models.workflow_execution_plan import (
    ExecutionPlanNode,
    ExecutionWave,
    WorkflowExecutionPlan,
)
from core.workflow.models.workflow_graph_definition import (
    WorkflowGraphDefinition,
)
from core.workflow.models.workflow_node_definition import (
    WorkflowNodeDefinition,
)


@dataclass(frozen=True, slots=True)
class CompiledWorkflow:
    """
    Fully compiled workflow artifact.

    Contains:
    - runtime node instances
    - execution graph topology
    - immutable execution plan
    """

    workflow_name: str
    execution_graph: ExecutionGraph
    execution_plan: WorkflowExecutionPlan
    runtime_nodes: dict[str, RuntimeNode]
    metadata: dict[str, Any]

    def get_node(
        self,
        node_name: str,
    ) -> RuntimeNode:
        return self.runtime_nodes[node_name]

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "workflow_name": self.workflow_name,
            "execution_graph": self.execution_graph.to_dict(),
            "execution_plan": self.execution_plan.to_dict(),
            "runtime_nodes": {
                node_name: node.to_dict()
                for node_name, node in sorted(
                    self.runtime_nodes.items(),
                    key=lambda item: item[0],
                )
            },
            "metadata": deepcopy(self.metadata),
        }


class WorkflowCompiler:
    """
    Canonical workflow compiler.

    Converts declarative workflow definitions into runtime-ready
    execution artifacts.

    Supports DI-backed RuntimeNode construction through
    RuntimeNodeFactory. This keeps the compiler Dishka-compatible
    without depending directly on Dishka APIs.
    """

    def __init__(
        self,
        runtime_node_factory: RuntimeNodeFactory | None = None,
    ) -> None:
        self.runtime_node_factory = runtime_node_factory

    def compile(
        self,
        workflow_definition: WorkflowGraphDefinition,
        execution_id: str,
    ) -> CompiledWorkflow:
        if not execution_id.strip():
            raise ValueError("execution_id cannot be empty.")

        workflow_definition.validate()

        node_definitions = workflow_definition.build_graph()

        self._validate_node_definitions(
            node_definitions=node_definitions,
        )

        enabled_nodes = {node.name: node for node in node_definitions if node.enabled}

        if not enabled_nodes:
            raise ValueError(
                f"Workflow '{workflow_definition.workflow_name}' has no enabled nodes."
            )

        self._validate_dependencies(
            nodes=enabled_nodes,
        )

        runtime_nodes = self._instantiate_runtime_nodes(
            nodes=enabled_nodes,
        )

        execution_graph = self._build_execution_graph(
            nodes=enabled_nodes,
            runtime_nodes=runtime_nodes,
        )

        execution_waves = execution_graph.build_execution_order()

        metadata = {
            "workflow_description": workflow_definition.workflow_description,
            "runtime_node_factory_enabled": self.runtime_node_factory is not None,
        }

        execution_plan = self._build_execution_plan(
            workflow_definition=workflow_definition,
            execution_id=execution_id,
            nodes=enabled_nodes,
            runtime_nodes=runtime_nodes,
            execution_waves=execution_waves,
            metadata=metadata,
        )

        execution_plan.validate()

        return CompiledWorkflow(
            workflow_name=workflow_definition.workflow_name,
            execution_graph=execution_graph,
            execution_plan=execution_plan,
            runtime_nodes=runtime_nodes,
            metadata=metadata,
        )

    def _validate_node_definitions(
        self,
        node_definitions: list[WorkflowNodeDefinition],
    ) -> None:
        seen: set[str] = set()

        for node_definition in node_definitions:
            node_definition.validate()

            if node_definition.name in seen:
                raise ValueError(
                    f"Duplicate workflow node definition: {node_definition.name}"
                )

            seen.add(
                node_definition.name,
            )

    def _validate_dependencies(
        self,
        nodes: dict[str, WorkflowNodeDefinition],
    ) -> None:
        for node_name, node_definition in nodes.items():
            for dependency in node_definition.dependencies:
                if dependency not in nodes:
                    raise ValueError(
                        f"Node '{node_name}' depends on missing "
                        f"or disabled node '{dependency}'."
                    )

    def _instantiate_runtime_nodes(
        self,
        nodes: dict[str, WorkflowNodeDefinition],
    ) -> dict[str, RuntimeNode]:
        runtime_nodes: dict[str, RuntimeNode] = {}

        for node_name, node_definition in sorted(
            nodes.items(),
            key=lambda item: item[0],
        ):
            runtime_node = self._create_runtime_node(
                node_definition=node_definition,
            )

            if not isinstance(runtime_node, RuntimeNode):
                raise TypeError(
                    f"Node '{node_name}' did not instantiate a RuntimeNode."
                )

            runtime_nodes[node_name] = runtime_node

        return runtime_nodes

    def _create_runtime_node(
        self,
        node_definition: WorkflowNodeDefinition,
    ) -> RuntimeNode:
        """
        Create RuntimeNode instance.

        If RuntimeNodeFactory is configured, node construction is delegated
        to the factory, which may resolve nodes through Dishka or another
        DI container.

        Otherwise, the RuntimeNode class is instantiated directly.
        """

        if self.runtime_node_factory is not None:
            return self.runtime_node_factory.create_from_type(
                node_definition.node_type,
            )

        return node_definition.node_type()

    def _build_execution_graph(
        self,
        nodes: dict[str, WorkflowNodeDefinition],
        runtime_nodes: dict[str, RuntimeNode],
    ) -> ExecutionGraph:
        execution_graph = ExecutionGraph()

        for node_name, node_definition in sorted(
            nodes.items(),
            key=lambda item: item[0],
        ):
            descriptor = NodeDescriptor(
                name=node_name,
                node=runtime_nodes[node_name],
                dependencies=tuple(node_definition.dependencies),
                enabled=node_definition.enabled,
            )

            execution_graph.add_node(
                descriptor,
            )

        execution_graph.validate()

        return execution_graph

    def _build_execution_plan(
        self,
        workflow_definition: WorkflowGraphDefinition,
        execution_id: str,
        nodes: dict[str, WorkflowNodeDefinition],
        runtime_nodes: dict[str, RuntimeNode],
        execution_waves: list[list[str]],
        metadata: dict[str, Any],
    ) -> WorkflowExecutionPlan:
        plan_nodes: dict[str, ExecutionPlanNode] = {}

        for node_name, node_definition in sorted(
            nodes.items(),
            key=lambda item: item[0],
        ):
            runtime_node = runtime_nodes[node_name]

            plan_nodes[node_name] = ExecutionPlanNode(
                name=node_name,
                node_type=runtime_node.node_type,
                dependencies=tuple(node_definition.dependencies),
                enabled=node_definition.enabled,
                max_retries=node_definition.max_retries,
                timeout_seconds=node_definition.timeout_seconds,
                parallel_safe=runtime_node.parallel_safe,
                metadata={
                    **dict(node_definition.metadata),
                    "node_type": node_definition.node_type.__name__,
                    "node_module": node_definition.node_type.__module__,
                    "node_version": runtime_node.node_version,
                    "tags": list(node_definition.tags),
                    "retry_backoff_seconds": node_definition.retry_backoff_seconds,
                    "fail_fast": node_definition.fail_fast,
                    "created_via_factory": self.runtime_node_factory is not None,
                },
            )

        waves = tuple(
            ExecutionWave(
                index=index,
                nodes=tuple(wave),
            )
            for index, wave in enumerate(
                execution_waves,
            )
        )

        return WorkflowExecutionPlan(
            workflow_name=workflow_definition.workflow_name,
            execution_id=execution_id,
            nodes=plan_nodes,
            waves=waves,
            metadata=metadata,
        )
