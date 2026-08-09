from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from core.runtime.governance import GovernanceEvaluationResult
from core.runtime.policies import PolicyEvaluationResult
from core.storage.persistence.governance_audit import (
    AutomatedDecisionAuditPersistenceResult,
    AutomatedDecisionEvidenceReference,
    AutomatedDecisionSubject,
)
from core.telemetry.tracing import TraceContext
from domain.authority import RiskAuthorityContract
from domain.decision_evidence import DecisionEvidencePacket

WORKFLOW_AUTOMATED_DECISION_AUDIT_CONTEXT_KEY = "automated_decision_audit_context"


@dataclass(frozen=True, slots=True)
class AutomatedDecisionAuditContext:
    """Canonical context required to audit one automated decision."""

    subject: AutomatedDecisionSubject
    authority: RiskAuthorityContract
    evidence: AutomatedDecisionEvidenceReference | None = None
    timestamp: datetime | None = None
    trace_context: TraceContext | None = None

    @classmethod
    def from_packet(
        cls,
        *,
        subject: AutomatedDecisionSubject,
        packet: DecisionEvidencePacket,
        timestamp: datetime | None = None,
    ) -> AutomatedDecisionAuditContext:
        return cls(
            subject=subject,
            authority=packet.authority,
            evidence=AutomatedDecisionEvidenceReference(
                packet_id=packet.packet_id,
                packet_version=packet.schema_version,
            ),
            timestamp=timestamp,
        )

    @property
    def effective_timestamp(self) -> datetime:
        return self.timestamp or datetime.now(UTC)


class WorkflowAutomatedDecisionAuditService(Protocol):
    """Facade-facing seam for authoritative automated decision audit writes."""

    async def record_policy_evaluation(
        self,
        *,
        context: AutomatedDecisionAuditContext,
        evaluation: PolicyEvaluationResult,
    ) -> Sequence[AutomatedDecisionAuditPersistenceResult]: ...

    async def record_governance_evaluation(
        self,
        *,
        context: AutomatedDecisionAuditContext,
        evaluation: GovernanceEvaluationResult,
    ) -> Sequence[AutomatedDecisionAuditPersistenceResult]: ...


def audit_context_from_workflow_context(
    context: Mapping[str, Any] | None,
) -> AutomatedDecisionAuditContext | None:
    """Extract the application-owned audit context from workflow evaluation context."""

    if context is None:
        return None
    audit_context = context.get(WORKFLOW_AUTOMATED_DECISION_AUDIT_CONTEXT_KEY)
    if isinstance(audit_context, AutomatedDecisionAuditContext):
        return audit_context
    return None
