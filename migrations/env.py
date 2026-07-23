from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    async_engine_from_config,
)

# Import model modules so SQLAlchemy attaches them to Base.metadata.
import core.database.models  # noqa: F401
from core.database.base import Base
from core.database.settings import PostgresSettings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = config.attributes.get("target_metadata", Base.metadata)


def _database_url() -> str:
    configured_url = config.get_main_option("sqlalchemy.url")

    if configured_url and configured_url.strip():
        return configured_url

    return PostgresSettings.from_env().async_database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(
    connection: Connection,
) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=config.attributes.get("include_schemas", False),
        process_revision_directives=config.attributes.get(
            "process_revision_directives",
        ),
    )

    with context.begin_transaction():
        context.run_migrations()


def _create_async_engine() -> AsyncEngine:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _database_url()

    return async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )


async def _run_async_migrations(
    connection: AsyncConnection,
) -> None:
    await connection.run_sync(do_run_migrations)


async def run_migrations_online() -> None:
    injected_connection = config.attributes.get("connection")

    if isinstance(injected_connection, AsyncEngine):
        async with injected_connection.connect() as connection:
            await _run_async_migrations(connection)
        return

    if isinstance(injected_connection, AsyncConnection):
        await _run_async_migrations(injected_connection)
        return

    if isinstance(injected_connection, Engine):
        with injected_connection.connect() as connection:
            do_run_migrations(connection)
        return

    if isinstance(injected_connection, Connection):
        do_run_migrations(injected_connection)
        return

    connectable = _create_async_engine()
    try:
        async with connectable.connect() as connection:
            await _run_async_migrations(connection)
    finally:
        await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_migrations_online())
