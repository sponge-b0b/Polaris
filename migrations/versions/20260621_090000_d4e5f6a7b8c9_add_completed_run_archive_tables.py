"""add completed run archive tables

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-21 09:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "completed_workflow_runs",
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("workflow_name", sa.String(), nullable=False),
        sa.Column("workflow_id", sa.String(), nullable=True),
        sa.Column("execution_id", sa.String(), nullable=False),
        sa.Column("runtime_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column(
            "context_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "inputs_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "outputs_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "errors_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("node_count", sa.Integer(), nullable=True),
        sa.Column("completed_node_count", sa.Integer(), nullable=True),
        sa.Column("failed_node_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("run_id"),
        sa.UniqueConstraint(
            "execution_id",
            name="uq_completed_workflow_runs_execution_id",
        ),
    )
    op.create_index(
        op.f("ix_completed_workflow_runs_completed_at"),
        "completed_workflow_runs",
        ["completed_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_completed_workflow_runs_execution_id"),
        "completed_workflow_runs",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_completed_workflow_runs_runtime_id"),
        "completed_workflow_runs",
        ["runtime_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_completed_workflow_runs_started_at"),
        "completed_workflow_runs",
        ["started_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_completed_workflow_runs_status"),
        "completed_workflow_runs",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_completed_workflow_runs_success"),
        "completed_workflow_runs",
        ["success"],
        unique=False,
    )
    op.create_index(
        op.f("ix_completed_workflow_runs_workflow_id"),
        "completed_workflow_runs",
        ["workflow_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_completed_workflow_runs_workflow_name"),
        "completed_workflow_runs",
        ["workflow_name"],
        unique=False,
    )
    op.create_index(
        "idx_completed_runs_created_at",
        "completed_workflow_runs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "idx_completed_runs_execution_id",
        "completed_workflow_runs",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        "idx_completed_runs_status",
        "completed_workflow_runs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "idx_completed_runs_success",
        "completed_workflow_runs",
        ["success"],
        unique=False,
    )
    op.create_index(
        "idx_completed_runs_workflow_completed_at",
        "completed_workflow_runs",
        ["workflow_name", "completed_at"],
        unique=False,
    )

    op.create_table(
        "completed_workflow_node_outputs",
        sa.Column("node_output_id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("workflow_name", sa.String(), nullable=False),
        sa.Column("execution_id", sa.String(), nullable=False),
        sa.Column("node_name", sa.String(), nullable=False),
        sa.Column("node_type", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("outputs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "errors_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["completed_workflow_runs.run_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("node_output_id"),
    )
    op.create_index(
        op.f("ix_completed_workflow_node_outputs_execution_id"),
        "completed_workflow_node_outputs",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_completed_workflow_node_outputs_node_name"),
        "completed_workflow_node_outputs",
        ["node_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_completed_workflow_node_outputs_node_type"),
        "completed_workflow_node_outputs",
        ["node_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_completed_workflow_node_outputs_run_id"),
        "completed_workflow_node_outputs",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_completed_workflow_node_outputs_status"),
        "completed_workflow_node_outputs",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_completed_workflow_node_outputs_success"),
        "completed_workflow_node_outputs",
        ["success"],
        unique=False,
    )
    op.create_index(
        op.f("ix_completed_workflow_node_outputs_workflow_name"),
        "completed_workflow_node_outputs",
        ["workflow_name"],
        unique=False,
    )
    op.create_index(
        "idx_completed_node_outputs_execution_id",
        "completed_workflow_node_outputs",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        "idx_completed_node_outputs_node_name",
        "completed_workflow_node_outputs",
        ["node_name"],
        unique=False,
    )
    op.create_index(
        "idx_completed_node_outputs_node_type",
        "completed_workflow_node_outputs",
        ["node_type"],
        unique=False,
    )
    op.create_index(
        "idx_completed_node_outputs_run_id",
        "completed_workflow_node_outputs",
        ["run_id"],
        unique=False,
    )

    op.create_table(
        "completed_run_artifacts",
        sa.Column("artifact_id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("workflow_name", sa.String(), nullable=False),
        sa.Column("execution_id", sa.String(), nullable=False),
        sa.Column("artifact_type", sa.String(), nullable=False),
        sa.Column("artifact_name", sa.String(), nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["completed_workflow_runs.run_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("artifact_id"),
    )
    op.create_index(
        op.f("ix_completed_run_artifacts_artifact_type"),
        "completed_run_artifacts",
        ["artifact_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_completed_run_artifacts_execution_id"),
        "completed_run_artifacts",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_completed_run_artifacts_run_id"),
        "completed_run_artifacts",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_completed_run_artifacts_workflow_name"),
        "completed_run_artifacts",
        ["workflow_name"],
        unique=False,
    )
    op.create_index(
        "idx_completed_artifacts_execution_id",
        "completed_run_artifacts",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        "idx_completed_artifacts_run_id",
        "completed_run_artifacts",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "idx_completed_artifacts_type",
        "completed_run_artifacts",
        ["artifact_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_completed_artifacts_type", table_name="completed_run_artifacts")
    op.drop_index(
        "idx_completed_artifacts_run_id", table_name="completed_run_artifacts"
    )
    op.drop_index(
        "idx_completed_artifacts_execution_id", table_name="completed_run_artifacts"
    )
    op.drop_index(
        op.f("ix_completed_run_artifacts_workflow_name"),
        table_name="completed_run_artifacts",
    )
    op.drop_index(
        op.f("ix_completed_run_artifacts_run_id"),
        table_name="completed_run_artifacts",
    )
    op.drop_index(
        op.f("ix_completed_run_artifacts_execution_id"),
        table_name="completed_run_artifacts",
    )
    op.drop_index(
        op.f("ix_completed_run_artifacts_artifact_type"),
        table_name="completed_run_artifacts",
    )
    op.drop_table("completed_run_artifacts")

    op.drop_index(
        "idx_completed_node_outputs_run_id",
        table_name="completed_workflow_node_outputs",
    )
    op.drop_index(
        "idx_completed_node_outputs_node_type",
        table_name="completed_workflow_node_outputs",
    )
    op.drop_index(
        "idx_completed_node_outputs_node_name",
        table_name="completed_workflow_node_outputs",
    )
    op.drop_index(
        "idx_completed_node_outputs_execution_id",
        table_name="completed_workflow_node_outputs",
    )
    op.drop_index(
        op.f("ix_completed_workflow_node_outputs_workflow_name"),
        table_name="completed_workflow_node_outputs",
    )
    op.drop_index(
        op.f("ix_completed_workflow_node_outputs_success"),
        table_name="completed_workflow_node_outputs",
    )
    op.drop_index(
        op.f("ix_completed_workflow_node_outputs_status"),
        table_name="completed_workflow_node_outputs",
    )
    op.drop_index(
        op.f("ix_completed_workflow_node_outputs_run_id"),
        table_name="completed_workflow_node_outputs",
    )
    op.drop_index(
        op.f("ix_completed_workflow_node_outputs_node_type"),
        table_name="completed_workflow_node_outputs",
    )
    op.drop_index(
        op.f("ix_completed_workflow_node_outputs_node_name"),
        table_name="completed_workflow_node_outputs",
    )
    op.drop_index(
        op.f("ix_completed_workflow_node_outputs_execution_id"),
        table_name="completed_workflow_node_outputs",
    )
    op.drop_table("completed_workflow_node_outputs")

    op.drop_index(
        "idx_completed_runs_workflow_completed_at",
        table_name="completed_workflow_runs",
    )
    op.drop_index("idx_completed_runs_success", table_name="completed_workflow_runs")
    op.drop_index("idx_completed_runs_status", table_name="completed_workflow_runs")
    op.drop_index(
        "idx_completed_runs_execution_id", table_name="completed_workflow_runs"
    )
    op.drop_index("idx_completed_runs_created_at", table_name="completed_workflow_runs")
    op.drop_index(
        op.f("ix_completed_workflow_runs_workflow_name"),
        table_name="completed_workflow_runs",
    )
    op.drop_index(
        op.f("ix_completed_workflow_runs_workflow_id"),
        table_name="completed_workflow_runs",
    )
    op.drop_index(
        op.f("ix_completed_workflow_runs_success"),
        table_name="completed_workflow_runs",
    )
    op.drop_index(
        op.f("ix_completed_workflow_runs_status"),
        table_name="completed_workflow_runs",
    )
    op.drop_index(
        op.f("ix_completed_workflow_runs_started_at"),
        table_name="completed_workflow_runs",
    )
    op.drop_index(
        op.f("ix_completed_workflow_runs_runtime_id"),
        table_name="completed_workflow_runs",
    )
    op.drop_index(
        op.f("ix_completed_workflow_runs_execution_id"),
        table_name="completed_workflow_runs",
    )
    op.drop_index(
        op.f("ix_completed_workflow_runs_completed_at"),
        table_name="completed_workflow_runs",
    )
    op.drop_table("completed_workflow_runs")
