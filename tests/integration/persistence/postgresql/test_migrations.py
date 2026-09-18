from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from polaris.infrastructure.persistence.postgresql import (
    DECISION_TABLE_NAMES,
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
    # duplicate-code: migration assertions prove separate schema invariants; sharing the repeated assertion shape would couple independently meaningful migration checks.
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
    # duplicate-code: migration assertions prove separate schema invariants; sharing the repeated assertion shape would couple independently meaningful migration checks.
    # arid: disable
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


def test_fresh_root_migrates_only_greenfield_decision_schema(
    postgres_target: PostgresTestTarget,
) -> None:
    migration = Path("migrations/versions/0001_decision_persistence_foundation.py")
    source = migration.read_text(encoding="utf-8")
    assert "down_revision: str | None = None" in source
    assert "legacy" not in source.lower()

    tables = asyncio.run(_table_names(postgres_target))
    assert tables == DECISION_TABLE_NAMES | {"alembic_version"}
    assert not {
        table
        for table in tables
        if any(fragment in table for fragment in FORBIDDEN_TABLE_FRAGMENTS)
    }

    column_types = asyncio.run(_identity_column_types(postgres_target))
    assert column_types
    for (_, column_name), data_type in column_types.items():
        assert data_type == ("int8" if column_name == "row_id" else "uuid")

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
    alembic = Config("alembic.ini")
    command.downgrade(alembic, "base")
    assert asyncio.run(_table_names(postgres_target)) == frozenset({"alembic_version"})

    command.upgrade(alembic, "head")
    assert asyncio.run(_table_names(postgres_target)) == (
        DECISION_TABLE_NAMES | {"alembic_version"}
    )
