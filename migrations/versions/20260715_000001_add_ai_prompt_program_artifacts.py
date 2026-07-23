"""add_ai_prompt_program_artifacts

Revision ID: 9d1e2f3a4b5c
Revises: 8c0d1e2f3a4b
Create Date: 2026-07-15 00:00:01.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9d1e2f3a4b5c"
down_revision: str | None = "8c0d1e2f3a4b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_prompt_program_artifacts",
        sa.Column("artifact_id", sa.String(), nullable=False),
        sa.Column("artifact_type", sa.String(), nullable=False),
        sa.Column("artifact_name", sa.String(), nullable=False),
        sa.Column("artifact_version", sa.String(), nullable=False),
        sa.Column("target_component", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("provider_name", sa.String(), nullable=False),
        sa.Column("prompt_reference", sa.Text(), nullable=False),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("evaluation_dataset_id", sa.String(), nullable=True),
        sa.Column("evaluation_run_id", sa.String(), nullable=True),
        sa.Column(
            "deepeval_score_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("langfuse_trace_id", sa.String(), nullable=True),
        sa.Column("approval_status", sa.String(), nullable=False),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "artifact_type IN ("
            "'source_controlled_prompt', "
            "'langfuse_prompt', "
            "'dspy_program', "
            "'dspy_compiled_prompt'"
            ")",
            name="ck_ai_prompt_program_artifacts_type",
        ),
        sa.CheckConstraint(
            "approval_status IN ('draft', 'approved', 'rejected', 'inactive')",
            name="ck_ai_prompt_program_artifacts_approval_status",
        ),
        sa.CheckConstraint(
            "deepeval_score_summary IS NULL OR "
            "jsonb_typeof(deepeval_score_summary) = 'object'",
            name="ck_ai_prompt_program_artifacts_deepeval_summary_object",
        ),
        sa.CheckConstraint(
            "approval_status != 'approved' OR "
            "(approved_by IS NOT NULL AND approved_at IS NOT NULL)",
            name="ck_ai_prompt_program_artifacts_approved_identity",
        ),
        sa.CheckConstraint(
            "active = false OR approval_status = 'approved'",
            name="ck_ai_prompt_program_artifacts_active_requires_approved",
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_dataset_id"],
            ["evaluation_datasets.dataset_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_run_id"],
            ["evaluation_runs.run_id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("artifact_id"),
        sa.UniqueConstraint(
            "artifact_name",
            "artifact_version",
            "target_component",
            name="uq_ai_prompt_program_artifacts_name_version_target",
        ),
    )
    for column_name in (
        "active",
        "approval_status",
        "artifact_name",
        "artifact_type",
        "artifact_version",
        "evaluation_dataset_id",
        "evaluation_run_id",
        "langfuse_trace_id",
        "model_name",
        "prompt_hash",
        "provider_name",
        "source",
        "target_component",
    ):
        op.create_index(
            op.f(f"ix_ai_prompt_program_artifacts_{column_name}"),
            "ai_prompt_program_artifacts",
            [column_name],
            unique=False,
        )
    op.create_index(
        "idx_ai_prompt_program_artifacts_active_target",
        "ai_prompt_program_artifacts",
        ["target_component", "artifact_type", "active"],
        unique=False,
    )
    op.create_index(
        "idx_ai_prompt_program_artifacts_evaluation",
        "ai_prompt_program_artifacts",
        ["evaluation_dataset_id", "evaluation_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_ai_prompt_program_artifacts_evaluation",
        table_name="ai_prompt_program_artifacts",
    )
    op.drop_index(
        "idx_ai_prompt_program_artifacts_active_target",
        table_name="ai_prompt_program_artifacts",
    )
    for column_name in reversed(
        (
            "active",
            "approval_status",
            "artifact_name",
            "artifact_type",
            "artifact_version",
            "evaluation_dataset_id",
            "evaluation_run_id",
            "langfuse_trace_id",
            "model_name",
            "prompt_hash",
            "provider_name",
            "source",
            "target_component",
        )
    ):
        op.drop_index(
            op.f(f"ix_ai_prompt_program_artifacts_{column_name}"),
            table_name="ai_prompt_program_artifacts",
        )
    op.drop_table("ai_prompt_program_artifacts")
