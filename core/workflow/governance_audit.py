from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from core.runtime.governance import GovernanceEvaluationResult
from core.runtime.policies import PolicyEvaluationResult

WORKFLOW_AUTOMATED_DECISION_AUDIT_CONTEXT_KEY = "automated_decision_audit_context"


class WorkflowAutomatedDecisionAuditService(Protocol):
    """Facade-facing seam for authoritative automated decision audit writes."""

    async def record_policy_evaluation(
        self,
        *,
        context: Any,
        evaluation: PolicyEvaluationResult,
    ) -> Sequence[Any]: ...

    async def record_governance_evaluation(
        self,
        *,
        context: Any,
        evaluation: GovernanceEvaluationResult,
    ) -> Sequence[Any]: ...


def audit_context_from_workflow_context(
    context: Mapping[str, Any] | None,
) -> Any | None:
    """Extract the application-owned audit context from workflow evaluation context."""

    if context is None:
        return None
    return context.get(WORKFLOW_AUTOMATED_DECISION_AUDIT_CONTEXT_KEY)
