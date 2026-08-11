from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from core.workflow.models.workflow_graph_definition import (
    WorkflowGraphDefinition,
)
from domain.authority import RiskAuthorityContract


@dataclass(frozen=True, slots=True)
class WorkflowIdentity:
    """Immutable identity of one registered workflow definition."""

    workflow_name: str
    definition_fingerprint: str


@dataclass(frozen=True, slots=True)
class WorkflowAuthorityFacts:
    """Registry-owned authority binding used for governed execution."""

    identity: WorkflowIdentity
    authority: RiskAuthorityContract


@dataclass(frozen=True, slots=True)
class WorkflowRegistryEntry:
    """
    Immutable workflow registry entry.
    """

    workflow_name: str

    workflow_definition: WorkflowGraphDefinition

    description: str = ""

    tags: tuple[str, ...] = ()

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )
    authority_facts: WorkflowAuthorityFacts | None = None

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "workflow_name": self.workflow_name,
            "description": self.description,
            "tags": list(self.tags),
            "metadata": deepcopy(self.metadata),
        }


class WorkflowRegistry:
    """
    Canonical workflow definition registry.

    Provides deterministic lookup for workflow definitions.
    """

    def __init__(
        self,
    ) -> None:
        self._workflows: dict[str, WorkflowRegistryEntry] = {}

    # ========================================================
    # REGISTRATION
    # ========================================================

    def register(
        self,
        workflow_definition: WorkflowGraphDefinition,
        tags: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
        risk_authority_contract: RiskAuthorityContract | None = None,
        overwrite: bool = False,
    ) -> None:
        workflow_definition.validate()

        workflow_name = workflow_definition.workflow_name.strip()

        if not workflow_name:
            raise ValueError("Workflow name cannot be empty.")

        if workflow_name in self._workflows and not overwrite:
            raise ValueError(f"Workflow already registered: {workflow_name}")

        self._workflows[workflow_name] = WorkflowRegistryEntry(
            workflow_name=workflow_name,
            workflow_definition=workflow_definition,
            description=workflow_definition.workflow_description,
            tags=tuple(tags),
            metadata=deepcopy(metadata or {}),
            authority_facts=(
                WorkflowAuthorityFacts(
                    identity=WorkflowIdentity(
                        workflow_name=workflow_name,
                        definition_fingerprint=_definition_fingerprint(
                            workflow_definition
                        ),
                    ),
                    authority=risk_authority_contract,
                )
                if risk_authority_contract is not None
                else None
            ),
        )

    # ========================================================
    # LOOKUP
    # ========================================================

    def get(
        self,
        workflow_name: str,
    ) -> WorkflowGraphDefinition:
        return self.get_entry(
            workflow_name,
        ).workflow_definition

    def get_entry(
        self,
        workflow_name: str,
    ) -> WorkflowRegistryEntry:
        workflow_name = workflow_name.strip()

        entry = self._workflows.get(
            workflow_name,
        )

        if entry is None:
            raise KeyError(f"Workflow not registered: {workflow_name}")

        return entry

    def get_authority_facts(self, workflow_name: str) -> WorkflowAuthorityFacts:
        """Resolve the only authority facts accepted for a governed invocation."""

        facts = self.get_entry(workflow_name).authority_facts
        if facts is None:
            raise KeyError(
                f"Workflow has no registered governed authority facts: {workflow_name}"
            )
        return facts

    def exists(
        self,
        workflow_name: str,
    ) -> bool:
        return workflow_name.strip() in self._workflows

    # ========================================================
    # LISTING
    # ========================================================

    def list_workflows(
        self,
        tag: str | None = None,
    ) -> list[str]:
        if tag is None:
            return sorted(
                self._workflows.keys(),
            )

        return sorted(
            name for name, entry in self._workflows.items() if tag in entry.tags
        )

    def list_entries(
        self,
        tag: str | None = None,
    ) -> list[WorkflowRegistryEntry]:
        return [
            self._workflows[name]
            for name in self.list_workflows(
                tag=tag,
            )
        ]

    def count(
        self,
    ) -> int:
        return len(
            self._workflows,
        )

    # ========================================================
    # REMOVAL
    # ========================================================

    def unregister(
        self,
        workflow_name: str,
    ) -> None:
        workflow_name = workflow_name.strip()

        if workflow_name not in self._workflows:
            raise KeyError(f"Workflow not registered: {workflow_name}")

        del self._workflows[workflow_name]

    def clear(
        self,
    ) -> None:
        self._workflows.clear()

    # ========================================================
    # SERIALIZATION
    # ========================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "workflow_count": self.count(),
            "workflows": {
                name: entry.to_dict()
                for name, entry in sorted(
                    self._workflows.items(),
                    key=lambda item: item[0],
                )
            },
        }


def _definition_fingerprint(workflow_definition: WorkflowGraphDefinition) -> str:
    serialized = json.dumps(
        workflow_definition.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
