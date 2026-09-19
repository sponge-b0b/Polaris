"""Alembic environment for the greenfield Polaris migration lineage."""

from __future__ import annotations

import asyncio
import os
import re
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool, text
from sqlalchemy.ext.asyncio import async_engine_from_config

from polaris.infrastructure.persistence.postgresql.runtime_qualification import (
    require_qualified_postgres_runtime,
)
from polaris.infrastructure.persistence.postgresql.schema import metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata
_SCHEMA_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _database_url() -> str:
    value = os.environ.get("POLARIS_DATABASE_URL")
    if not value:
        raise RuntimeError("POLARIS_DATABASE_URL is required for migrations")
    if not value.startswith("postgresql+asyncpg://"):
        raise RuntimeError(
            "POLARIS_DATABASE_URL must use the postgresql+asyncpg driver"
        )
    return value


def _schema() -> str | None:
    value = os.environ.get("POLARIS_DATABASE_SCHEMA")
    if value is None:
        return None
    if _SCHEMA_NAME.fullmatch(value) is None:
        raise RuntimeError("POLARIS_DATABASE_SCHEMA must be a PostgreSQL identifier")
    return value


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    require_qualified_postgres_runtime()
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _database_url()
    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    try:
        async with connectable.connect() as connection:
            schema = _schema()
            if schema is not None:
                await connection.execute(text(f'SET search_path TO "{schema}"'))
                await connection.commit()
            await connection.run_sync(_run_migrations)
    finally:
        await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
