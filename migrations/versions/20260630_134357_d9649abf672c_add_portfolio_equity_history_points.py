"""add portfolio equity history points

Revision ID: d9649abf672c
Revises: a7b8c9d0e1f2
Create Date: 2026-06-30 13:43:57.614568+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d9649abf672c"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portfolio_equity_history_points",
        sa.Column("portfolio_equity_history_point_id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("timeframe", sa.String(), nullable=False),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("equity", sa.Float(), nullable=False),
        sa.Column("profit_loss", sa.Float(), nullable=False),
        sa.Column("profit_loss_pct", sa.Float(), nullable=True),
        sa.Column("base_value", sa.Float(), nullable=True),
        sa.Column(
            "cashflow_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("workflow_name", sa.String(), nullable=True),
        sa.Column("execution_id", sa.String(), nullable=True),
        sa.Column("runtime_id", sa.String(), nullable=True),
        sa.Column("node_name", sa.String(), nullable=True),
        sa.Column(
            "row_created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "row_updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("portfolio_equity_history_point_id"),
        sa.UniqueConstraint(
            "account_id",
            "source",
            "timeframe",
            "observed_at",
            name="uq_portfolio_equity_history_natural_key",
        ),
    )
    for column in (
        "account_id",
        "source",
        "observed_at",
        "workflow_name",
        "execution_id",
        "runtime_id",
        "node_name",
    ):
        op.create_index(
            f"ix_portfolio_equity_history_points_{column}",
            "portfolio_equity_history_points",
            [column],
            unique=False,
        )
    op.create_index(
        "idx_portfolio_equity_history_account_observed_at",
        "portfolio_equity_history_points",
        ["account_id", "observed_at"],
        unique=False,
    )
    op.create_index(
        "idx_portfolio_equity_history_workflow_execution",
        "portfolio_equity_history_points",
        ["workflow_name", "execution_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_portfolio_equity_history_workflow_execution",
        table_name="portfolio_equity_history_points",
    )
    op.drop_index(
        "idx_portfolio_equity_history_account_observed_at",
        table_name="portfolio_equity_history_points",
    )
    for column in reversed(
        (
            "account_id",
            "source",
            "observed_at",
            "workflow_name",
            "execution_id",
            "runtime_id",
            "node_name",
        )
    ):
        op.drop_index(
            f"ix_portfolio_equity_history_points_{column}",
            table_name="portfolio_equity_history_points",
        )
    op.drop_table("portfolio_equity_history_points")
