"""Persist minimum authority regimes and immutable Human Investment Decisions.

Revision ID: 0016_governance_human_decisions
Revises: 0015_intelligence_judgments
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016_governance_human_decisions"
down_revision: str | None = "0015_intelligence_judgments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "governance_authority_regimes",
        sa.Column("regime_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("power", sa.String(length=48), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "power = 'human-investment-decision'",
            name=op.f("ck_governance_authority_regimes_r3_human_decision_power"),
        ),
        sa.CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name=op.f("ck_governance_authority_regimes_valid_authority_interval"),
        ),
    )
    op.create_table(
        "human_investment_decisions",
        sa.Column("decision_ref", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "operation_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True
        ),
        sa.Column(
            "investment_decision_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("regime_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("made_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("choice", sa.String(length=16), nullable=False),
        sa.Column("effect", sa.String(length=32), nullable=False),
        sa.Column("recommendations", postgresql.JSONB(), nullable=False),
        sa.Column("material_rationale", sa.Text()),
        sa.Column("expected_decision_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["investment_decision_id"],
            ["investment_decisions.decision_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["regime_id"],
            ["governance_authority_regimes.regime_id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "choice IN ('increase', 'hold', 'reduce', 'deferral')",
            name=op.f("ck_human_investment_decisions_closed_human_choice"),
        ),
        sa.CheckConstraint(
            "(choice = 'deferral' AND effect = 'deferring') OR "
            "(choice <> 'deferral' AND effect = 'substantively_resolving')",
            name=op.f("ck_human_investment_decisions_human_choice_effect"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(recommendations) = 'array'",
            name=op.f("ck_human_investment_decisions_recommendation_links_array"),
        ),
        sa.CheckConstraint(
            "material_rationale IS NULL OR btrim(material_rationale) <> ''",
            name=op.f("ck_human_investment_decisions_material_rationale_nonempty"),
        ),
        sa.CheckConstraint(
            "expected_decision_version > 0",
            name=op.f("ck_human_investment_decisions_positive_decision_version"),
        ),
    )
    op.create_index(
        "ix_human_decision_history",
        "human_investment_decisions",
        ["investment_decision_id", "recorded_at"],
    )
    op.execute(
        "CREATE FUNCTION polaris_reject_governance_fact_mutation() "
        "RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN RAISE EXCEPTION 'immutable Governance fact cannot be changed'; END $$"
    )
    for table in ("governance_authority_regimes", "human_investment_decisions"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable "
            f"BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION polaris_reject_governance_fact_mutation()"
        )


def downgrade() -> None:
    for table in ("human_investment_decisions", "governance_authority_regimes"):
        op.execute(f"DROP TRIGGER trg_{table}_immutable ON {table}")
    op.execute("DROP FUNCTION polaris_reject_governance_fact_mutation()")
    op.drop_index("ix_human_decision_history", table_name="human_investment_decisions")
    op.drop_table("human_investment_decisions")
    op.drop_table("governance_authority_regimes")
