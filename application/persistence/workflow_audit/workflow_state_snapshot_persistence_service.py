from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from application.persistence.query_result_helpers import (
    build_common_query,
    build_list_result,
)
from core.storage.persistence.lineage import (
    clean_optional_identifier,
    require_non_empty_identifier,
)
from core.storage.persistence.query import PersistenceListResult
from core.storage.persistence.runtime import (
    RuntimePersistenceRepository,
    RuntimePersistenceResult,
    WorkflowStateSnapshotRecord,
)


@dataclass(
    frozen=True,
    slots=True,
)
class WorkflowStateSnapshotPersistenceFilters:
    """
    Typed application-layer filters for workflow state snapshot retrieval.
    """

    workflow_name: str | None = None
    execution_id: str | None = None
    runtime_id: str | None = None
    workflow_status: str | None = None
    checkpoint_reference: str | None = None
    wave_index: int | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "workflow_name",
            clean_optional_identifier(
                self.workflow_name,
                "workflow_name",
            ),
        )
        object.__setattr__(
            self,
            "execution_id",
            clean_optional_identifier(
                self.execution_id,
                "execution_id",
            ),
        )
        object.__setattr__(
            self,
            "runtime_id",
            clean_optional_identifier(
                self.runtime_id,
                "runtime_id",
            ),
        )
        object.__setattr__(
            self,
            "workflow_status",
            clean_optional_identifier(
                self.workflow_status,
                "workflow_status",
            ),
        )
        object.__setattr__(
            self,
            "checkpoint_reference",
            clean_optional_identifier(
                self.checkpoint_reference,
                "checkpoint_reference",
            ),
        )
        _require_non_negative_optional(
            self.wave_index,
            "wave_index",
        )
        _require_ordered_time_window(
            self.start,
            self.end,
        )


class WorkflowStateSnapshotPersistenceService:
    """
    Application service for explicit workflow state snapshot audit persistence.

    This service delegates typed snapshot records to the runtime persistence
    repository. It does not auto-capture runtime state, mutate runtime control
    state, or change workflow execution semantics.
    """

    def __init__(
        self,
        repository: RuntimePersistenceRepository,
    ) -> None:
        self._repository = repository

    async def persist_snapshot(
        self,
        snapshot: WorkflowStateSnapshotRecord,
    ) -> RuntimePersistenceResult:
        return await self._repository.persist_workflow_state_snapshot(
            snapshot,
        )

    async def get_snapshot(
        self,
        snapshot_id: str,
    ) -> WorkflowStateSnapshotRecord | None:
        clean_snapshot_id = require_non_empty_identifier(
            snapshot_id,
            "snapshot_id",
        )
        return await self._repository.get_workflow_state_snapshot(
            clean_snapshot_id,
        )

    async def list_snapshots(
        self,
        filters: WorkflowStateSnapshotPersistenceFilters | None = None,
    ) -> Sequence[WorkflowStateSnapshotRecord]:
        result = await self.list_snapshots_result(
            filters,
        )
        return result.records

    async def list_snapshots_result(
        self,
        filters: WorkflowStateSnapshotPersistenceFilters | None = None,
    ) -> PersistenceListResult[WorkflowStateSnapshotRecord]:
        active_filters = filters or WorkflowStateSnapshotPersistenceFilters()
        records = await self._repository.list_workflow_state_snapshots(
            workflow_name=active_filters.workflow_name,
            execution_id=active_filters.execution_id,
            runtime_id=active_filters.runtime_id,
            workflow_status=active_filters.workflow_status,
            checkpoint_reference=active_filters.checkpoint_reference,
            wave_index=active_filters.wave_index,
            start=active_filters.start,
            end=active_filters.end,
        )
        query = build_common_query(
            record_type="workflow_state_snapshot",
            workflow_name=active_filters.workflow_name,
            execution_id=active_filters.execution_id,
            runtime_id=active_filters.runtime_id,
            start=active_filters.start,
            end=active_filters.end,
            metadata={
                "workflow_status": active_filters.workflow_status,
                "checkpoint_reference": active_filters.checkpoint_reference,
                "wave_index": active_filters.wave_index,
            },
        )
        return build_list_result(
            records,
            query=query,
        )


def _require_non_negative_optional(
    value: int | None,
    field_name: str,
) -> None:
    if value is not None and value < 0:
        raise ValueError(f"{field_name} must be greater than or equal to zero.")


def _require_ordered_time_window(
    start: datetime | None,
    end: datetime | None,
) -> None:
    if start is not None and end is not None and start > end:
        raise ValueError("start must be less than or equal to end.")
