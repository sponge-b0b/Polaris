from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import ClassVar
from urllib.parse import quote


@dataclass(frozen=True, slots=True)
class PostgresSettings:
    """
    Typed PostgreSQL connection settings.

    `POLARIS_DATABASE_URL` is the preferred override. When absent, the settings
    derive a URL from Polaris-specific environment variables and compose-aligned
    defaults.
    """

    DEFAULT_HOST: ClassVar[str] = "localhost"
    DEFAULT_PORT: ClassVar[int] = 5432
    DEFAULT_DATABASE: ClassVar[str] = "polaris"
    DEFAULT_USER: ClassVar[str] = "polaris"
    DEFAULT_DRIVER: ClassVar[str] = "asyncpg"
    DEFAULT_ECHO: ClassVar[bool] = False
    DEFAULT_POOL_PRE_PING: ClassVar[bool] = True

    database_url: str | None = field(default=None, repr=False)
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    database: str = DEFAULT_DATABASE
    user: str = DEFAULT_USER
    password: str | None = field(default=None, repr=False)
    driver: str = DEFAULT_DRIVER
    echo: bool = DEFAULT_ECHO
    pool_pre_ping: bool = DEFAULT_POOL_PRE_PING

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
    ) -> PostgresSettings:
        source = os.environ if env is None else env

        database_url = _blank_to_none(
            source.get("POLARIS_DATABASE_URL"),
        )

        return cls(
            database_url=database_url,
            host=source.get(
                "POLARIS_POSTGRES_HOST",
                cls.DEFAULT_HOST,
            ),
            port=_parse_int(
                source.get("POLARIS_POSTGRES_PORT"),
                cls.DEFAULT_PORT,
                name="POLARIS_POSTGRES_PORT",
            ),
            database=source.get(
                "POLARIS_POSTGRES_DB",
                cls.DEFAULT_DATABASE,
            ),
            user=source.get(
                "POLARIS_POSTGRES_USER",
                cls.DEFAULT_USER,
            ),
            password=_blank_to_none(
                source.get("POLARIS_POSTGRES_PASSWORD"),
            ),
            driver=source.get(
                "POLARIS_POSTGRES_DRIVER",
                cls.DEFAULT_DRIVER,
            ),
            echo=_parse_bool(
                source.get("POLARIS_POSTGRES_ECHO"),
                cls.DEFAULT_ECHO,
            ),
            pool_pre_ping=_parse_bool(
                source.get("POLARIS_POSTGRES_POOL_PRE_PING"),
                cls.DEFAULT_POOL_PRE_PING,
            ),
        )

    @property
    def async_database_url(
        self,
    ) -> str:
        if self.database_url is not None:
            return _normalize_async_database_url(
                self.database_url,
                driver=self.driver,
            )

        if self.password is None:
            raise ValueError(
                "POLARIS_POSTGRES_PASSWORD is required when "
                "POLARIS_DATABASE_URL is not set.",
            )

        user = quote(
            self.user,
            safe="",
        )
        password = quote(
            self.password,
            safe="",
        )
        database = quote(
            self.database,
            safe="",
        )

        return (
            f"postgresql+{self.driver}://"
            f"{user}:{password}@{self.host}:{self.port}/{database}"
        )


def _normalize_async_database_url(
    database_url: str,
    *,
    driver: str,
) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url

    if database_url.startswith("postgresql://"):
        return database_url.replace(
            "postgresql://",
            f"postgresql+{driver}://",
            1,
        )

    return database_url


def _parse_bool(
    value: str | None,
    default: bool,
) -> bool:
    if value is None:
        return default

    normalized = value.strip().lower()

    if normalized in {"1", "true", "yes", "on"}:
        return True

    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ValueError(
        f"Invalid boolean value: {value!r}",
    )


def _parse_int(
    value: str | None,
    default: int,
    *,
    name: str,
) -> int:
    if value is None:
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(
            f"{name} must be an integer.",
        ) from exc


def _blank_to_none(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    return value


__all__ = [
    "PostgresSettings",
]
