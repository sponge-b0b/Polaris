from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import cast

from sqlalchemy import Select, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Executable
from sqlalchemy.sql.elements import ColumnElement

from core.database.models.ai_observability import AiObservabilityExportJobModel
from core.storage.persistence.ai_observability import (
    AiObservabilityExportJobClaim,
    AiObservabilityExportJobRecord,
    AiObservabilityExportJobStatus,
    AiObservabilityExportQueueStatus,
    JsonObject,
)


class PostgresAiObservabilityExportJobRepository:
    """PostgreSQL repository for durable AI-observability export jobs."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def create_job(
        self,
        record: AiObservabilityExportJobRecord,
    ) -> AiObservabilityExportJobRecord:
        try:
            result = await self._session.execute(_upsert_job_statement(record))
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise

        model = result.scalar_one()
        return _job_record_from_model(model)

    async def get_job(
        self,
        export_job_id: str,
    ) -> AiObservabilityExportJobRecord | None:
        result = await self._session.execute(
            select(AiObservabilityExportJobModel).where(
                AiObservabilityExportJobModel.export_job_id
                == _require_non_empty(export_job_id, "export_job_id")
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return _job_record_from_model(model)

    async def claim_next_job(
        self,
        claim: AiObservabilityExportJobClaim | None = None,
    ) -> AiObservabilityExportJobRecord | None:
        claim = claim or AiObservabilityExportJobClaim()
        return await self._claim_first_matching_job(_claimable_job_select(claim))

    async def mark_exported(
        self,
        export_job_id: str,
        *,
        external_trace_id: str | None = None,
        external_observation_id: str | None = None,
        exported_at: datetime | None = None,
    ) -> AiObservabilityExportJobRecord | None:
        try:
            result = await self._session.execute(
                update(AiObservabilityExportJobModel)
                .where(
                    AiObservabilityExportJobModel.export_job_id
                    == _require_non_empty(export_job_id, "export_job_id"),
                )
                .values(
                    status=AiObservabilityExportJobStatus.EXPORTED.value,
                    external_trace_id=_clean_optional(
                        external_trace_id,
                        "external_trace_id",
                    ),
                    external_observation_id=_clean_optional(
                        external_observation_id,
                        "external_observation_id",
                    ),
                    last_error=None,
                    retry_after_seconds=None,
                    exported_at=exported_at or func.now(),
                    updated_at=func.now(),
                )
                .returning(AiObservabilityExportJobModel)
            )
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise

        model = result.scalar_one_or_none()
        if model is None:
            return None
        return _job_record_from_model(model)

    async def mark_failed(
        self,
        export_job_id: str,
        *,
        error: str,
        retry_after_seconds: float | None = None,
        available_at: datetime | None = None,
    ) -> AiObservabilityExportJobRecord | None:
        if retry_after_seconds is not None and retry_after_seconds < 0.0:
            raise ValueError("retry_after_seconds cannot be negative.")
        try:
            result = await self._session.execute(
                update(AiObservabilityExportJobModel)
                .where(
                    AiObservabilityExportJobModel.export_job_id
                    == _require_non_empty(export_job_id, "export_job_id"),
                )
                .values(
                    status=AiObservabilityExportJobStatus.FAILED.value,
                    last_error=_require_non_empty(error, "error"),
                    retry_after_seconds=retry_after_seconds,
                    available_at=available_at or func.now(),
                    updated_at=func.now(),
                )
                .returning(AiObservabilityExportJobModel)
            )
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise

        model = result.scalar_one_or_none()
        if model is None:
            return None
        return _job_record_from_model(model)

    async def mark_skipped(
        self,
        export_job_id: str,
        *,
        reason: str | None = None,
    ) -> AiObservabilityExportJobRecord | None:
        try:
            result = await self._session.execute(
                update(AiObservabilityExportJobModel)
                .where(
                    AiObservabilityExportJobModel.export_job_id
                    == _require_non_empty(export_job_id, "export_job_id"),
                )
                .values(
                    status=AiObservabilityExportJobStatus.SKIPPED.value,
                    last_error=_clean_optional(reason, "reason"),
                    updated_at=func.now(),
                )
                .returning(AiObservabilityExportJobModel)
            )
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise

        model = result.scalar_one_or_none()
        if model is None:
            return None
        return _job_record_from_model(model)

    async def list_jobs(
        self,
        *,
        statuses: Sequence[AiObservabilityExportJobStatus | str] | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        observation_type: str | None = None,
        limit: int | None = None,
    ) -> Sequence[AiObservabilityExportJobRecord]:
        result = await self._session.execute(
            _filtered_jobs_select(
                statuses=statuses,
                workflow_name=workflow_name,
                execution_id=execution_id,
                observation_type=observation_type,
                limit=limit,
            )
        )
        return tuple(_job_record_from_model(model) for model in result.scalars().all())

    async def get_queue_status(self) -> AiObservabilityExportQueueStatus:
        status_counts_result = await self._session.execute(
            select(
                AiObservabilityExportJobModel.status,
                func.count(AiObservabilityExportJobModel.export_job_id),
            ).group_by(AiObservabilityExportJobModel.status)
        )
        status_counts = {
            str(status): int(count) for status, count in status_counts_result.all()
        }

        retryable_failed_count = await self._count_jobs(
            AiObservabilityExportJobModel.status
            == AiObservabilityExportJobStatus.FAILED.value,
            AiObservabilityExportJobModel.attempt_count
            < AiObservabilityExportJobModel.max_attempts,
        )
        exhausted_failed_count = await self._count_jobs(
            AiObservabilityExportJobModel.status
            == AiObservabilityExportJobStatus.FAILED.value,
            AiObservabilityExportJobModel.attempt_count
            >= AiObservabilityExportJobModel.max_attempts,
        )
        oldest_retryable_available_at = await self._scalar_datetime(
            select(func.min(AiObservabilityExportJobModel.available_at)).where(
                or_(
                    AiObservabilityExportJobModel.status
                    == AiObservabilityExportJobStatus.PENDING.value,
                    (
                        AiObservabilityExportJobModel.status
                        == AiObservabilityExportJobStatus.FAILED.value
                    )
                    & (
                        AiObservabilityExportJobModel.attempt_count
                        < AiObservabilityExportJobModel.max_attempts
                    ),
                )
            )
        )
        latest_failure_at = await self._scalar_datetime(
            select(func.max(AiObservabilityExportJobModel.updated_at)).where(
                AiObservabilityExportJobModel.status
                == AiObservabilityExportJobStatus.FAILED.value
            )
        )
        latest_exported_at = await self._scalar_datetime(
            select(func.max(AiObservabilityExportJobModel.exported_at)).where(
                AiObservabilityExportJobModel.status
                == AiObservabilityExportJobStatus.EXPORTED.value
            )
        )

        return AiObservabilityExportQueueStatus(
            pending_count=status_counts.get(
                AiObservabilityExportJobStatus.PENDING.value,
                0,
            ),
            running_count=status_counts.get(
                AiObservabilityExportJobStatus.RUNNING.value,
                0,
            ),
            exported_count=status_counts.get(
                AiObservabilityExportJobStatus.EXPORTED.value,
                0,
            ),
            failed_count=status_counts.get(
                AiObservabilityExportJobStatus.FAILED.value,
                0,
            ),
            skipped_count=status_counts.get(
                AiObservabilityExportJobStatus.SKIPPED.value,
                0,
            ),
            retryable_failed_count=retryable_failed_count,
            exhausted_failed_count=exhausted_failed_count,
            oldest_retryable_available_at=oldest_retryable_available_at,
            latest_failure_at=latest_failure_at,
            latest_exported_at=latest_exported_at,
        )

    async def delete_terminal_jobs_before(
        self,
        *,
        cutoff: datetime,
        statuses: Sequence[AiObservabilityExportJobStatus | str] | None = None,
    ) -> int:
        terminal_statuses = statuses or (
            AiObservabilityExportJobStatus.EXPORTED,
            AiObservabilityExportJobStatus.SKIPPED,
        )
        try:
            result = await self._session.execute(
                delete(AiObservabilityExportJobModel).where(
                    AiObservabilityExportJobModel.status.in_(
                        _status_values(terminal_statuses)
                    ),
                    AiObservabilityExportJobModel.updated_at < cutoff,
                )
            )
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise
        return int(getattr(result, "rowcount", 0) or 0)

    async def _count_jobs(self, *conditions: ColumnElement[bool]) -> int:
        result = await self._session.execute(
            select(func.count(AiObservabilityExportJobModel.export_job_id)).where(
                *conditions
            )
        )
        return int(result.scalar_one() or 0)

    async def _scalar_datetime(
        self,
        stmt: Select[tuple[datetime | None]],
    ) -> datetime | None:
        result = await self._session.execute(stmt)
        value = result.scalar_one_or_none()
        return cast(datetime | None, value)

    async def recover_stale_running_jobs(
        self,
        *,
        started_before: datetime,
        error: str,
    ) -> int:
        try:
            result = await self._session.execute(
                update(AiObservabilityExportJobModel)
                .where(
                    AiObservabilityExportJobModel.status
                    == AiObservabilityExportJobStatus.RUNNING.value,
                    AiObservabilityExportJobModel.started_at < started_before,
                )
                .values(
                    status=AiObservabilityExportJobStatus.FAILED.value,
                    last_error=_require_non_empty(error, "error"),
                    available_at=func.now(),
                    updated_at=func.now(),
                )
            )
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise

        return int(getattr(result, "rowcount", 0) or 0)

    async def _claim_first_matching_job(
        self,
        stmt: Select[tuple[AiObservabilityExportJobModel]],
    ) -> AiObservabilityExportJobRecord | None:
        try:
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None

            update_result = await self._session.execute(
                update(AiObservabilityExportJobModel)
                .where(
                    AiObservabilityExportJobModel.export_job_id == model.export_job_id,
                )
                .values(
                    status=AiObservabilityExportJobStatus.RUNNING.value,
                    attempt_count=AiObservabilityExportJobModel.attempt_count + 1,
                    started_at=func.now(),
                    last_error=None,
                    updated_at=func.now(),
                )
                .returning(AiObservabilityExportJobModel)
            )
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise

        updated_model = update_result.scalar_one()
        return _job_record_from_model(updated_model)


def _upsert_job_statement(record: AiObservabilityExportJobRecord) -> Executable:
    values = _job_values(record)
    stmt = insert(AiObservabilityExportJobModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        constraint="uq_ai_observability_export_jobs_idempotency_key",
        set_={
            "observation_type": excluded.observation_type,
            "observation_name": excluded.observation_name,
            "observation_family": excluded.observation_family,
            "observation_status": excluded.observation_status,
            "payload": excluded.payload,
            "max_attempts": excluded.max_attempts,
            "trace_id": excluded.trace_id,
            "span_id": excluded.span_id,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "observation_id": excluded.observation_id,
            "parent_observation_id": excluded.parent_observation_id,
            "dataset_id": excluded.dataset_id,
            "case_id": excluded.case_id,
            "run_id": excluded.run_id,
            "updated_at": func.now(),
        },
    ).returning(AiObservabilityExportJobModel)


def _claimable_job_select(
    claim: AiObservabilityExportJobClaim,
) -> Select[tuple[AiObservabilityExportJobModel]]:
    stmt = select(AiObservabilityExportJobModel).where(
        AiObservabilityExportJobModel.status.in_(_status_values(claim.statuses)),
        AiObservabilityExportJobModel.available_at <= func.now(),
        AiObservabilityExportJobModel.attempt_count
        < AiObservabilityExportJobModel.max_attempts,
    )
    if claim.workflow_name is not None:
        stmt = stmt.where(
            AiObservabilityExportJobModel.workflow_name == claim.workflow_name
        )
    if claim.execution_id is not None:
        stmt = stmt.where(
            AiObservabilityExportJobModel.execution_id == claim.execution_id
        )
    if claim.observation_type is not None:
        stmt = stmt.where(
            AiObservabilityExportJobModel.observation_type == claim.observation_type,
        )

    return (
        stmt.order_by(
            AiObservabilityExportJobModel.available_at.asc(),
            AiObservabilityExportJobModel.created_at.asc(),
            AiObservabilityExportJobModel.export_job_id.asc(),
        )
        .limit(1)
        .with_for_update(skip_locked=True)
    )


def _filtered_jobs_select(
    *,
    statuses: Sequence[AiObservabilityExportJobStatus | str] | None,
    workflow_name: str | None,
    execution_id: str | None,
    observation_type: str | None,
    limit: int | None,
) -> Select[tuple[AiObservabilityExportJobModel]]:
    stmt = select(AiObservabilityExportJobModel)
    if statuses is not None:
        stmt = stmt.where(
            AiObservabilityExportJobModel.status.in_(_status_values(statuses))
        )
    if workflow_name is not None:
        stmt = stmt.where(
            AiObservabilityExportJobModel.workflow_name
            == _require_non_empty(workflow_name, "workflow_name")
        )
    if execution_id is not None:
        stmt = stmt.where(
            AiObservabilityExportJobModel.execution_id
            == _require_non_empty(execution_id, "execution_id")
        )
    if observation_type is not None:
        stmt = stmt.where(
            AiObservabilityExportJobModel.observation_type
            == _require_non_empty(observation_type, "observation_type")
        )
    stmt = stmt.order_by(
        AiObservabilityExportJobModel.created_at.asc(),
        AiObservabilityExportJobModel.export_job_id.asc(),
    )
    if limit is not None:
        if limit <= 0:
            raise ValueError("limit must be positive when provided.")
        stmt = stmt.limit(limit)
    return stmt


def _job_values(record: AiObservabilityExportJobRecord) -> dict[str, object]:
    status = cast(AiObservabilityExportJobStatus, record.status)
    values: dict[str, object] = {
        "export_job_id": record.export_job_id,
        "idempotency_key": record.idempotency_key,
        "observation_type": record.observation_type,
        "observation_name": record.observation_name,
        "observation_family": record.observation_family,
        "observation_status": record.observation_status,
        "payload": dict(record.payload),
        "status": status.value,
        "attempt_count": record.attempt_count,
        "max_attempts": record.max_attempts,
        "trace_id": record.trace_id,
        "span_id": record.span_id,
        "workflow_name": record.workflow_name,
        "execution_id": record.execution_id,
        "runtime_id": record.runtime_id,
        "node_name": record.node_name,
        "observation_id": record.observation_id,
        "parent_observation_id": record.parent_observation_id,
        "dataset_id": record.dataset_id,
        "case_id": record.case_id,
        "run_id": record.run_id,
        "external_trace_id": record.external_trace_id,
        "external_observation_id": record.external_observation_id,
        "last_error": record.last_error,
        "retry_after_seconds": record.retry_after_seconds,
    }
    if record.available_at is not None:
        values["available_at"] = record.available_at
    if record.created_at is not None:
        values["created_at"] = record.created_at
    if record.started_at is not None:
        values["started_at"] = record.started_at
    if record.exported_at is not None:
        values["exported_at"] = record.exported_at
    if record.updated_at is not None:
        values["updated_at"] = record.updated_at
    return values


def _job_record_from_model(
    model: AiObservabilityExportJobModel,
) -> AiObservabilityExportJobRecord:
    payload = cast(JsonObject, dict(model.payload))
    return AiObservabilityExportJobRecord(
        export_job_id=model.export_job_id,
        idempotency_key=model.idempotency_key,
        observation_type=model.observation_type,
        observation_name=model.observation_name,
        observation_family=model.observation_family,
        observation_status=model.observation_status,
        payload=payload,
        status=model.status,
        attempt_count=model.attempt_count,
        max_attempts=model.max_attempts,
        trace_id=model.trace_id,
        span_id=model.span_id,
        workflow_name=model.workflow_name,
        execution_id=model.execution_id,
        runtime_id=model.runtime_id,
        node_name=model.node_name,
        observation_id=model.observation_id,
        parent_observation_id=model.parent_observation_id,
        dataset_id=model.dataset_id,
        case_id=model.case_id,
        run_id=model.run_id,
        external_trace_id=model.external_trace_id,
        external_observation_id=model.external_observation_id,
        last_error=model.last_error,
        retry_after_seconds=model.retry_after_seconds,
        available_at=model.available_at,
        created_at=model.created_at,
        started_at=model.started_at,
        exported_at=model.exported_at,
        updated_at=model.updated_at,
    )


def _status_values(
    statuses: Sequence[AiObservabilityExportJobStatus | str],
) -> tuple[str, ...]:
    return tuple(
        status.value if isinstance(status, AiObservabilityExportJobStatus) else status
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
