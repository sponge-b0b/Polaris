"""Persist alternative-relative hypothetical Portfolio consequences.

Revision ID: 0011_portfolio_consequences
Revises: 0010_merge_r3_foundations
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_portfolio_consequences"
down_revision: str | None = "0010_merge_r3_foundations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_portfolio_states_state_id", "portfolio_states", ["state_id", "as_of"]
    )
    op.create_table(
        "projected_portfolio_consequences",
        sa.Column("consequence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alternative_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alternative_revision", sa.Integer(), nullable=False),
        sa.Column("source_state_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("horizon", sa.Text(), nullable=False),
        sa.Column("scenario", sa.Text(), nullable=False),
        sa.Column("assumptions", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("exposure_change", sa.Numeric()),
        sa.Column("exposure_unresolved", sa.Text()),
        sa.Column("allocation_change", sa.Numeric()),
        sa.Column("allocation_unresolved", sa.Text()),
        sa.Column("cash_effect", sa.Numeric()),
        sa.Column("cash_unresolved", sa.Text()),
        sa.Column("economic_benefits", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("adverse_possibilities", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("material_risk_changes", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("actor_attribution_kind", sa.String(length=16), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "actor_candidate_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True))
        ),
        sa.Column("formed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("known_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("uncertainty", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "alternative_revision > 0",
            name=op.f(
                "ck_projected_portfolio_consequences_positive_alternative_revision"
            ),
        ),
        sa.CheckConstraint(
            "exposure_change IS NOT NULL OR exposure_unresolved IS NOT NULL OR "
            "allocation_change IS NOT NULL OR allocation_unresolved IS NOT NULL",
            name=op.f("ck_projected_portfolio_consequences_material_spy_change"),
        ),
        sa.CheckConstraint(
            "NOT (exposure_change IS NOT NULL AND exposure_unresolved IS NOT NULL) "
            "AND NOT (allocation_change IS NOT NULL AND "
            "allocation_unresolved IS NOT NULL) "
            "AND NOT (cash_effect IS NOT NULL AND cash_unresolved IS NOT NULL)",
            name=op.f("ck_projected_portfolio_consequences_change_resolution"),
        ),
        sa.CheckConstraint(
            "actor_attribution_kind IN ('known', 'unknown', 'contested')",
            name=op.f("ck_projected_portfolio_consequences_actor_attribution_kind"),
        ),
        # duplicate-code: This migration freezes the actor attribution shape
        # independently of the mutable current schema declaration.
        # arid: disable
        sa.CheckConstraint(
            "(actor_attribution_kind = 'known' AND actor_id IS NOT NULL "
            "AND actor_candidate_ids IS NULL) OR "
            "(actor_attribution_kind = 'unknown' AND actor_id IS NULL "
            "AND actor_candidate_ids IS NULL) OR "
            "(actor_attribution_kind = 'contested' AND actor_id IS NULL "
            "AND cardinality(actor_candidate_ids) > 0)",
            name=op.f("ck_projected_portfolio_consequences_actor_attribution_shape"),
        ),
        # arid: enable
        sa.ForeignKeyConstraint(
            ["source_state_id", "source_as_of"],
            ["portfolio_states.state_id", "portfolio_states.as_of"],
            name=op.f("fk_consequence_source_state_as_of"),
        ),
        sa.ForeignKeyConstraint(
            ["alternative_id", "alternative_revision"],
            [
                "decision_alternative_revisions.alternative_id",
                "decision_alternative_revisions.revision",
            ],
            name=op.f("fk_projected_portfolio_consequences_alternative_revision"),
        ),
        sa.PrimaryKeyConstraint(
            "consequence_id", name=op.f("pk_projected_portfolio_consequences")
        ),
    )
    op.create_index(
        "ix_projected_consequence_alternative",
        "projected_portfolio_consequences",
        ["alternative_id", "known_at"],
    )
    op.execute(
        """
        CREATE FUNCTION polaris_reject_projected_consequence_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'immutable Projected Consequence cannot be changed';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_projected_portfolio_consequences_immutable
        BEFORE UPDATE OR DELETE ON projected_portfolio_consequences
        FOR EACH ROW EXECUTE FUNCTION polaris_reject_projected_consequence_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER trg_projected_portfolio_consequences_immutable "
        "ON projected_portfolio_consequences"
    )
    op.execute("DROP FUNCTION polaris_reject_projected_consequence_mutation()")
    op.drop_index(
        "ix_projected_consequence_alternative",
        table_name="projected_portfolio_consequences",
    )
    op.drop_table("projected_portfolio_consequences")
    op.drop_constraint(
        "uq_portfolio_states_state_id", "portfolio_states", type_="unique"
    )
