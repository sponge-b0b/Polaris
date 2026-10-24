"""Persist Investment Intelligence target acts and exact consumed Evidence bases.

Revision ID: 0015_intelligence_judgments
Revises: 0014_portfolio_context_commits
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_intelligence_judgments"
down_revision: str | None = "0014_portfolio_context_commits"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "investment_intelligence_judgment_acts",
        sa.Column("act_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("row_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("target_family", sa.String(length=48), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        # duplicate-code: Sharing DDL would couple frozen migration revisions.
        # arid: disable
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("known_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("judgment_revision", sa.Integer(), nullable=False),
        sa.Column("claim_catalog_version", sa.Integer(), nullable=False),
        sa.Column("act", postgresql.JSONB(), nullable=False),
        # arid: enable
        sa.ForeignKeyConstraint(
            ["decision_id"],
            ["investment_decisions.decision_id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "sequence > 0",
            name="ck_investment_intelligence_judgment_acts_positive_sequence",
        ),
        sa.CheckConstraint(
            "judgment_revision > 0",
            name="ck_investment_intelligence_judgment_acts_positive_judgment_revision",
        ),
        sa.CheckConstraint(
            "claim_catalog_version > 0",
            name="ck_investment_intelligence_judgment_acts_positive_catalog_version",
        ),
        sa.CheckConstraint(
            "known_at >= recorded_at",
            name="ck_investment_intelligence_judgment_acts_known_after_recorded",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(act) = 'object'",
            name="ck_investment_intelligence_judgment_acts_act_object",
        ),
        sa.CheckConstraint(
            "target_family IN ('InvestmentHypothesisRef', 'InvestmentViewRef', "
            "'MeaningfulChallengeResultRef', 'InvestmentRecommendationRef', "
            "'RecommendationWithholdingJudgmentRef')",
            name="ck_investment_intelligence_judgment_acts_closed_target_family",
        ),
        sa.UniqueConstraint(
            "target_family",
            "target_id",
            "sequence",
            name="uq_intelligence_act_sequence",
        ),
        sa.UniqueConstraint("row_id", name="uq_intelligence_act_row_id"),
    )
    op.create_index(
        "ix_intelligence_act_history",
        "investment_intelligence_judgment_acts",
        ["target_family", "target_id", "known_at"],
    )
    op.create_table(
        "investment_intelligence_judgment_bases",
        sa.Column("row_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("basis_index", sa.Integer(), nullable=False),
        sa.Column("basis", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["operation_id"],
            ["investment_intelligence_command_receipts.operation_id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "basis_index >= 0",
            name="ck_investment_intelligence_judgment_bases_basis_index_nonnegative",
        ),
        sa.UniqueConstraint(
            "operation_id", "basis_index", name="uq_intelligence_basis"
        ),
    )
    for table in (
        "investment_intelligence_judgment_acts",
        "investment_intelligence_judgment_bases",
    ):
        # duplicate-code: Sharing DDL would couple frozen migration revisions.
        # arid: disable
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable "
            f"BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION "
            "polaris_reject_immutable_intelligence_mutation()"
        )
        # arid: enable


def downgrade() -> None:
    for table in (
        "investment_intelligence_judgment_bases",
        "investment_intelligence_judgment_acts",
    ):
        op.execute(f"DROP TRIGGER trg_{table}_immutable ON {table}")
        op.drop_table(table)
