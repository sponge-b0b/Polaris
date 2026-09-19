from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Table, func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from polaris.infrastructure.persistence.postgresql import (
    PostgresDecisionStore,
    create_postgres_engine,
)
from polaris.infrastructure.persistence.postgresql.runtime_qualification import (
    require_qualified_postgres_runtime,
)


@dataclass(frozen=True, slots=True)
class PostgresTestTarget:
    database_url: str
    schema: str


@asynccontextmanager
async def postgres_engine_store(
    target: PostgresTestTarget,
    *,
    store_type: type[PostgresDecisionStore] = PostgresDecisionStore,
) -> AsyncIterator[tuple[AsyncEngine, PostgresDecisionStore]]:
    engine = create_postgres_engine(target.database_url, schema=target.schema)
    try:
        yield engine, store_type(engine)
    finally:
        await engine.dispose()


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
