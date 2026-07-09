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
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from core.database.base import Base


class WorkflowRunModel(Base):
    __tablename__ = "workflow_runs"

    workflow_name: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    execution_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
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
    mode: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    state_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
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
    "idx_workflow_runs_execution_id",
    WorkflowRunModel.execution_id,
)

Index(
    "idx_workflow_runs_workflow_started_at",
    WorkflowRunModel.workflow_name,
    WorkflowRunModel.started_at,
)


class WorkflowNodeRunModel(Base):
    __tablename__ = "workflow_node_runs"

    workflow_name: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    execution_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    node_name: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    wave_index: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=0,
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
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    output_payload: Mapped[dict[str, Any]] = mapped_column(
        "outputs",
        JSONB,
        nullable=False,
        default=dict,
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
    "idx_workflow_node_runs_execution_id",
    WorkflowNodeRunModel.execution_id,
)

Index(
    "idx_workflow_node_runs_execution_status",
    WorkflowNodeRunModel.workflow_name,
    WorkflowNodeRunModel.execution_id,
    WorkflowNodeRunModel.status,
)


class WorkflowEventModel(Base):
    __tablename__ = "workflow_events"

    event_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    event_type: Mapped[str] = mapped_column(
        String,
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
    wave_index: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


Index(
    "idx_workflow_events_execution_timestamp",
    WorkflowEventModel.workflow_name,
    WorkflowEventModel.execution_id,
    WorkflowEventModel.timestamp,
)


class WorkflowStateSnapshotModel(Base):
    __tablename__ = "workflow_state_snapshots"

    snapshot_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
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
    workflow_status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
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
    wave_index: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )
    checkpoint_reference: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    state_payload: Mapped[dict[str, Any]] = mapped_column(
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

    __table_args__ = (
        CheckConstraint(
            "wave_index IS NULL OR wave_index >= 0",
            name="ck_workflow_state_snapshots_wave_index_non_negative",
        ),
    )


Index(
    "idx_workflow_state_snapshots_workflow_timestamp",
    WorkflowStateSnapshotModel.workflow_name,
    WorkflowStateSnapshotModel.timestamp,
)

Index(
    "idx_workflow_state_snapshots_execution_timestamp",
    WorkflowStateSnapshotModel.workflow_name,
    WorkflowStateSnapshotModel.execution_id,
    WorkflowStateSnapshotModel.timestamp,
)

Index(
    "idx_workflow_state_snapshots_runtime_timestamp",
    WorkflowStateSnapshotModel.runtime_id,
    WorkflowStateSnapshotModel.timestamp,
)

Index(
    "idx_workflow_state_snapshots_wave_timestamp",
    WorkflowStateSnapshotModel.workflow_name,
    WorkflowStateSnapshotModel.execution_id,
    WorkflowStateSnapshotModel.wave_index,
    WorkflowStateSnapshotModel.timestamp,
)
