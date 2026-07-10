"""add node output contract identity

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-07-09 12:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c9d0e1f2a3b4"
down_revision: str | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "completed_workflow_node_outputs",
        sa.Column("output_contract", sa.String(), nullable=True),
    )
    op.add_column(
        "completed_workflow_node_outputs",
        sa.Column("output_schema_version", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_completed_workflow_node_outputs_output_contract",
        "completed_workflow_node_outputs",
        ["output_contract"],
    )
    op.create_index(
        "ix_completed_workflow_node_outputs_output_schema_version",
        "completed_workflow_node_outputs",
        ["output_schema_version"],
    )
    op.create_index(
        "idx_completed_node_outputs_contract_version",
        "completed_workflow_node_outputs",
        ["output_contract", "output_schema_version"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_completed_node_outputs_contract_version",
        table_name="completed_workflow_node_outputs",
    )
    op.drop_index(
        "ix_completed_workflow_node_outputs_output_schema_version",
        table_name="completed_workflow_node_outputs",
    )
    op.drop_index(
        "ix_completed_workflow_node_outputs_output_contract",
        table_name="completed_workflow_node_outputs",
    )
    op.drop_column("completed_workflow_node_outputs", "output_schema_version")
    op.drop_column("completed_workflow_node_outputs", "output_contract")
