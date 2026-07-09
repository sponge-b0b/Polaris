from __future__ import annotations

import asyncio

from core.database.base import Base
from core.database.postgres import engine

# Import model modules so SQLAlchemy attaches them to Base.metadata.
import core.database.models  # noqa: F401


async def initialize_database() -> None:
    """
    Local development helper for creating tables directly from metadata.

    Production and durable schema evolution should use Alembic migrations.
    This helper remains available for quick local experiments only.
    """

    async with engine.begin() as conn:
        print("Initializing database tables from SQLAlchemy metadata...")
        print("For durable schema changes, use Alembic migrations instead.")
        await conn.run_sync(Base.metadata.create_all)
        print("Tables initialized successfully!")


if __name__ == "__main__":
    asyncio.run(initialize_database())
