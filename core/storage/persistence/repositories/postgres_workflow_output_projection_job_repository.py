from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import cast

from sqlalchemy import Select
from sqlalchemy import and_
from sqlalchemy import exists
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Executable

from core.database.models.completed_runs import CompletedWorkflowRunModel
from core.database.models.projections import WorkflowOutputProjectionJobModel
from core.storage.persistence.projections import MissingProjectionRunRecord
from core.storage.persistence.projections import ProjectionJobClaim
from core.storage.persistence.projections import WorkflowOutputProjectionJobRecord
from core.storage.persistence.projections import WorkflowOutputProjectionJobStatus


class PostgresWorkflowOutputProjectionJobRepository:
    """PostgreSQL repository for durable workflow-output projection jobs."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def create_job(
        self,
        record: WorkflowOutputProjectionJobRecord,
    ) -> WorkflowOutputProjectionJobRecord:
        try:
            result = await self._session.execute(
                _upsert_job_statement(record),
            )
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise

        model = result.scalar_one()
        return _job_record_from_model(model)

    async def claim_next_job(
        self,
        claim: ProjectionJobClaim | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None:
        claim = claim or ProjectionJobClaim()
        return await self._claim_first_matching_job(_claimable_job_select(claim))

    async def claim_job(
        self,
        projection_job_id: str,
        *,
        statuses: Sequence[WorkflowOutputProjectionJobStatus | str] | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None:
        allowed_statuses = statuses or (
            WorkflowOutputProjectionJobStatus.PENDING,
            WorkflowOutputProjectionJobStatus.FAILED,
        )
        return await self._claim_first_matching_job(
            _claim_job_select(
                projection_job_id=projection_job_id,
                statuses=allowed_statuses,
            )
        )

    async def mark_succeeded(
        self,
        projection_job_id: str,
        *,
        completed_at: datetime | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None:
        return await self._mark_terminal(
            projection_job_id,
            status=WorkflowOutputProjectionJobStatus.SUCCEEDED,
            completed_at=completed_at,
            last_error=None,
        )

    async def mark_failed(
        self,
        projection_job_id: str,
        *,
        error: str,
        completed_at: datetime | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None:
        return await self._mark_terminal(
            projection_job_id,
            status=WorkflowOutputProjectionJobStatus.FAILED,
            completed_at=completed_at,
            last_error=_require_non_empty(error, "error"),
        )

    async def mark_skipped(
        self,
        projection_job_id: str,
        *,
        reason: str | None = None,
        completed_at: datetime | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None:
        return await self._mark_terminal(
            projection_job_id,
            status=WorkflowOutputProjectionJobStatus.SKIPPED,
            completed_at=completed_at,
            last_error=_clean_optional(reason, "reason"),
        )

    async def list_jobs(
        self,
        *,
        run_id: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        projector_name: str | None = None,
        statuses: Sequence[WorkflowOutputProjectionJobStatus | str] | None = None,
        limit: int | None = None,
    ) -> Sequence[WorkflowOutputProjectionJobRecord]:
        stmt = _filtered_jobs_select(
            run_id=run_id,
            workflow_name=workflow_name,
            execution_id=execution_id,
            projector_name=projector_name,
            statuses=statuses,
            limit=limit,
        )
        result = await self._session.execute(stmt)
        return tuple(_job_record_from_model(model) for model in result.scalars().all())

    async def recover_stale_running_jobs(
        self,
        *,
        started_before: datetime,
        error: str,
    ) -> int:
        try:
            result = await self._session.execute(
                update(WorkflowOutputProjectionJobModel)
                .where(
                    WorkflowOutputProjectionJobModel.status
                    == WorkflowOutputProjectionJobStatus.RUNNING.value,
                    WorkflowOutputProjectionJobModel.started_at < started_before,
                )
                .values(
                    status=WorkflowOutputProjectionJobStatus.FAILED.value,
                    last_error=_require_non_empty(error, "error"),
                    completed_at=func.now(),
                    updated_at=func.now(),
                )
            )
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise

        return int(getattr(result, "rowcount", 0) or 0)

    async def list_runs_missing_projection_jobs(
        self,
        *,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        limit: int | None = None,
    ) -> Sequence[MissingProjectionRunRecord]:
        stmt = _missing_projection_runs_select(
            workflow_name=workflow_name,
            execution_id=execution_id,
            limit=limit,
        )
        result = await self._session.execute(stmt)
        return tuple(
            MissingProjectionRunRecord(
                run_id=model.run_id,
                workflow_name=model.workflow_name,
                execution_id=model.execution_id,
                completed_at=model.completed_at,
            )
            for model in result.scalars().all()
        )

    async def _claim_first_matching_job(
        self,
        stmt: Select[tuple[WorkflowOutputProjectionJobModel]],
    ) -> WorkflowOutputProjectionJobRecord | None:
        try:
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None

            update_result = await self._session.execute(
                update(WorkflowOutputProjectionJobModel)
                .where(
                    WorkflowOutputProjectionJobModel.projection_job_id
                    == model.projection_job_id,
                )
                .values(
                    status=WorkflowOutputProjectionJobStatus.RUNNING.value,
                    attempt_count=WorkflowOutputProjectionJobModel.attempt_count + 1,
                    started_at=func.now(),
                    completed_at=None,
                    last_error=None,
                    updated_at=func.now(),
                )
                .returning(WorkflowOutputProjectionJobModel)
            )
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise

        updated_model = update_result.scalar_one()
        return _job_record_from_model(updated_model)

    async def _mark_terminal(
        self,
        projection_job_id: str,
        *,
        status: WorkflowOutputProjectionJobStatus,
        completed_at: datetime | None,
        last_error: str | None,
    ) -> WorkflowOutputProjectionJobRecord | None:
        try:
            result = await self._session.execute(
                update(WorkflowOutputProjectionJobModel)
                .where(
                    WorkflowOutputProjectionJobModel.projection_job_id
                    == _require_non_empty(projection_job_id, "projection_job_id"),
                )
                .values(
                    status=status.value,
                    completed_at=completed_at or func.now(),
                    last_error=last_error,
                    updated_at=func.now(),
                )
                .returning(WorkflowOutputProjectionJobModel)
            )
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise

        model = result.scalar_one_or_none()
        if model is None:
            return None
        return _job_record_from_model(model)


def _upsert_job_statement(record: WorkflowOutputProjectionJobRecord) -> Executable:
    values = _job_values(record)
    stmt = insert(WorkflowOutputProjectionJobModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        constraint="uq_workflow_output_projection_jobs_source",
        set_={
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "output_contract": excluded.output_contract,
            "output_schema_version": excluded.output_schema_version,
            "updated_at": func.now(),
        },
    ).returning(WorkflowOutputProjectionJobModel)


def _claim_job_select(
    *,
    projection_job_id: str,
    statuses: Sequence[WorkflowOutputProjectionJobStatus | str],
) -> Select[tuple[WorkflowOutputProjectionJobModel]]:
    return (
        select(WorkflowOutputProjectionJobModel)
        .where(
            WorkflowOutputProjectionJobModel.projection_job_id
            == _require_non_empty(projection_job_id, "projection_job_id"),
            WorkflowOutputProjectionJobModel.status.in_(_status_values(statuses)),
        )
        .limit(1)
        .with_for_update(skip_locked=True)
    )


def _claimable_job_select(
    claim: ProjectionJobClaim,
) -> Select[tuple[WorkflowOutputProjectionJobModel]]:
    stmt = select(WorkflowOutputProjectionJobModel).where(
        WorkflowOutputProjectionJobModel.status.in_(_status_values(claim.statuses)),
    )
    if claim.workflow_name is not None:
        stmt = stmt.where(
            WorkflowOutputProjectionJobModel.workflow_name == claim.workflow_name
        )
    if claim.execution_id is not None:
        stmt = stmt.where(
            WorkflowOutputProjectionJobModel.execution_id == claim.execution_id
        )
    if claim.projector_name is not None:
        stmt = stmt.where(
            WorkflowOutputProjectionJobModel.projector_name == claim.projector_name,
        )

    return (
        stmt.order_by(
            WorkflowOutputProjectionJobModel.created_at.asc(),
            WorkflowOutputProjectionJobModel.projection_job_id.asc(),
        )
        .limit(1)
        .with_for_update(skip_locked=True)
    )


def _filtered_jobs_select(
    *,
    run_id: str | None,
    workflow_name: str | None,
    execution_id: str | None,
    projector_name: str | None,
    statuses: Sequence[WorkflowOutputProjectionJobStatus | str] | None,
    limit: int | None,
) -> Select[tuple[WorkflowOutputProjectionJobModel]]:
    stmt = select(WorkflowOutputProjectionJobModel)
    if run_id is not None:
        stmt = stmt.where(
            WorkflowOutputProjectionJobModel.run_id
            == _require_non_empty(run_id, "run_id")
        )
    if workflow_name is not None:
        stmt = stmt.where(
            WorkflowOutputProjectionJobModel.workflow_name
            == _require_non_empty(workflow_name, "workflow_name"),
        )
    if execution_id is not None:
        stmt = stmt.where(
            WorkflowOutputProjectionJobModel.execution_id
            == _require_non_empty(execution_id, "execution_id"),
        )
    if projector_name is not None:
        stmt = stmt.where(
            WorkflowOutputProjectionJobModel.projector_name
            == _require_non_empty(projector_name, "projector_name"),
        )
    if statuses is not None:
        stmt = stmt.where(
            WorkflowOutputProjectionJobModel.status.in_(_status_values(statuses))
        )
    stmt = stmt.order_by(
        WorkflowOutputProjectionJobModel.created_at.asc(),
        WorkflowOutputProjectionJobModel.projection_job_id.asc(),
    )
    if limit is not None:
        if limit <= 0:
            raise ValueError("limit must be positive when provided.")
        stmt = stmt.limit(limit)
    return stmt


def _missing_projection_runs_select(
    *,
    workflow_name: str | None,
    execution_id: str | None,
    limit: int | None,
) -> Select[tuple[CompletedWorkflowRunModel]]:
    stmt = select(CompletedWorkflowRunModel).where(
        ~exists().where(
            and_(
                WorkflowOutputProjectionJobModel.run_id
                == CompletedWorkflowRunModel.run_id,
            )
        )
    )
    if workflow_name is not None:
        stmt = stmt.where(
            CompletedWorkflowRunModel.workflow_name
            == _require_non_empty(workflow_name, "workflow_name"),
        )
    if execution_id is not None:
        stmt = stmt.where(
            CompletedWorkflowRunModel.execution_id
            == _require_non_empty(execution_id, "execution_id"),
        )
    stmt = stmt.order_by(
        CompletedWorkflowRunModel.completed_at.desc().nullslast(),
        CompletedWorkflowRunModel.created_at.desc(),
        CompletedWorkflowRunModel.run_id.asc(),
    )
    if limit is not None:
        if limit <= 0:
            raise ValueError("limit must be positive when provided.")
        stmt = stmt.limit(limit)
    return stmt


def _job_values(record: WorkflowOutputProjectionJobRecord) -> dict[str, object]:
    status = cast(WorkflowOutputProjectionJobStatus, record.status)
    values: dict[str, object] = {
        "projection_job_id": record.projection_job_id,
        "run_id": record.run_id,
        "workflow_name": record.workflow_name,
        "execution_id": record.execution_id,
        "node_name": record.node_name,
        "projector_name": record.projector_name,
        "output_contract": record.output_contract,
        "output_schema_version": record.output_schema_version,
        "source_fingerprint": record.source_fingerprint,
        "status": status.value,
        "attempt_count": record.attempt_count,
        "last_error": record.last_error,
        "started_at": record.started_at,
        "completed_at": record.completed_at,
    }
    if record.created_at is not None:
        values["created_at"] = record.created_at
    if record.updated_at is not None:
        values["updated_at"] = record.updated_at
    return values


def _job_record_from_model(
    model: WorkflowOutputProjectionJobModel,
) -> WorkflowOutputProjectionJobRecord:
    return WorkflowOutputProjectionJobRecord(
        projection_job_id=model.projection_job_id,
        run_id=model.run_id,
        workflow_name=model.workflow_name,
        execution_id=model.execution_id,
        node_name=model.node_name,
        projector_name=model.projector_name,
        output_contract=model.output_contract,
        output_schema_version=model.output_schema_version,
        source_fingerprint=model.source_fingerprint,
        status=model.status,
        attempt_count=model.attempt_count,
        last_error=model.last_error,
        created_at=model.created_at,
        started_at=model.started_at,
        completed_at=model.completed_at,
        updated_at=model.updated_at,
    )


def _status_values(
    statuses: Sequence[WorkflowOutputProjectionJobStatus | str],
) -> tuple[str, ...]:
    return tuple(
        status.value
        if isinstance(status, WorkflowOutputProjectionJobStatus)
        else status
        for status in statuses
    )


def _require_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")
    return cleaned


def _clean_optional(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty when provided.")
    return cleaned
