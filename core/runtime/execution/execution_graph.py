from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.runtime.contracts.runtime_node import RuntimeNode


@dataclass(frozen=True, slots=True)
class NodeDescriptor:
    """
    Immutable runtime topology descriptor.

    Contains:
    - runtime node instance
    - dependency topology
    - enabled flag

    Does not contain:
    - retry policy
    - timeout policy
    - execution state
    - runtime context
    """

    name: str

    node: RuntimeNode

    dependencies: tuple[str, ...] = field(
        default_factory=tuple,
    )

    enabled: bool = True

    def validate(
        self,
    ) -> None:
        if not self.name.strip():
            raise ValueError("NodeDescriptor name cannot be empty.")

        if self.name in self.dependencies:
            raise ValueError(f"NodeDescriptor '{self.name}' cannot depend on itself.")

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "name": self.name,
            "dependencies": list(self.dependencies),
            "enabled": self.enabled,
            "node_type": self.node.node_type,
            "node_version": self.node.node_version,
        }


class ExecutionGraph:
    """
    Deterministic DAG topology graph.

    Responsibilities:
    - node registration
    - dependency validation
    - cycle detection
    - topological wave generation

    Non-responsibilities:
    - runtime execution
    - retry handling
    - timeout handling
    - context mutation
    """

    def __init__(self) -> None:
        self.nodes: dict[str, NodeDescriptor] = {}
        self.run_id: str = ""
        self.workflow_name: str = ""

    @property
    def edges(
        self,
    ) -> list[tuple[str, str]]:
        return [
            (
                dependency,
                descriptor.name,
            )
            for descriptor in self.nodes.values()
            for dependency in descriptor.dependencies
        ]

    # ========================================================
    # REGISTRATION
    # ========================================================

    def add_node(
        self,
        descriptor: NodeDescriptor,
    ) -> None:
        descriptor.validate()

        if descriptor.name in self.nodes:
            raise ValueError(f"Duplicate node registration: {descriptor.name}")

        self.nodes[descriptor.name] = descriptor

    # ========================================================
    # LOOKUP
    # ========================================================

    def get_node(
        self,
        node_name: str,
    ) -> NodeDescriptor:
        descriptor = self.nodes.get(
            node_name,
        )

        if descriptor is None:
            raise ValueError(f"Unknown node: {node_name}")

        return descriptor

    def node_count(
        self,
    ) -> int:
        return len(self.nodes)

    # ========================================================
    # VALIDATION
    # ========================================================

    def validate(
        self,
    ) -> None:
        visited: set[str] = set()
        active_stack: set[str] = set()

        def dfs(
            node_name: str,
        ) -> None:
            if node_name in active_stack:
                raise ValueError(f"Circular dependency detected: {node_name}")

            if node_name in visited:
                return

            descriptor = self.nodes.get(
                node_name,
            )

            if descriptor is None:
                raise ValueError(f"Missing node dependency: {node_name}")

            descriptor.validate()

            active_stack.add(
                node_name,
            )

            for dependency in descriptor.dependencies:
                if dependency not in self.nodes:
                    raise ValueError(
                        f"Node '{node_name}' depends on missing node '{dependency}'"
                    )

                dfs(
                    dependency,
                )

            active_stack.remove(
                node_name,
            )

            visited.add(
                node_name,
            )

        for node_name in sorted(self.nodes):
            dfs(
                node_name,
            )

    # ========================================================
    # EXECUTION WAVES
    # ========================================================

    def build_execution_order(
        self,
    ) -> list[list[str]]:
        self.validate()

        in_degree: dict[str, int] = {name: 0 for name in self.nodes}

        for descriptor in self.nodes.values():
            in_degree[descriptor.name] = len(
                descriptor.dependencies,
            )

        execution_waves: list[list[str]] = []

        current_wave = sorted(
            node_name for node_name, degree in in_degree.items() if degree == 0
        )

        processed_nodes = 0

        while current_wave:
            execution_waves.append(
                list(current_wave),
            )

            processed_nodes += len(
                current_wave,
            )

            next_wave: set[str] = set()

            for completed_node in current_wave:
                for descriptor in self.nodes.values():
                    if completed_node in descriptor.dependencies:
                        in_degree[descriptor.name] -= 1

                        if in_degree[descriptor.name] == 0:
                            next_wave.add(
                                descriptor.name,
                            )

            current_wave = sorted(
                next_wave,
            )

        if processed_nodes != len(self.nodes):
            processed = {node for wave in execution_waves for node in wave}

            unresolved = sorted(
                set(self.nodes) - processed,
            )

            raise ValueError(
                "Failed to build complete execution order. "
                f"Unresolved nodes: {unresolved}"
            )

        return execution_waves

    # ========================================================
    # SERIALIZATION
    # ========================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "node_count": self.node_count(),
            "nodes": {name: self.nodes[name].to_dict() for name in sorted(self.nodes)},
        }
