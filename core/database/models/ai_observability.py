from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from core.database.base import Base


class AiObservabilityExportJobModel(Base):
    """Durable export queue for Langfuse AI-observability projections."""

    __tablename__ = "ai_observability_export_jobs"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name="uq_ai_observability_export_jobs_idempotency_key",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'exported', 'failed', 'skipped')",
            name="ck_ai_observability_export_jobs_status",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_ai_observability_export_jobs_attempt_count_non_negative",
        ),
        CheckConstraint(
            "max_attempts > 0",
            name="ck_ai_observability_export_jobs_max_attempts_positive",
        ),
        CheckConstraint(
            "retry_after_seconds IS NULL OR retry_after_seconds >= 0.0",
            name="ck_ai_observability_export_jobs_retry_after_non_negative",
        ),
        CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name="ck_ai_observability_export_jobs_payload_object",
        ),
    )

    export_job_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    observation_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    observation_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    observation_family: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    observation_status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )
    trace_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    span_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    workflow_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    execution_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    runtime_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    node_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    observation_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    parent_observation_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    dataset_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    case_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    run_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    external_trace_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    external_observation_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    retry_after_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    exported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_ai_observability_export_jobs_status_available_at",
    AiObservabilityExportJobModel.status,
    AiObservabilityExportJobModel.available_at,
)

Index(
    "idx_ai_observability_export_jobs_workflow_execution",
    AiObservabilityExportJobModel.workflow_name,
    AiObservabilityExportJobModel.execution_id,
)

Index(
    "idx_ai_observability_export_jobs_observation_status",
    AiObservabilityExportJobModel.observation_type,
    AiObservabilityExportJobModel.status,
)

Index(
    "idx_ai_observability_export_jobs_dataset_case_run",
    AiObservabilityExportJobModel.dataset_id,
    AiObservabilityExportJobModel.case_id,
    AiObservabilityExportJobModel.run_id,
)

Index(
    "idx_ai_observability_export_jobs_trace_span",
    AiObservabilityExportJobModel.trace_id,
    AiObservabilityExportJobModel.span_id,
)
