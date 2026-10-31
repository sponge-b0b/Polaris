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
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("draft", postgresql.JSONB(), nullable=False),
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
            "jsonb_typeof(draft) = 'object'",
            name="ck_investment_intelligence_judgment_acts_draft_object",
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
        ["target_family", "target_id", "sequence"],
    )
    op.create_table(
        "investment_intelligence_act_publications",
        sa.Column("act_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["act_id"],
            ["investment_intelligence_judgment_acts.act_id"],
            ondelete="RESTRICT",
        ),
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
        "investment_intelligence_act_publications",
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
    op.execute(
        "DO $$ DECLARE slot_name text := 'polaris_ii_' || "
        "substr(md5(current_database() || ':' || current_schema()), 1, 32); "
        "BEGIN EXECUTE format('CREATE PUBLICATION %I', slot_name); END $$"
    )
    op.execute(
        "CREATE FUNCTION polaris_intelligence_act_commit_message() "
        "RETURNS trigger LANGUAGE plpgsql AS $$ "
        "DECLARE expected_slot text := 'polaris_ii_' || "
        "substr(md5(current_database() || ':' || TG_TABLE_SCHEMA), 1, 32); "
        "BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_replication_slots AS s "
        "WHERE s.slot_name = expected_slot AND s.plugin = 'pgoutput' "
        "AND s.database = current_database() AND NOT s.temporary "
        "AND s.wal_status IN ('reserved', 'extended') "
        "AND s.invalidation_reason IS NULL) THEN "
        "RAISE EXCEPTION 'Investment Intelligence commit slot is unavailable'; "
        "END IF; "
        "PERFORM pg_logical_emit_message(true, expected_slot, NEW.act_id::text); "
        "RETURN NEW; END $$"
    )
    op.execute(
        "CREATE TRIGGER trg_investment_intelligence_act_commit_message "
        "AFTER INSERT ON investment_intelligence_judgment_acts "
        "FOR EACH ROW EXECUTE FUNCTION polaris_intelligence_act_commit_message()"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER trg_investment_intelligence_act_commit_message "
        "ON investment_intelligence_judgment_acts"
    )
    op.execute("DROP FUNCTION polaris_intelligence_act_commit_message()")
    op.execute(
        "DO $$ DECLARE expected_slot text := 'polaris_ii_' || "
        "substr(md5(current_database() || ':' || current_schema()), 1, 32); "
        "BEGIN IF EXISTS (SELECT 1 FROM pg_replication_slots AS s "
        "WHERE s.slot_name = expected_slot) THEN "
        "PERFORM pg_drop_replication_slot(expected_slot); END IF; END $$"
    )
    op.execute(
        "DO $$ DECLARE slot_name text := 'polaris_ii_' || "
        "substr(md5(current_database() || ':' || current_schema()), 1, 32); "
        "BEGIN EXECUTE format('DROP PUBLICATION %I', slot_name); END $$"
    )
    for table in (
        "investment_intelligence_judgment_bases",
        "investment_intelligence_act_publications",
        "investment_intelligence_judgment_acts",
    ):
        op.execute(f"DROP TRIGGER trg_{table}_immutable ON {table}")
        op.drop_table(table)
