from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import cast

import pytest

from application.projections.workflow_outputs import (
    CompletedRunProjectionSummary,
    WorkflowOutputProjectionOperationsService,
    WorkflowOutputProjectionOutcome,
    WorkflowOutputProjectionReconciliationRequest,
    WorkflowOutputProjectionRequest,
    WorkflowOutputProjectionRetryRequest,
    WorkflowOutputProjectionService,
    WorkflowOutputProjectionStatus,
    WorkflowOutputProjectionStatusRequest,
)
from core.storage.persistence.projections import (
    MissingProjectionRunRecord,
    ProjectionJobClaim,
    WorkflowOutputProjectionJobRecord,
    WorkflowOutputProjectionJobRepository,
    WorkflowOutputProjectionJobStatus,
)


class FakeProjectionService:
    def __init__(
        self,
        *,
        outcomes: Sequence[WorkflowOutputProjectionOutcome] = (),
    ) -> None:
        self.requests: list[WorkflowOutputProjectionRequest] = []
        self.outcomes = tuple(outcomes)

    async def project_completed_run(
        self,
        request: WorkflowOutputProjectionRequest,
    ) -> CompletedRunProjectionSummary:
        self.requests.append(request)
        return CompletedRunProjectionSummary(
            workflow_name=request.workflow_name,
            execution_id=request.execution_id,
            run_id=request.run_id,
            outcomes=self.outcomes,
        )


class FakeProjectionJobRepository:
    def __init__(
        self,
        *,
        jobs: Sequence[WorkflowOutputProjectionJobRecord] = (),
        missing_runs: Sequence[MissingProjectionRunRecord] = (),
        recovered_jobs: int = 0,
    ) -> None:
        self.jobs = tuple(jobs)
        self.missing_runs = tuple(missing_runs)
        self.recovered_jobs = recovered_jobs
        self.list_calls: list[dict[str, object]] = []
        self.recover_calls: list[tuple[datetime, str]] = []

    async def create_job(
        self,
        record: WorkflowOutputProjectionJobRecord,
    ) -> WorkflowOutputProjectionJobRecord:
        return record

    async def claim_next_job(
        self,
        claim: ProjectionJobClaim | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None:
        return None

    async def claim_job(
        self,
        projection_job_id: str,
        *,
        statuses: Sequence[WorkflowOutputProjectionJobStatus | str] | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None:
        return None

    async def mark_succeeded(
        self,
        projection_job_id: str,
        *,
        completed_at: datetime | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None:
        return None

    async def mark_failed(
        self,
        projection_job_id: str,
        *,
        error: str,
        completed_at: datetime | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None:
        return None

    async def mark_skipped(
        self,
        projection_job_id: str,
        *,
        reason: str | None = None,
        completed_at: datetime | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None:
        return None

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
        self.list_calls.append(
            {
                "run_id": run_id,
                "workflow_name": workflow_name,
                "execution_id": execution_id,
                "projector_name": projector_name,
                "statuses": tuple(statuses or ()),
                "limit": limit,
            }
        )
        return self.jobs[:limit]

    async def recover_stale_running_jobs(
        self,
        *,
        started_before: datetime,
        error: str,
    ) -> int:
        self.recover_calls.append((started_before, error))
        return self.recovered_jobs

    async def list_runs_missing_projection_jobs(
        self,
        *,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        limit: int | None = None,
    ) -> Sequence[MissingProjectionRunRecord]:
        return self.missing_runs[:limit]


@pytest.mark.asyncio
async def test_projection_operations_status_filters_jobs() -> None:
    job = _job_record(status=WorkflowOutputProjectionJobStatus.FAILED)
    repository = FakeProjectionJobRepository(jobs=(job,))
    service = _operations_service(repository=repository)

    result = await service.projection_status(
        WorkflowOutputProjectionStatusRequest(
            workflow_name="morning_report",
            statuses=(WorkflowOutputProjectionStatus.FAILED,),
            limit=10,
        )
    )

    assert result.jobs == (job,)
    assert repository.list_calls == [
        {
            "run_id": None,
            "workflow_name": "morning_report",
            "execution_id": None,
            "projector_name": None,
            "statuses": (WorkflowOutputProjectionJobStatus.FAILED,),
            "limit": 10,
        }
    ]


@pytest.mark.asyncio
async def test_projection_operations_retry_projects_unique_runs_and_recovers_stale_jobs() -> (  # noqa: E501 - descriptive pytest node id
    None
):
    started_before = datetime(2026, 1, 1, tzinfo=UTC)
    jobs = (
        _job_record(projection_job_id="job-1", run_id="run-1"),
        _job_record(projection_job_id="job-2", run_id="run-1"),
    )
    projection_service = FakeProjectionService()
    repository = FakeProjectionJobRepository(jobs=jobs, recovered_jobs=2)
    service = _operations_service(
        projection_service=projection_service,
        repository=repository,
    )

    result = await service.retry_projection(
        WorkflowOutputProjectionRetryRequest(
            statuses=(WorkflowOutputProjectionStatus.FAILED,),
            stale_running_started_before=started_before,
        )
    )

    assert result.matched_jobs == 2
    assert result.retried_jobs == 2
    assert result.recovered_stale_running_jobs == 2
    assert len(result.summaries) == 1
    assert projection_service.requests == [
        WorkflowOutputProjectionRequest(
            workflow_name="morning_report",
            execution_id="exec-1",
            run_id="run-1",
            requested_at=result.requested.requested_at,
            force_reproject=False,
        )
    ]
    assert repository.recover_calls == [
        (started_before, "Projection job recovered by operational retry command.")
    ]


@pytest.mark.asyncio
async def test_projection_operations_retry_dry_run_does_not_recover_or_project() -> (
    None
):
    started_before = datetime(2026, 1, 1, tzinfo=UTC)
    jobs = (
        _job_record(projection_job_id="job-1", run_id="run-1"),
        _job_record(projection_job_id="job-2", run_id="run-1"),
    )
    projection_service = FakeProjectionService()
    repository = FakeProjectionJobRepository(jobs=jobs, recovered_jobs=2)
    service = _operations_service(
        projection_service=projection_service,
        repository=repository,
    )

    result = await service.retry_projection(
        WorkflowOutputProjectionRetryRequest(
            statuses=(WorkflowOutputProjectionStatus.FAILED,),
            stale_running_started_before=started_before,
            dry_run=True,
        )
    )

    assert result.matched_jobs == 2
    assert result.retried_jobs == 0
    assert result.recovered_stale_running_jobs == 0
    assert result.summaries == ()
    assert projection_service.requests == []
    assert repository.recover_calls == []


@pytest.mark.asyncio
async def test_projection_operations_reconcile_reports_missing_runs_in_dry_run() -> (
    None
):
    missing = MissingProjectionRunRecord(
        run_id="run-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        completed_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    projection_service = FakeProjectionService()
    repository = FakeProjectionJobRepository(missing_runs=(missing,))
    service = _operations_service(
        projection_service=projection_service,
        repository=repository,
    )

    result = await service.reconcile_projections(
        WorkflowOutputProjectionReconciliationRequest(dry_run=True)
    )

    assert result.scanned_runs == 1
    assert result.missing_projection_runs == 1
    assert result.missing_runs == (missing,)
    assert projection_service.requests == []


@pytest.mark.asyncio
async def test_projection_operations_reconcile_filters_window_and_projects_missing_runs() -> (  # noqa: E501 - descriptive pytest node id
    None
):
    before_window = MissingProjectionRunRecord(
        run_id="run-before",
        workflow_name="morning_report",
        execution_id="exec-before",
        completed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    in_window = MissingProjectionRunRecord(
        run_id="run-in",
        workflow_name="morning_report",
        execution_id="exec-in",
        completed_at=datetime(2026, 1, 15, tzinfo=UTC),
    )
    after_window = MissingProjectionRunRecord(
        run_id="run-after",
        workflow_name="morning_report",
        execution_id="exec-after",
        completed_at=datetime(2026, 2, 1, tzinfo=UTC),
    )
    projection_service = FakeProjectionService(
        outcomes=(
            WorkflowOutputProjectionOutcome(
                status=WorkflowOutputProjectionStatus.SUCCEEDED,
                projector_name="technical_projector",
                node_name="technical_agent",
                output_contract="polaris.market.technical_analysis",
                output_schema_version=1,
                source_fingerprint="source-fingerprint-1",
                records_written=1,
            ),
        )
    )
    repository = FakeProjectionJobRepository(
        missing_runs=(before_window, in_window, after_window)
    )
    service = _operations_service(
        projection_service=projection_service,
        repository=repository,
    )

    result = await service.reconcile_projections(
        WorkflowOutputProjectionReconciliationRequest(
            since=datetime(2026, 1, 10, tzinfo=UTC),
            until=datetime(2026, 1, 20, tzinfo=UTC),
            dry_run=False,
            enqueue_missing_jobs=True,
        )
    )

    assert result.scanned_runs == 1
    assert result.missing_projection_runs == 1
    assert result.enqueued_jobs == 1
    assert result.missing_runs == (in_window,)
    assert len(result.summaries) == 1
    assert projection_service.requests == [
        WorkflowOutputProjectionRequest(
            workflow_name="morning_report",
            execution_id="exec-in",
            run_id="run-in",
            requested_at=result.requested.requested_at,
        )
    ]


def test_projection_operations_requests_reject_invalid_status_and_limit() -> None:
    with pytest.raises(
        ValueError, match="Unsupported workflow output projection status"
    ):
        WorkflowOutputProjectionStatusRequest(statuses=("unknown",))

    with pytest.raises(ValueError, match="limit must be positive"):
        WorkflowOutputProjectionStatusRequest(limit=0)

    with pytest.raises(ValueError, match="limit must be positive"):
        WorkflowOutputProjectionRetryRequest(limit=0)

    with pytest.raises(ValueError, match="since cannot be later than until"):
        WorkflowOutputProjectionReconciliationRequest(
            since=datetime(2026, 1, 2, tzinfo=UTC),
            until=datetime(2026, 1, 1, tzinfo=UTC),
        )


def _operations_service(
    *,
    projection_service: FakeProjectionService | None = None,
    repository: FakeProjectionJobRepository | None = None,
) -> WorkflowOutputProjectionOperationsService:
    return WorkflowOutputProjectionOperationsService(
        projection_service=cast(
            WorkflowOutputProjectionService,
            projection_service or FakeProjectionService(),
        ),
        projection_job_repository=cast(
            WorkflowOutputProjectionJobRepository,
            repository or FakeProjectionJobRepository(),
        ),
    )


def _job_record(
    *,
    projection_job_id: str = "job-1",
    run_id: str = "run-1",
    status: WorkflowOutputProjectionJobStatus = (
        WorkflowOutputProjectionJobStatus.FAILED
    ),
) -> WorkflowOutputProjectionJobRecord:
    return WorkflowOutputProjectionJobRecord(
        projection_job_id=projection_job_id,
        run_id=run_id,
        workflow_name="morning_report",
        execution_id="exec-1",
        node_name="technical_agent",
        projector_name="technical_projector",
        output_contract="polaris.market.technical_analysis",
        output_schema_version=1,
        source_fingerprint=f"fingerprint-{projection_job_id}",
        status=status,
    )
