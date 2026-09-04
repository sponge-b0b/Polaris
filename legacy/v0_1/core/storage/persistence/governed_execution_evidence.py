"""Persistence contracts for canonical governed-execution evidence selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from core.workflow.registry.workflow_registry import WorkflowIdentity
from domain.authority import RiskTier


class GovernedExecutionEvidenceSelectionConflictError(ValueError):
    """Raised when an execution already has a durable evidence selection."""


@dataclass(frozen=True, slots=True)
class GovernedExecutionEvidenceSelection:
    """Durable execution-scoped binding of identity to one evidence record."""

    execution_id: str
    identity: WorkflowIdentity
    risk_tier: RiskTier
    evidence_id: str


class GovernedExecutionEvidenceSelectionRepository(Protocol):
    async def create(
        self,
        selection: GovernedExecutionEvidenceSelection,
        *,
        commit: bool = True,
    ) -> None: ...

    async def get(
        self, *, execution_id: str, identity: WorkflowIdentity
    ) -> tuple[GovernedExecutionEvidenceSelection, ...]: ...
