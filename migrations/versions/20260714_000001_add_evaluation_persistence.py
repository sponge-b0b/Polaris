"""add_evaluation_persistence

Revision ID: 8c0d1e2f3a4b
Revises: 7b9f2d6a4c31
Create Date: 2026-07-14 00:00:01.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "8c0d1e2f3a4b"
down_revision: str | None = "7b9f2d6a4c31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evaluation_datasets",
        sa.Column("dataset_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("target_type", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "source_lineage",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("deterministic_fixture_uri", sa.String(), nullable=True),
        sa.Column(
            "threshold_profile",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("active", sa.Boolean(), nullable=False),
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
            "jsonb_typeof(tags) = 'array'",
            name="ck_evaluation_datasets_tags_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(source_lineage) = 'array'",
            name="ck_evaluation_datasets_source_lineage_array",
        ),
        sa.CheckConstraint(
            "threshold_profile IS NULL OR jsonb_typeof(threshold_profile) = 'object'",
            name="ck_evaluation_datasets_threshold_profile_object",
        ),
        sa.PrimaryKeyConstraint("dataset_id"),
        sa.UniqueConstraint(
            "name", "version", name="uq_evaluation_datasets_name_version"
        ),
    )
    op.create_index(
        op.f("ix_evaluation_datasets_name"),
        "evaluation_datasets",
        ["name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_datasets_target_type"),
        "evaluation_datasets",
        ["target_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_datasets_version"),
        "evaluation_datasets",
        ["version"],
        unique=False,
    )

    op.create_table(
        "evaluation_cases",
        sa.Column("case_id", sa.String(), nullable=False),
        sa.Column("dataset_id", sa.String(), nullable=True),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("actual_output", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=True),
        sa.Column("rubric", sa.Text(), nullable=True),
        sa.Column(
            "source_record_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("workflow_execution_id", sa.String(), nullable=True),
        sa.Column("langfuse_trace_id", sa.String(), nullable=True),
        sa.Column("langfuse_observation_id", sa.String(), nullable=True),
        sa.Column(
            "retrieval_context",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "citation_context_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
            "expected_output IS NOT NULL OR rubric IS NOT NULL",
            name="ck_evaluation_cases_expected_output_or_rubric",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(citation_context_ids) = 'array'",
            name="ck_evaluation_cases_citation_context_ids_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(retrieval_context) = 'array'",
            name="ck_evaluation_cases_retrieval_context_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(source_record_ids) = 'array'",
            name="ck_evaluation_cases_source_record_ids_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(tags) = 'array'",
            name="ck_evaluation_cases_tags_array",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["evaluation_datasets.dataset_id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("case_id"),
    )
    op.create_index(
        op.f("ix_evaluation_cases_dataset_id"),
        "evaluation_cases",
        ["dataset_id"],
        unique=False,
    )
    op.create_index(
        "idx_evaluation_cases_dataset_target",
        "evaluation_cases",
        ["dataset_id", "target_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_cases_langfuse_observation_id"),
        "evaluation_cases",
        ["langfuse_observation_id"],
        unique=False,
    )
    op.create_index(
        "idx_evaluation_cases_langfuse_trace_observation",
        "evaluation_cases",
        ["langfuse_trace_id", "langfuse_observation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_cases_langfuse_trace_id"),
        "evaluation_cases",
        ["langfuse_trace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_cases_target_type"),
        "evaluation_cases",
        ["target_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_cases_workflow_execution_id"),
        "evaluation_cases",
        ["workflow_execution_id"],
        unique=False,
    )

    op.create_table(
        "evaluation_runs",
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("dataset_id", sa.String(), nullable=True),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("evaluator_provider", sa.String(), nullable=False),
        sa.Column("evaluator_model", sa.String(), nullable=False),
        sa.Column("case_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("langfuse_projection_status", sa.String(), nullable=False),
        sa.Column("langfuse_export_job_id", sa.String(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "error_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True
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
            "jsonb_typeof(case_ids) = 'array'",
            name="ck_evaluation_runs_case_ids_array",
        ),
        sa.CheckConstraint(
            "langfuse_projection_status IN ('pending', 'projected', 'failed', 'skipped')",  # noqa: E501
            name="ck_evaluation_runs_langfuse_projection_status",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'passed', 'failed', 'errored', 'skipped')",  # noqa: E501
            name="ck_evaluation_runs_status",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["evaluation_datasets.dataset_id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index(
        op.f("ix_evaluation_runs_dataset_id"),
        "evaluation_runs",
        ["dataset_id"],
        unique=False,
    )
    op.create_index(
        "idx_evaluation_runs_dataset_status",
        "evaluation_runs",
        ["dataset_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_runs_evaluator_model"),
        "evaluation_runs",
        ["evaluator_model"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_runs_evaluator_provider"),
        "evaluation_runs",
        ["evaluator_provider"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_runs_langfuse_export_job_id"),
        "evaluation_runs",
        ["langfuse_export_job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_runs_langfuse_projection_status"),
        "evaluation_runs",
        ["langfuse_projection_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_runs_started_at"),
        "evaluation_runs",
        ["started_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_runs_status"), "evaluation_runs", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_evaluation_runs_target_type"),
        "evaluation_runs",
        ["target_type"],
        unique=False,
    )
    op.create_index(
        "idx_evaluation_runs_target_started_at",
        "evaluation_runs",
        ["target_type", "started_at"],
        unique=False,
    )

    op.create_table(
        "evaluation_metric_results",
        sa.Column("metric_result_id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("case_id", sa.String(), nullable=False),
        sa.Column("metric_name", sa.String(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=True),
        sa.Column("threshold_version", sa.String(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("evaluator_provider", sa.String(), nullable=False),
        sa.Column("evaluator_model", sa.String(), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "error_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("langfuse_projection_status", sa.String(), nullable=False),
        sa.Column("langfuse_export_job_id", sa.String(), nullable=True),
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
            "duration_ms IS NULL OR duration_ms >= 0.0",
            name="ck_evaluation_metric_results_duration_non_negative",
        ),
        sa.CheckConstraint(
            "error_details IS NULL OR jsonb_typeof(error_details) = 'object'",
            name="ck_evaluation_metric_results_error_details_object",
        ),
        sa.CheckConstraint(
            "langfuse_projection_status IN ('pending', 'projected', 'failed', 'skipped')",  # noqa: E501
            name="ck_evaluation_metric_results_langfuse_projection_status",
        ),
        sa.CheckConstraint(
            "score >= 0.0 AND score <= 1.0",
            name="ck_evaluation_metric_results_score_range",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'passed', 'failed', 'errored', 'skipped')",  # noqa: E501
            name="ck_evaluation_metric_results_status",
        ),
        sa.CheckConstraint(
            "threshold IS NULL OR (threshold >= 0.0 AND threshold <= 1.0)",
            name="ck_evaluation_metric_results_threshold_range",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"], ["evaluation_cases.case_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["evaluation_runs.run_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("metric_result_id"),
        sa.UniqueConstraint(
            "run_id",
            "case_id",
            "metric_name",
            name="uq_evaluation_metric_results_run_case_metric",
        ),
    )
    op.create_index(
        op.f("ix_evaluation_metric_results_case_id"),
        "evaluation_metric_results",
        ["case_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_metric_results_evaluator_model"),
        "evaluation_metric_results",
        ["evaluator_model"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_metric_results_evaluator_provider"),
        "evaluation_metric_results",
        ["evaluator_provider"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_metric_results_langfuse_export_job_id"),
        "evaluation_metric_results",
        ["langfuse_export_job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_metric_results_langfuse_projection_status"),
        "evaluation_metric_results",
        ["langfuse_projection_status"],
        unique=False,
    )
    op.create_index(
        "idx_evaluation_metric_results_metric_passed",
        "evaluation_metric_results",
        ["metric_name", "passed"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_metric_results_metric_name"),
        "evaluation_metric_results",
        ["metric_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_metric_results_passed"),
        "evaluation_metric_results",
        ["passed"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_metric_results_run_id"),
        "evaluation_metric_results",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "idx_evaluation_metric_results_run_status",
        "evaluation_metric_results",
        ["run_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_metric_results_status"),
        "evaluation_metric_results",
        ["status"],
        unique=False,
    )

    op.create_table(
        "evaluation_artifacts",
        sa.Column("artifact_id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("case_id", sa.String(), nullable=True),
        sa.Column("artifact_type", sa.String(), nullable=False),
        sa.Column("uri", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "payload IS NULL OR jsonb_typeof(payload) = 'object'",
            name="ck_evaluation_artifacts_payload_object",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"], ["evaluation_cases.case_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["evaluation_runs.run_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("artifact_id"),
    )
    op.create_index(
        op.f("ix_evaluation_artifacts_artifact_type"),
        "evaluation_artifacts",
        ["artifact_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_artifacts_case_id"),
        "evaluation_artifacts",
        ["case_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_artifacts_run_id"),
        "evaluation_artifacts",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "idx_evaluation_artifacts_run_type",
        "evaluation_artifacts",
        ["run_id", "artifact_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_evaluation_artifacts_run_type", table_name="evaluation_artifacts"
    )
    op.drop_index(
        op.f("ix_evaluation_artifacts_run_id"), table_name="evaluation_artifacts"
    )
    op.drop_index(
        op.f("ix_evaluation_artifacts_case_id"), table_name="evaluation_artifacts"
    )
    op.drop_index(
        op.f("ix_evaluation_artifacts_artifact_type"), table_name="evaluation_artifacts"
    )
    op.drop_table("evaluation_artifacts")

    op.drop_index(
        op.f("ix_evaluation_metric_results_status"),
        table_name="evaluation_metric_results",
    )
    op.drop_index(
        "idx_evaluation_metric_results_run_status",
        table_name="evaluation_metric_results",
    )
    op.drop_index(
        op.f("ix_evaluation_metric_results_run_id"),
        table_name="evaluation_metric_results",
    )
    op.drop_index(
        op.f("ix_evaluation_metric_results_passed"),
        table_name="evaluation_metric_results",
    )
    op.drop_index(
        op.f("ix_evaluation_metric_results_metric_name"),
        table_name="evaluation_metric_results",
    )
    op.drop_index(
        "idx_evaluation_metric_results_metric_passed",
        table_name="evaluation_metric_results",
    )
    op.drop_index(
        op.f("ix_evaluation_metric_results_langfuse_projection_status"),
        table_name="evaluation_metric_results",
    )
    op.drop_index(
        op.f("ix_evaluation_metric_results_langfuse_export_job_id"),
        table_name="evaluation_metric_results",
    )
    op.drop_index(
        op.f("ix_evaluation_metric_results_evaluator_provider"),
        table_name="evaluation_metric_results",
    )
    op.drop_index(
        op.f("ix_evaluation_metric_results_evaluator_model"),
        table_name="evaluation_metric_results",
    )
    op.drop_index(
        op.f("ix_evaluation_metric_results_case_id"),
        table_name="evaluation_metric_results",
    )
    op.drop_table("evaluation_metric_results")

    op.drop_index("idx_evaluation_runs_target_started_at", table_name="evaluation_runs")
    op.drop_index(op.f("ix_evaluation_runs_target_type"), table_name="evaluation_runs")
    op.drop_index(op.f("ix_evaluation_runs_status"), table_name="evaluation_runs")
    op.drop_index(op.f("ix_evaluation_runs_started_at"), table_name="evaluation_runs")
    op.drop_index(
        op.f("ix_evaluation_runs_langfuse_projection_status"),
        table_name="evaluation_runs",
    )
    op.drop_index(
        op.f("ix_evaluation_runs_langfuse_export_job_id"), table_name="evaluation_runs"
    )
    op.drop_index(
        op.f("ix_evaluation_runs_evaluator_provider"), table_name="evaluation_runs"
    )
    op.drop_index(
        op.f("ix_evaluation_runs_evaluator_model"), table_name="evaluation_runs"
    )
    op.drop_index("idx_evaluation_runs_dataset_status", table_name="evaluation_runs")
    op.drop_index(op.f("ix_evaluation_runs_dataset_id"), table_name="evaluation_runs")
    op.drop_table("evaluation_runs")

    op.drop_index(
        op.f("ix_evaluation_cases_workflow_execution_id"), table_name="evaluation_cases"
    )
    op.drop_index(
        op.f("ix_evaluation_cases_target_type"), table_name="evaluation_cases"
    )
    op.drop_index(
        op.f("ix_evaluation_cases_langfuse_trace_id"), table_name="evaluation_cases"
    )
    op.drop_index(
        "idx_evaluation_cases_langfuse_trace_observation", table_name="evaluation_cases"
    )
    op.drop_index(
        op.f("ix_evaluation_cases_langfuse_observation_id"),
        table_name="evaluation_cases",
    )
    op.drop_index("idx_evaluation_cases_dataset_target", table_name="evaluation_cases")
    op.drop_index(op.f("ix_evaluation_cases_dataset_id"), table_name="evaluation_cases")
    op.drop_table("evaluation_cases")

    op.drop_index(
        op.f("ix_evaluation_datasets_version"), table_name="evaluation_datasets"
    )
    op.drop_index(
        op.f("ix_evaluation_datasets_target_type"), table_name="evaluation_datasets"
    )
    op.drop_index(op.f("ix_evaluation_datasets_name"), table_name="evaluation_datasets")
    op.drop_table("evaluation_datasets")
