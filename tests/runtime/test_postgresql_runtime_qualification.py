from __future__ import annotations

import asyncio
import sys
import sysconfig
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from polaris.infrastructure.persistence.postgresql import (
    PostgresDecisionStore,
    create_postgres_engine,
)
from polaris.infrastructure.persistence.postgresql.runtime_qualification import (
    require_qualified_postgres_runtime,
)


def test_postgresql_runtime_matches_qualification_boundary() -> None:
    is_gil_enabled = getattr(sys, "_is_gil_enabled", None)
    injected_engine = cast(AsyncEngine, object())

    if is_gil_enabled is not None and not is_gil_enabled():
        blocked_operations = (
            lambda: create_postgres_engine(
                "postgresql+asyncpg://user:pass@localhost/polaris"
            ),
            lambda: PostgresDecisionStore(injected_engine),
        )
        for blocked_operation in blocked_operations:
            with pytest.raises(
                RuntimeError,
                match=(
                    "PostgreSQL persistence is not qualified for GIL-disabled CPython"
                ),
            ):
                blocked_operation()
        return

    engine = create_postgres_engine("postgresql+asyncpg://user:pass@localhost/polaris")
    asyncio.run(engine.dispose())
    PostgresDecisionStore(injected_engine)


def test_runtime_guard_rejects_free_threaded_build_with_gil_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_get_config_var = sysconfig.get_config_var
    monkeypatch.setattr(sys, "_is_gil_enabled", lambda: True, raising=False)
    monkeypatch.setattr(
        sysconfig,
        "get_config_var",
        lambda name: 1 if name == "Py_GIL_DISABLED" else original_get_config_var(name),
    )

    with pytest.raises(
        RuntimeError,
        match="qualified only for standard GIL-enabled CPython 3.14",
    ):
        require_qualified_postgres_runtime()


def test_online_alembic_qualifies_runtime_before_engine_construction() -> None:
    source = Path("migrations/env.py").read_text(encoding="utf-8")
    online = source.split(
        "async def run_migrations_online() -> None:\n",
        maxsplit=1,
    )[1]

    guard_index = online.index("    require_qualified_postgres_runtime()\n")
    engine_index = online.index("    connectable = async_engine_from_config(\n")

    assert guard_index < engine_index
