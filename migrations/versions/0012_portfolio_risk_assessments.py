"""Persist immutable attributable Portfolio Risk assessments.

Revision ID: 0012_portfolio_risk_assessments
Revises: 0011_portfolio_consequences
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_portfolio_risk_assessments"
down_revision: str | None = "0011_portfolio_consequences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portfolio_risk_assessments",
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_state_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("projected_consequence_id", postgresql.UUID(as_uuid=True)),
        sa.Column("horizon", sa.Text(), nullable=False),
        sa.Column("scenario", sa.Text(), nullable=False),
        sa.Column("support_basis", sa.Text(), nullable=False),
        sa.Column(
            "evidence_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
        ),
        sa.Column("assumptions", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("downside_fraction", sa.Numeric()),
        sa.Column("market_volatility_fraction", sa.Numeric()),
        sa.Column("objective_shortfall_amount", sa.Numeric()),
        sa.Column("dimensions", postgresql.JSONB(), nullable=False),
        sa.Column("support_uncertainty", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("uncertainty", postgresql.ARRAY(sa.Text()), nullable=False),
        # duplicate-code: this revision freezes Risk actor storage independently
        # of the earlier consequence revision and mutable current schema.
        # arid: disable
        sa.Column("actor_attribution_kind", sa.String(length=16), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "actor_candidate_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True))
        ),
        sa.Column("formed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("known_at", sa.DateTime(timezone=True), nullable=False),
        # arid: enable
        sa.CheckConstraint(
            "jsonb_typeof(dimensions) = 'array'",
            name=op.f("ck_portfolio_risk_assessments_dimensions_array"),
        ),
        sa.CheckConstraint(
            "jsonb_array_length(dimensions) > 0",
            name=op.f("ck_portfolio_risk_assessments_dimensions_present"),
        ),
        sa.CheckConstraint(
            "actor_attribution_kind IN ('known', 'unknown', 'contested')",
            name=op.f("ck_portfolio_risk_assessments_actor_attribution_kind"),
        ),
        # duplicate-code: the historical Risk revision must retain its own actor
        # shape even if the current schema helper later evolves.
        # arid: disable
        sa.CheckConstraint(
            "(actor_attribution_kind = 'known' AND actor_id IS NOT NULL "
            "AND actor_candidate_ids IS NULL) OR "
            "(actor_attribution_kind = 'unknown' AND actor_id IS NULL "
            "AND actor_candidate_ids IS NULL) OR "
            "(actor_attribution_kind = 'contested' AND actor_id IS NULL "
            "AND cardinality(actor_candidate_ids) > 0)",
            name=op.f("ck_portfolio_risk_assessments_actor_attribution_shape"),
        ),
        # arid: enable
        sa.ForeignKeyConstraint(
            ["source_state_id", "source_as_of"],
            ["portfolio_states.state_id", "portfolio_states.as_of"],
            name=op.f("fk_risk_source_state_as_of"),
        ),
        sa.ForeignKeyConstraint(
            ["projected_consequence_id"],
            ["projected_portfolio_consequences.consequence_id"],
            name=op.f("fk_risk_projected_consequence"),
        ),
        sa.PrimaryKeyConstraint(
            "assessment_id", name=op.f("pk_portfolio_risk_assessments")
        ),
    )
    op.create_index(
        "ix_portfolio_risk_source_history",
        "portfolio_risk_assessments",
        ["source_state_id", "known_at"],
    )
    op.create_index(
        "ix_portfolio_risk_projection_history",
        "portfolio_risk_assessments",
        ["projected_consequence_id", "known_at"],
    )
    op.execute(
        """
        CREATE FUNCTION polaris_reject_portfolio_risk_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'immutable Portfolio Risk Assessment cannot be changed';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_portfolio_risk_assessments_immutable
        BEFORE UPDATE OR DELETE ON portfolio_risk_assessments
        FOR EACH ROW EXECUTE FUNCTION polaris_reject_portfolio_risk_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER trg_portfolio_risk_assessments_immutable "
        "ON portfolio_risk_assessments"
    )
    op.execute("DROP FUNCTION polaris_reject_portfolio_risk_mutation()")
    op.drop_index(
        "ix_portfolio_risk_projection_history", table_name="portfolio_risk_assessments"
    )
    op.drop_index(
        "ix_portfolio_risk_source_history", table_name="portfolio_risk_assessments"
    )
    op.drop_table("portfolio_risk_assessments")
