from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.runtime import (
    WorkflowEventModel,
    WorkflowNodeRunModel,
    WorkflowRunModel,
    WorkflowStateSnapshotModel,
)
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.repositories.postgres_runtime_persistence_repository import (  # noqa: E501 - canonical module path
    PostgresRuntimePersistenceRepository,
)
from core.storage.persistence.runtime import (
    WorkflowEventRecord,
    WorkflowNodeRunRecord,
    WorkflowRunRecord,
    WorkflowStateSnapshotRecord,
)
from core.storage.persistence.serializers.runtime_persistence_serializer import (
    RuntimePersistenceSerializer,
)


class FakeScalarResult:
    def __init__(
        self,
        rows: Sequence[object],
    ) -> None:
        self._rows = list(rows)

    def all(
        self,
    ) -> list[object]:
        return self._rows


class FakeExecuteResult:
    def __init__(
        self,
        rows: Sequence[object] | None = None,
    ) -> None:
        self._rows = list(rows or [])

    def scalar_one_or_none(
        self,
    ) -> object | None:
        if not self._rows:
            return None

        return self._rows[0]

    def scalars(
        self,
    ) -> FakeScalarResult:
        return FakeScalarResult(
            self._rows,
        )


class FakeAsyncSession:
    def __init__(
        self,
        result: FakeExecuteResult | None = None,
        error: SQLAlchemyError | None = None,
    ) -> None:
        self.result = result or FakeExecuteResult()
        self.error = error
        self.executed: list[Any] = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(
        self,
        statement: Any,
    ) -> FakeExecuteResult:
        self.executed.append(statement)

        if self.error is not None:
            raise self.error

        return self.result

    async def commit(
        self,
    ) -> None:
        self.commits += 1

    async def rollback(
        self,
    ) -> None:
        self.rollbacks += 1


def build_workflow_run_record() -> WorkflowRunRecord:
    return WorkflowRunRecord(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        status="succeeded",
        started_at=datetime(2026, 5, 30, 14, tzinfo=UTC),
        completed_at=datetime(2026, 5, 30, 14, 1, tzinfo=UTC),
        duration_seconds=60.0,
        mode="paper",
        metadata={"source": "test"},
        state_payload={"node_count": 3},
    )


def build_workflow_state_snapshot_record() -> WorkflowStateSnapshotRecord:
    return WorkflowStateSnapshotRecord(
        snapshot_id="snapshot-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        workflow_status="paused",
        timestamp=datetime(2026, 5, 30, 14, 2, tzinfo=UTC),
        runtime_id="runtime-1",
        wave_index=1,
        checkpoint_reference="checkpoint-1",
        state_payload={"completed_nodes": ["macro"]},
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
            runtime_id="runtime-1",
            node_name="macro",
        ),
        metadata={"source": "test"},
    )


def test_runtime_serializer_converts_workflow_run_record_to_values() -> None:
    record = build_workflow_run_record()

    values = RuntimePersistenceSerializer.workflow_run_values(record)

    assert values["workflow_name"] == "morning_report"
    assert values["execution_id"] == "exec-1"
    assert values["metadata_payload"] == {"source": "test"}
    assert values["state_payload"] == {"node_count": 3}


def test_runtime_serializer_uses_default_node_wave_index() -> None:
    record = WorkflowNodeRunRecord(
        workflow_name="morning_report",
        execution_id="exec-1",
        node_name="macro",
        status="succeeded",
        outputs={"score": 0.7},
    )

    values = RuntimePersistenceSerializer.node_run_values(record)

    assert values["wave_index"] == 0
    assert values["output_payload"] == {"score": 0.7}


def test_runtime_serializer_converts_workflow_state_snapshot_record_to_values() -> None:
    record = build_workflow_state_snapshot_record()

    values = RuntimePersistenceSerializer.workflow_state_snapshot_values(record)

    assert values["snapshot_id"] == "snapshot-1"
    assert values["workflow_status"] == "paused"
    assert values["node_name"] == "macro"
    assert values["state_payload"] == {"completed_nodes": ["macro"]}
    assert values["metadata_payload"] == {"source": "test"}


@pytest.mark.asyncio
async def test_persist_workflow_run_uses_idempotent_upsert() -> None:
    session = FakeAsyncSession()
    repository = PostgresRuntimePersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    result = await repository.persist_workflow_run(
        build_workflow_run_record(),
    )

    compiled = str(
        session.executed[0].compile(
            dialect=postgresql.dialect(),
        )
    )

    assert result.success is True
    assert session.commits == 1
    assert "ON CONFLICT" in compiled
    assert "workflow_name, execution_id" in compiled


@pytest.mark.asyncio
async def test_persist_node_run_uses_idempotent_upsert() -> None:
    session = FakeAsyncSession()
    repository = PostgresRuntimePersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    result = await repository.persist_node_run(
        WorkflowNodeRunRecord(
            workflow_name="morning_report",
            execution_id="exec-1",
            node_name="macro",
            wave_index=1,
            status="succeeded",
        )
    )

    compiled = str(
        session.executed[0].compile(
            dialect=postgresql.dialect(),
        )
    )

    assert result.success is True
    assert session.commits == 1
    assert "ON CONFLICT" in compiled
    assert "workflow_name, execution_id, node_name, wave_index" in compiled


@pytest.mark.asyncio
async def test_persist_workflow_state_snapshot_uses_stable_id_upsert() -> None:
    session = FakeAsyncSession()
    repository = PostgresRuntimePersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    result = await repository.persist_workflow_state_snapshot(
        build_workflow_state_snapshot_record(),
    )

    compiled = str(
        session.executed[0].compile(
            dialect=postgresql.dialect(),
        )
    )

    assert result.success is True
    assert session.commits == 1
    assert "INSERT INTO workflow_state_snapshots" in compiled
    assert "ON CONFLICT" in compiled
    assert "snapshot_id" in compiled


@pytest.mark.asyncio
async def test_persist_event_is_append_only_insert() -> None:
    session = FakeAsyncSession()
    repository = PostgresRuntimePersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    result = await repository.persist_event(
        WorkflowEventRecord(
            event_id="event-1",
            event_type="runtime.node.completed",
            workflow_name="morning_report",
            execution_id="exec-1",
            timestamp=datetime(2026, 5, 30, tzinfo=UTC),
            payload={"progress": 1.0},
        )
    )

    compiled = str(
        session.executed[0].compile(
            dialect=postgresql.dialect(),
        )
    )

    assert result.success is True
    assert session.commits == 1
    assert "INSERT INTO workflow_events" in compiled
    assert "ON CONFLICT" not in compiled


@pytest.mark.asyncio
async def test_persist_statement_rolls_back_on_database_error() -> None:
    session = FakeAsyncSession(
        error=SQLAlchemyError("database unavailable"),
    )
    repository = PostgresRuntimePersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    result = await repository.persist_workflow_run(
        build_workflow_run_record(),
    )

    assert result.success is False
    assert result.error is not None
    assert "database unavailable" in result.error
    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_get_workflow_run_returns_typed_record() -> None:
    model = WorkflowRunModel(
        **RuntimePersistenceSerializer.workflow_run_values(
            build_workflow_run_record(),
        )
    )
    session = FakeAsyncSession(
        result=FakeExecuteResult([model]),
    )
    repository = PostgresRuntimePersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    record = await repository.get_workflow_run(
        workflow_name="morning_report",
        execution_id="exec-1",
    )

    assert record is not None
    assert record.workflow_name == "morning_report"
    assert record.metadata == {"source": "test"}


@pytest.mark.asyncio
async def test_list_events_returns_typed_records() -> None:
    model = WorkflowEventModel(
        **RuntimePersistenceSerializer.event_values(
            WorkflowEventRecord(
                event_id="event-1",
                event_type="runtime.node.completed",
                workflow_name="morning_report",
                execution_id="exec-1",
                timestamp=datetime(2026, 5, 30, tzinfo=UTC),
            )
        )
    )
    session = FakeAsyncSession(
        result=FakeExecuteResult([model]),
    )
    repository = PostgresRuntimePersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    records = await repository.list_events(
        workflow_name="morning_report",
        execution_id="exec-1",
    )

    assert len(records) == 1
    assert records[0].event_id == "event-1"


def test_repository_module_does_not_require_raw_runtime_dict_contracts() -> None:
    assert WorkflowRunModel.__tablename__ == "workflow_runs"
    assert WorkflowNodeRunModel.__tablename__ == "workflow_node_runs"
    assert WorkflowEventModel.__tablename__ == "workflow_events"


@pytest.mark.asyncio
async def test_list_node_runs_returns_typed_records() -> None:
    model = WorkflowNodeRunModel(
        **RuntimePersistenceSerializer.node_run_values(
            WorkflowNodeRunRecord(
                workflow_name="morning_report",
                execution_id="exec-1",
                node_name="macro",
                wave_index=0,
                status="succeeded",
                outputs={"score": 0.7},
            )
        )
    )
    session = FakeAsyncSession(
        result=FakeExecuteResult([model]),
    )
    repository = PostgresRuntimePersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    records = await repository.list_node_runs(
        workflow_name="morning_report",
        execution_id="exec-1",
    )

    assert len(records) == 1
    assert records[0].node_name == "macro"
    assert records[0].outputs == {"score": 0.7}


@pytest.mark.asyncio
async def test_get_workflow_state_snapshot_returns_typed_record() -> None:
    model = WorkflowStateSnapshotModel(
        **RuntimePersistenceSerializer.workflow_state_snapshot_values(
            build_workflow_state_snapshot_record(),
        )
    )
    session = FakeAsyncSession(
        result=FakeExecuteResult([model]),
    )
    repository = PostgresRuntimePersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    record = await repository.get_workflow_state_snapshot(
        snapshot_id="snapshot-1",
    )

    assert record is not None
    assert record.snapshot_id == "snapshot-1"
    assert record.lineage.node_name == "macro"
    assert record.state_payload == {"completed_nodes": ["macro"]}


@pytest.mark.asyncio
async def test_list_workflow_state_snapshots_applies_filters_and_returns_records() -> (
    None
):
    model = WorkflowStateSnapshotModel(
        **RuntimePersistenceSerializer.workflow_state_snapshot_values(
            build_workflow_state_snapshot_record(),
        )
    )
    session = FakeAsyncSession(
        result=FakeExecuteResult([model]),
    )
    repository = PostgresRuntimePersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    records = await repository.list_workflow_state_snapshots(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        workflow_status="paused",
        checkpoint_reference="checkpoint-1",
        wave_index=1,
        start=datetime(2026, 5, 30, 14, tzinfo=UTC),
        end=datetime(2026, 5, 30, 15, tzinfo=UTC),
    )

    compiled = str(
        session.executed[0].compile(
            dialect=postgresql.dialect(),
        )
    )

    assert len(records) == 1
    assert records[0].snapshot_id == "snapshot-1"
    assert "FROM workflow_state_snapshots" in compiled
    assert "workflow_state_snapshots.workflow_name" in compiled
    assert "workflow_state_snapshots.timestamp" in compiled
    assert "ORDER BY" in compiled
