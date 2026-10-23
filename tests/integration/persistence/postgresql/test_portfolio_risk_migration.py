from __future__ import annotations

import asyncio

from polaris.infrastructure.persistence.postgresql import POLARIS_TABLE_NAMES

from . import _migration_tests_portfolio_base as _base
from .conftest import PostgresTestTarget


def test_portfolio_risk_revision_round_trips(
    postgres_target: PostgresTestTarget,
) -> None:
    assert {
        "assessment_id",
        "source_state_id",
        "source_as_of",
        "projected_consequence_id",
        "evidence_ids",
        "dimensions",
        "uncertainty",
        "known_at",
    } <= asyncio.run(_base._column_names(postgres_target, "portfolio_risk_assessments"))
    assert {
        "fk_risk_source_state_as_of",
        "fk_risk_projected_consequence",
        "ck_portfolio_risk_assessments_dimensions_present",
    } <= asyncio.run(
        _base._constraint_names(postgres_target, "portfolio_risk_assessments")
    )
    # duplicate-code: this revision's expected tables must stay independent of
    # later revisions and the current schema registry.
    # arid: disable
    _base._assert_revision_round_trip(
        postgres_target,
        "0011_portfolio_consequences",
        (
            POLARIS_TABLE_NAMES
            - {
                "portfolio_risk_assessments",
                "portfolio_judgment_acts",
                "portfolio_context_commits",
            }
        )
        | {"alembic_version"},
    )
    # arid: enable
    assert "portfolio_risk_assessments" in asyncio.run(
        _base._table_names(postgres_target)
    )
