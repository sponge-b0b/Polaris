from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import cast
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from core.database.models.completed_runs import CompletedRunArtifactModel
from core.database.models.completed_runs import CompletedWorkflowNodeOutputModel
from core.database.models.completed_runs import CompletedWorkflowRunModel
from core.storage.persistence.completed_run_archive import CompletedRunBundle
from core.storage.persistence.completed_run_archive import CompletedRunRecord
from core.storage.persistence.postgres_completed_run_archive import (
    PostgresCompletedRunArchive,
)

TEST_DATABASE_URL = os.environ.get("POLARIS_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="POLARIS_TEST_DATABASE_URL is required for completed-run archive integration tests.",
)


@pytest_asyncio.fixture
async def postgres_session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(
        TEST_DATABASE_URL,
        future=True,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: cast(
                Any, CompletedWorkflowRunModel.__table__
            ).create(
                sync_connection,
                checkfirst=True,
            )
        )
        await connection.run_sync(
            lambda sync_connection: cast(
                Any, CompletedWorkflowNodeOutputModel.__table__
            ).create(
                sync_connection,
                checkfirst=True,
            )
        )
        await connection.run_sync(
            lambda sync_connection: cast(
                Any, CompletedRunArtifactModel.__table__
            ).create(
                sync_connection,
                checkfirst=True,
            )
        )

    yield session_factory

    await engine.dispose()


async def _delete_test_records(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    workflow_name: str,
) -> None:
    async with session_factory() as session:
        await session.execute(
            delete(CompletedWorkflowRunModel).where(
                CompletedWorkflowRunModel.workflow_name == workflow_name,
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_postgres_completed_run_archive_saves_loads_lists_and_deletes(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    workflow_name = f"completed-run-archive-{uuid4().hex}"
    execution_id = f"exec-{uuid4().hex}"
    archive = PostgresCompletedRunArchive(
        session_factory=postgres_session_factory,
    )

    await _delete_test_records(
        postgres_session_factory,
        workflow_name=workflow_name,
    )

    try:
        await archive.archive_run(
            _bundle(
                workflow_name=workflow_name,
                execution_id=execution_id,
                suffix="initial",
            )
        )
        await archive.archive_run(
            _bundle(
                workflow_name=workflow_name,
                execution_id=execution_id,
                suffix="updated",
            )
        )

        loaded = await archive.load_archived_run(
            workflow_name=workflow_name,
            execution_id=execution_id,
        )
        execution_ids = await archive.list_archived_runs(
            workflow_name,
        )

        assert loaded is not None
        assert loaded.run.context_json["suffix"] == "updated"
        assert loaded.run.outputs_json["report"] == "updated report"
        assert execution_ids == [execution_id]

        await archive.delete_archived_run(
            workflow_name=workflow_name,
            execution_id=execution_id,
        )

        deleted = await archive.load_archived_run(
            workflow_name=workflow_name,
            execution_id=execution_id,
        )

        assert deleted is None
    finally:
        await _delete_test_records(
            postgres_session_factory,
            workflow_name=workflow_name,
        )


def _bundle(
    *,
    workflow_name: str,
    execution_id: str,
    suffix: str,
) -> CompletedRunBundle:
    completed_at = datetime(2026, 6, 21, 12, tzinfo=timezone.utc)
    return CompletedRunBundle(
        run=CompletedRunRecord(
            run_id=f"run-{execution_id}",
            workflow_name=workflow_name,
            workflow_id=workflow_name,
            execution_id=execution_id,
            runtime_id=f"runtime-{suffix}",
            status="succeeded",
            success=True,
            context_json={
                "execution_id": execution_id,
                "workflow_id": workflow_name,
                "suffix": suffix,
                "score": 0.12345678901234568,
            },
            inputs_json={"symbols": ["SPY"]},
            outputs_json={"report": f"{suffix} report"},
            metadata={"source": "archive-integration-test", "suffix": suffix},
            errors_json=[],
            started_at=completed_at,
            completed_at=completed_at,
            duration_seconds=1.2345678901234567,
            node_count=0,
            completed_node_count=0,
            failed_node_count=0,
        )
    )
