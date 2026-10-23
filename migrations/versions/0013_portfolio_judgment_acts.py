"""Persist Portfolio Evidence target and claim correction acts.

Revision ID: 0013_portfolio_judgment_acts
Revises: 0012_portfolio_risk_assessments
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_portfolio_judgment_acts"
down_revision: str | None = "0012_portfolio_risk_assessments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portfolio_judgment_acts",
        sa.Column("act_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("consequence_id", postgresql.UUID(as_uuid=True)),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True)),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("known_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("judgment_revision", sa.Integer(), nullable=False),
        sa.Column("claim_catalog_version", sa.Integer(), nullable=False),
        sa.Column("act", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint(
            "(consequence_id IS NULL) <> (assessment_id IS NULL)",
            name=op.f("ck_portfolio_judgment_acts_one_portfolio_judgment_root"),
        ),
        sa.CheckConstraint(
            "sequence > 0",
            name=op.f("ck_portfolio_judgment_acts_positive_sequence"),
        ),
        sa.CheckConstraint(
            "judgment_revision > 0",
            name=op.f("ck_portfolio_judgment_acts_positive_judgment_revision"),
        ),
        sa.CheckConstraint(
            "claim_catalog_version > 0",
            name=op.f("ck_portfolio_judgment_acts_positive_catalog_version"),
        ),
        sa.CheckConstraint(
            "known_at >= recorded_at",
            name=op.f("ck_portfolio_judgment_acts_known_after_recorded"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(act) = 'object'",
            name=op.f("ck_portfolio_judgment_acts_act_object"),
        ),
        sa.ForeignKeyConstraint(
            ["consequence_id"],
            ["projected_portfolio_consequences.consequence_id"],
            name=op.f("fk_portfolio_judgment_consequence"),
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["portfolio_risk_assessments.assessment_id"],
            name=op.f("fk_portfolio_judgment_assessment"),
        ),
        sa.UniqueConstraint(
            "consequence_id",
            "sequence",
            name=op.f("uq_consequence_act_sequence"),
        ),
        sa.UniqueConstraint(
            "assessment_id",
            "sequence",
            name=op.f("uq_risk_act_sequence"),
        ),
    )
    op.create_index(
        "ix_portfolio_judgment_consequence_history",
        "portfolio_judgment_acts",
        ["consequence_id", "known_at"],
    )
    op.create_index(
        "ix_portfolio_judgment_risk_history",
        "portfolio_judgment_acts",
        ["assessment_id", "known_at"],
    )
    op.execute(
        """
        CREATE FUNCTION polaris_reject_portfolio_judgment_act_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'immutable Portfolio judgment act cannot be changed';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_portfolio_judgment_acts_immutable
        BEFORE UPDATE OR DELETE ON portfolio_judgment_acts
        FOR EACH ROW EXECUTE FUNCTION polaris_reject_portfolio_judgment_act_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER trg_portfolio_judgment_acts_immutable ON portfolio_judgment_acts"
    )
    op.execute("DROP FUNCTION polaris_reject_portfolio_judgment_act_mutation()")
    op.drop_index(
        "ix_portfolio_judgment_risk_history",
        table_name="portfolio_judgment_acts",
    )
    op.drop_index(
        "ix_portfolio_judgment_consequence_history",
        table_name="portfolio_judgment_acts",
    )
    op.drop_table("portfolio_judgment_acts")
