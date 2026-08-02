from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from core.runtime.governance import GovernanceEvaluationResult, GovernanceResult
from core.runtime.policies import PolicyEvaluationResult, PolicyResult
from core.storage.persistence.governance_audit import (
    AutomatedDecisionAuditPersistenceResult,
    AutomatedDecisionAuditRepository,
    AutomatedDecisionEvidenceReference,
    AutomatedDecisionSubject,
    AutomatedGovernanceAuditOutcome,
    AutomatedGovernanceAuditRecord,
    AutomatedPolicyAuditOutcome,
    AutomatedPolicyAuditRecord,
    authority_metadata_from_contract,
    new_automated_governance_audit_record_id,
    new_automated_policy_audit_record_id,
)
from domain.authority import RiskAuthorityContract
from domain.decision_evidence import DecisionEvidencePacket


@dataclass(frozen=True, slots=True)
class AutomatedDecisionAuditContext:
    """Canonical context required to audit one automated decision."""

    subject: AutomatedDecisionSubject
    authority: RiskAuthorityContract
    evidence: AutomatedDecisionEvidenceReference | None = None
    timestamp: datetime | None = None

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


class AutomatedDecisionAuditService:
    """Application service for authoritative automated decision audit records."""

    def __init__(
        self,
        repository: AutomatedDecisionAuditRepository,
    ) -> None:
        self._repository = repository

    async def record_policy_evaluation(
        self,
        *,
        context: AutomatedDecisionAuditContext,
        evaluation: PolicyEvaluationResult,
    ) -> tuple[AutomatedDecisionAuditPersistenceResult, ...]:
        return tuple(
            [
                await self.record_policy_decision(
                    context=context,
                    result=result,
                )
                for result in evaluation.results
            ]
        )

    async def record_policy_decision(
        self,
        *,
        context: AutomatedDecisionAuditContext,
        result: PolicyResult,
    ) -> AutomatedDecisionAuditPersistenceResult:
        record = AutomatedPolicyAuditRecord(
            audit_record_id=new_automated_policy_audit_record_id(),
            subject=context.subject,
            risk_tier=context.authority.risk_tier,
            authority_metadata=authority_metadata_from_contract(context.authority),
            evidence=context.evidence,
            outcome=AutomatedPolicyAuditOutcome(result.decision.value),
            policy_name=result.policy_name,
            timestamp=context.effective_timestamp,
            reason=result.reason,
            message=result.message,
            metadata=result.metadata,
        )
        return await self._repository.persist_policy_audit_record(record)

    async def record_governance_evaluation(
        self,
        *,
        context: AutomatedDecisionAuditContext,
        evaluation: GovernanceEvaluationResult,
    ) -> tuple[AutomatedDecisionAuditPersistenceResult, ...]:
        return tuple(
            [
                await self.record_governance_decision(
                    context=context,
                    result=result,
                )
                for result in evaluation.results
            ]
        )

    async def record_governance_decision(
        self,
        *,
        context: AutomatedDecisionAuditContext,
        result: GovernanceResult,
    ) -> AutomatedDecisionAuditPersistenceResult:
        record = AutomatedGovernanceAuditRecord(
            audit_record_id=new_automated_governance_audit_record_id(),
            subject=context.subject,
            risk_tier=context.authority.risk_tier,
            authority_metadata=authority_metadata_from_contract(context.authority),
            evidence=context.evidence,
            outcome=AutomatedGovernanceAuditOutcome(result.decision.value),
            rule_name=result.rule_name,
            timestamp=context.effective_timestamp,
            reason=result.reason,
            message=result.message,
            metadata={
                **result.metadata,
                "approval_required": result.approval_required,
                "blocking": result.blocking,
            },
        )
        return await self._repository.persist_governance_audit_record(record)
