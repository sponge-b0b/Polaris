from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, func
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
