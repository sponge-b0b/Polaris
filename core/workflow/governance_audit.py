from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

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


@dataclass(frozen=True, slots=True)
class WorkflowExecutionAuditCapability:
    """Opaque audit composition passed from the application boundary to the facade."""

    _service: WorkflowAutomatedDecisionAuditService
    _context: AutomatedDecisionAuditContext

    @property
    def service(self) -> WorkflowAutomatedDecisionAuditService:
        return self._service

    @property
    def context(self) -> AutomatedDecisionAuditContext:
        return self._context


def issue_workflow_execution_audit_capability(
    *,
    service: WorkflowAutomatedDecisionAuditService,
    context: AutomatedDecisionAuditContext,
) -> WorkflowExecutionAuditCapability:
    """Create the capability used for one governed facade invocation.

    The request-scoped application service is the only production caller of this
    factory; the facade accepts the resulting capability rather than a database
    service or mutable evidence metadata.
    """

    return WorkflowExecutionAuditCapability(
        _service=service,
        _context=context,
    )
