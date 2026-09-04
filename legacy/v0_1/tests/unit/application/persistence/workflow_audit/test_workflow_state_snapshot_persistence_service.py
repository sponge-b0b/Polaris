from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import cast

import pytest

from application.persistence import (
    WorkflowStateSnapshotPersistenceFilters,
    WorkflowStateSnapshotPersistenceService,
)
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.runtime import (
    RuntimePersistenceRepository,
    RuntimePersistenceResult,
    WorkflowStateSnapshotRecord,
)


class FakeRuntimePersistenceRepository:
    def __init__(
        self,
        snapshots: Sequence[WorkflowStateSnapshotRecord] = (),
    ) -> None:
        self.snapshots = tuple(snapshots)
        self.persisted_snapshot: WorkflowStateSnapshotRecord | None = None
        self.snapshot_id: str | None = None
        self.snapshot_filters: dict[str, str | int | datetime | None] | None = None

    async def persist_workflow_state_snapshot(
        self,
        record: WorkflowStateSnapshotRecord,
    ) -> RuntimePersistenceResult:
        self.persisted_snapshot = record
        return RuntimePersistenceResult.succeeded()

    async def get_workflow_state_snapshot(
        self,
        snapshot_id: str,
    ) -> WorkflowStateSnapshotRecord | None:
        self.snapshot_id = snapshot_id
        return self.snapshots[0] if self.snapshots else None

    async def list_workflow_state_snapshots(
        self,
        *,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        runtime_id: str | None = None,
        workflow_status: str | None = None,
        checkpoint_reference: str | None = None,
        wave_index: int | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[WorkflowStateSnapshotRecord]:
        self.snapshot_filters = {
            "workflow_name": workflow_name,
            "execution_id": execution_id,
            "runtime_id": runtime_id,
            "workflow_status": workflow_status,
            "checkpoint_reference": checkpoint_reference,
            "wave_index": wave_index,
            "start": start,
            "end": end,
        }
        return self.snapshots


@pytest.mark.asyncio
async def test_workflow_state_snapshot_service_persists_snapshot() -> None:
    repository = FakeRuntimePersistenceRepository()
    service = WorkflowStateSnapshotPersistenceService(
        cast(
            RuntimePersistenceRepository,
            repository,
        )
    )
    snapshot = _snapshot()

    result = await service.persist_snapshot(snapshot)

    assert result.success is True
    assert repository.persisted_snapshot == snapshot


@pytest.mark.asyncio
async def test_workflow_state_snapshot_service_gets_snapshot_by_clean_id() -> None:
    repository = FakeRuntimePersistenceRepository(
        snapshots=(_snapshot(),),
    )
    service = WorkflowStateSnapshotPersistenceService(
        cast(
            RuntimePersistenceRepository,
            repository,
        )
    )

    snapshot = await service.get_snapshot(" snapshot-1 ")

    assert snapshot is not None
    assert snapshot.snapshot_id == "snapshot-1"
    assert repository.snapshot_id == "snapshot-1"


@pytest.mark.asyncio
async def test_workflow_state_snapshot_service_lists_with_typed_filters() -> None:
    start = datetime(2026, 5, 30, 14, tzinfo=UTC)
    end = datetime(2026, 5, 30, 15, tzinfo=UTC)
    repository = FakeRuntimePersistenceRepository(
        snapshots=(_snapshot(),),
    )
    service = WorkflowStateSnapshotPersistenceService(
        cast(
            RuntimePersistenceRepository,
            repository,
        )
    )

    snapshots = await service.list_snapshots(
        WorkflowStateSnapshotPersistenceFilters(
            workflow_name=" morning_report ",
            execution_id=" exec-1 ",
            runtime_id=" runtime-1 ",
            workflow_status=" paused ",
            checkpoint_reference=" checkpoint-1 ",
            wave_index=1,
            start=start,
            end=end,
        )
    )

    assert len(snapshots) == 1
    assert repository.snapshot_filters == {
        "workflow_name": "morning_report",
        "execution_id": "exec-1",
        "runtime_id": "runtime-1",
        "workflow_status": "paused",
        "checkpoint_reference": "checkpoint-1",
        "wave_index": 1,
        "start": start,
        "end": end,
    }


def test_workflow_state_snapshot_filters_reject_negative_wave_index() -> None:
    with pytest.raises(ValueError, match="wave_index"):
        WorkflowStateSnapshotPersistenceFilters(
            wave_index=-1,
        )


def test_workflow_state_snapshot_filters_reject_reversed_time_window() -> None:
    with pytest.raises(ValueError, match="start"):
        WorkflowStateSnapshotPersistenceFilters(
            start=datetime(2026, 5, 30, 15, tzinfo=UTC),
            end=datetime(2026, 5, 30, 14, tzinfo=UTC),
        )


def test_workflow_state_snapshot_service_is_exported_from_application_persistence() -> (
    None
):
    assert WorkflowStateSnapshotPersistenceService.__name__ == (
        "WorkflowStateSnapshotPersistenceService"
    )
    assert WorkflowStateSnapshotPersistenceFilters.__name__ == (
        "WorkflowStateSnapshotPersistenceFilters"
    )


def _snapshot() -> WorkflowStateSnapshotRecord:
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
