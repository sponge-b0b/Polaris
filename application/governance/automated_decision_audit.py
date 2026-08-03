from __future__ import annotations

from dataclasses import dataclass, replace
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
    GovernanceReviewTaskRecord,
    GovernanceReviewTaskStatus,
    authority_metadata_from_contract,
    governance_review_task_id,
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
        audit_result = await self._repository.persist_governance_audit_record(record)
        if not audit_result.success or not _requires_review_task(record):
            return audit_result

        task = _review_task_from_record(record)
        review_result = await self._repository.persist_governance_review_task(task)
        if not review_result.success:
            return AutomatedDecisionAuditPersistenceResult(
                success=False,
                audit_record_id=audit_result.audit_record_id,
                errors=review_result.errors,
            )
        return replace(audit_result, review_task_id=task.review_task_id)


def _requires_review_task(record: AutomatedGovernanceAuditRecord) -> bool:
    return (
        record.outcome is AutomatedGovernanceAuditOutcome.REQUIRE_APPROVAL
        and record.evidence is not None
    )


def _review_task_from_record(
    record: AutomatedGovernanceAuditRecord,
) -> GovernanceReviewTaskRecord:
    if record.evidence is None:
        raise ValueError("governance review tasks require decision evidence.")
    review_scope = _review_scope(record)
    requested_action = record.reason or record.rule_name
    intended_sink = _intended_sink(record)
    return GovernanceReviewTaskRecord(
        review_task_id=governance_review_task_id(
            subject=record.subject,
            evidence=record.evidence,
            review_scope=review_scope,
            requested_action=requested_action,
        ),
        automated_governance_audit_record_id=record.audit_record_id,
        subject=record.subject,
        risk_tier=record.risk_tier,
        authority_metadata=record.authority_metadata,
        review_scope=review_scope,
        intended_sink=intended_sink,
        requested_action=requested_action,
        status=GovernanceReviewTaskStatus.PENDING,
        evidence=record.evidence,
        evidence_references={
            "automated_governance_audit_record_id": record.audit_record_id,
            "evidence_packet": record.evidence.as_dict(),
        },
        created_at=record.timestamp,
        updated_at=record.timestamp,
    )


def _review_scope(record: AutomatedGovernanceAuditRecord) -> str:
    candidate = record.metadata.get("authority_subject_family")
    if isinstance(candidate, str) and candidate.strip():
        return candidate
    return record.subject_type


def _intended_sink(record: AutomatedGovernanceAuditRecord) -> str:
    candidate = record.authority_metadata.get("intended_sink")
    if isinstance(candidate, str) and candidate.strip():
        return candidate
    return record.subject_type
