from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum

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
    GovernanceResidualRiskAcceptanceRecord,
    GovernanceReviewDecisionOutcome,
    GovernanceReviewDecisionRecord,
    GovernanceReviewerIdentity,
    GovernanceReviewTaskRecord,
    GovernanceReviewTaskStatus,
    JsonObject,
    authority_metadata_from_contract,
    governance_review_task_id,
    new_automated_governance_audit_record_id,
    new_automated_policy_audit_record_id,
    new_governance_residual_risk_acceptance_id,
    new_governance_review_decision_id,
)
from domain.authority import RiskAuthorityContract, RiskTier
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


class GovernanceReviewApprovalState(StrEnum):
    """Externally visible approval state for a governance review task."""

    PENDING_REVIEW = "pending_review"
    REVIEW_APPROVED = "review_approved"
    REVIEW_DENIED = "review_denied"
    RESIDUAL_RISK_ACCEPTANCE_REQUIRED = "residual_risk_acceptance_required"


@dataclass(frozen=True, slots=True)
class GovernanceResidualRiskAcceptanceRequest:
    """Explicit reviewer acceptance of residual risk for one reviewed version."""

    reviewer: GovernanceReviewerIdentity
    rationale: str
    residual_risk_scope: str
    accepted_at: datetime | None = None
    metadata: JsonObject | None = None


@dataclass(frozen=True, slots=True)
class GovernanceReviewResolutionRequest:
    """Human review resolution request for one scoped evidence version."""

    review_task_id: str
    outcome: GovernanceReviewDecisionOutcome
    reviewer: GovernanceReviewerIdentity
    rationale: str
    reviewed_evidence: AutomatedDecisionEvidenceReference
    review_scope: str
    decided_at: datetime | None = None
    residual_risk_remaining: bool = False
    residual_risk_acceptance: GovernanceResidualRiskAcceptanceRequest | None = None
    metadata: JsonObject | None = None


@dataclass(frozen=True, slots=True)
class GovernanceReviewResolution:
    """Result of applying a human review resolution."""

    review_task_id: str
    approval_state: GovernanceReviewApprovalState
    decision_record: GovernanceReviewDecisionRecord | None = None
    residual_risk_acceptance: GovernanceResidualRiskAcceptanceRecord | None = None

    @property
    def review_approved(self) -> bool:
        return self.approval_state is GovernanceReviewApprovalState.REVIEW_APPROVED


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

    async def resolve_governance_review_task(
        self,
        request: GovernanceReviewResolutionRequest,
    ) -> GovernanceReviewResolution:
        task = await self._repository.get_governance_review_task(request.review_task_id)
        if task is None:
            raise ValueError("governance review task was not found.")
        _validate_review_matches_task(task=task, request=request)

        if request.outcome is GovernanceReviewDecisionOutcome.DENIED:
            decision = _review_decision_record_from_request(
                task=task,
                request=request,
                residual_risk_acceptance_id=None,
            )
            await self._persist_review_decision_and_status(
                decision=decision,
                status=GovernanceReviewTaskStatus.DENIED,
            )
            return GovernanceReviewResolution(
                review_task_id=task.review_task_id,
                approval_state=GovernanceReviewApprovalState.REVIEW_DENIED,
                decision_record=decision,
            )

        residual_risk_required = _requires_residual_risk_acceptance(
            task=task,
            request=request,
        )
        if residual_risk_required and request.residual_risk_acceptance is None:
            return GovernanceReviewResolution(
                review_task_id=task.review_task_id,
                approval_state=(
                    GovernanceReviewApprovalState.RESIDUAL_RISK_ACCEPTANCE_REQUIRED
                ),
            )

        acceptance = None
        if request.residual_risk_acceptance is not None:
            acceptance = _residual_risk_acceptance_record_from_request(
                task=task,
                request=request,
            )
            acceptance_result = await self._repository.persist_residual_risk_acceptance(
                acceptance,
            )
            if not acceptance_result.success:
                raise ValueError("residual-risk acceptance could not be persisted.")

        decision = _review_decision_record_from_request(
            task=task,
            request=request,
            residual_risk_acceptance_id=(
                acceptance.acceptance_id if acceptance is not None else None
            ),
        )
        await self._persist_review_decision_and_status(
            decision=decision,
            status=GovernanceReviewTaskStatus.APPROVED,
        )
        return GovernanceReviewResolution(
            review_task_id=task.review_task_id,
            approval_state=GovernanceReviewApprovalState.REVIEW_APPROVED,
            decision_record=decision,
            residual_risk_acceptance=acceptance,
        )

    async def approval_state_for_review_task(
        self,
        review_task_id: str,
    ) -> GovernanceReviewApprovalState:
        task = await self._repository.get_governance_review_task(review_task_id)
        if task is None:
            raise ValueError("governance review task was not found.")
        if task.status is GovernanceReviewTaskStatus.APPROVED:
            return GovernanceReviewApprovalState.REVIEW_APPROVED
        if task.status is GovernanceReviewTaskStatus.DENIED:
            return GovernanceReviewApprovalState.REVIEW_DENIED
        return GovernanceReviewApprovalState.PENDING_REVIEW

    async def _persist_review_decision_and_status(
        self,
        *,
        decision: GovernanceReviewDecisionRecord,
        status: GovernanceReviewTaskStatus,
    ) -> None:
        decision_result = await self._repository.persist_governance_review_decision(
            decision,
        )
        if not decision_result.success:
            raise ValueError("governance review decision could not be persisted.")
        status_result = await self._repository.update_governance_review_task_status(
            review_task_id=decision.review_task_id,
            status=status,
            updated_at=decision.decided_at,
        )
        if not status_result.success:
            raise ValueError("governance review task status could not be updated.")


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


def _validate_review_matches_task(
    *,
    task: GovernanceReviewTaskRecord,
    request: GovernanceReviewResolutionRequest,
) -> None:
    if request.reviewed_evidence != task.evidence:
        raise ValueError(
            "reviewed evidence version must match the governance review task."
        )
    if request.review_scope != task.review_scope:
        raise ValueError("review scope must match the governance review task.")
    if task.status not in {
        GovernanceReviewTaskStatus.PENDING,
        GovernanceReviewTaskStatus.IN_REVIEW,
    }:
        raise ValueError("governance review task is not open for resolution.")


def _requires_residual_risk_acceptance(
    *,
    task: GovernanceReviewTaskRecord,
    request: GovernanceReviewResolutionRequest,
) -> bool:
    return (
        request.outcome is GovernanceReviewDecisionOutcome.APPROVED
        and task.risk_tier is RiskTier.VIGILANT
        and request.residual_risk_remaining
    )


def _review_decision_record_from_request(
    *,
    task: GovernanceReviewTaskRecord,
    request: GovernanceReviewResolutionRequest,
    residual_risk_acceptance_id: str | None,
) -> GovernanceReviewDecisionRecord:
    residual_risk_acceptance_required = _requires_residual_risk_acceptance(
        task=task,
        request=request,
    )
    return GovernanceReviewDecisionRecord(
        review_decision_id=new_governance_review_decision_id(),
        review_task_id=task.review_task_id,
        automated_governance_audit_record_id=(
            task.automated_governance_audit_record_id
        ),
        subject=task.subject,
        risk_tier=task.risk_tier,
        outcome=request.outcome,
        reviewer=request.reviewer,
        rationale=request.rationale,
        review_scope=task.review_scope,
        evidence=task.evidence,
        decided_at=request.decided_at or datetime.now(UTC),
        residual_risk_acceptance_required=residual_risk_acceptance_required,
        residual_risk_acceptance_id=residual_risk_acceptance_id,
        metadata=request.metadata or {},
    )


def _residual_risk_acceptance_record_from_request(
    *,
    task: GovernanceReviewTaskRecord,
    request: GovernanceReviewResolutionRequest,
) -> GovernanceResidualRiskAcceptanceRecord:
    acceptance_request = request.residual_risk_acceptance
    if acceptance_request is None:
        raise ValueError("residual-risk acceptance is required.")
    return GovernanceResidualRiskAcceptanceRecord(
        acceptance_id=new_governance_residual_risk_acceptance_id(),
        review_task_id=task.review_task_id,
        subject=task.subject,
        risk_tier=task.risk_tier,
        reviewer=acceptance_request.reviewer,
        rationale=acceptance_request.rationale,
        review_scope=task.review_scope,
        residual_risk_scope=acceptance_request.residual_risk_scope,
        evidence=task.evidence,
        accepted_at=acceptance_request.accepted_at or datetime.now(UTC),
        metadata=acceptance_request.metadata or {},
    )
