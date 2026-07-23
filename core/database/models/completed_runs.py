from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base


class CompletedWorkflowRunModel(Base):
    __tablename__ = "completed_workflow_runs"
    __table_args__ = (
        UniqueConstraint(
            "execution_id",
            name="uq_completed_workflow_runs_execution_id",
        ),
        CheckConstraint(
            "execution_mode IN ('normal', 'replay', 'backtest', 'simulated')",
            name="ck_completed_workflow_runs_execution_mode",
        ),
    )

    run_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    workflow_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    workflow_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    execution_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    runtime_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
    )
    execution_mode: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="normal",
        server_default="normal",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    schema_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
    )
    context_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    inputs_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    outputs_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    errors_json: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    node_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    completed_node_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    failed_node_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
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
    "idx_completed_runs_workflow_completed_at",
    CompletedWorkflowRunModel.workflow_name,
    CompletedWorkflowRunModel.completed_at,
)

Index(
    "idx_completed_runs_execution_id",
    CompletedWorkflowRunModel.execution_id,
)

Index(
    "idx_completed_runs_status",
    CompletedWorkflowRunModel.status,
)

Index(
    "idx_completed_runs_success",
    CompletedWorkflowRunModel.success,
)

Index(
    "idx_completed_runs_execution_mode",
    CompletedWorkflowRunModel.execution_mode,
)

Index(
    "idx_completed_runs_created_at",
    CompletedWorkflowRunModel.created_at,
)


class CompletedWorkflowNodeOutputModel(Base):
    __tablename__ = "completed_workflow_node_outputs"

    node_output_id: Mapped[str] = mapped_column(
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
    node_type: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    output_contract: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    output_schema_version: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    success: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    outputs_payload: Mapped[dict[str, Any]] = mapped_column(
        "outputs",
        JSONB,
        nullable=False,
        default=dict,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    errors_json: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


Index(
    "idx_completed_node_outputs_run_id",
    CompletedWorkflowNodeOutputModel.run_id,
)

Index(
    "idx_completed_node_outputs_node_name",
    CompletedWorkflowNodeOutputModel.node_name,
)

Index(
    "idx_completed_node_outputs_node_type",
    CompletedWorkflowNodeOutputModel.node_type,
)

Index(
    "idx_completed_node_outputs_execution_id",
    CompletedWorkflowNodeOutputModel.execution_id,
)

Index(
    "idx_completed_node_outputs_contract_version",
    CompletedWorkflowNodeOutputModel.output_contract,
    CompletedWorkflowNodeOutputModel.output_schema_version,
)


class CompletedRunArtifactModel(Base):
    __tablename__ = "completed_run_artifacts"

    artifact_id: Mapped[str] = mapped_column(
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
    artifact_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    artifact_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    artifact_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    mime_type: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    size_bytes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
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
    "idx_completed_artifacts_run_id",
    CompletedRunArtifactModel.run_id,
)

Index(
    "idx_completed_artifacts_type",
    CompletedRunArtifactModel.artifact_type,
)

Index(
    "idx_completed_artifacts_execution_id",
    CompletedRunArtifactModel.execution_id,
)
