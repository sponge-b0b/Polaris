from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from typing import Protocol

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
    GovernanceReviewerActorType,
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
    review_task_status_for_decision_outcome,
)
from core.telemetry.observability import ObservabilityManager
from core.telemetry.tracing import TraceContext
from core.workflow.governance_audit import AutomatedDecisionAuditContext
from domain.authority import RiskAuthorityContract, RiskTier

from .approval_lifecycle_observability import ApprovalLifecycleObservability


class _AutomatedAuditRecordForQuery(Protocol):
    @property
    def evidence_packet_version(self) -> int | None: ...

    @property
    def timestamp(self) -> datetime: ...


class GovernanceReviewApprovalState(StrEnum):
    """Externally visible approval state for a governance review task."""

    PENDING_REVIEW = "pending_review"
    REVIEW_APPROVED = "review_approved"
    REVIEW_DENIED = "review_denied"
    REVIEW_CONTESTED = "review_contested"
    CHANGES_REQUESTED = "changes_requested"
    REVIEW_OVERRIDDEN = "review_overridden"
    RESIDUAL_RISK_ACCEPTANCE_REQUIRED = "residual_risk_acceptance_required"


@dataclass(frozen=True, slots=True)
class GovernedOutputReleaseRequest:
    """Review-state lookup for one capital-relevant publication or promotion."""

    authority: RiskAuthorityContract
    subject: AutomatedDecisionSubject
    evidence: AutomatedDecisionEvidenceReference
    review_scope: str
    requested_action: str
    boundary_name: str
    residual_risk_acceptance_required: bool = False
    residual_risk_scope: str | None = None
    trace_context: TraceContext | None = None


@dataclass(frozen=True, slots=True)
class GovernedOutputReleaseDecision:
    """Decision for whether a governed output may leave its pending state."""

    allowed: bool
    reason: str
    approval_state: GovernanceReviewApprovalState | None = None
    review_task_id: str | None = None
    residual_risk_acceptance_id: str | None = None
    review_decision_outcome: GovernanceReviewDecisionOutcome | None = None


@dataclass(frozen=True, slots=True)
class AutomatedDecisionAuditQuery:
    """Typed query filters for authoritative automated decision records."""

    subject_type: str | None = None
    subject_id: str | None = None
    risk_tier: RiskTier | str | None = None
    outcome: StrEnum | str | None = None
    evidence_packet_id: str | None = None
    evidence_packet_version: int | None = None
    rule_name: str | None = None
    policy_name: str | None = None
    start: datetime | None = None
    end: datetime | None = None


@dataclass(frozen=True, slots=True)
class GovernanceReviewTaskQuery:
    """Typed query filters for operator-visible governance review work."""

    subject_type: str | None = None
    subject_id: str | None = None
    risk_tier: RiskTier | str | None = None
    status: GovernanceReviewTaskStatus | str | None = None
    approval_state: GovernanceReviewApprovalState | str | None = None
    review_scope: str | None = None
    intended_sink: str | None = None
    requested_action: str | None = None
    evidence_packet_id: str | None = None
    evidence_packet_version: int | None = None
    closed: bool | None = None


@dataclass(frozen=True, slots=True)
class GovernanceReviewDecisionQuery:
    """Typed query filters for immutable human review audit entries."""

    review_task_id: str | None = None
    subject_type: str | None = None
    subject_id: str | None = None
    risk_tier: RiskTier | str | None = None
    outcome: GovernanceReviewDecisionOutcome | str | None = None
    review_scope: str | None = None
    reviewer_id: str | None = None
    reviewer_actor_type: GovernanceReviewerActorType | str | None = None
    evidence_packet_id: str | None = None
    evidence_packet_version: int | None = None


@dataclass(frozen=True, slots=True)
class GovernanceResidualRiskAcceptanceQuery:
    """Typed query filters for scoped residual-risk acceptance records."""

    review_task_id: str | None = None
    subject_type: str | None = None
    subject_id: str | None = None
    risk_tier: RiskTier | str | None = None
    review_scope: str | None = None
    residual_risk_scope: str | None = None
    reviewer_id: str | None = None
    reviewer_actor_type: GovernanceReviewerActorType | str | None = None
    evidence_packet_id: str | None = None
    evidence_packet_version: int | None = None


@dataclass(frozen=True, slots=True)
class GovernanceReviewState:
    """Transport-ready read model for one governance review task."""

    task: GovernanceReviewTaskRecord
    approval_state: GovernanceReviewApprovalState
    automated_decision: AutomatedGovernanceAuditRecord | None
    audit_history: tuple[GovernanceReviewDecisionRecord, ...]
    residual_risk_acceptances: tuple[GovernanceResidualRiskAcceptanceRecord, ...]

    @property
    def review_task_id(self) -> str:
        return self.task.review_task_id

    @property
    def risk_tier(self) -> RiskTier:
        return self.task.risk_tier

    @property
    def review_scope(self) -> str:
        return self.task.review_scope

    @property
    def status(self) -> GovernanceReviewTaskStatus:
        return self.task.status

    @property
    def evidence_packet_version(self) -> int:
        return self.task.evidence_packet_version

    @property
    def closed(self) -> bool:
        return _review_task_is_closed(self.task)


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
    requested_remediation: str | None = None
    residual_risk_remaining: bool = False
    residual_risk_acceptance: GovernanceResidualRiskAcceptanceRequest | None = None
    metadata: JsonObject | None = None
    trace_context: TraceContext | None = None


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


_RELEASE_REVIEW_TIERS = frozenset((RiskTier.ENHANCED, RiskTier.VIGILANT))
_RELEASE_APPROVED_TASK_STATUSES = frozenset(
    (GovernanceReviewTaskStatus.APPROVED, GovernanceReviewTaskStatus.OVERRIDDEN)
)


class AutomatedDecisionAuditService:
    """Application service for authoritative automated decision audit records."""

    def __init__(
        self,
        repository: AutomatedDecisionAuditRepository,
        observability_manager: ObservabilityManager | None = None,
    ) -> None:
        self._repository = repository
        self._approval_observability = ApprovalLifecycleObservability(
            observability_manager,
        )

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
        if not audit_result.success:
            await self._approval_observability.review_failure(
                operation="record_governance_decision",
                reason="governance_audit_persistence_failed",
                error=ValueError(
                    "automated governance audit record could not be persisted.",
                ),
                trace_context=context.trace_context,
                record=record,
                metadata={"repository_errors": tuple(audit_result.errors)},
            )
            return audit_result

        if record.outcome is AutomatedGovernanceAuditOutcome.DENY:
            await self._approval_observability.automated_governance_outcome(
                record=record,
                lifecycle_outcome="denied",
                trace_context=context.trace_context,
            )
        if record.outcome is AutomatedGovernanceAuditOutcome.SKIP:
            await self._approval_observability.automated_governance_outcome(
                record=record,
                lifecycle_outcome="skipped",
                trace_context=context.trace_context,
            )

        if not _requires_review_task(record):
            if record.outcome is AutomatedGovernanceAuditOutcome.REQUIRE_APPROVAL:
                await self._approval_observability.review_failure(
                    operation="record_governance_decision",
                    reason="required_approval_missing_evidence",
                    error=ValueError(
                        "governance review tasks require decision evidence.",
                    ),
                    trace_context=context.trace_context,
                    record=record,
                )
            return audit_result

        task = _review_task_from_record(record)
        review_result = await self._repository.persist_governance_review_task(task)
        if not review_result.success:
            await self._approval_observability.review_failure(
                operation="record_governance_decision",
                reason="review_task_persistence_failed",
                error=ValueError("governance review task could not be persisted."),
                trace_context=context.trace_context,
                record=record,
                task=task,
                metadata={"repository_errors": tuple(review_result.errors)},
            )
            return AutomatedDecisionAuditPersistenceResult(
                success=False,
                audit_record_id=audit_result.audit_record_id,
                errors=review_result.errors,
            )
        await self._approval_observability.required_approval(
            record=record,
            task=task,
            trace_context=context.trace_context,
        )
        return replace(audit_result, review_task_id=task.review_task_id)

    async def list_policy_audit_records(
        self,
        query: AutomatedDecisionAuditQuery | None = None,
    ) -> tuple[AutomatedPolicyAuditRecord, ...]:
        """List authoritative automated policy decisions for operator queries."""
        filters = query or AutomatedDecisionAuditQuery()
        records = await self._repository.list_policy_audit_records(
            subject_type=filters.subject_type,
            subject_id=filters.subject_id,
            risk_tier=_filter_value(filters.risk_tier),
            outcome=_filter_value(filters.outcome),
            policy_name=filters.policy_name,
            evidence_packet_id=filters.evidence_packet_id,
            start=filters.start,
            end=filters.end,
        )
        return _filter_and_sort_audit_records(
            records,
            evidence_packet_version=filters.evidence_packet_version,
        )

    async def list_governance_audit_records(
        self,
        query: AutomatedDecisionAuditQuery | None = None,
    ) -> tuple[AutomatedGovernanceAuditRecord, ...]:
        """List authoritative automated governance decisions for queries."""
        filters = query or AutomatedDecisionAuditQuery()
        records = await self._repository.list_governance_audit_records(
            subject_type=filters.subject_type,
            subject_id=filters.subject_id,
            risk_tier=_filter_value(filters.risk_tier),
            outcome=_filter_value(filters.outcome),
            rule_name=filters.rule_name,
            evidence_packet_id=filters.evidence_packet_id,
            start=filters.start,
            end=filters.end,
        )
        return _filter_and_sort_audit_records(
            records,
            evidence_packet_version=filters.evidence_packet_version,
        )

    async def list_governance_review_tasks(
        self,
        query: GovernanceReviewTaskQuery | None = None,
    ) -> tuple[GovernanceReviewTaskRecord, ...]:
        """List pending or closed review work without exposing mutation paths."""
        filters = query or GovernanceReviewTaskQuery()
        tasks = await self._repository.list_governance_review_tasks(
            subject_type=filters.subject_type,
            subject_id=filters.subject_id,
            risk_tier=_filter_value(filters.risk_tier),
            status=_filter_value(filters.status),
            evidence_packet_id=filters.evidence_packet_id,
        )
        return tuple(
            sorted(
                (task for task in tasks if _matches_review_task_filters(task, filters)),
                key=lambda task: task.updated_at,
                reverse=True,
            )
        )

    async def list_governance_review_decisions(
        self,
        query: GovernanceReviewDecisionQuery | None = None,
    ) -> tuple[GovernanceReviewDecisionRecord, ...]:
        """List immutable approvals, denials, contests, and overrides."""
        filters = query or GovernanceReviewDecisionQuery()
        decisions = await self._repository.list_governance_review_decisions(
            review_task_id=filters.review_task_id,
            subject_type=filters.subject_type,
            subject_id=filters.subject_id,
            outcome=_filter_value(filters.outcome),
            evidence_packet_id=filters.evidence_packet_id,
        )
        return tuple(
            sorted(
                (
                    decision
                    for decision in decisions
                    if _matches_review_decision_filters(decision, filters)
                ),
                key=lambda decision: decision.decided_at,
                reverse=True,
            )
        )

    async def list_residual_risk_acceptances(
        self,
        query: GovernanceResidualRiskAcceptanceQuery | None = None,
    ) -> tuple[GovernanceResidualRiskAcceptanceRecord, ...]:
        """List explicit scoped residual-risk acceptance records."""
        filters = query or GovernanceResidualRiskAcceptanceQuery()
        acceptances = await self._repository.list_residual_risk_acceptances(
            review_task_id=filters.review_task_id,
            subject_type=filters.subject_type,
            subject_id=filters.subject_id,
            evidence_packet_id=filters.evidence_packet_id,
        )
        return tuple(
            sorted(
                (
                    acceptance
                    for acceptance in acceptances
                    if _matches_residual_risk_acceptance_filters(
                        acceptance,
                        filters,
                    )
                ),
                key=lambda acceptance: acceptance.accepted_at,
                reverse=True,
            )
        )

    async def get_governance_review_state(
        self,
        review_task_id: str,
    ) -> GovernanceReviewState:
        """Inspect one review task with automated decision and audit history."""
        task = await self._repository.get_governance_review_task(review_task_id)
        if task is None:
            raise ValueError("governance review task was not found.")
        return await self._governance_review_state_from_task(task)

    async def list_governance_review_states(
        self,
        query: GovernanceReviewTaskQuery | None = None,
    ) -> tuple[GovernanceReviewState, ...]:
        """List review work as transport-ready states with audit history."""
        states: list[GovernanceReviewState] = []
        for task in await self.list_governance_review_tasks(query):
            states.append(await self._governance_review_state_from_task(task))
        return tuple(states)

    async def resolve_governance_review_task(
        self,
        request: GovernanceReviewResolutionRequest,
    ) -> GovernanceReviewResolution:
        task = await self._repository.get_governance_review_task(request.review_task_id)
        if task is None:
            error = ValueError("governance review task was not found.")
            await self._approval_observability.review_failure(
                operation="resolve_governance_review_task",
                reason="review_task_not_found",
                error=error,
                trace_context=request.trace_context,
                review_task_id=request.review_task_id,
            )
            raise error
        resolution_fingerprint = _resolution_fingerprint(request)
        existing_resolution = await self._repository.get_governance_review_resolution(
            review_task_id=task.review_task_id,
            resolution_fingerprint=resolution_fingerprint,
        )
        if existing_resolution is not None:
            decision, acceptance = existing_resolution
            return GovernanceReviewResolution(
                review_task_id=task.review_task_id,
                approval_state=_approval_state_for_task_status(
                    decision.resulting_task_status
                ),
                decision_record=decision,
                residual_risk_acceptance=acceptance,
            )
        try:
            _validate_review_matches_task(task=task, request=request)
        except ValueError as error:
            await self._approval_observability.review_failure(
                operation="resolve_governance_review_task",
                reason="review_validation_failed",
                error=error,
                trace_context=request.trace_context,
                task=task,
                evidence=request.reviewed_evidence,
                review_task_id=request.review_task_id,
                metadata={"review_outcome": request.outcome.value},
            )
            raise

        residual_risk_required = _requires_residual_risk_acceptance(
            task=task,
            request=request,
        )
        if residual_risk_required and request.residual_risk_acceptance is None:
            await self._approval_observability.review_failure(
                operation="resolve_governance_review_task",
                reason="residual_risk_acceptance_required",
                error=ValueError(
                    "residual-risk acceptance is required before vigilant review "
                    "can be approved.",
                ),
                trace_context=request.trace_context,
                task=task,
                metadata={"review_outcome": request.outcome.value},
            )
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
        decision = _review_decision_record_from_request(
            task=task,
            request=request,
            residual_risk_acceptance_id=(
                acceptance.acceptance_id if acceptance is not None else None
            ),
        )
        status = review_task_status_for_decision_outcome(request.outcome)
        try:
            (
                decision,
                acceptance,
            ) = await self._repository.resolve_governance_review_task(
                decision=decision,
                acceptance=acceptance,
                expected_task_updated_at=task.updated_at,
                resolution_fingerprint=resolution_fingerprint,
            )
        except ValueError as error:
            await self._approval_observability.review_failure(
                operation="resolve_governance_review_task",
                reason="review_decision_or_status_persistence_failed",
                error=error,
                trace_context=request.trace_context,
                task=task,
                metadata={"review_outcome": request.outcome.value},
            )
            raise
        await self._approval_observability.review_resolution(
            task=task,
            decision=decision,
            residual_risk_acceptance=acceptance,
            trace_context=request.trace_context,
        )
        return GovernanceReviewResolution(
            review_task_id=task.review_task_id,
            approval_state=_approval_state_for_task_status(status),
            decision_record=decision,
            residual_risk_acceptance=acceptance,
        )

    async def evaluate_governed_output_release(
        self,
        request: GovernedOutputReleaseRequest,
    ) -> GovernedOutputReleaseDecision:
        """Gate capital-relevant publication and durable promotion by review state."""
        if not requires_governed_output_release_review(request.authority):
            return GovernedOutputReleaseDecision(
                allowed=True,
                reason="authority tier does not require governed release review",
            )

        tasks = await self._repository.list_governance_review_tasks(
            subject_type=request.subject.subject_type,
            subject_id=request.subject.subject_id,
            risk_tier=request.authority.risk_tier.value,
            evidence_packet_id=request.evidence.packet_id,
        )
        task = _latest_matching_release_task(tasks, request=request)
        if task is None:
            review_work = await self._record_governed_output_release_review_work(
                request
            )
            if not review_work.success:
                return await self._blocked_governed_output_release_decision(
                    request,
                    approval_state=GovernanceReviewApprovalState.PENDING_REVIEW,
                    reason=(
                        f"{request.boundary_name} is blocked: governed output "
                        "review work could not be durably persisted."
                    ),
                )
            return await self._blocked_governed_output_release_decision(
                request,
                approval_state=GovernanceReviewApprovalState.PENDING_REVIEW,
                review_task_id=review_work.review_task_id,
                reason=(
                    f"{request.boundary_name} is blocked: authoritative "
                    "governance review is pending for this subject, scope, "
                    "requested action, sink, and evidence version."
                ),
            )

        approval_state = _approval_state_for_task_status(task.status)
        review_decision_outcome = await self._latest_review_decision_outcome(
            task.review_task_id,
        )
        if task.status not in _RELEASE_APPROVED_TASK_STATUSES:
            return await self._blocked_governed_output_release_decision(
                request,
                approval_state=approval_state,
                review_task_id=task.review_task_id,
                review_decision_outcome=review_decision_outcome,
                reason=(
                    f"{request.boundary_name} is blocked by governance review "
                    f"state {approval_state.value}."
                ),
            )

        if request.residual_risk_acceptance_required:
            acceptance = await self._matching_residual_risk_acceptance(
                task=task,
                request=request,
            )
            if acceptance is None:
                return await self._blocked_governed_output_release_decision(
                    request,
                    approval_state=(
                        GovernanceReviewApprovalState.RESIDUAL_RISK_ACCEPTANCE_REQUIRED
                    ),
                    review_task_id=task.review_task_id,
                    review_decision_outcome=review_decision_outcome,
                    reason=(
                        f"{request.boundary_name} is blocked: vigilant review "
                        "requires scoped residual-risk acceptance for this "
                        "evidence version."
                    ),
                )
            return GovernedOutputReleaseDecision(
                allowed=True,
                approval_state=approval_state,
                review_task_id=task.review_task_id,
                residual_risk_acceptance_id=acceptance.acceptance_id,
                review_decision_outcome=review_decision_outcome,
                reason="governance review and residual-risk acceptance permit release",
            )

        return GovernedOutputReleaseDecision(
            allowed=True,
            approval_state=approval_state,
            review_task_id=task.review_task_id,
            review_decision_outcome=review_decision_outcome,
            reason="governance review permits release",
        )

    async def _record_governed_output_release_review_work(
        self,
        request: GovernedOutputReleaseRequest,
    ) -> AutomatedDecisionAuditPersistenceResult:
        timestamp = datetime.now(UTC)
        record = AutomatedGovernanceAuditRecord(
            audit_record_id=new_automated_governance_audit_record_id(),
            subject=request.subject,
            risk_tier=request.authority.risk_tier,
            authority_metadata=authority_metadata_from_contract(request.authority),
            evidence=request.evidence,
            outcome=AutomatedGovernanceAuditOutcome.REQUIRE_APPROVAL,
            rule_name="governed_output_release",
            timestamp=timestamp,
            reason=request.requested_action,
            message=(
                f"{request.boundary_name} requires evidence-scoped governance "
                "review before release."
            ),
            metadata={
                "approval_required": True,
                "blocking": True,
                "boundary_name": request.boundary_name,
            },
        )
        audit_result = await self._repository.persist_governance_audit_record(record)
        if not audit_result.success:
            await self._approval_observability.review_failure(
                operation="evaluate_governed_output_release",
                reason="output_governance_audit_persistence_failed",
                error=ValueError(
                    "governed output governance audit record could not be persisted."
                ),
                trace_context=request.trace_context,
                record=record,
                metadata={"repository_errors": tuple(audit_result.errors)},
            )
            return audit_result

        task = _review_task_from_release_request(
            request=request,
            record=record,
        )
        review_result = await self._repository.persist_governance_review_task(task)
        if not review_result.success:
            await self._approval_observability.review_failure(
                operation="evaluate_governed_output_release",
                reason="output_review_task_persistence_failed",
                error=ValueError("governed output review task could not be persisted."),
                trace_context=request.trace_context,
                record=record,
                task=task,
                metadata={"repository_errors": tuple(review_result.errors)},
            )
            return AutomatedDecisionAuditPersistenceResult(
                success=False,
                audit_record_id=audit_result.audit_record_id,
                errors=review_result.errors,
            )
        await self._approval_observability.required_approval(
            record=record,
            task=task,
            trace_context=request.trace_context,
        )
        return replace(audit_result, review_task_id=task.review_task_id)

    async def _blocked_governed_output_release_decision(
        self,
        request: GovernedOutputReleaseRequest,
        *,
        approval_state: GovernanceReviewApprovalState,
        reason: str,
        review_task_id: str | None = None,
        review_decision_outcome: GovernanceReviewDecisionOutcome | None = None,
    ) -> GovernedOutputReleaseDecision:
        decision = GovernedOutputReleaseDecision(
            allowed=False,
            approval_state=approval_state,
            review_task_id=review_task_id,
            review_decision_outcome=review_decision_outcome,
            reason=reason,
        )
        await self._approval_observability.blocked_release(
            authority=request.authority,
            subject=request.subject,
            evidence=request.evidence,
            review_scope=request.review_scope,
            requested_action=request.requested_action,
            boundary_name=request.boundary_name,
            reason=decision.reason,
            approval_state=approval_state.value,
            review_task_id=review_task_id,
            trace_context=request.trace_context,
        )
        return decision

    async def _latest_review_decision_outcome(
        self,
        review_task_id: str,
    ) -> GovernanceReviewDecisionOutcome | None:
        decisions = await self.list_governance_review_decisions(
            GovernanceReviewDecisionQuery(review_task_id=review_task_id),
        )
        if not decisions:
            return None
        return max(decisions, key=lambda decision: decision.decided_at).outcome

    async def _governance_review_state_from_task(
        self,
        task: GovernanceReviewTaskRecord,
    ) -> GovernanceReviewState:
        automated_decision = await self._repository.get_governance_audit_record(
            task.automated_governance_audit_record_id,
        )
        audit_history = await self.list_governance_review_decisions(
            GovernanceReviewDecisionQuery(review_task_id=task.review_task_id),
        )
        residual_risk_acceptances = await self.list_residual_risk_acceptances(
            GovernanceResidualRiskAcceptanceQuery(review_task_id=task.review_task_id),
        )
        return GovernanceReviewState(
            task=task,
            approval_state=_approval_state_for_task_status(task.status),
            automated_decision=automated_decision,
            audit_history=tuple(reversed(audit_history)),
            residual_risk_acceptances=tuple(reversed(residual_risk_acceptances)),
        )

    async def _matching_residual_risk_acceptance(
        self,
        *,
        task: GovernanceReviewTaskRecord,
        request: GovernedOutputReleaseRequest,
    ) -> GovernanceResidualRiskAcceptanceRecord | None:
        acceptances = await self._repository.list_residual_risk_acceptances(
            review_task_id=task.review_task_id,
            subject_type=request.subject.subject_type,
            subject_id=request.subject.subject_id,
            evidence_packet_id=request.evidence.packet_id,
        )
        matching_acceptances = tuple(
            acceptance
            for acceptance in acceptances
            if acceptance.evidence.packet_version == request.evidence.packet_version
            and acceptance.review_scope == request.review_scope
            and acceptance.residual_risk_scope == request.residual_risk_scope
        )
        if not matching_acceptances:
            return None
        return max(matching_acceptances, key=lambda acceptance: acceptance.accepted_at)

    async def approval_state_for_review_task(
        self,
        review_task_id: str,
    ) -> GovernanceReviewApprovalState:
        task = await self._repository.get_governance_review_task(review_task_id)
        if task is None:
            raise ValueError("governance review task was not found.")
        return _approval_state_for_task_status(task.status)


def requires_governed_output_release_review(
    authority: RiskAuthorityContract,
) -> bool:
    return (
        authority.capital_relevant
        and authority.risk_tier in _RELEASE_REVIEW_TIERS
        and (
            authority.durable_authority
            or authority.externally_visible
            or authority.governance_impact
        )
    )


def _resolution_fingerprint(request: GovernanceReviewResolutionRequest) -> str:
    """Derive a stable retry key from the reviewer action, excluding clock values."""
    acceptance = request.residual_risk_acceptance
    payload = {
        "review_task_id": request.review_task_id,
        "outcome": request.outcome.value,
        "reviewer_id": request.reviewer.reviewer_id,
        "reviewer_actor_type": request.reviewer.actor_type.value,
        "rationale": request.rationale,
        "reviewed_evidence": {
            "packet_id": request.reviewed_evidence.packet_id,
            "packet_version": request.reviewed_evidence.packet_version,
        },
        "review_scope": request.review_scope,
        "requested_remediation": request.requested_remediation,
        "residual_risk_remaining": request.residual_risk_remaining,
        "residual_risk_acceptance": (
            {
                "reviewer_id": acceptance.reviewer.reviewer_id,
                "reviewer_actor_type": acceptance.reviewer.actor_type.value,
                "rationale": acceptance.rationale,
                "residual_risk_scope": acceptance.residual_risk_scope,
                "accepted_at": (
                    acceptance.accepted_at.isoformat()
                    if acceptance.accepted_at is not None
                    else None
                ),
                "metadata": acceptance.metadata or {},
            }
            if acceptance is not None
            else None
        ),
        "metadata": request.metadata or {},
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _filter_value(value: StrEnum | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, StrEnum):
        return value.value
    return value


def _matches_evidence_version(
    record_version: int | None,
    query_version: int | None,
) -> bool:
    return query_version is None or record_version == query_version


def _filter_and_sort_audit_records[T: _AutomatedAuditRecordForQuery](
    records: Iterable[T],
    *,
    evidence_packet_version: int | None,
) -> tuple[T, ...]:
    return tuple(
        sorted(
            (
                record
                for record in records
                if _matches_evidence_version(
                    record.evidence_packet_version,
                    evidence_packet_version,
                )
            ),
            key=lambda record: record.timestamp,
            reverse=True,
        )
    )


def _matches_review_task_filters(
    task: GovernanceReviewTaskRecord,
    query: GovernanceReviewTaskQuery,
) -> bool:
    approval_state = _approval_state_for_task_status(task.status)
    return (
        _matches_evidence_version(
            task.evidence_packet_version,
            query.evidence_packet_version,
        )
        and (query.review_scope is None or task.review_scope == query.review_scope)
        and (query.intended_sink is None or task.intended_sink == query.intended_sink)
        and (
            query.requested_action is None
            or task.requested_action == query.requested_action
        )
        and (
            query.approval_state is None
            or approval_state.value == _filter_value(query.approval_state)
        )
        and (query.closed is None or _review_task_is_closed(task) is query.closed)
    )


def _matches_review_decision_filters(
    decision: GovernanceReviewDecisionRecord,
    query: GovernanceReviewDecisionQuery,
) -> bool:
    return (
        (
            query.risk_tier is None
            or decision.risk_tier.value == _filter_value(query.risk_tier)
        )
        and _matches_evidence_version(
            decision.evidence_packet_version,
            query.evidence_packet_version,
        )
        and (query.review_scope is None or decision.review_scope == query.review_scope)
        and (
            query.reviewer_id is None
            or decision.reviewer.reviewer_id == query.reviewer_id
        )
        and (
            query.reviewer_actor_type is None
            or decision.reviewer.actor_type.value
            == _filter_value(query.reviewer_actor_type)
        )
    )


def _matches_residual_risk_acceptance_filters(
    acceptance: GovernanceResidualRiskAcceptanceRecord,
    query: GovernanceResidualRiskAcceptanceQuery,
) -> bool:
    return (
        (
            query.risk_tier is None
            or acceptance.risk_tier.value == _filter_value(query.risk_tier)
        )
        and _matches_evidence_version(
            acceptance.evidence_packet_version,
            query.evidence_packet_version,
        )
        and (
            query.review_scope is None or acceptance.review_scope == query.review_scope
        )
        and (
            query.residual_risk_scope is None
            or acceptance.residual_risk_scope == query.residual_risk_scope
        )
        and (
            query.reviewer_id is None
            or acceptance.reviewer.reviewer_id == query.reviewer_id
        )
        and (
            query.reviewer_actor_type is None
            or acceptance.reviewer.actor_type.value
            == _filter_value(query.reviewer_actor_type)
        )
    )


def _review_task_is_closed(task: GovernanceReviewTaskRecord) -> bool:
    return task.status not in {
        GovernanceReviewTaskStatus.PENDING,
        GovernanceReviewTaskStatus.IN_REVIEW,
    }


def _latest_matching_release_task(
    tasks: Sequence[GovernanceReviewTaskRecord],
    *,
    request: GovernedOutputReleaseRequest,
) -> GovernanceReviewTaskRecord | None:
    matching_tasks = tuple(
        task
        for task in tasks
        if task.evidence.packet_version == request.evidence.packet_version
        and task.review_scope == request.review_scope
        and task.requested_action == request.requested_action
        and task.intended_sink == request.authority.intended_sink.value
    )
    if not matching_tasks:
        return None
    return max(matching_tasks, key=lambda task: task.updated_at)


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
            intended_sink=intended_sink,
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


def _review_task_from_release_request(
    *,
    request: GovernedOutputReleaseRequest,
    record: AutomatedGovernanceAuditRecord,
) -> GovernanceReviewTaskRecord:
    return GovernanceReviewTaskRecord(
        review_task_id=governance_review_task_id(
            subject=request.subject,
            evidence=request.evidence,
            review_scope=request.review_scope,
            intended_sink=request.authority.intended_sink.value,
            requested_action=request.requested_action,
        ),
        automated_governance_audit_record_id=record.audit_record_id,
        subject=request.subject,
        risk_tier=request.authority.risk_tier,
        authority_metadata=record.authority_metadata,
        review_scope=request.review_scope,
        intended_sink=request.authority.intended_sink.value,
        requested_action=request.requested_action,
        status=GovernanceReviewTaskStatus.PENDING,
        evidence=request.evidence,
        evidence_references={
            "automated_governance_audit_record_id": record.audit_record_id,
            "boundary_name": request.boundary_name,
            "evidence_packet": request.evidence.as_dict(),
        },
        created_at=record.timestamp,
        updated_at=record.timestamp,
    )


def _review_scope(record: AutomatedGovernanceAuditRecord) -> str:
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
    if not _task_status_accepts_outcome(status=task.status, outcome=request.outcome):
        raise ValueError("governance review task status cannot accept that outcome.")


def _requires_residual_risk_acceptance(
    *,
    task: GovernanceReviewTaskRecord,
    request: GovernanceReviewResolutionRequest,
) -> bool:
    return (
        request.outcome
        in {
            GovernanceReviewDecisionOutcome.APPROVED,
            GovernanceReviewDecisionOutcome.OVERRIDDEN,
        }
        and task.risk_tier is RiskTier.VIGILANT
        and request.residual_risk_remaining
    )


def _approval_state_for_task_status(
    status: GovernanceReviewTaskStatus,
) -> GovernanceReviewApprovalState:
    return {
        GovernanceReviewTaskStatus.PENDING: (
            GovernanceReviewApprovalState.PENDING_REVIEW
        ),
        GovernanceReviewTaskStatus.IN_REVIEW: (
            GovernanceReviewApprovalState.PENDING_REVIEW
        ),
        GovernanceReviewTaskStatus.APPROVED: (
            GovernanceReviewApprovalState.REVIEW_APPROVED
        ),
        GovernanceReviewTaskStatus.DENIED: (
            GovernanceReviewApprovalState.REVIEW_DENIED
        ),
        GovernanceReviewTaskStatus.CONTESTED: (
            GovernanceReviewApprovalState.REVIEW_CONTESTED
        ),
        GovernanceReviewTaskStatus.CHANGES_REQUESTED: (
            GovernanceReviewApprovalState.CHANGES_REQUESTED
        ),
        GovernanceReviewTaskStatus.OVERRIDDEN: (
            GovernanceReviewApprovalState.REVIEW_OVERRIDDEN
        ),
        GovernanceReviewTaskStatus.CANCELLED: (
            GovernanceReviewApprovalState.PENDING_REVIEW
        ),
    }[status]


def _task_status_accepts_outcome(
    *,
    status: GovernanceReviewTaskStatus,
    outcome: GovernanceReviewDecisionOutcome,
) -> bool:
    if status in {
        GovernanceReviewTaskStatus.PENDING,
        GovernanceReviewTaskStatus.IN_REVIEW,
    }:
        return True
    if outcome is GovernanceReviewDecisionOutcome.OVERRIDDEN:
        return status in {
            GovernanceReviewTaskStatus.DENIED,
            GovernanceReviewTaskStatus.CONTESTED,
            GovernanceReviewTaskStatus.CHANGES_REQUESTED,
        }
    return False


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
        resulting_task_status=review_task_status_for_decision_outcome(request.outcome),
        requested_remediation=request.requested_remediation,
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
