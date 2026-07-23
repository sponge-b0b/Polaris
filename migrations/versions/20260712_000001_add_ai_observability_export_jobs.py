"""add_ai_observability_export_jobs

Revision ID: 7b9f2d6a4c31
Revises: 48812a306b31
Create Date: 2026-07-12 00:00:01.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7b9f2d6a4c31"
down_revision: str | None = "48812a306b31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_observability_export_jobs",
        sa.Column("export_job_id", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("observation_type", sa.String(), nullable=False),
        sa.Column("observation_name", sa.String(), nullable=False),
        sa.Column("observation_family", sa.String(), nullable=False),
        sa.Column("observation_status", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("trace_id", sa.String(), nullable=True),
        sa.Column("span_id", sa.String(), nullable=True),
        sa.Column("workflow_name", sa.String(), nullable=True),
        sa.Column("execution_id", sa.String(), nullable=True),
        sa.Column("runtime_id", sa.String(), nullable=True),
        sa.Column("node_name", sa.String(), nullable=True),
        sa.Column("observation_id", sa.String(), nullable=True),
        sa.Column("parent_observation_id", sa.String(), nullable=True),
        sa.Column("dataset_id", sa.String(), nullable=True),
        sa.Column("case_id", sa.String(), nullable=True),
        sa.Column("run_id", sa.String(), nullable=True),
        sa.Column("external_trace_id", sa.String(), nullable=True),
        sa.Column("external_observation_id", sa.String(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("retry_after_seconds", sa.Float(), nullable=True),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_ai_observability_export_jobs_attempt_count_non_negative",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name="ck_ai_observability_export_jobs_payload_object",
        ),
        sa.CheckConstraint(
            "max_attempts > 0",
            name="ck_ai_observability_export_jobs_max_attempts_positive",
        ),
        sa.CheckConstraint(
            "retry_after_seconds IS NULL OR retry_after_seconds >= 0.0",
            name="ck_ai_observability_export_jobs_retry_after_non_negative",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'exported', 'failed', 'skipped')",
            name="ck_ai_observability_export_jobs_status",
        ),
        sa.PrimaryKeyConstraint("export_job_id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_ai_observability_export_jobs_idempotency_key",
        ),
    )
    op.create_index(
        "idx_ai_observability_export_jobs_dataset_case_run",
        "ai_observability_export_jobs",
        ["dataset_id", "case_id", "run_id"],
        unique=False,
    )
    op.create_index(
        "idx_ai_observability_export_jobs_observation_status",
        "ai_observability_export_jobs",
        ["observation_type", "status"],
        unique=False,
    )
    op.create_index(
        "idx_ai_observability_export_jobs_status_available_at",
        "ai_observability_export_jobs",
        ["status", "available_at"],
        unique=False,
    )
    op.create_index(
        "idx_ai_observability_export_jobs_trace_span",
        "ai_observability_export_jobs",
        ["trace_id", "span_id"],
        unique=False,
    )
    op.create_index(
        "idx_ai_observability_export_jobs_workflow_execution",
        "ai_observability_export_jobs",
        ["workflow_name", "execution_id"],
        unique=False,
    )
    for column_name in (
        "available_at",
        "case_id",
        "dataset_id",
        "execution_id",
        "external_observation_id",
        "external_trace_id",
        "idempotency_key",
        "node_name",
        "observation_family",
        "observation_id",
        "observation_status",
        "observation_type",
        "parent_observation_id",
        "run_id",
        "runtime_id",
        "span_id",
        "status",
        "trace_id",
        "workflow_name",
    ):
        op.create_index(
            op.f(f"ix_ai_observability_export_jobs_{column_name}"),
            "ai_observability_export_jobs",
            [column_name],
            unique=False,
        )


def downgrade() -> None:
    for column_name in (
        "workflow_name",
        "trace_id",
        "status",
        "span_id",
        "runtime_id",
        "run_id",
        "parent_observation_id",
        "observation_type",
        "observation_status",
        "observation_id",
        "observation_family",
        "node_name",
        "idempotency_key",
        "external_trace_id",
        "external_observation_id",
        "execution_id",
        "dataset_id",
        "case_id",
        "available_at",
    ):
        op.drop_index(
            op.f(f"ix_ai_observability_export_jobs_{column_name}"),
            table_name="ai_observability_export_jobs",
        )
    op.drop_index(
        "idx_ai_observability_export_jobs_workflow_execution",
        table_name="ai_observability_export_jobs",
    )
    op.drop_index(
        "idx_ai_observability_export_jobs_trace_span",
        table_name="ai_observability_export_jobs",
    )
    op.drop_index(
        "idx_ai_observability_export_jobs_status_available_at",
        table_name="ai_observability_export_jobs",
    )
    op.drop_index(
        "idx_ai_observability_export_jobs_observation_status",
        table_name="ai_observability_export_jobs",
    )
    op.drop_index(
        "idx_ai_observability_export_jobs_dataset_case_run",
        table_name="ai_observability_export_jobs",
    )
    op.drop_table("ai_observability_export_jobs")
