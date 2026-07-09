"""add backtest persistence tables

Revision ID: b7c2d4e6f8a1
Revises: 2fa484dd367f
Create Date: 2026-06-14 15:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7c2d4e6f8a1"
down_revision: str | None = "2fa484dd367f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "backtest_scenarios",
        sa.Column("scenario_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("workflow_name", sa.String(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("symbols", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("benchmark_symbol", sa.String(), nullable=False),
        sa.Column("initial_cash", sa.Numeric(38, 18), nullable=False),
        sa.Column("provider_profile", sa.String(), nullable=False),
        sa.Column(
            "initial_positions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "expected_outcomes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.PrimaryKeyConstraint("scenario_id"),
    )
    op.create_index(
        op.f("ix_backtest_scenarios_benchmark_symbol"),
        "backtest_scenarios",
        ["benchmark_symbol"],
        unique=False,
    )
    op.create_index(
        op.f("ix_backtest_scenarios_end_date"),
        "backtest_scenarios",
        ["end_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_backtest_scenarios_provider_profile"),
        "backtest_scenarios",
        ["provider_profile"],
        unique=False,
    )
    op.create_index(
        op.f("ix_backtest_scenarios_start_date"),
        "backtest_scenarios",
        ["start_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_backtest_scenarios_workflow_name"),
        "backtest_scenarios",
        ["workflow_name"],
        unique=False,
    )
    op.create_index(
        "idx_backtest_scenarios_workflow_dates",
        "backtest_scenarios",
        ["workflow_name", "start_date", "end_date"],
        unique=False,
    )

    op.create_table(
        "backtest_runs",
        sa.Column("backtest_run_id", sa.String(), nullable=False),
        sa.Column("scenario_id", sa.String(), nullable=False),
        sa.Column("workflow_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["scenario_id"], ["backtest_scenarios.scenario_id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("backtest_run_id"),
    )
    op.create_index(
        op.f("ix_backtest_runs_completed_at"),
        "backtest_runs",
        ["completed_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_backtest_runs_scenario_id"),
        "backtest_runs",
        ["scenario_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_backtest_runs_started_at"),
        "backtest_runs",
        ["started_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_backtest_runs_status"), "backtest_runs", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_backtest_runs_success"), "backtest_runs", ["success"], unique=False
    )
    op.create_index(
        op.f("ix_backtest_runs_workflow_name"),
        "backtest_runs",
        ["workflow_name"],
        unique=False,
    )
    op.create_index(
        "idx_backtest_runs_workflow_started_at",
        "backtest_runs",
        ["workflow_name", "started_at"],
        unique=False,
    )

    op.create_table(
        "backtest_steps",
        sa.Column("step_id", sa.String(), nullable=False),
        sa.Column("backtest_run_id", sa.String(), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("workflow_run_id", sa.String(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column(
            "node_output_keys", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["backtest_run_id"], ["backtest_runs.backtest_run_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("step_id"),
        sa.UniqueConstraint(
            "backtest_run_id", "step_index", name="uq_backtest_steps_run_step_index"
        ),
    )
    op.create_index(
        op.f("ix_backtest_steps_backtest_run_id"),
        "backtest_steps",
        ["backtest_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_backtest_steps_success"), "backtest_steps", ["success"], unique=False
    )
    op.create_index(
        op.f("ix_backtest_steps_timestamp"),
        "backtest_steps",
        ["timestamp"],
        unique=False,
    )
    op.create_index(
        op.f("ix_backtest_steps_workflow_run_id"),
        "backtest_steps",
        ["workflow_run_id"],
        unique=False,
    )
    op.create_index(
        "idx_backtest_steps_run_timestamp",
        "backtest_steps",
        ["backtest_run_id", "timestamp"],
        unique=False,
    )

    op.create_table(
        "backtest_portfolio_snapshots",
        sa.Column("snapshot_id", sa.String(), nullable=False),
        sa.Column("backtest_run_id", sa.String(), nullable=False),
        sa.Column("step_id", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cash", sa.Numeric(38, 18), nullable=False),
        sa.Column("equity", sa.Numeric(38, 18), nullable=False),
        sa.Column("market_value", sa.Numeric(38, 18), nullable=False),
        sa.Column("positions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["backtest_run_id"], ["backtest_runs.backtest_run_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["step_id"], ["backtest_steps.step_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("snapshot_id"),
    )
    op.create_index(
        op.f("ix_backtest_portfolio_snapshots_backtest_run_id"),
        "backtest_portfolio_snapshots",
        ["backtest_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_backtest_portfolio_snapshots_step_id"),
        "backtest_portfolio_snapshots",
        ["step_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_backtest_portfolio_snapshots_timestamp"),
        "backtest_portfolio_snapshots",
        ["timestamp"],
        unique=False,
    )

    op.create_table(
        "backtest_fills",
        sa.Column("fill_id", sa.String(), nullable=False),
        sa.Column("backtest_run_id", sa.String(), nullable=False),
        sa.Column("step_id", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("side", sa.String(), nullable=False),
        sa.Column("quantity", sa.Numeric(38, 18), nullable=False),
        sa.Column("price", sa.Numeric(38, 18), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(38, 18), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["backtest_run_id"], ["backtest_runs.backtest_run_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["step_id"], ["backtest_steps.step_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("fill_id"),
    )
    op.create_index(
        op.f("ix_backtest_fills_backtest_run_id"),
        "backtest_fills",
        ["backtest_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_backtest_fills_side"), "backtest_fills", ["side"], unique=False
    )
    op.create_index(
        op.f("ix_backtest_fills_status"), "backtest_fills", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_backtest_fills_step_id"), "backtest_fills", ["step_id"], unique=False
    )
    op.create_index(
        op.f("ix_backtest_fills_symbol"), "backtest_fills", ["symbol"], unique=False
    )
    op.create_index(
        op.f("ix_backtest_fills_timestamp"),
        "backtest_fills",
        ["timestamp"],
        unique=False,
    )
    op.create_index(
        "idx_backtest_fills_run_symbol",
        "backtest_fills",
        ["backtest_run_id", "symbol"],
        unique=False,
    )

    op.create_table(
        "backtest_metrics",
        sa.Column("metric_id", sa.String(), nullable=False),
        sa.Column("backtest_run_id", sa.String(), nullable=False),
        sa.Column("metric_name", sa.String(), nullable=False),
        sa.Column("metric_value", sa.Numeric(38, 18), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["backtest_run_id"], ["backtest_runs.backtest_run_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("metric_id"),
        sa.UniqueConstraint(
            "backtest_run_id", "metric_name", name="uq_backtest_metrics_run_metric"
        ),
    )
    op.create_index(
        op.f("ix_backtest_metrics_backtest_run_id"),
        "backtest_metrics",
        ["backtest_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_backtest_metrics_metric_name"),
        "backtest_metrics",
        ["metric_name"],
        unique=False,
    )

    op.create_table(
        "backtest_artifacts",
        sa.Column("artifact_id", sa.String(), nullable=False),
        sa.Column("backtest_run_id", sa.String(), nullable=False),
        sa.Column("artifact_format", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["backtest_run_id"], ["backtest_runs.backtest_run_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("artifact_id"),
        sa.UniqueConstraint(
            "backtest_run_id",
            "artifact_format",
            name="uq_backtest_artifacts_run_format",
        ),
    )
    op.create_index(
        op.f("ix_backtest_artifacts_artifact_format"),
        "backtest_artifacts",
        ["artifact_format"],
        unique=False,
    )
    op.create_index(
        op.f("ix_backtest_artifacts_backtest_run_id"),
        "backtest_artifacts",
        ["backtest_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_backtest_artifacts_backtest_run_id"), table_name="backtest_artifacts"
    )
    op.drop_index(
        op.f("ix_backtest_artifacts_artifact_format"), table_name="backtest_artifacts"
    )
    op.drop_table("backtest_artifacts")
    op.drop_index(
        op.f("ix_backtest_metrics_metric_name"), table_name="backtest_metrics"
    )
    op.drop_index(
        op.f("ix_backtest_metrics_backtest_run_id"), table_name="backtest_metrics"
    )
    op.drop_table("backtest_metrics")
    op.drop_index("idx_backtest_fills_run_symbol", table_name="backtest_fills")
    op.drop_index(op.f("ix_backtest_fills_timestamp"), table_name="backtest_fills")
    op.drop_index(op.f("ix_backtest_fills_symbol"), table_name="backtest_fills")
    op.drop_index(op.f("ix_backtest_fills_step_id"), table_name="backtest_fills")
    op.drop_index(op.f("ix_backtest_fills_status"), table_name="backtest_fills")
    op.drop_index(op.f("ix_backtest_fills_side"), table_name="backtest_fills")
    op.drop_index(
        op.f("ix_backtest_fills_backtest_run_id"), table_name="backtest_fills"
    )
    op.drop_table("backtest_fills")
    op.drop_index(
        op.f("ix_backtest_portfolio_snapshots_timestamp"),
        table_name="backtest_portfolio_snapshots",
    )
    op.drop_index(
        op.f("ix_backtest_portfolio_snapshots_step_id"),
        table_name="backtest_portfolio_snapshots",
    )
    op.drop_index(
        op.f("ix_backtest_portfolio_snapshots_backtest_run_id"),
        table_name="backtest_portfolio_snapshots",
    )
    op.drop_table("backtest_portfolio_snapshots")
    op.drop_index("idx_backtest_steps_run_timestamp", table_name="backtest_steps")
    op.drop_index(
        op.f("ix_backtest_steps_workflow_run_id"), table_name="backtest_steps"
    )
    op.drop_index(op.f("ix_backtest_steps_timestamp"), table_name="backtest_steps")
    op.drop_index(op.f("ix_backtest_steps_success"), table_name="backtest_steps")
    op.drop_index(
        op.f("ix_backtest_steps_backtest_run_id"), table_name="backtest_steps"
    )
    op.drop_table("backtest_steps")
    op.drop_index("idx_backtest_runs_workflow_started_at", table_name="backtest_runs")
    op.drop_index(op.f("ix_backtest_runs_workflow_name"), table_name="backtest_runs")
    op.drop_index(op.f("ix_backtest_runs_success"), table_name="backtest_runs")
    op.drop_index(op.f("ix_backtest_runs_status"), table_name="backtest_runs")
    op.drop_index(op.f("ix_backtest_runs_started_at"), table_name="backtest_runs")
    op.drop_index(op.f("ix_backtest_runs_scenario_id"), table_name="backtest_runs")
    op.drop_index(op.f("ix_backtest_runs_completed_at"), table_name="backtest_runs")
    op.drop_table("backtest_runs")
    op.drop_index(
        "idx_backtest_scenarios_workflow_dates", table_name="backtest_scenarios"
    )
    op.drop_index(
        op.f("ix_backtest_scenarios_workflow_name"), table_name="backtest_scenarios"
    )
    op.drop_index(
        op.f("ix_backtest_scenarios_start_date"), table_name="backtest_scenarios"
    )
    op.drop_index(
        op.f("ix_backtest_scenarios_provider_profile"), table_name="backtest_scenarios"
    )
    op.drop_index(
        op.f("ix_backtest_scenarios_end_date"), table_name="backtest_scenarios"
    )
    op.drop_index(
        op.f("ix_backtest_scenarios_benchmark_symbol"), table_name="backtest_scenarios"
    )
    op.drop_table("backtest_scenarios")
