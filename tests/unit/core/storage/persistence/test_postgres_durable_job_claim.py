from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.ai_observability import AiObservabilityExportJobModel
from core.database.models.projections import WorkflowOutputProjectionJobModel
from core.storage.persistence.ai_observability import (
    AiObservabilityExportJobClaim,
    AiObservabilityExportJobStatus,
)
from core.storage.persistence.projections import (
    ProjectionJobClaim,
    WorkflowOutputProjectionJobStatus,
)
from core.storage.persistence.repositories import (
    PostgresAiObservabilityExportJobRepository,
    PostgresWorkflowOutputProjectionJobRepository,
)


class FakeExecuteResult:
    def __init__(self, rows: Sequence[object] | None = None) -> None:
        self._rows = list(rows or [])

    def scalar_one(self) -> object:
        if not self._rows:
            raise AssertionError("Expected one row.")
        return self._rows[0]

    def scalar_one_or_none(self) -> object | None:
        if not self._rows:
            return None
        return self._rows[0]

    def scalars(self) -> FakeExecuteResult:
        return self

    def all(self) -> Sequence[object]:
        return tuple(self._rows)


class FakeAsyncSession:
    def __init__(
        self,
        responses: Sequence[FakeExecuteResult | SQLAlchemyError],
        *,
        commit_error: SQLAlchemyError | None = None,
    ) -> None:
        self.responses = list(responses)
        self.commit_error = commit_error
        self.executed: list[Any] = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, statement: Any) -> FakeExecuteResult:
        self.executed.append(statement)
        if not self.responses:
            raise AssertionError("Unexpected execute call.")
        response = self.responses.pop(0)
        if isinstance(response, SQLAlchemyError):
            raise response
        return response

    async def commit(self) -> None:
        self.commits += 1
        if self.commit_error is not None:
            raise self.commit_error

    async def rollback(self) -> None:
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_projection_claim_preserves_selection_and_reclaim_reset() -> None:
    running_model = _projection_model(
        status=WorkflowOutputProjectionJobStatus.RUNNING,
        attempt_count=2,
        completed_at=None,
    )
    session = FakeAsyncSession(
        (
            FakeExecuteResult(
                [
                    _projection_model(
                        status=WorkflowOutputProjectionJobStatus.FAILED,
                        attempt_count=1,
                        completed_at=datetime(2026, 8, 1, 12, tzinfo=UTC),
                    )
                ]
            ),
            FakeExecuteResult([running_model]),
        )
    )
    repository = PostgresWorkflowOutputProjectionJobRepository(
        cast(AsyncSession, session)
    )

    record = await repository.claim_next_job(
        ProjectionJobClaim(
            workflow_name="morning_report",
            execution_id="exec-1",
            projector_name="technical_projector",
        )
    )

    select_sql = _compile(session.executed[0])
    update_sql = _compile(session.executed[1])
    assert record is not None
    assert record.status == WorkflowOutputProjectionJobStatus.RUNNING
    assert record.attempt_count == 2
    assert session.commits == 1
    assert session.rollbacks == 0
    assert "FOR UPDATE SKIP LOCKED" in select_sql
    assert "workflow_output_projection_jobs.status IN" in select_sql
    assert "workflow_output_projection_jobs.workflow_name" in select_sql
    assert "workflow_output_projection_jobs.execution_id" in select_sql
    assert "workflow_output_projection_jobs.projector_name" in select_sql
    assert "ORDER BY workflow_output_projection_jobs.created_at ASC" in select_sql
    assert "workflow_output_projection_jobs.projection_job_id ASC" in select_sql
    assert "UPDATE workflow_output_projection_jobs" in update_sql
    assert (
        "attempt_count=(workflow_output_projection_jobs.attempt_count +" in update_sql
    )
    assert "started_at=now()" in update_sql
    assert "completed_at=NULL" in update_sql
    assert "last_error=NULL" in update_sql
    assert "updated_at=now()" in update_sql


@pytest.mark.asyncio
async def test_projection_specific_claim_preserves_lock_and_status_filter() -> None:
    running_model = _projection_model(
        status=WorkflowOutputProjectionJobStatus.RUNNING,
        attempt_count=1,
    )
    session = FakeAsyncSession(
        (
            FakeExecuteResult(
                [_projection_model(status=WorkflowOutputProjectionJobStatus.PENDING)]
            ),
            FakeExecuteResult([running_model]),
        )
    )
    repository = PostgresWorkflowOutputProjectionJobRepository(
        cast(AsyncSession, session)
    )

    record = await repository.claim_job(
        "projection-job-1",
        statuses=(WorkflowOutputProjectionJobStatus.PENDING,),
    )

    select_sql = _compile(session.executed[0])
    assert record is not None
    assert record.status == WorkflowOutputProjectionJobStatus.RUNNING
    assert "workflow_output_projection_jobs.projection_job_id" in select_sql
    assert "workflow_output_projection_jobs.status IN" in select_sql
    assert "FOR UPDATE SKIP LOCKED" in select_sql


@pytest.mark.asyncio
async def test_observability_claim_preserves_retry_eligibility_and_ordering() -> None:
    running_model = _observability_model(
        status=AiObservabilityExportJobStatus.RUNNING,
        attempt_count=2,
    )
    session = FakeAsyncSession(
        (
            FakeExecuteResult(
                [
                    _observability_model(
                        status=AiObservabilityExportJobStatus.FAILED,
                        attempt_count=1,
                    )
                ]
            ),
            FakeExecuteResult([running_model]),
        )
    )
    repository = PostgresAiObservabilityExportJobRepository(cast(AsyncSession, session))

    record = await repository.claim_next_job(
        AiObservabilityExportJobClaim(
            workflow_name="morning_report",
            execution_id="exec-1",
            observation_type="generation",
        )
    )

    select_sql = _compile(session.executed[0])
    update_sql = _compile(session.executed[1])
    assert record is not None
    assert record.status == AiObservabilityExportJobStatus.RUNNING
    assert record.attempt_count == 2
    assert session.commits == 1
    assert session.rollbacks == 0
    assert "FOR UPDATE SKIP LOCKED" in select_sql
    assert "ai_observability_export_jobs.status IN" in select_sql
    assert "ai_observability_export_jobs.available_at <= now()" in select_sql
    assert "ai_observability_export_jobs.attempt_count <" in select_sql
    assert "ai_observability_export_jobs.max_attempts" in select_sql
    assert "ai_observability_export_jobs.workflow_name" in select_sql
    assert "ai_observability_export_jobs.execution_id" in select_sql
    assert "ai_observability_export_jobs.observation_type" in select_sql
    assert "ORDER BY ai_observability_export_jobs.available_at ASC" in select_sql
    assert "ai_observability_export_jobs.created_at ASC" in select_sql
    assert "ai_observability_export_jobs.export_job_id ASC" in select_sql
    assert "UPDATE ai_observability_export_jobs" in update_sql
    assert "attempt_count=(ai_observability_export_jobs.attempt_count +" in update_sql
    assert "started_at=now()" in update_sql
    assert "last_error=NULL" in update_sql
    assert "updated_at=now()" in update_sql


@pytest.mark.asyncio
@pytest.mark.parametrize("repository_name", ["projection", "observability"])
async def test_claim_without_candidate_does_not_transition_or_commit(
    repository_name: str,
) -> None:
    session = FakeAsyncSession((FakeExecuteResult(),))
    repository: (
        PostgresWorkflowOutputProjectionJobRepository
        | PostgresAiObservabilityExportJobRepository
    )
    if repository_name == "projection":
        repository = PostgresWorkflowOutputProjectionJobRepository(
            cast(AsyncSession, session)
        )
    else:
        repository = PostgresAiObservabilityExportJobRepository(
            cast(AsyncSession, session)
        )

    record = await repository.claim_next_job()

    assert record is None
    assert len(session.executed) == 1
    assert session.commits == 0
    assert session.rollbacks == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("repository_name", ["projection", "observability"])
@pytest.mark.parametrize("failure_index", [0, 1])
async def test_claim_sqlalchemy_error_rolls_back_and_propagates(
    repository_name: str,
    failure_index: int,
) -> None:
    repository: (
        type[PostgresWorkflowOutputProjectionJobRepository]
        | type[PostgresAiObservabilityExportJobRepository]
    )
    if repository_name == "projection":
        selected = _projection_model(status=WorkflowOutputProjectionJobStatus.FAILED)
        repository = PostgresWorkflowOutputProjectionJobRepository
    else:
        selected = _observability_model(status=AiObservabilityExportJobStatus.FAILED)
        repository = PostgresAiObservabilityExportJobRepository

    responses: tuple[FakeExecuteResult | SQLAlchemyError, ...]
    if failure_index == 0:
        responses = (SQLAlchemyError("selection failed"),)
    else:
        responses = (
            FakeExecuteResult([selected]),
            SQLAlchemyError("transition failed"),
        )
    session = FakeAsyncSession(responses)
    durable_job_repository = repository(cast(AsyncSession, session))

    with pytest.raises(SQLAlchemyError):
        await durable_job_repository.claim_next_job()

    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("repository_name", ["projection", "observability"])
async def test_claim_commit_error_rolls_back_and_propagates(
    repository_name: str,
) -> None:
    repository: (
        type[PostgresWorkflowOutputProjectionJobRepository]
        | type[PostgresAiObservabilityExportJobRepository]
    )
    if repository_name == "projection":
        selected = _projection_model(status=WorkflowOutputProjectionJobStatus.FAILED)
        running = _projection_model(
            status=WorkflowOutputProjectionJobStatus.RUNNING,
            attempt_count=1,
        )
        repository = PostgresWorkflowOutputProjectionJobRepository
    else:
        selected = _observability_model(status=AiObservabilityExportJobStatus.FAILED)
        running = _observability_model(
            status=AiObservabilityExportJobStatus.RUNNING,
            attempt_count=1,
        )
        repository = PostgresAiObservabilityExportJobRepository

    session = FakeAsyncSession(
        (FakeExecuteResult([selected]), FakeExecuteResult([running])),
        commit_error=SQLAlchemyError("commit failed"),
    )
    durable_job_repository = repository(cast(AsyncSession, session))

    with pytest.raises(SQLAlchemyError):
        await durable_job_repository.claim_next_job()

    assert session.commits == 1
    assert session.rollbacks == 1


def _projection_model(
    *,
    status: WorkflowOutputProjectionJobStatus,
    attempt_count: int = 0,
    completed_at: datetime | None = None,
) -> WorkflowOutputProjectionJobModel:
    now = datetime(2026, 8, 1, 12, tzinfo=UTC)
    return WorkflowOutputProjectionJobModel(
        projection_job_id="projection-job-1",
        run_id="run-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        node_name="technical_analysis",
        projector_name="technical_projector",
        output_contract="polaris.market.technical_analysis",
        output_schema_version=1,
        source_fingerprint="fingerprint-1",
        status=status.value,
        attempt_count=attempt_count,
        last_error=(
            "previous failure"
            if status is WorkflowOutputProjectionJobStatus.FAILED
            else None
        ),
        created_at=now,
        started_at=now if status is WorkflowOutputProjectionJobStatus.FAILED else None,
        completed_at=completed_at,
        updated_at=now,
    )


def _observability_model(
    *,
    status: AiObservabilityExportJobStatus,
    attempt_count: int = 0,
) -> AiObservabilityExportJobModel:
    now = datetime(2026, 8, 1, 12, tzinfo=UTC)
    return AiObservabilityExportJobModel(
        export_job_id="export-job-1",
        idempotency_key="idempotency-1",
        observation_type="generation",
        observation_name="strategy synthesis",
        observation_family="llm",
        observation_status="succeeded",
        payload={"value": "ok"},
        status=status.value,
        attempt_count=attempt_count,
        max_attempts=3,
        workflow_name="morning_report",
        execution_id="exec-1",
        last_error=(
            "previous failure"
            if status is AiObservabilityExportJobStatus.FAILED
            else None
        ),
        available_at=now,
        created_at=now,
        started_at=now if status is AiObservabilityExportJobStatus.FAILED else None,
        updated_at=now,
    )


def _compile(statement: Any) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
