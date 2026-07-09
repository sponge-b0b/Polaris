from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from pytest_alembic import Config as PytestAlembicConfig
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url

from core.database.base import Base

# Import model modules so SQLAlchemy attaches them to Base.metadata.
import core.database.models  # noqa: F401


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _sync_database_url(database_url: str) -> str:
    url = make_url(database_url)
    sync_url = url.set(drivername="postgresql+psycopg2")
    return sync_url.render_as_string(hide_password=False)


def _create_schema(
    engine: Engine,
    schema_name: str,
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(f"CREATE SCHEMA {_quote_identifier(schema_name)}"),
        )


def _drop_schema(
    engine: Engine,
    schema_name: str,
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(f"DROP SCHEMA IF EXISTS {_quote_identifier(schema_name)} CASCADE"),
        )


@pytest.fixture()
def test_database_url() -> str:
    database_url = os.environ.get("POLARIS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(
            "POLARIS_TEST_DATABASE_URL is required for migration contract tests"
        )
    return database_url


@pytest.fixture()
def migration_test_schema() -> str:
    return f"polaris_migration_test_{uuid.uuid4().hex}"


@pytest.fixture()
def alembic_engine(
    test_database_url: str,
    migration_test_schema: str,
) -> Iterator[Engine]:
    sync_url = _sync_database_url(test_database_url)
    admin_engine = create_engine(sync_url)
    test_engine = create_engine(
        sync_url,
        connect_args={
            "options": f"-csearch_path={migration_test_schema}",
        },
    )

    _create_schema(admin_engine, migration_test_schema)
    try:
        yield test_engine
    finally:
        test_engine.dispose()
        _drop_schema(admin_engine, migration_test_schema)
        admin_engine.dispose()


@pytest.fixture()
def alembic_config(
    test_database_url: str,
) -> PytestAlembicConfig:
    return PytestAlembicConfig(
        config_options={
            "file": "alembic.ini",
            "script_location": "migrations",
            "sqlalchemy.url": test_database_url,
            "target_metadata": Base.metadata,
            "include_schemas": False,
        },
    )
