from __future__ import annotations

from pathlib import Path

from polaris.infrastructure.persistence.postgresql import POLARIS_TABLE_NAMES

from . import _migration_tests_portfolio_base as _base
from .conftest import PostgresTestTarget

_INVESTMENT_INTELLIGENCE_TABLE_NAMES = frozenset(
    {
        "investment_hypotheses",
        "investment_views",
        "meaningful_challenges",
        "decision_alternatives",
        "decision_alternative_revisions",
        "decision_alternative_selections",
        "investment_intelligence_command_receipts",
    }
)
_SIBLING_0009_TABLE_NAMES = _INVESTMENT_INTELLIGENCE_TABLE_NAMES | frozenset(
    {"portfolio_states"}
)


def test_r3_foundation_merge_revision_preserves_both_certified_heads(
    postgres_target: PostgresTestTarget,
) -> None:
    intelligence_migration = Path(
        "migrations/versions/0009_investment_intelligence_judgments.py"
    ).read_text(encoding="utf-8")
    portfolio_migration = Path(
        "migrations/versions/0009_portfolio_states.py"
    ).read_text(encoding="utf-8")
    merge_migration = Path(
        "migrations/versions/0010_merge_r3_foundations.py"
    ).read_text(encoding="utf-8")

    assert 'revision: str = "0009_investment_intelligence"' in intelligence_migration
    assert 'down_revision: str | None = "0008_support_epochs"' in intelligence_migration
    assert 'revision: str = "0009_portfolio_states"' in portfolio_migration
    assert 'down_revision: str | None = "0008_support_epochs"' in portfolio_migration
    assert 'revision: str = "0010_merge_r3_foundations"' in merge_migration
    assert '"0009_investment_intelligence"' in merge_migration
    assert '"0009_portfolio_states"' in merge_migration

    _base._assert_revision_round_trip(
        postgres_target,
        "0008_support_epochs",
        (POLARIS_TABLE_NAMES - _SIBLING_0009_TABLE_NAMES) | {"alembic_version"},
    )
