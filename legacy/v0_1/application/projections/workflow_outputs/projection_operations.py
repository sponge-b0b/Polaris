from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from application.projections.workflow_outputs.projection_models import (
    CompletedRunProjectionSummary,
    WorkflowOutputProjectionReconciliationRequest,
    WorkflowOutputProjectionReconciliationResult,
    WorkflowOutputProjectionRequest,
    WorkflowOutputProjectionRetryRequest,
    WorkflowOutputProjectionRetryResult,
    WorkflowOutputProjectionStatus,
)
from application.projections.workflow_outputs.projection_service import (
    WorkflowOutputProjectionService,
)
from core.storage.persistence.projections import (
    MissingProjectionRunRecord,
    WorkflowOutputProjectionJobRecord,
    WorkflowOutputProjectionJobRepository,
    WorkflowOutputProjectionJobStatus,
)


@dataclass(frozen=True, slots=True)
class WorkflowOutputProjectionStatusRequest:
    """Request to inspect durable workflow-output projection jobs."""

    run_id: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    projector_name: str | None = None
    statuses: tuple[WorkflowOutputProjectionStatus | str, ...] = ()
    limit: int | None = 50

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _clean_optional(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "workflow_name",
            _clean_optional(self.workflow_name, "workflow_name"),
        )
        object.__setattr__(
            self,
            "execution_id",
            _clean_optional(self.execution_id, "execution_id"),
        )
        object.__setattr__(
            self,
            "projector_name",
            _clean_optional(self.projector_name, "projector_name"),
        )
        object.__setattr__(self, "statuses", _coerce_statuses(self.statuses))
        if self.limit is not None and self.limit <= 0:
            raise ValueError("limit must be positive when provided.")


@dataclass(frozen=True, slots=True)
class WorkflowOutputProjectionStatusResult:
    """Projection job status query result."""

    requested: WorkflowOutputProjectionStatusRequest
    jobs: tuple[WorkflowOutputProjectionJobRecord, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "jobs", tuple(self.jobs))

    @property
    def total_jobs(self) -> int:
        return len(self.jobs)


class WorkflowOutputProjectionOperationsService:
    """Application-owned operational API for workflow-output projections."""

    def __init__(
        self,
        *,
        projection_service: WorkflowOutputProjectionService,
        projection_job_repository: WorkflowOutputProjectionJobRepository,
    ) -> None:
        self._projection_service = projection_service
        self._projection_job_repository = projection_job_repository

    async def projection_status(
        self,
        request: WorkflowOutputProjectionStatusRequest,
    ) -> WorkflowOutputProjectionStatusResult:
        jobs = await self._projection_job_repository.list_jobs(
            run_id=request.run_id,
            workflow_name=request.workflow_name,
            execution_id=request.execution_id,
            projector_name=request.projector_name,
            statuses=_storage_statuses(_normalized_statuses(request.statuses))
            if request.statuses
            else None,
            limit=request.limit,
        )
        return WorkflowOutputProjectionStatusResult(
            requested=request,
            jobs=tuple(jobs),
        )

    async def project(
        self,
        request: WorkflowOutputProjectionRequest,
    ) -> CompletedRunProjectionSummary:
        return await self._projection_service.project_completed_run(request)

    async def retry_projection(
        self,
        request: WorkflowOutputProjectionRetryRequest,
    ) -> WorkflowOutputProjectionRetryResult:
        recovered_stale_jobs = 0
        if request.stale_running_started_before is not None and not request.dry_run:
            recovered_stale_jobs = (
                await self._projection_job_repository.recover_stale_running_jobs(
                    started_before=request.stale_running_started_before,
                    error="Projection job recovered by operational retry command.",
                )
            )

        jobs = await self._projection_job_repository.list_jobs(
            workflow_name=request.workflow_name,
            execution_id=request.execution_id,
            projector_name=request.projector_name,
            statuses=_storage_statuses(_normalized_statuses(request.statuses)),
            limit=request.limit,
        )
        if request.dry_run:
            return WorkflowOutputProjectionRetryResult(
                requested=request,
                matched_jobs=len(jobs),
                retried_jobs=0,
                recovered_stale_running_jobs=recovered_stale_jobs,
            )

        summaries: list[CompletedRunProjectionSummary] = []
        for workflow_name, execution_id, run_id in _unique_run_keys(jobs):
            summaries.append(
                await self._projection_service.project_completed_run(
                    WorkflowOutputProjectionRequest(
                        workflow_name=workflow_name,
                        execution_id=execution_id,
                        run_id=run_id,
                        requested_at=request.requested_at,
                        force_reproject=_requires_force_reproject(
                            _normalized_statuses(request.statuses)
                        ),
                    )
                )
            )
        return WorkflowOutputProjectionRetryResult(
            requested=request,
            matched_jobs=len(jobs),
            retried_jobs=len(jobs),
            recovered_stale_running_jobs=recovered_stale_jobs,
            summaries=tuple(summaries),
        )

    async def reconcile_projections(
        self,
        request: WorkflowOutputProjectionReconciliationRequest,
    ) -> WorkflowOutputProjectionReconciliationResult:
        missing_runs = (
            await self._projection_job_repository.list_runs_missing_projection_jobs(
                workflow_name=request.workflow_name,
                execution_id=request.execution_id,
                limit=request.limit,
            )
        )
        filtered_missing_runs = _filter_missing_runs_by_window(
            missing_runs,
            since=request.since,
            until=request.until,
        )
        if request.dry_run or not request.enqueue_missing_jobs:
            return WorkflowOutputProjectionReconciliationResult(
                requested=request,
                scanned_runs=len(filtered_missing_runs),
                missing_projection_runs=len(filtered_missing_runs),
                missing_runs=filtered_missing_runs,
            )

        summaries: list[CompletedRunProjectionSummary] = []
        for run in filtered_missing_runs:
            summaries.append(
                await self._projection_service.project_completed_run(
                    WorkflowOutputProjectionRequest(
                        workflow_name=run.workflow_name,
                        execution_id=run.execution_id,
                        run_id=run.run_id,
                        requested_at=request.requested_at,
                    )
                )
            )
        return WorkflowOutputProjectionReconciliationResult(
            requested=request,
            scanned_runs=len(filtered_missing_runs),
            missing_projection_runs=len(filtered_missing_runs),
            enqueued_jobs=sum(summary.total_jobs for summary in summaries),
            missing_runs=filtered_missing_runs,
            summaries=tuple(summaries),
        )


def _unique_run_keys(
    jobs: Sequence[WorkflowOutputProjectionJobRecord],
) -> tuple[tuple[str, str, str], ...]:
    seen: set[tuple[str, str, str]] = set()
    ordered: list[tuple[str, str, str]] = []
    for job in jobs:
        key = (job.workflow_name, job.execution_id, job.run_id)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return tuple(ordered)


def _requires_force_reproject(
    statuses: Sequence[WorkflowOutputProjectionStatus],
) -> bool:
    force_statuses = {
        WorkflowOutputProjectionStatus.SUCCEEDED,
        WorkflowOutputProjectionStatus.SKIPPED,
    }
    return any(status in force_statuses for status in statuses)


def _filter_missing_runs_by_window(
    runs: Sequence[MissingProjectionRunRecord],
    *,
    since: datetime | None,
    until: datetime | None,
) -> tuple[MissingProjectionRunRecord, ...]:
    return tuple(
        run
        for run in runs
        if _within_optional_window(
            run.completed_at,
            since=since,
            until=until,
        )
    )


def _within_optional_window(
    completed_at: datetime | None,
    *,
    since: datetime | None,
    until: datetime | None,
) -> bool:
    if completed_at is None:
        return since is None and until is None
    normalized_completed_at = _normalize_datetime(completed_at)
    if since is not None and normalized_completed_at < _normalize_datetime(since):
        return False
    if until is not None and normalized_completed_at > _normalize_datetime(until):
        return False
    return True


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalized_statuses(
    statuses: Sequence[WorkflowOutputProjectionStatus | str],
) -> tuple[WorkflowOutputProjectionStatus, ...]:
    return cast(tuple[WorkflowOutputProjectionStatus, ...], tuple(statuses))


def _storage_statuses(
    statuses: Sequence[WorkflowOutputProjectionStatus],
) -> tuple[WorkflowOutputProjectionJobStatus, ...]:
    return tuple(WorkflowOutputProjectionJobStatus(status.value) for status in statuses)


def _coerce_statuses(
    statuses: Sequence[WorkflowOutputProjectionStatus | str],
) -> tuple[WorkflowOutputProjectionStatus, ...]:
    return tuple(_coerce_status(status) for status in statuses)


def _coerce_status(
    status: WorkflowOutputProjectionStatus | str,
) -> WorkflowOutputProjectionStatus:
    if isinstance(status, WorkflowOutputProjectionStatus):
        return status
    try:
        return WorkflowOutputProjectionStatus(status)
    except ValueError as exc:
        raise ValueError(
            f"Unsupported workflow output projection status: {status!r}."
        ) from exc


def _clean_optional(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty when provided.")
    return cleaned
