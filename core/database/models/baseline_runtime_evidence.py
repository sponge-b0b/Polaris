from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base


class BaselineRuntimeEvidenceModel(Base):
    """PostgreSQL authority record for reconstructable Baseline provenance."""

    __tablename__ = "baseline_runtime_evidence"
    __table_args__ = (
        CheckConstraint(
            "jsonb_typeof(authority_metadata) = 'object'",
            name="ck_baseline_runtime_evidence_authority_metadata_object",
        ),
    )

    evidence_id: Mapped[str] = mapped_column(String, primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    workflow_name: Mapped[str] = mapped_column(String, nullable=False)
    workflow_version: Mapped[str] = mapped_column(String, nullable=False)
    provenance_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


Index(
    "idx_baseline_runtime_evidence_workflow",
    BaselineRuntimeEvidenceModel.workflow_name,
)
