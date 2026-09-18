from __future__ import annotations

import asyncio
import sys

import pytest

from polaris.infrastructure.persistence.postgresql import create_postgres_engine


def test_postgresql_runtime_matches_qualification_boundary() -> None:
    is_gil_enabled = getattr(sys, "_is_gil_enabled", None)
    if is_gil_enabled is not None and not is_gil_enabled():
        with pytest.raises(
            RuntimeError,
            match="PostgreSQL persistence is not qualified for GIL-disabled CPython",
        ):
            create_postgres_engine("postgresql+asyncpg://user:pass@localhost/polaris")
        return

    engine = create_postgres_engine(
        "postgresql+asyncpg://user:pass@localhost/polaris"
    )
    asyncio.run(engine.dispose())
