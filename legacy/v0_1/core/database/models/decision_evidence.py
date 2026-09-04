from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base


class DecisionEvidencePacketModel(Base):
    """PostgreSQL audit record for a canonical decision evidence packet."""

    __tablename__ = "decision_evidence_packets"
    __table_args__ = (
        CheckConstraint(
            "risk_tier IN ('enhanced', 'vigilant')",
            name="ck_decision_evidence_packets_risk_tier",
        ),
        CheckConstraint(
            "jsonb_typeof(authority_metadata) = 'object'",
            name="ck_decision_evidence_packets_authority_metadata_object",
        ),
        CheckConstraint(
            "jsonb_typeof(retention_metadata) = 'object'",
            name="ck_decision_evidence_packets_retention_metadata_object",
        ),
        CheckConstraint(
            "jsonb_typeof(reconstruction_reference_ids) = 'array'",
            name="ck_decision_evidence_packets_reconstruction_ids_array",
        ),
        CheckConstraint(
            "jsonb_typeof(claim_audit) = 'array'",
            name="ck_decision_evidence_packets_claim_audit_array",
        ),
        CheckConstraint(
            "jsonb_typeof(evidence_references) = 'array'",
            name="ck_decision_evidence_packets_evidence_refs_array",
        ),
        CheckConstraint(
            "jsonb_typeof(reconstruction_references) = 'array'",
            name="ck_decision_evidence_packets_reconstruction_refs_array",
        ),
        CheckConstraint(
            "jsonb_typeof(constraints) = 'array'",
            name="ck_decision_evidence_packets_constraints_array",
        ),
        CheckConstraint(
            "jsonb_typeof(uncertainties) = 'array'",
            name="ck_decision_evidence_packets_uncertainties_array",
        ),
        CheckConstraint(
            "jsonb_typeof(limitations) = 'array'",
            name="ck_decision_evidence_packets_limitations_array",
        ),
    )

    packet_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    output_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    workflow_name: Mapped[str] = mapped_column(String, nullable=False)
    workflow_definition_fingerprint: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    execution_id: Mapped[str] = mapped_column(String, nullable=False)
    schema_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    risk_tier: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    authority_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    retention_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    reconstruction_reference_ids: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    claim_audit: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    evidence_references: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    reconstruction_references: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    constraints: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    uncertainties: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    limitations: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_decision_evidence_packets_output_id",
    DecisionEvidencePacketModel.output_id,
)

Index(
    "idx_decision_evidence_packets_risk_tier",
    DecisionEvidencePacketModel.risk_tier,
)
