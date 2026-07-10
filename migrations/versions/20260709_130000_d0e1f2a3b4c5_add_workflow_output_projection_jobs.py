"""add workflow output projection jobs

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-07-09 13:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d0e1f2a3b4c5"
down_revision: str | None = "c9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_PROJECTION_STATUS_CHECK = (
    "status IN ('pending', 'running', 'succeeded', 'failed', 'skipped')"
)


def upgrade() -> None:
    op.create_table(
        "workflow_output_projection_jobs",
        sa.Column("projection_job_id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("workflow_name", sa.String(), nullable=False),
        sa.Column("execution_id", sa.String(), nullable=False),
        sa.Column("node_name", sa.String(), nullable=False),
        sa.Column("projector_name", sa.String(), nullable=False),
        sa.Column("output_contract", sa.String(), nullable=False),
        sa.Column("output_schema_version", sa.Integer(), nullable=False),
        sa.Column("source_fingerprint", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            _PROJECTION_STATUS_CHECK,
            name="ck_workflow_output_projection_jobs_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_workflow_output_projection_jobs_attempt_count_non_negative",
        ),
        sa.CheckConstraint(
            "output_schema_version > 0",
            name="ck_workflow_output_projection_jobs_schema_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["completed_workflow_runs.run_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("projection_job_id"),
        sa.UniqueConstraint(
            "run_id",
            "projector_name",
            "node_name",
            "source_fingerprint",
            name="uq_workflow_output_projection_jobs_source",
        ),
    )
    op.create_index(
        op.f("ix_workflow_output_projection_jobs_execution_id"),
        "workflow_output_projection_jobs",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_output_projection_jobs_node_name"),
        "workflow_output_projection_jobs",
        ["node_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_output_projection_jobs_output_contract"),
        "workflow_output_projection_jobs",
        ["output_contract"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_output_projection_jobs_output_schema_version"),
        "workflow_output_projection_jobs",
        ["output_schema_version"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_output_projection_jobs_projector_name"),
        "workflow_output_projection_jobs",
        ["projector_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_output_projection_jobs_run_id"),
        "workflow_output_projection_jobs",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_output_projection_jobs_status"),
        "workflow_output_projection_jobs",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_output_projection_jobs_workflow_name"),
        "workflow_output_projection_jobs",
        ["workflow_name"],
        unique=False,
    )
    op.create_index(
        "idx_workflow_projection_jobs_status_created_at",
        "workflow_output_projection_jobs",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_workflow_projection_jobs_workflow_execution",
        "workflow_output_projection_jobs",
        ["workflow_name", "execution_id"],
        unique=False,
    )
    op.create_index(
        "idx_workflow_projection_jobs_projector_node",
        "workflow_output_projection_jobs",
        ["projector_name", "node_name"],
        unique=False,
    )
    op.create_index(
        "idx_workflow_projection_jobs_pending_failed",
        "workflow_output_projection_jobs",
        ["status", "updated_at"],
        unique=False,
    )
    op.create_index(
        "idx_workflow_projection_jobs_contract_version",
        "workflow_output_projection_jobs",
        ["output_contract", "output_schema_version"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_workflow_projection_jobs_contract_version",
        table_name="workflow_output_projection_jobs",
    )
    op.drop_index(
        "idx_workflow_projection_jobs_pending_failed",
        table_name="workflow_output_projection_jobs",
    )
    op.drop_index(
        "idx_workflow_projection_jobs_projector_node",
        table_name="workflow_output_projection_jobs",
    )
    op.drop_index(
        "idx_workflow_projection_jobs_workflow_execution",
        table_name="workflow_output_projection_jobs",
    )
    op.drop_index(
        "idx_workflow_projection_jobs_status_created_at",
        table_name="workflow_output_projection_jobs",
    )
    op.drop_index(
        op.f("ix_workflow_output_projection_jobs_workflow_name"),
        table_name="workflow_output_projection_jobs",
    )
    op.drop_index(
        op.f("ix_workflow_output_projection_jobs_status"),
        table_name="workflow_output_projection_jobs",
    )
    op.drop_index(
        op.f("ix_workflow_output_projection_jobs_run_id"),
        table_name="workflow_output_projection_jobs",
    )
    op.drop_index(
        op.f("ix_workflow_output_projection_jobs_projector_name"),
        table_name="workflow_output_projection_jobs",
    )
    op.drop_index(
        op.f("ix_workflow_output_projection_jobs_output_schema_version"),
        table_name="workflow_output_projection_jobs",
    )
    op.drop_index(
        op.f("ix_workflow_output_projection_jobs_output_contract"),
        table_name="workflow_output_projection_jobs",
    )
    op.drop_index(
        op.f("ix_workflow_output_projection_jobs_node_name"),
        table_name="workflow_output_projection_jobs",
    )
    op.drop_index(
        op.f("ix_workflow_output_projection_jobs_execution_id"),
        table_name="workflow_output_projection_jobs",
    )
    op.drop_table("workflow_output_projection_jobs")
