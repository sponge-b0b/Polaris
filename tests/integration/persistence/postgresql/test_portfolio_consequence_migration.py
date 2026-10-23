from __future__ import annotations

import asyncio

from polaris.infrastructure.persistence.postgresql import POLARIS_TABLE_NAMES

from . import _migration_tests_portfolio_base as _base
from .conftest import PostgresTestTarget


def test_consequence_revision_binds_both_owner_roots_and_round_trips(
    postgres_target: PostgresTestTarget,
) -> None:
    assert {
        "consequence_id",
        "alternative_id",
        "alternative_revision",
        "source_state_id",
        "source_as_of",
        "horizon",
        "scenario",
        "uncertainty",
    } <= asyncio.run(
        _base._column_names(postgres_target, "projected_portfolio_consequences")
    )
    assert "uq_portfolio_states_state_id" in asyncio.run(
        _base._constraint_names(postgres_target, "portfolio_states")
    )
    assert {
        "fk_consequence_source_state_as_of",
        "fk_projected_portfolio_consequences_alternative_revision",
    } <= asyncio.run(
        _base._constraint_names(postgres_target, "projected_portfolio_consequences")
    )
    # duplicate-code: this revision's expected tables must stay independent of
    # later revisions and the current schema registry.
    # arid: disable
    _base._assert_revision_round_trip(
        postgres_target,
        "0010_merge_r3_foundations",
        (
            POLARIS_TABLE_NAMES
            - {
                "projected_portfolio_consequences",
                "portfolio_risk_assessments",
                "portfolio_judgment_acts",
                "portfolio_context_commits",
            }
        )
        | {"alembic_version"},
    )
    # arid: enable
    assert "projected_portfolio_consequences" in asyncio.run(
        _base._table_names(postgres_target)
    )
