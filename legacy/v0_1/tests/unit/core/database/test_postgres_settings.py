from __future__ import annotations

from secrets import token_urlsafe
from urllib.parse import unquote, urlsplit

import pytest

from core.database.settings import PostgresSettings


def test_postgres_settings_requires_password_without_database_url() -> None:
    settings = PostgresSettings.from_env({})

    with pytest.raises(
        ValueError,
        match="POLARIS_POSTGRES_PASSWORD is required",
    ):
        _ = settings.async_database_url


def test_postgres_settings_prefers_polaris_database_url() -> None:
    database_url = "postgresql+asyncpg://db.example.invalid:5433/app"
    settings = PostgresSettings.from_env(
        {
            "POLARIS_DATABASE_URL": database_url,
            "POLARIS_POSTGRES_DB": "ignored",
        }
    )

    assert settings.async_database_url == database_url


def test_postgres_settings_normalizes_plain_postgresql_url() -> None:
    database_url = "postgresql://db.example.invalid:5433/app"
    settings = PostgresSettings.from_env(
        {
            "POLARIS_DATABASE_URL": database_url,
        }
    )

    assert (
        settings.async_database_url
        == "postgresql+asyncpg://db.example.invalid:5433/app"
    )


def test_postgres_settings_derives_url_from_polaris_postgres_parts() -> None:
    password = f"{token_urlsafe(16)} @"
    settings = PostgresSettings.from_env(
        {
            "POLARIS_POSTGRES_HOST": "postgres.internal",
            "POLARIS_POSTGRES_PORT": "5544",
            "POLARIS_POSTGRES_DB": "research",
            "POLARIS_POSTGRES_USER": "analyst",
            "POLARIS_POSTGRES_PASSWORD": password,
        }
    )

    parsed_url = urlsplit(settings.async_database_url)

    assert parsed_url.scheme == "postgresql+asyncpg"
    assert parsed_url.username == "analyst"
    assert parsed_url.password is not None
    assert unquote(parsed_url.password) == password
    assert parsed_url.hostname == "postgres.internal"
    assert parsed_url.port == 5544
    assert parsed_url.path == "/research"


def test_postgres_settings_repr_does_not_expose_credentials() -> None:
    password = token_urlsafe(16)
    database_url = "".join(
        (
            "postgresql+asyncpg://analyst:",
            password,
            "@postgres.internal:5544/research",
        )
    )

    settings = PostgresSettings.from_env(
        {
            "POLARIS_DATABASE_URL": database_url,
            "POLARIS_POSTGRES_PASSWORD": password,
        }
    )

    rendered = repr(settings)

    assert password not in rendered
    assert database_url not in rendered


def test_postgres_settings_invalid_port_raises() -> None:
    with pytest.raises(
        ValueError,
        match="POLARIS_POSTGRES_PORT must be an integer",
    ):
        PostgresSettings.from_env(
            {
                "POLARIS_POSTGRES_PORT": "invalid",
            }
        )


def test_postgres_settings_invalid_bool_raises() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid boolean value",
    ):
        PostgresSettings.from_env(
            {
                "POLARIS_POSTGRES_ECHO": "sometimes",
            }
        )
