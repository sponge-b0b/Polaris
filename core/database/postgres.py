from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.database.settings import PostgresSettings

database_settings = PostgresSettings.from_env()
DATABASE_URL = database_settings.async_database_url


def create_database_engine(
    settings: PostgresSettings | None = None,
) -> AsyncEngine:
    resolved_settings = settings or PostgresSettings.from_env()

    return create_async_engine(
        resolved_settings.async_database_url,
        echo=resolved_settings.echo,
        future=True,
        pool_pre_ping=resolved_settings.pool_pre_ping,
    )


engine = create_database_engine(
    database_settings,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


__all__ = [
    "AsyncSessionLocal",
    "DATABASE_URL",
    "create_database_engine",
    "database_settings",
    "engine",
]
