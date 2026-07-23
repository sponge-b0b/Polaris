from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.workflow.models.workflow_node_definition import (
    WorkflowNodeDefinition,
)


class WorkflowGraphDefinition(ABC):
    """
    Canonical declarative workflow graph definition.

    PURPOSE
    ============================================================
    Defines workflow topology only.

    RESPONSIBILITIES
    ============================================================
    - expose workflow identity
    - expose workflow description
    - declaratively define WorkflowNodeDefinition objects

    DOES NOT
    ============================================================
    - compile workflows
    - instantiate RuntimeNodes
    - build execution waves
    - manage RuntimeContext
    - execute workflows
    - access DI container

    Compilation is owned by:
        core.workflow.compiler.workflow_compiler.WorkflowCompiler
    """

    # ========================================================
    # WORKFLOW INFO
    # ========================================================

    @property
    @abstractmethod
    def workflow_name(
        self,
    ) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def workflow_description(
        self,
    ) -> str:
        raise NotImplementedError

    # ========================================================
    # GRAPH DEFINITION
    # ========================================================

    @abstractmethod
    def build_graph(
        self,
    ) -> list[WorkflowNodeDefinition]:
        """
        Declaratively define workflow DAG nodes.
        """
        raise NotImplementedError

    # ========================================================
    # VALIDATION
    # ========================================================

    def validate(
        self,
    ) -> None:
        """
        Validate workflow definition-level integrity.

        Full dependency/DAG validation is performed by WorkflowCompiler.
        """

        if not self.workflow_name.strip():
            raise ValueError("Workflow name cannot be empty.")

        node_definitions = self.build_graph()

        if not node_definitions:
            raise ValueError(f"Workflow '{self.workflow_name}' has no nodes.")

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

    # ========================================================
    # SERIALIZATION
    # ========================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "workflow_name": self.workflow_name,
            "workflow_description": self.workflow_description,
            "nodes": [node.to_dict() for node in self.build_graph()],
        }
