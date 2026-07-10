"""add completed run execution mode

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-07-09 14:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "d0e1f2a3b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "completed_workflow_runs",
        sa.Column(
            "execution_mode",
            sa.String(),
            nullable=False,
            server_default="normal",
        ),
    )
    op.create_check_constraint(
        "ck_completed_workflow_runs_execution_mode",
        "completed_workflow_runs",
        "execution_mode IN ('normal', 'replay', 'backtest', 'simulated')",
    )
    op.create_index(
        "idx_completed_runs_execution_mode",
        "completed_workflow_runs",
        ["execution_mode"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_completed_runs_execution_mode",
        table_name="completed_workflow_runs",
    )
    op.drop_constraint(
        "ck_completed_workflow_runs_execution_mode",
        "completed_workflow_runs",
        type_="check",
    )
    op.drop_column(
        "completed_workflow_runs",
        "execution_mode",
    )
