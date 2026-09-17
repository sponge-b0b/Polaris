from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator
from dataclasses import dataclass
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


@dataclass(frozen=True, slots=True)
class PostgresTestTarget:
    database_url: str
    schema: str


async def _create_schema(database_url: str, schema: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    finally:
        await engine.dispose()


async def _drop_schema(database_url: str, schema: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
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
