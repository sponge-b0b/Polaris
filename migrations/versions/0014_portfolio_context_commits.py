"""Persist append-only Portfolio Evidence context owner commits.

Revision ID: 0014_portfolio_context_commits
Revises: 0013_portfolio_judgment_acts
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_portfolio_context_commits"
down_revision: str | None = "0013_portfolio_judgment_acts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portfolio_context_commits",
        sa.Column("commit_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("known_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name=op.f("ck_portfolio_context_commits_payload_object"),
        ),
    )
    op.create_index(
        "ix_portfolio_context_commits_known_at",
        "portfolio_context_commits",
        ["known_at"],
    )
    op.execute(
        """
        CREATE FUNCTION polaris_reject_portfolio_context_commit_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'immutable Portfolio context commit cannot be changed';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_portfolio_context_commits_immutable
        BEFORE UPDATE OR DELETE ON portfolio_context_commits
        FOR EACH ROW EXECUTE FUNCTION polaris_reject_portfolio_context_commit_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER trg_portfolio_context_commits_immutable "
        "ON portfolio_context_commits"
    )
    op.execute("DROP FUNCTION polaris_reject_portfolio_context_commit_mutation()")
    op.drop_index(
        "ix_portfolio_context_commits_known_at",
        table_name="portfolio_context_commits",
    )
    op.drop_table("portfolio_context_commits")
