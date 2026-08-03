from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
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
            "'changes_requested', 'cancelled')",
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
            "requested_action",
            name="uq_governance_review_tasks_scoped_evidence_action",
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
