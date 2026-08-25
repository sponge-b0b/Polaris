from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base


class AutomatedPolicyAuditRecordModel(Base):
    """Authoritative PostgreSQL audit record for automated policy outcomes."""

    __tablename__ = "automated_policy_audit_records"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('allow', 'warn', 'deny', 'skip')",
            name="ck_automated_policy_audit_records_outcome",
        ),
        CheckConstraint(
            "risk_tier IN ('baseline', 'enhanced', 'vigilant', "
            "'prohibited_outside_authority')",
            name="ck_automated_policy_audit_records_risk_tier",
        ),
        CheckConstraint(
            "jsonb_typeof(authority_metadata) = 'object'",
            name="ck_automated_policy_audit_records_authority_metadata_object",
        ),
        CheckConstraint(
            "jsonb_typeof(metadata) = 'object'",
            name="ck_automated_policy_audit_records_metadata_object",
        ),
    )

    audit_record_id: Mapped[str] = mapped_column(String, primary_key=True)
    subject_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    risk_tier: Mapped[str] = mapped_column(String, nullable=False, index=True)
    authority_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    evidence_packet_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    evidence_packet_version: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    outcome: Mapped[str] = mapped_column(String, nullable=False, index=True)
    policy_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    message: Mapped[str] = mapped_column(String, nullable=False, default="")
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    row_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    row_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class AutomatedGovernanceAuditRecordModel(Base):
    """Authoritative PostgreSQL audit record for automated governance outcomes."""

    __tablename__ = "automated_governance_audit_records"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('allow', 'warn', 'deny', 'require_approval', 'skip')",
            name="ck_automated_governance_audit_records_outcome",
        ),
        CheckConstraint(
            "risk_tier IN ('baseline', 'enhanced', 'vigilant', "
            "'prohibited_outside_authority')",
            name="ck_automated_governance_audit_records_risk_tier",
        ),
        CheckConstraint(
            "jsonb_typeof(authority_metadata) = 'object'",
            name="ck_automated_governance_audit_records_authority_metadata_object",
        ),
        CheckConstraint(
            "jsonb_typeof(metadata) = 'object'",
            name="ck_automated_governance_audit_records_metadata_object",
        ),
    )

    audit_record_id: Mapped[str] = mapped_column(String, primary_key=True)
    subject_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    risk_tier: Mapped[str] = mapped_column(String, nullable=False, index=True)
    authority_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    evidence_packet_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    evidence_packet_version: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    outcome: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rule_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    message: Mapped[str] = mapped_column(String, nullable=False, default="")
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    row_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    row_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class GovernanceReviewTaskModel(Base):
    """Durable human review task for governance approval requirements."""

    __tablename__ = "governance_review_tasks"
    __table_args__ = (
        CheckConstraint(
            "risk_tier IN ('baseline', 'enhanced', 'vigilant', "
            "'prohibited_outside_authority')",
            name="ck_governance_review_tasks_risk_tier",
        ),
        CheckConstraint(
            "status IN ('pending', 'in_review', 'approved', 'denied', "
            "'contested', 'changes_requested', 'overridden', 'cancelled')",
            name="ck_governance_review_tasks_status",
        ),
        CheckConstraint(
            "jsonb_typeof(authority_metadata) = 'object'",
            name="ck_governance_review_tasks_authority_metadata_object",
        ),
        CheckConstraint(
            "jsonb_typeof(evidence_references) = 'object'",
            name="ck_governance_review_tasks_evidence_references_object",
        ),
        UniqueConstraint(
            "subject_type",
            "subject_id",
            "evidence_packet_id",
            "evidence_packet_version",
            "review_scope",
            "intended_sink",
            "requested_action",
            name="uq_governance_review_tasks_scoped_evidence_sink_action",
        ),
    )

    review_task_id: Mapped[str] = mapped_column(String, primary_key=True)
    automated_governance_audit_record_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("automated_governance_audit_records.audit_record_id"),
        nullable=False,
        index=True,
    )
    subject_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    risk_tier: Mapped[str] = mapped_column(String, nullable=False, index=True)
    authority_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    review_scope: Mapped[str] = mapped_column(String, nullable=False, index=True)
    intended_sink: Mapped[str] = mapped_column(String, nullable=False, index=True)
    requested_action: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    evidence_packet_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    evidence_packet_version: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_references: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    row_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    row_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class GovernanceReviewDecisionModel(Base):
    """Immutable attributable human review outcome audit entry."""

    __tablename__ = "governance_review_decisions"
    __table_args__ = (
        CheckConstraint(
            "risk_tier IN ('baseline', 'enhanced', 'vigilant', "
            "'prohibited_outside_authority')",
            name="ck_governance_review_decisions_risk_tier",
        ),
        CheckConstraint(
            "outcome IN ('approved', 'denied', 'contested', "
            "'changes_requested', 'overridden')",
            name="ck_governance_review_decisions_outcome",
        ),
        CheckConstraint(
            "resulting_task_status IN ('approved', 'denied', 'contested', "
            "'changes_requested', 'overridden')",
            name="ck_governance_review_decisions_resulting_status",
        ),
        CheckConstraint(
            "reviewer_actor_type IN ('human_reviewer', 'organization_reviewer')",
            name="ck_governance_review_decisions_reviewer_actor_type",
        ),
        CheckConstraint(
            "jsonb_typeof(metadata) = 'object'",
            name="ck_governance_review_decisions_metadata_object",
        ),
        UniqueConstraint(
            "review_task_id",
            "resolution_fingerprint",
            name="uq_governance_review_decisions_task_resolution_fingerprint",
        ),
    )

    review_decision_id: Mapped[str] = mapped_column(String, primary_key=True)
    review_task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("governance_review_tasks.review_task_id"),
        nullable=False,
        index=True,
    )
    resolution_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    automated_governance_audit_record_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("automated_governance_audit_records.audit_record_id"),
        nullable=False,
    )
    subject_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    risk_tier: Mapped[str] = mapped_column(String, nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(String, nullable=False, index=True)
    reviewer_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    reviewer_actor_type: Mapped[str] = mapped_column(String, nullable=False)
    reviewer_display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    rationale: Mapped[str] = mapped_column(String, nullable=False)
    review_scope: Mapped[str] = mapped_column(String, nullable=False, index=True)
    evidence_packet_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    evidence_packet_version: Mapped[int] = mapped_column(Integer, nullable=False)
    resulting_task_status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    requested_remediation: Mapped[str | None] = mapped_column(String, nullable=True)
    residual_risk_acceptance_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    residual_risk_acceptance_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    row_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class GovernanceResidualRiskAcceptanceModel(Base):
    """Explicit scoped residual-risk acceptance audit entry."""

    __tablename__ = "governance_residual_risk_acceptances"
    __table_args__ = (
        CheckConstraint(
            "risk_tier IN ('vigilant')",
            name="ck_governance_residual_risk_acceptances_risk_tier",
        ),
        CheckConstraint(
            "reviewer_actor_type IN ('human_reviewer', 'organization_reviewer')",
            name="ck_governance_residual_acceptances_reviewer_actor_type",
        ),
        CheckConstraint(
            "jsonb_typeof(metadata) = 'object'",
            name="ck_governance_residual_risk_acceptances_metadata_object",
        ),
        UniqueConstraint(
            "review_task_id",
            "evidence_packet_id",
            "evidence_packet_version",
            "review_scope",
            "residual_risk_scope",
            name="uq_governance_residual_acceptances_scoped_evidence",
        ),
    )

    acceptance_id: Mapped[str] = mapped_column(String, primary_key=True)
    review_task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("governance_review_tasks.review_task_id"),
        nullable=False,
        index=True,
    )
    subject_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    risk_tier: Mapped[str] = mapped_column(String, nullable=False, index=True)
    reviewer_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    reviewer_actor_type: Mapped[str] = mapped_column(String, nullable=False)
    reviewer_display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    rationale: Mapped[str] = mapped_column(String, nullable=False)
    review_scope: Mapped[str] = mapped_column(String, nullable=False, index=True)
    residual_risk_scope: Mapped[str] = mapped_column(String, nullable=False, index=True)
    evidence_packet_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    evidence_packet_version: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    row_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


Index(
    "idx_automated_policy_audit_subject_outcome",
    AutomatedPolicyAuditRecordModel.subject_type,
    AutomatedPolicyAuditRecordModel.subject_id,
    AutomatedPolicyAuditRecordModel.outcome,
)
Index(
    "idx_automated_policy_audit_evidence_outcome",
    AutomatedPolicyAuditRecordModel.evidence_packet_id,
    AutomatedPolicyAuditRecordModel.outcome,
)
Index(
    "idx_automated_governance_audit_subject_outcome",
    AutomatedGovernanceAuditRecordModel.subject_type,
    AutomatedGovernanceAuditRecordModel.subject_id,
    AutomatedGovernanceAuditRecordModel.outcome,
)
Index(
    "idx_automated_governance_audit_evidence_outcome",
    AutomatedGovernanceAuditRecordModel.evidence_packet_id,
    AutomatedGovernanceAuditRecordModel.outcome,
)

Index(
    "idx_governance_review_tasks_subject_status",
    GovernanceReviewTaskModel.subject_type,
    GovernanceReviewTaskModel.subject_id,
    GovernanceReviewTaskModel.status,
)
Index(
    "idx_governance_review_tasks_evidence_status",
    GovernanceReviewTaskModel.evidence_packet_id,
    GovernanceReviewTaskModel.evidence_packet_version,
    GovernanceReviewTaskModel.status,
)
Index(
    "ix_governance_review_decisions_gov_audit_id",
    GovernanceReviewDecisionModel.automated_governance_audit_record_id,
)
Index(
    "idx_governance_review_decisions_task_outcome",
    GovernanceReviewDecisionModel.review_task_id,
    GovernanceReviewDecisionModel.outcome,
)
Index(
    "idx_governance_review_decisions_evidence_outcome",
    GovernanceReviewDecisionModel.evidence_packet_id,
    GovernanceReviewDecisionModel.evidence_packet_version,
    GovernanceReviewDecisionModel.outcome,
)
Index(
    "idx_governance_residual_acceptances_task_evidence",
    GovernanceResidualRiskAcceptanceModel.review_task_id,
    GovernanceResidualRiskAcceptanceModel.evidence_packet_id,
    GovernanceResidualRiskAcceptanceModel.evidence_packet_version,
)
