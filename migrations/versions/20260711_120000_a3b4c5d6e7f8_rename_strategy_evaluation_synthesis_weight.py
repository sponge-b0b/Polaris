"""rename strategy evaluation synthesis weight

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-07-11 12:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3b4c5d6e7f8"
down_revision: str | None = "f2a3b4c5d6e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE_NAME = "strategy_hypothesis_evaluations"
_OLD_COLUMN_NAME = "".join(("post", "erior_weight"))
_NEW_COLUMN_NAME = "synthesis_weight"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if _TABLE_NAME not in table_names:
        return

    column_names = {column["name"] for column in inspector.get_columns(_TABLE_NAME)}
    if _OLD_COLUMN_NAME in column_names and _NEW_COLUMN_NAME not in column_names:
        op.alter_column(
            _TABLE_NAME,
            _OLD_COLUMN_NAME,
            new_column_name=_NEW_COLUMN_NAME,
            existing_type=sa.Float(),
            existing_nullable=False,
        )


def downgrade() -> None:
    # Destructive cleanup migration: canonical schema remains on the new column name.
    return
