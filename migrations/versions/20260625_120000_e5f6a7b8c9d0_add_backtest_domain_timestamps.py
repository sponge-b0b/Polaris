"""add first-class backtest metric and artifact timestamps

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-25 12:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "backtest_metrics",
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "backtest_artifacts",
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(
        """
        UPDATE backtest_metrics AS metric
        SET recorded_at = COALESCE(
            CASE
                WHEN jsonb_typeof(metric.metadata -> 'timestamp') = 'string'
                 AND pg_input_is_valid(
                    metric.metadata ->> 'timestamp',
                    'timestamp with time zone'
                 )
                THEN (metric.metadata ->> 'timestamp')::timestamptz
            END,
            CASE
                WHEN jsonb_typeof(metric.metadata -> 'created_at') = 'string'
                 AND pg_input_is_valid(
                    metric.metadata ->> 'created_at',
                    'timestamp with time zone'
                 )
                THEN (metric.metadata ->> 'created_at')::timestamptz
            END,
            run.completed_at,
            metric.created_at
        )
        FROM backtest_runs AS run
        WHERE run.backtest_run_id = metric.backtest_run_id
        """
    )
    op.execute(
        """
        UPDATE backtest_artifacts AS artifact
        SET generated_at = COALESCE(
            CASE
                WHEN jsonb_typeof(artifact.metadata -> 'timestamp') = 'string'
                 AND pg_input_is_valid(
                    artifact.metadata ->> 'timestamp',
                    'timestamp with time zone'
                 )
                THEN (artifact.metadata ->> 'timestamp')::timestamptz
            END,
            CASE
                WHEN jsonb_typeof(artifact.metadata -> 'created_at') = 'string'
                 AND pg_input_is_valid(
                    artifact.metadata ->> 'created_at',
                    'timestamp with time zone'
                 )
                THEN (artifact.metadata ->> 'created_at')::timestamptz
            END,
            run.completed_at,
            artifact.created_at
        )
        FROM backtest_runs AS run
        WHERE run.backtest_run_id = artifact.backtest_run_id
        """
    )

    op.alter_column("backtest_metrics", "recorded_at", nullable=False)
    op.alter_column("backtest_artifacts", "generated_at", nullable=False)


def downgrade() -> None:
    op.drop_column("backtest_artifacts", "generated_at")
    op.drop_column("backtest_metrics", "recorded_at")
