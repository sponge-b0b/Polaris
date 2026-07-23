from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.database.models.completed_runs import (
    CompletedRunArtifactModel,
    CompletedWorkflowNodeOutputModel,
    CompletedWorkflowRunModel,
)
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunArtifactRecord,
    CompletedRunBundle,
    CompletedRunRecord,
)
from core.storage.persistence.repositories.postgres_completed_run_repository import (
    PostgresCompletedRunRepository,
)

TEST_DATABASE_URL = os.environ.get("POLARIS_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason=(
        "POLARIS_TEST_DATABASE_URL is required for completed-run repository "
        "integration tests."
    ),
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
async def test_postgres_completed_run_repository_saves_loads_lists_and_deletes(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    workflow_name = f"completed-run-repository-{uuid4().hex}"
    execution_id = f"exec-{uuid4().hex}"
    bundle = _bundle(
        workflow_name=workflow_name,
        execution_id=execution_id,
        suffix="initial",
    )
    updated_bundle = _bundle(
        workflow_name=workflow_name,
        execution_id=execution_id,
        suffix="updated",
    )

    await _delete_test_records(
        postgres_session_factory,
        workflow_name=workflow_name,
    )

    try:
        async with postgres_session_factory() as session:
            repository = PostgresCompletedRunRepository(session)
            await repository.persist_completed_run_bundle(bundle)
            await repository.persist_completed_run_bundle(updated_bundle)

        async with postgres_session_factory() as session:
            repository = PostgresCompletedRunRepository(session)
            loaded = await repository.load_completed_run_bundle(
                workflow_name=workflow_name,
                execution_id=execution_id,
            )
            execution_ids = await repository.list_completed_run_ids(workflow_name)

        assert loaded is not None
        assert loaded.run.execution_id == execution_id
        assert loaded.run.context_json["suffix"] == "updated"
        assert loaded.run.outputs_json["report"] == "updated report"
        assert loaded.node_outputs == updated_bundle.node_outputs
        assert loaded.artifacts == updated_bundle.artifacts
        assert execution_ids == [execution_id]

        async with postgres_session_factory() as session:
            repository = PostgresCompletedRunRepository(session)
            await repository.delete_completed_run(
                workflow_name=workflow_name,
                execution_id=execution_id,
            )

        async with postgres_session_factory() as session:
            repository = PostgresCompletedRunRepository(session)
            deleted = await repository.load_completed_run_bundle(
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
    run_id = f"run-{execution_id}"
    completed_at = datetime(2026, 6, 21, 12, tzinfo=UTC)
    return CompletedRunBundle(
        run=CompletedRunRecord(
            run_id=run_id,
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
            metadata={"source": "integration-test", "suffix": suffix},
            errors_json=[],
            started_at=completed_at,
            completed_at=completed_at,
            duration_seconds=1.2345678901234567,
            node_count=1,
            completed_node_count=1,
            failed_node_count=0,
        ),
        node_outputs=(
            CompletedNodeOutputRecord(
                node_output_id=f"node-{execution_id}",
                run_id=run_id,
                workflow_name=workflow_name,
                execution_id=execution_id,
                node_name="technical_analysis",
                node_type="runtime",
                output_contract="polaris.market.technical_analysis",
                output_schema_version=1,
                status="succeeded",
                success=True,
                outputs={"technical_score": 0.12345678901234568, "suffix": suffix},
                metadata={"source": "integration-test", "suffix": suffix},
                errors_json=[],
                started_at=completed_at,
                completed_at=completed_at,
                duration_seconds=1.2345678901234567,
            ),
        ),
        artifacts=(
            CompletedRunArtifactRecord(
                artifact_id=f"artifact-{execution_id}",
                run_id=run_id,
                workflow_name=workflow_name,
                execution_id=execution_id,
                artifact_type="markdown",
                artifact_name=f"{suffix}.md",
                artifact_path=f"reports/{suffix}.md",
                mime_type="text/markdown",
                size_bytes=2048,
                metadata={"source": "integration-test", "suffix": suffix},
            ),
        ),
    )
