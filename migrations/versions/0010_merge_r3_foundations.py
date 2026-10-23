"""Merge certified R3 Investment Intelligence and Portfolio State foundations.

Revision ID: 0010_merge_r3_foundations
Revises: 0009_investment_intelligence, 0009_portfolio_states
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0010_merge_r3_foundations"
down_revision: tuple[str, str] = (
    "0009_investment_intelligence",
    "0009_portfolio_states",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Join the two already-applied certified sibling foundations."""


def downgrade() -> None:
    """Split back to the two certified sibling heads without rewriting either."""
