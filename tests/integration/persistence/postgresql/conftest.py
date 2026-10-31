from __future__ import annotations

import asyncio
import hashlib
import os
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Table, delete, func, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from polaris.domain.decisions import DecisionRelationshipFactId, InvestmentDecisionId
from polaris.infrastructure.persistence.postgresql import (
    PostgresDecisionStore,
    create_postgres_engine,
)
from polaris.infrastructure.persistence.postgresql.runtime_qualification import (
    require_qualified_postgres_runtime,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    investment_decision_relationships,
)


@dataclass(frozen=True, slots=True)
class PostgresTestTarget:
    database_url: str
    schema: str


class ConcurrentCandidateReadStore(PostgresDecisionStore):
    """Pause candidate discovery after its read for concurrent-write proofs."""

    def __init__(self, engine: AsyncEngine, barrier: asyncio.Barrier) -> None:
        super().__init__(engine)
        self._barrier = barrier

    async def find_unresolved_continuity_candidates(
        self, *, known_at: datetime
    ) -> tuple[InvestmentDecisionId, ...]:
        candidates = await super().find_unresolved_continuity_candidates(
            known_at=known_at
        )
        await self._barrier.wait()
        return candidates


@asynccontextmanager
async def postgres_store[StoreT](
    target: PostgresTestTarget,
    store_type: Callable[[AsyncEngine], StoreT],
) -> AsyncIterator[tuple[AsyncEngine, StoreT]]:
    engine = create_postgres_engine(target.database_url, schema=target.schema)
    try:
        yield engine, store_type(engine)
    finally:
        await engine.dispose()


@asynccontextmanager
async def postgres_engine_store(
    target: PostgresTestTarget,
    *,
    store_type: type[PostgresDecisionStore] = PostgresDecisionStore,
) -> AsyncIterator[tuple[AsyncEngine, PostgresDecisionStore]]:
    async with postgres_store(target, store_type) as pair:
        yield pair


async def postgres_row_counts(
    engine: AsyncEngine,
    *tables: Table,
) -> tuple[int, ...]:
    async with engine.connect() as connection:
        counts: list[int] = []
        for table in tables:
            count = await connection.scalar(select(func.count()).select_from(table))
            if count is None:
                raise AssertionError("PostgreSQL row count query returned no result")
            counts.append(count)
    return tuple(counts)


async def assert_intelligence_table_immutable(
    engine: AsyncEngine, table: Table
) -> None:
    key = next(iter(table.primary_key.columns))
    row = select(key).limit(1).scalar_subquery()
    async with engine.connect() as connection:
        assert await connection.scalar(select(func.count()).select_from(table)) > 0
    for statement in (
        update(table).where(key == row).values({key.name: key}),
        delete(table).where(key == row),
    ):
        with pytest.raises(
            DBAPIError,
            match="immutable Investment Intelligence facts cannot be changed",
        ):
            async with engine.begin() as connection:
                await connection.execute(statement)


async def corrupt_relationship_lineage_source(
    engine: AsyncEngine,
    *,
    relationship_fact_id: DecisionRelationshipFactId,
    source_decision_id: InvestmentDecisionId,
) -> None:
    """Corrupt one persisted correction lineage for fail-closed read tests."""
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "ALTER TABLE investment_decision_relationships "
                "DISABLE TRIGGER "
                "trg_investment_decision_relationships_immutable"
            )
        )
        try:
            await connection.execute(
                investment_decision_relationships.update()
                .where(
                    investment_decision_relationships.c.relationship_fact_id
                    == relationship_fact_id.value
                )
                .values(source_decision_id=source_decision_id.value)
            )
        finally:
            await connection.execute(
                text(
                    "ALTER TABLE investment_decision_relationships "
                    "ENABLE TRIGGER "
                    "trg_investment_decision_relationships_immutable"
                )
            )


async def _execute_schema_ddl(database_url: str, statement: str) -> None:
    require_qualified_postgres_runtime()
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text(statement))
    finally:
        await engine.dispose()


async def _create_schema(database_url: str, schema: str) -> None:
    await _execute_schema_ddl(database_url, f'CREATE SCHEMA "{schema}"')


async def _drop_schema(database_url: str, schema: str) -> None:
    await _execute_schema_ddl(
        database_url,
        f'DROP SCHEMA IF EXISTS "{schema}" CASCADE',
    )


async def _drop_intelligence_commit_log(database_url: str, schema: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            connection = await connection.execution_options(
                isolation_level="AUTOCOMMIT"
            )
            database = await connection.scalar(text("SELECT current_database()"))
            identity = f"{database}:{schema}".encode()
            suffix = hashlib.md5(identity, usedforsecurity=False).hexdigest()[:32]
            slot = f"polaris_ii_{suffix}"
            exists = await connection.scalar(
                text("SELECT 1 FROM pg_replication_slots WHERE slot_name = :slot"),
                {"slot": slot},
            )
            if exists:
                await connection.execute(
                    text("SELECT pg_drop_replication_slot(:slot)"), {"slot": slot}
                )
            await connection.execute(text(f'DROP PUBLICATION IF EXISTS "{slot}"'))
    finally:
        await engine.dispose()


@pytest.fixture
def postgres_target(monkeypatch: pytest.MonkeyPatch) -> Iterator[PostgresTestTarget]:
    database_url = os.environ.get("POLARIS_TEST_DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "POLARIS_TEST_DATABASE_URL is required for PostgreSQL contract tests"
        )
    if not database_url.startswith("postgresql+asyncpg://"):
        raise RuntimeError(
            "POLARIS_TEST_DATABASE_URL must use the postgresql+asyncpg driver"
        )
    schema = f"polaris_test_{uuid4().hex}"
    asyncio.run(_create_schema(database_url, schema))
    monkeypatch.setenv("POLARIS_DATABASE_URL", database_url)
    monkeypatch.setenv("POLARIS_DATABASE_SCHEMA", schema)
    alembic = Config("alembic.ini")
    try:
        command.upgrade(alembic, "head")
        yield PostgresTestTarget(database_url, schema)
    finally:
        asyncio.run(_drop_schema(database_url, schema))
        asyncio.run(_drop_intelligence_commit_log(database_url, schema))
