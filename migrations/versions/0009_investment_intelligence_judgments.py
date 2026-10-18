"""Persist Investment Intelligence-owned R3 judgment facts.

Revision ID: 0009_investment_intelligence
Revises: 0008_support_epochs
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_investment_intelligence"
down_revision: str | None = "0008_support_epochs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# duplicate-code: this migration's frozen table inventory must not import the
# mutable runtime schema registry; future schema changes must not rewrite history.
# arid: disable
_FACT_TABLES = (
    "investment_hypotheses",
    "investment_views",
    "meaningful_challenges",
    "decision_alternatives",
    "decision_alternative_revisions",
    "decision_alternative_selections",
    "investment_intelligence_command_receipts",
)
# arid: enable


def _root_columns() -> list[sa.Column]:
    return [sa.Column("row_id", sa.BigInteger(), sa.Identity(), nullable=False)]


def _decision_fk() -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["decision_id"], ["investment_decisions.decision_id"], ondelete="RESTRICT"
    )


def _alternative_fk(column: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], ["decision_alternatives.alternative_id"], ondelete="RESTRICT"
    )


def _judgment_content_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("formed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "investment_views",
        *_root_columns(),
        sa.Column("view_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        *_judgment_content_columns(),
        _decision_fk(),
        sa.PrimaryKeyConstraint("row_id"),
        sa.UniqueConstraint("view_id"),
    )
    op.create_table(
        "investment_hypotheses",
        *_root_columns(),
        sa.Column("hypothesis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_to_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_to_family", sa.String(length=48), nullable=False),
        *_judgment_content_columns(),
        _decision_fk(),
        sa.PrimaryKeyConstraint("row_id"),
        sa.UniqueConstraint("hypothesis_id"),
    )
    op.create_table(
        "meaningful_challenges",
        *_root_columns(),
        sa.Column("challenge_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("view_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        *_judgment_content_columns(),
        sa.ForeignKeyConstraint(
            ["view_id"], ["investment_views.view_id"], ondelete="RESTRICT"
        ),
        _decision_fk(),
        sa.PrimaryKeyConstraint("row_id"),
        sa.UniqueConstraint("challenge_id"),
    )
    op.create_table(
        "decision_alternatives",
        *_root_columns(),
        sa.Column("alternative_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        _decision_fk(),
        sa.PrimaryKeyConstraint("row_id"),
        sa.UniqueConstraint("alternative_id"),
    )
    op.create_table(
        "decision_alternative_revisions",
        *_root_columns(),
        sa.Column("alternative_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint(
            "revision >= 1", name="ck_decision_alternative_revisions_revision_positive"
        ),
        _alternative_fk("alternative_id"),
        sa.PrimaryKeyConstraint("row_id"),
        sa.UniqueConstraint(
            "alternative_id", "revision", name="uq_decision_alternative_root_revision"
        ),
    )
    op.create_table(
        "decision_alternative_selections",
        *_root_columns(),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("selection_revision", sa.Integer(), nullable=False),
        sa.Column("selected_alternative_id", postgresql.UUID(as_uuid=True)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "selection_revision >= 1",
            name="ck_decision_alternative_selections_selection_revision_positive",
        ),
        _decision_fk(),
        _alternative_fk("selected_alternative_id"),
        sa.PrimaryKeyConstraint("row_id"),
        sa.UniqueConstraint(
            "decision_id",
            "selection_revision",
            name="uq_alternative_selection_decision_revision",
        ),
    )
    op.create_table(
        "investment_intelligence_command_receipts",
        *_root_columns(),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("judgment_ids", postgresql.JSONB(), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "char_length(request_fingerprint) = 64",
            name="ck_investment_intelligence_command_receipts_fingerprint_sha256",
        ),
        sa.PrimaryKeyConstraint("row_id"),
        sa.UniqueConstraint("operation_id"),
    )
    op.execute(
        """
        CREATE FUNCTION polaris_reject_immutable_intelligence_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'immutable Investment Intelligence facts cannot be changed';
        END;
        $$
        """
    )
    for table in _FACT_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable "
            f"BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION "
            "polaris_reject_immutable_intelligence_mutation()"
        )


def downgrade() -> None:
    for table in reversed(_FACT_TABLES):
        op.execute(f"DROP TRIGGER trg_{table}_immutable ON {table}")
        op.drop_table(table)
    op.execute("DROP FUNCTION polaris_reject_immutable_intelligence_mutation()")
