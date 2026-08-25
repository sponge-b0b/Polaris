from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from core.storage.persistence.governance_audit.governance_audit_models import (
    AutomatedDecisionAuditPersistenceResult,
    AutomatedGovernanceAuditRecord,
    AutomatedPolicyAuditRecord,
    GovernanceResidualRiskAcceptanceRecord,
    GovernanceReviewDecisionRecord,
    GovernanceReviewTaskRecord,
    GovernanceReviewTaskStatus,
)


class AutomatedDecisionAuditRepository(Protocol):
    """Repository for authoritative automated policy/governance audit records."""

    async def persist_policy_audit_record(
        self,
        record: AutomatedPolicyAuditRecord,
    ) -> AutomatedDecisionAuditPersistenceResult: ...

    async def persist_governance_audit_record(
        self,
        record: AutomatedGovernanceAuditRecord,
    ) -> AutomatedDecisionAuditPersistenceResult: ...

    async def get_policy_audit_record(
        self,
        audit_record_id: str,
    ) -> AutomatedPolicyAuditRecord | None: ...

    async def persist_governance_review_task(
        self,
        task: GovernanceReviewTaskRecord,
    ) -> AutomatedDecisionAuditPersistenceResult: ...

    async def get_governance_review_task(
        self,
        review_task_id: str,
    ) -> GovernanceReviewTaskRecord | None: ...

    async def update_governance_review_task_status(
        self,
        *,
        review_task_id: str,
        status: GovernanceReviewTaskStatus,
        updated_at: datetime,
    ) -> AutomatedDecisionAuditPersistenceResult: ...

    async def resolve_governance_review_task(
        self,
        *,
        decision: GovernanceReviewDecisionRecord,
        acceptance: GovernanceResidualRiskAcceptanceRecord | None,
        expected_task_updated_at: datetime,
        resolution_fingerprint: str,
    ) -> tuple[
        GovernanceReviewDecisionRecord,
        GovernanceResidualRiskAcceptanceRecord | None,
    ]: ...

    async def get_governance_review_resolution(
        self,
        *,
        review_task_id: str,
        resolution_fingerprint: str,
    ) -> (
        tuple[
            GovernanceReviewDecisionRecord,
            GovernanceResidualRiskAcceptanceRecord | None,
        ]
        | None
    ): ...

    async def persist_governance_review_decision(
        self,
        decision: GovernanceReviewDecisionRecord,
    ) -> AutomatedDecisionAuditPersistenceResult: ...

    async def get_governance_review_decision(
        self,
        review_decision_id: str,
    ) -> GovernanceReviewDecisionRecord | None: ...

    async def persist_residual_risk_acceptance(
        self,
        acceptance: GovernanceResidualRiskAcceptanceRecord,
    ) -> AutomatedDecisionAuditPersistenceResult: ...

    async def get_residual_risk_acceptance(
        self,
        acceptance_id: str,
    ) -> GovernanceResidualRiskAcceptanceRecord | None: ...

    async def get_governance_audit_record(
        self,
        audit_record_id: str,
    ) -> AutomatedGovernanceAuditRecord | None: ...

    async def list_policy_audit_records(
        self,
        *,
        subject_type: str | None = None,
        subject_id: str | None = None,
        risk_tier: str | None = None,
        outcome: str | None = None,
        policy_name: str | None = None,
        evidence_packet_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[AutomatedPolicyAuditRecord]: ...

    async def list_governance_audit_records(
        self,
        *,
        subject_type: str | None = None,
        subject_id: str | None = None,
        risk_tier: str | None = None,
        outcome: str | None = None,
        rule_name: str | None = None,
        evidence_packet_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[AutomatedGovernanceAuditRecord]: ...

    async def list_governance_review_tasks(
        self,
        *,
        subject_type: str | None = None,
        subject_id: str | None = None,
        risk_tier: str | None = None,
        status: str | None = None,
        evidence_packet_id: str | None = None,
    ) -> Sequence[GovernanceReviewTaskRecord]: ...

    async def list_governance_review_decisions(
        self,
        *,
        review_task_id: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        outcome: str | None = None,
        evidence_packet_id: str | None = None,
    ) -> Sequence[GovernanceReviewDecisionRecord]: ...

    async def list_residual_risk_acceptances(
        self,
        *,
        review_task_id: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        evidence_packet_id: str | None = None,
    ) -> Sequence[GovernanceResidualRiskAcceptanceRecord]: ...
