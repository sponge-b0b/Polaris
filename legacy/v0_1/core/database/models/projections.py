from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base


class WorkflowOutputProjectionJobModel(Base):
    __tablename__ = "workflow_output_projection_jobs"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "projector_name",
            "node_name",
            "source_fingerprint",
            name="uq_workflow_output_projection_jobs_source",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed', 'skipped')",
            name="ck_workflow_output_projection_jobs_status",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_workflow_output_projection_jobs_attempt_count_non_negative",
        ),
        CheckConstraint(
            "output_schema_version > 0",
            name="ck_workflow_output_projection_jobs_schema_version_positive",
        ),
    )

    projection_job_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    run_id: Mapped[str] = mapped_column(
        ForeignKey(
            "completed_workflow_runs.run_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    workflow_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    execution_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    node_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    projector_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    output_contract: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    output_schema_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    source_fingerprint: Mapped[str] = mapped_column(
        String,
        nullable=False,
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
    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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
    completed_at: Mapped[datetime | None] = mapped_column(
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
    "idx_workflow_projection_jobs_status_created_at",
    WorkflowOutputProjectionJobModel.status,
    WorkflowOutputProjectionJobModel.created_at,
)

Index(
    "idx_workflow_projection_jobs_workflow_execution",
    WorkflowOutputProjectionJobModel.workflow_name,
    WorkflowOutputProjectionJobModel.execution_id,
)

Index(
    "idx_workflow_projection_jobs_projector_node",
    WorkflowOutputProjectionJobModel.projector_name,
    WorkflowOutputProjectionJobModel.node_name,
)

Index(
    "idx_workflow_projection_jobs_pending_failed",
    WorkflowOutputProjectionJobModel.status,
    WorkflowOutputProjectionJobModel.updated_at,
)

Index(
    "idx_workflow_projection_jobs_contract_version",
    WorkflowOutputProjectionJobModel.output_contract,
    WorkflowOutputProjectionJobModel.output_schema_version,
)
