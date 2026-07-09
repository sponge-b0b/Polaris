from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ExecutionPlanNode:
    """
    Fully compiled runtime-ready node descriptor.

    This is not a RuntimeNode.
    This is immutable execution metadata produced by WorkflowCompiler.
    """

    name: str

    node_type: str

    dependencies: tuple[str, ...] = ()

    enabled: bool = True

    max_retries: int = 2

    timeout_seconds: float | None = None

    parallel_safe: bool = True

    metadata: Mapping[str, Any] = field(
        default_factory=dict,
    )

    def validate(
        self,
    ) -> None:
        if not self.name.strip():
            raise ValueError("ExecutionPlanNode name cannot be empty.")

        if not self.node_type.strip():
            raise ValueError(
                f"ExecutionPlanNode '{self.name}' node_type cannot be empty."
            )

        if self.name in self.dependencies:
            raise ValueError(
                f"ExecutionPlanNode '{self.name}' cannot depend on itself."
            )

        if self.max_retries < 0:
            raise ValueError(
                f"ExecutionPlanNode '{self.name}' max_retries cannot be negative."
            )

        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError(
                f"ExecutionPlanNode '{self.name}' timeout_seconds "
                "must be greater than 0 when provided."
            )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "name": self.name,
            "node_type": self.node_type,
            "dependencies": list(self.dependencies),
            "enabled": self.enabled,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "parallel_safe": self.parallel_safe,
            "metadata": deepcopy(dict(self.metadata)),
        }


@dataclass(frozen=True, slots=True)
class ExecutionWave:
    """
    Deterministic parallel execution group.
    """

    index: int

    nodes: tuple[str, ...]

    def validate(
        self,
    ) -> None:
        if self.index < 0:
            raise ValueError("ExecutionWave index cannot be negative.")

        if len(set(self.nodes)) != len(self.nodes):
            raise ValueError(f"ExecutionWave {self.index} contains duplicate nodes.")

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "index": self.index,
            "nodes": list(self.nodes),
        }


@dataclass(frozen=True, slots=True)
class WorkflowExecutionPlan:
    """
    Fully compiled immutable workflow execution blueprint.

    Produced by WorkflowCompiler.
    Consumed by RuntimeEngine.
    """

    workflow_name: str

    execution_id: str

    nodes: Mapping[str, ExecutionPlanNode]

    waves: tuple[ExecutionWave, ...]

    metadata: Mapping[str, Any] = field(
        default_factory=dict,
    )

    def validate(
        self,
    ) -> None:
        if not self.workflow_name.strip():
            raise ValueError("WorkflowExecutionPlan workflow_name cannot be empty.")

        if not self.execution_id.strip():
            raise ValueError("WorkflowExecutionPlan execution_id cannot be empty.")

        if not self.nodes:
            raise ValueError(
                f"WorkflowExecutionPlan '{self.workflow_name}' has no nodes."
            )

        if not self.waves:
            raise ValueError(
                f"WorkflowExecutionPlan '{self.workflow_name}' has no waves."
            )

        known_nodes = set(self.nodes.keys())

        for node_name, node in self.nodes.items():
            if node_name != node.name:
                raise ValueError(
                    f"Node key '{node_name}' does not match node name '{node.name}'."
                )

            node.validate()

            for dependency in node.dependencies:
                if dependency not in known_nodes:
                    raise ValueError(
                        f"Node '{node.name}' depends on unknown node '{dependency}'."
                    )

        wave_nodes: set[str] = set()

        expected_wave_index = 0

        node_to_wave: dict[str, int] = {}

        for wave in self.waves:
            wave.validate()

            if wave.index != expected_wave_index:
                raise ValueError(
                    f"Expected wave index {expected_wave_index}, got {wave.index}."
                )

            expected_wave_index += 1

            for node_name in wave.nodes:
                if node_name not in known_nodes:
                    raise ValueError(
                        f"Wave {wave.index} references unknown node '{node_name}'."
                    )

                if node_name in wave_nodes:
                    raise ValueError(f"Node '{node_name}' appears in multiple waves.")

                wave_nodes.add(node_name)
                node_to_wave[node_name] = wave.index

        missing = known_nodes - wave_nodes

        if missing:
            raise ValueError(f"Nodes missing from execution waves: {sorted(missing)}")

        for node in self.nodes.values():
            node_wave = node_to_wave[node.name]

            for dependency in node.dependencies:
                dependency_wave = node_to_wave[dependency]

                if dependency_wave >= node_wave:
                    raise ValueError(
                        f"Node '{node.name}' depends on '{dependency}', "
                        "but dependency is not in an earlier wave."
                    )

    def get_node(
        self,
        name: str,
    ) -> ExecutionPlanNode:
        return self.nodes[name]

    def get_wave(
        self,
        index: int,
    ) -> ExecutionWave:
        return self.waves[index]

    def total_nodes(
        self,
    ) -> int:
        return len(self.nodes)

    def total_waves(
        self,
    ) -> int:
        return len(self.waves)

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "workflow_name": self.workflow_name,
            "execution_id": self.execution_id,
            "nodes": {name: node.to_dict() for name, node in self.nodes.items()},
            "waves": [wave.to_dict() for wave in self.waves],
            "metadata": deepcopy(dict(self.metadata)),
        }
