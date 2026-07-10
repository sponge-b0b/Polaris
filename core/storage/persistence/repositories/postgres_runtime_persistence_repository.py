from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Executable

from core.database.models.runtime import WorkflowEventModel
from core.database.models.runtime import WorkflowStateSnapshotModel
from core.database.models.runtime import WorkflowNodeRunModel
from core.database.models.runtime import WorkflowRunModel
from core.storage.persistence.runtime.runtime_persistence_models import (
    RuntimePersistenceResult,
)
from core.storage.persistence.runtime.runtime_persistence_models import (
    WorkflowEventRecord,
)
from core.storage.persistence.runtime.runtime_persistence_models import (
    WorkflowNodeRunRecord,
)
from core.storage.persistence.runtime.runtime_persistence_models import (
    WorkflowStateSnapshotRecord,
)
from core.storage.persistence.runtime.runtime_persistence_models import (
    WorkflowRunRecord,
)
from core.storage.persistence.runtime.runtime_persistence_repository import (
    RuntimePersistenceRepository,
)
from core.storage.persistence.serializers.runtime_persistence_serializer import (
    RuntimePersistenceSerializer,
)


class PostgresRuntimePersistenceRepository(RuntimePersistenceRepository):
    """
    PostgreSQL adapter for durable runtime persistence.

    Workflow and node summaries are idempotent upserts. Runtime events are
    append-only inserts to preserve replay/audit history.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def persist_workflow_run(
        self,
        record: WorkflowRunRecord,
    ) -> RuntimePersistenceResult:
        values = RuntimePersistenceSerializer.workflow_run_values(record)
        stmt = insert(WorkflowRunModel).values(**values)
        excluded = stmt.excluded

        stmt = stmt.on_conflict_do_update(
            index_elements=[
                "workflow_name",
                "execution_id",
            ],
            set_={
                "runtime_id": excluded.runtime_id,
                "status": excluded.status,
                "started_at": func.coalesce(
                    WorkflowRunModel.started_at,
                    excluded.started_at,
                ),
                "completed_at": func.coalesce(
                    excluded.completed_at,
                    WorkflowRunModel.completed_at,
                ),
                "duration_seconds": func.coalesce(
                    excluded.duration_seconds,
                    WorkflowRunModel.duration_seconds,
                ),
                "mode": excluded.mode,
                "error": excluded.error,
                "metadata": excluded.metadata,
                "state_payload": excluded.state_payload,
                "updated_at": func.now(),
            },
        )

        return await self._execute_persistence_statement(stmt)

    async def persist_node_run(
        self,
        record: WorkflowNodeRunRecord,
    ) -> RuntimePersistenceResult:
        values = RuntimePersistenceSerializer.node_run_values(record)
        stmt = insert(WorkflowNodeRunModel).values(**values)
        excluded = stmt.excluded

        stmt = stmt.on_conflict_do_update(
            index_elements=[
                "workflow_name",
                "execution_id",
                "node_name",
                "wave_index",
            ],
            set_={
                "runtime_id": excluded.runtime_id,
                "status": excluded.status,
                "started_at": func.coalesce(
                    WorkflowNodeRunModel.started_at,
                    excluded.started_at,
                ),
                "completed_at": func.coalesce(
                    excluded.completed_at,
                    WorkflowNodeRunModel.completed_at,
                ),
                "duration_seconds": func.coalesce(
                    excluded.duration_seconds,
                    WorkflowNodeRunModel.duration_seconds,
                ),
                "error": excluded.error,
                "metadata": excluded.metadata,
                "outputs": excluded.outputs,
                "updated_at": func.now(),
            },
        )

        return await self._execute_persistence_statement(stmt)

    async def persist_event(
        self,
        record: WorkflowEventRecord,
    ) -> RuntimePersistenceResult:
        values = RuntimePersistenceSerializer.event_values(record)
        stmt = insert(WorkflowEventModel).values(**values)

        return await self._execute_persistence_statement(stmt)

    async def persist_workflow_state_snapshot(
        self,
        record: WorkflowStateSnapshotRecord,
    ) -> RuntimePersistenceResult:
        values = RuntimePersistenceSerializer.workflow_state_snapshot_values(record)
        stmt = insert(WorkflowStateSnapshotModel).values(**values)
        excluded = stmt.excluded

        stmt = stmt.on_conflict_do_update(
            index_elements=[
                "snapshot_id",
            ],
            set_={
                "workflow_name": excluded.workflow_name,
                "execution_id": excluded.execution_id,
                "workflow_status": excluded.workflow_status,
                "timestamp": excluded.timestamp,
                "runtime_id": excluded.runtime_id,
                "node_name": excluded.node_name,
                "wave_index": excluded.wave_index,
                "checkpoint_reference": excluded.checkpoint_reference,
                "state_payload": excluded.state_payload,
                "metadata": excluded.metadata,
                "row_updated_at": func.now(),
            },
        )

        return await self._execute_persistence_statement(stmt)

    async def get_workflow_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> WorkflowRunRecord | None:
        stmt = select(WorkflowRunModel).where(
            WorkflowRunModel.workflow_name == workflow_name,
            WorkflowRunModel.execution_id == execution_id,
        )

        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return RuntimePersistenceSerializer.workflow_run_from_model(
            model,
        )

    async def list_node_runs(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> Sequence[WorkflowNodeRunRecord]:
        stmt = (
            select(WorkflowNodeRunModel)
            .where(
                WorkflowNodeRunModel.workflow_name == workflow_name,
                WorkflowNodeRunModel.execution_id == execution_id,
            )
            .order_by(
                WorkflowNodeRunModel.wave_index.asc(),
                WorkflowNodeRunModel.node_name.asc(),
            )
        )

        result = await self._session.execute(stmt)

        return [
            RuntimePersistenceSerializer.node_run_from_model(model)
            for model in result.scalars().all()
        ]

    async def list_events(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> Sequence[WorkflowEventRecord]:
        stmt = (
            select(WorkflowEventModel)
            .where(
                WorkflowEventModel.workflow_name == workflow_name,
                WorkflowEventModel.execution_id == execution_id,
            )
            .order_by(
                WorkflowEventModel.timestamp.asc(),
                WorkflowEventModel.event_id.asc(),
            )
        )

        result = await self._session.execute(stmt)

        return [
            RuntimePersistenceSerializer.event_from_model(model)
            for model in result.scalars().all()
        ]

    async def get_workflow_state_snapshot(
        self,
        snapshot_id: str,
    ) -> WorkflowStateSnapshotRecord | None:
        stmt = select(WorkflowStateSnapshotModel).where(
            WorkflowStateSnapshotModel.snapshot_id == snapshot_id,
        )

        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return RuntimePersistenceSerializer.workflow_state_snapshot_from_model(
            model,
        )

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
        stmt = select(WorkflowStateSnapshotModel)

        if workflow_name is not None:
            stmt = stmt.where(
                WorkflowStateSnapshotModel.workflow_name == workflow_name,
            )
        if execution_id is not None:
            stmt = stmt.where(
                WorkflowStateSnapshotModel.execution_id == execution_id,
            )
        if runtime_id is not None:
            stmt = stmt.where(
                WorkflowStateSnapshotModel.runtime_id == runtime_id,
            )
        if workflow_status is not None:
            stmt = stmt.where(
                WorkflowStateSnapshotModel.workflow_status == workflow_status,
            )
        if checkpoint_reference is not None:
            stmt = stmt.where(
                WorkflowStateSnapshotModel.checkpoint_reference == checkpoint_reference,
            )
        if wave_index is not None:
            stmt = stmt.where(
                WorkflowStateSnapshotModel.wave_index == wave_index,
            )
        if start is not None:
            stmt = stmt.where(
                WorkflowStateSnapshotModel.timestamp >= start,
            )
        if end is not None:
            stmt = stmt.where(
                WorkflowStateSnapshotModel.timestamp <= end,
            )

        stmt = stmt.order_by(
            WorkflowStateSnapshotModel.timestamp.asc(),
            WorkflowStateSnapshotModel.snapshot_id.asc(),
        )

        result = await self._session.execute(stmt)

        return [
            RuntimePersistenceSerializer.workflow_state_snapshot_from_model(model)
            for model in result.scalars().all()
        ]

    async def _execute_persistence_statement(
        self,
        statement: Executable,
    ) -> RuntimePersistenceResult:
        try:
            await self._session.execute(statement)
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return RuntimePersistenceResult.failed(
                str(exc),
            )

        return RuntimePersistenceResult.succeeded()
