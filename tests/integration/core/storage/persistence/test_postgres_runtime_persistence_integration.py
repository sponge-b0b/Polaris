from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import datetime
from datetime import timezone
from typing import cast
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import Table
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from core.database.models.runtime import WorkflowEventModel
from core.database.models.runtime import WorkflowNodeRunModel
from core.database.models.runtime import WorkflowRunModel
from core.runtime.events import EventBus
from core.runtime.events import RuntimeEvent
from core.runtime.events import RuntimeEventType
from core.storage.persistence.repositories.postgres_runtime_persistence_repository import (
    PostgresRuntimePersistenceRepository,
)
from core.storage.persistence.runtime import RuntimePersistenceEventSubscriber
from core.storage.persistence.runtime import WorkflowEventRecord
from core.storage.persistence.runtime import WorkflowNodeRunRecord
from core.storage.persistence.runtime import WorkflowRunRecord

TEST_DATABASE_URL = os.environ.get("POLARIS_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="POLARIS_TEST_DATABASE_URL is required for Postgres persistence integration tests.",
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
                Table,
                WorkflowRunModel.__table__,
            ).create(
                sync_connection,
                checkfirst=True,
            )
        )
        await connection.run_sync(
            lambda sync_connection: cast(
                Table,
                WorkflowNodeRunModel.__table__,
            ).create(
                sync_connection,
                checkfirst=True,
            )
        )
        await connection.run_sync(
            lambda sync_connection: cast(
                Table,
                WorkflowEventModel.__table__,
            ).create(
                sync_connection,
                checkfirst=True,
            )
        )

    yield session_factory

    await engine.dispose()


async def _delete_test_records(
    session_factory: async_sessionmaker[AsyncSession],
    execution_id: str,
) -> None:
    async with session_factory() as session:
        await session.execute(
            delete(WorkflowEventModel).where(
                WorkflowEventModel.execution_id == execution_id,
            )
        )
        await session.execute(
            delete(WorkflowNodeRunModel).where(
                WorkflowNodeRunModel.execution_id == execution_id,
            )
        )
        await session.execute(
            delete(WorkflowRunModel).where(
                WorkflowRunModel.execution_id == execution_id,
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_postgres_runtime_repository_persists_and_reads_runtime_records(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    execution_id = f"runtime-repository-{uuid4().hex}"
    started_at = datetime(2026, 5, 30, 15, tzinfo=timezone.utc)
    completed_at = datetime(2026, 5, 30, 15, 1, tzinfo=timezone.utc)
    await _delete_test_records(
        postgres_session_factory,
        execution_id,
    )

    try:
        async with postgres_session_factory() as session:
            repository = PostgresRuntimePersistenceRepository(session)

            workflow_result = await repository.persist_workflow_run(
                WorkflowRunRecord(
                    workflow_name="morning_report",
                    execution_id=execution_id,
                    runtime_id="runtime-1",
                    status="started",
                    started_at=started_at,
                    mode="simulation",
                    metadata={"source": "integration-test"},
                    state_payload={"phase": "started"},
                )
            )
            node_result = await repository.persist_node_run(
                WorkflowNodeRunRecord(
                    workflow_name="morning_report",
                    execution_id=execution_id,
                    runtime_id="runtime-1",
                    node_name="macro_node",
                    wave_index=0,
                    status="succeeded",
                    completed_at=completed_at,
                    outputs={"macro_signal": {"confidence": 0.82}},
                )
            )
            event_result = await repository.persist_event(
                WorkflowEventRecord(
                    event_id=f"event-{uuid4().hex}",
                    event_type="runtime.node.completed",
                    workflow_name="morning_report",
                    execution_id=execution_id,
                    runtime_id="runtime-1",
                    node_name="macro_node",
                    wave_index=0,
                    timestamp=completed_at,
                    payload={"success": True},
                    metadata={"workflow_name": "morning_report"},
                )
            )

            assert workflow_result.success is True
            assert node_result.success is True
            assert event_result.success is True

        async with postgres_session_factory() as session:
            repository = PostgresRuntimePersistenceRepository(session)
            workflow = await repository.get_workflow_run(
                workflow_name="morning_report",
                execution_id=execution_id,
            )
            nodes = await repository.list_node_runs(
                workflow_name="morning_report",
                execution_id=execution_id,
            )
            events = await repository.list_events(
                workflow_name="morning_report",
                execution_id=execution_id,
            )

        assert workflow is not None
        assert workflow.workflow_name == "morning_report"
        assert workflow.started_at == started_at
        assert workflow.metadata == {"source": "integration-test"}
        assert len(nodes) == 1
        assert nodes[0].outputs == {"macro_signal": {"confidence": 0.82}}
        assert len(events) == 1
        assert events[0].event_type == "runtime.node.completed"
    finally:
        await _delete_test_records(
            postgres_session_factory,
            execution_id,
        )


@pytest.mark.asyncio
async def test_event_bus_subscriber_projects_runtime_events_to_postgres(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    execution_id = f"runtime-subscriber-{uuid4().hex}"
    timestamp = datetime(2026, 5, 30, 15, 5, tzinfo=timezone.utc)
    await _delete_test_records(
        postgres_session_factory,
        execution_id,
    )

    event_bus = EventBus(
        fail_fast=True,
    )
    subscriber = RuntimePersistenceEventSubscriber(
        session_factory=postgres_session_factory,
    )
    subscriber.subscribe(event_bus)

    try:
        await event_bus.emit(
            RuntimeEvent(
                event_type=RuntimeEventType.WORKFLOW_PROGRESS_STARTED,
                workflow_id="workflow-id-1",
                execution_id=execution_id,
                runtime_id="runtime-1",
                timestamp=timestamp,
                payload={
                    "workflow_name": "morning_report",
                    "state": "started",
                },
                metadata={
                    "workflow_name": "morning_report",
                    "mode": "simulation",
                },
            )
        )
        await event_bus.emit(
            RuntimeEvent(
                event_type=RuntimeEventType.NODE_PROGRESS_COMPLETED,
                workflow_id="workflow-id-1",
                execution_id=execution_id,
                runtime_id="runtime-1",
                node_name="macro_node",
                wave_index=0,
                timestamp=timestamp,
                payload={
                    "workflow_name": "morning_report",
                    "success": True,
                    "duration_seconds": 2.5,
                },
                metadata={
                    "workflow_name": "morning_report",
                },
            )
        )

        async with postgres_session_factory() as session:
            repository = PostgresRuntimePersistenceRepository(session)
            workflow = await repository.get_workflow_run(
                workflow_name="morning_report",
                execution_id=execution_id,
            )
            nodes = await repository.list_node_runs(
                workflow_name="morning_report",
                execution_id=execution_id,
            )
            events = await repository.list_events(
                workflow_name="morning_report",
                execution_id=execution_id,
            )

        assert workflow is not None
        assert workflow.status == "started"
        assert len(nodes) == 1
        assert nodes[0].node_name == "macro_node"
        assert nodes[0].status == "succeeded"
        assert len(events) == 2
    finally:
        await _delete_test_records(
            postgres_session_factory,
            execution_id,
        )
