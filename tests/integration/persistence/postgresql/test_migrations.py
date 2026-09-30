from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from polaris.infrastructure.persistence.postgresql import (
    DECISION_TABLE_NAMES,
    POLARIS_TABLE_NAMES,
    create_postgres_engine,
)

from .conftest import PostgresTestTarget

FORBIDDEN_TABLE_FRAGMENTS = {
    "action_intent",
    "agent",
    "event",
    "governance",
    "job",
    "lesson",
    "outcome",
    "rag",
    "recommendation",
    "report",
    "workflow",
}


async def _table_names(target: PostgresTestTarget) -> frozenset[str]:
    engine = create_postgres_engine(target.database_url, schema=target.schema)
    try:
        async with engine.connect() as connection:
            rows = await connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = :schema"
                ),
                {"schema": target.schema},
            )
            return frozenset(row.table_name for row in rows)
    finally:
        await engine.dispose()


async def _identity_column_types(
    target: PostgresTestTarget,
) -> dict[tuple[str, str], str]:
    # duplicate-code: migration falsifiers require local proof shape.
    # arid: disable
    engine = create_postgres_engine(target.database_url, schema=target.schema)
    try:
        async with engine.connect() as connection:
            rows = await connection.execute(
                text(
                    # arid: enable
                    "SELECT table_name, column_name, udt_name "
                    "FROM information_schema.columns "
                    "WHERE table_schema = :schema "
                    "AND (column_name = 'row_id' "
                    "OR column_name LIKE '%\\_id' ESCAPE '\\')"
                ),
                {"schema": target.schema},
            )
            return {(row.table_name, row.column_name): row.udt_name for row in rows}
    # duplicate-code: migration falsifiers require local proof shape.
    # arid: disable
    finally:
        await engine.dispose()


async def _column_default(
    target: PostgresTestTarget,
    table_name: str,
    column_name: str,
) -> str | None:
    engine = create_postgres_engine(target.database_url, schema=target.schema)
    try:
        async with engine.connect() as connection:
            return await connection.scalar(
                text(
                    "SELECT column_default FROM information_schema.columns "
                    "WHERE table_schema = :schema AND table_name = :table_name "
                    "AND column_name = :column_name"
                ),
                {
                    "schema": target.schema,
                    "table_name": table_name,
                    "column_name": column_name,
                },
            )
    finally:
        await engine.dispose()


async def _column_names(target: PostgresTestTarget, table_name: str) -> frozenset[str]:
    engine = create_postgres_engine(target.database_url, schema=target.schema)
    try:
        async with engine.connect() as connection:
            rows = await connection.execute(
                text(
                    # arid: enable
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = :schema AND table_name = :table_name"
                ),
                {"schema": target.schema, "table_name": table_name},
            )
            return frozenset(row.column_name for row in rows)
    finally:
        await engine.dispose()


def _assert_revision_round_trip(
    target: PostgresTestTarget,
    revision: str,
    expected_tables: frozenset[str],
) -> None:
    alembic = Config("alembic.ini")
    command.downgrade(alembic, revision)
    assert asyncio.run(_table_names(target)) == expected_tables

    command.upgrade(alembic, "head")
    assert asyncio.run(_table_names(target)) == (
        POLARIS_TABLE_NAMES | {"alembic_version"}
    )


def test_fresh_root_migrates_only_greenfield_polaris_schema(
    postgres_target: PostgresTestTarget,
) -> None:
    decision_migration = Path(
        "migrations/versions/0001_decision_persistence_foundation.py"
    ).read_text(encoding="utf-8")
    evidence_migration = Path(
        "migrations/versions/0002_evidence_observation_foundation.py"
    ).read_text(encoding="utf-8")
    requirement_migration = Path(
        "migrations/versions/0003_evidence_requirement_authority.py"
    ).read_text(encoding="utf-8")
    assert "down_revision: str | None = None" in decision_migration
    assert (
        'down_revision: str | None = "0001_decision_persistence"' in evidence_migration
    )
    assert (
        'down_revision: str | None = "0002_evidence_observations"'
        in requirement_migration
    )
    assert "legacy" not in decision_migration.lower()
    assert "legacy" not in evidence_migration.lower()
    assert "legacy" not in requirement_migration.lower()

    tables = asyncio.run(_table_names(postgres_target))
    assert tables == POLARIS_TABLE_NAMES | {"alembic_version"}
    assert not {
        table
        for table in tables
        if any(fragment in table for fragment in FORBIDDEN_TABLE_FRAGMENTS)
    }

    column_types = asyncio.run(_identity_column_types(postgres_target))
    assert column_types
    for (_, column_name), data_type in column_types.items():
        assert data_type == ("int8" if column_name == "row_id" else "uuid")

    assert (
        asyncio.run(
            _column_default(
                postgres_target,
                "evidence_observations",
                "observation_id",
            )
        )
        is None
    )

    relationship_columns = asyncio.run(
        _column_names(postgres_target, "investment_decision_relationships")
    )
    assert (
        not {
            "prior_decision_context",
            "target_known_at",
            "target_decision_version",
        }
        & relationship_columns
    )


def test_root_downgrades_to_empty_and_reupgrades(
    postgres_target: PostgresTestTarget,
) -> None:
    _assert_revision_round_trip(
        postgres_target,
        "base",
        frozenset({"alembic_version"}),
    )


def test_evidence_revision_downgrades_to_decision_foundation_and_reupgrades(
    postgres_target: PostgresTestTarget,
) -> None:
    _assert_revision_round_trip(
        postgres_target,
        "0001_decision_persistence",
        DECISION_TABLE_NAMES | {"alembic_version"},
    )


def test_requirement_revision_downgrades_to_evidence_foundation_and_reupgrades(
    postgres_target: PostgresTestTarget,
) -> None:
    _assert_revision_round_trip(
        postgres_target,
        "0002_evidence_observations",
        (
            POLARIS_TABLE_NAMES
            - {
                "evidence_requirement_set_versions",
                "evidence_requirement_definitions",
            }
        )
        | {"alembic_version"},
    )
