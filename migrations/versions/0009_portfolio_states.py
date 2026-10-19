"""Persist immutable actual Portfolio State readings.

Revision ID: 0009_portfolio_states
Revises: 0008_support_epochs
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_portfolio_states"
down_revision: str | None = "0008_support_epochs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portfolio_states",
        sa.Column("state_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("known_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_system", sa.Text(), nullable=False),
        sa.Column("source_record_reference", sa.Text(), nullable=False),
        sa.Column("source_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("capital_basis", sa.Numeric(), nullable=False),
        sa.Column("cash", sa.Numeric(), nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position_quantity", sa.Numeric(), nullable=False),
        sa.Column("position_value", sa.Numeric(), nullable=False),
        sa.Column("exposure_value", sa.Numeric(), nullable=False),
        sa.Column("allocation_fraction", sa.Numeric(), nullable=False),
        sa.Column("interpretation_basis", sa.Text(), nullable=False),
        sa.Column("uncertainty", sa.Text()),
        sa.CheckConstraint(
            "capital_basis > 0",
            name=op.f("ck_portfolio_states_positive_capital_basis"),
        ),
        sa.CheckConstraint(
            "known_at >= source_observed_at",
            name=op.f("ck_portfolio_states_known_after_source"),
        ),
        sa.PrimaryKeyConstraint("state_id", name="pk_portfolio_states"),
    )
    op.create_index(
        "ix_portfolio_states_history",
        "portfolio_states",
        ["portfolio_id", "as_of", "known_at"],
    )
    op.execute(
        """
        CREATE FUNCTION polaris_reject_portfolio_state_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'immutable Portfolio State cannot be changed';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_portfolio_states_immutable
        BEFORE UPDATE OR DELETE ON portfolio_states
        FOR EACH ROW EXECUTE FUNCTION polaris_reject_portfolio_state_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_portfolio_states_immutable ON portfolio_states")
    op.execute("DROP FUNCTION polaris_reject_portfolio_state_mutation()")
    op.drop_index("ix_portfolio_states_history", table_name="portfolio_states")
    op.drop_table("portfolio_states")
