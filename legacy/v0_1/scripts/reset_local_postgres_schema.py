from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.util.exc import CommandError
from dotenv import load_dotenv
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine

from application.persistence.health import HealthPersistenceService
from core.database.settings import PostgresSettings
from core.storage.persistence.health import PersistenceHealthReport

LOCAL_DATABASE_HOSTS = frozenset(
    {
        "",
        "localhost",
        "127.0.0.1",
        "::1",
        "postgres",
    }
)
PROTECTED_DATABASE_NAMES = frozenset(
    {
        "postgres",
        "template0",
        "template1",
    }
)
CONFIRM_DESTROY_LOCAL_DB_FLAG = "--confirm-destroy-local-db"


def main(
    argv: Sequence[str] | None = None,
) -> int:
    parser = _build_parser()
    args = parser.parse_args(
        argv,
    )
    if not args.confirm_destroy_local_db:
        print(
            f"Refusing to reset PostgreSQL without {CONFIRM_DESTROY_LOCAL_DB_FLAG}.",
            file=sys.stderr,
        )
        return 2

    load_dotenv(
        dotenv_path=Path(
            ".env",
        ),
    )
    try:
        settings = _load_settings()
        database_url = _local_database_url(
            settings,
        )
        target = _describe_database_target(
            database_url,
        )
        print(
            f"Resetting local PostgreSQL public schema for {target}...",
            flush=True,
        )
        asyncio.run(
            _reset_public_schema(
                settings,
            )
        )
        print(
            "Applying Alembic migrations to head...",
            flush=True,
        )
        _upgrade_database_to_head()
        report = asyncio.run(
            _load_persistence_health_report(),
        )
        unhealthy_checks = tuple(
            report.unhealthy_checks,
        )
        if unhealthy_checks:
            print(
                "Local PostgreSQL reset completed, but persistence diagnostics "
                "reported unhealthy checks:",
                file=sys.stderr,
            )
            for check in unhealthy_checks:
                print(
                    f"- {check.check_name}: {check.message}",
                    file=sys.stderr,
                )
            return 1
    except (CommandError, SQLAlchemyError, ValueError) as exc:
        print(
            f"Local PostgreSQL reset failed: {exc}",
            file=sys.stderr,
        )
        return 1

    print(
        "Local PostgreSQL schema is current and matches SQLAlchemy metadata.",
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Destructively reset the local Polaris PostgreSQL public schema, "
            "apply Alembic head, and verify schema drift."
        ),
    )
    parser.add_argument(
        CONFIRM_DESTROY_LOCAL_DB_FLAG,
        action="store_true",
        help="Required confirmation; destroys all data in the configured local DB.",
    )
    return parser


def _load_settings() -> PostgresSettings:
    return PostgresSettings.from_env()


def _local_database_url(
    settings: PostgresSettings,
) -> URL:
    database_url = make_url(
        settings.async_database_url,
    )
    _validate_local_database_url(
        database_url,
    )
    return database_url


def _validate_local_database_url(
    database_url: URL,
) -> None:
    host = database_url.host or ""
    database = database_url.database
    if host not in LOCAL_DATABASE_HOSTS:
        raise ValueError(
            f"Refusing destructive reset for non-local database host: {host!r}."
        )
    if database is None or not database.strip():
        raise ValueError(
            "Refusing destructive reset because the database name is empty."
        )
    if database.lower() in PROTECTED_DATABASE_NAMES:
        raise ValueError(
            f"Refusing destructive reset for protected database: {database!r}."
        )


def _describe_database_target(
    database_url: URL,
) -> str:
    host = database_url.host or "localhost"
    database = database_url.database or "<unknown>"
    return f"host={host!r} database={database!r}"


async def _reset_public_schema(
    settings: PostgresSettings,
) -> None:
    engine = create_async_engine(
        settings.async_database_url,
        future=True,
        isolation_level="AUTOCOMMIT",
    )
    try:
        async with engine.begin() as connection:
            await connection.exec_driver_sql(
                "DROP SCHEMA IF EXISTS public CASCADE",
            )
            await connection.exec_driver_sql(
                "CREATE SCHEMA public",
            )
    finally:
        await engine.dispose()


def _upgrade_database_to_head() -> None:
    command.upgrade(
        Config(
            "alembic.ini",
        ),
        "head",
    )


async def _load_persistence_health_report() -> PersistenceHealthReport:
    return await HealthPersistenceService().check_health()


if __name__ == "__main__":
    raise SystemExit(
        main(),
    )
