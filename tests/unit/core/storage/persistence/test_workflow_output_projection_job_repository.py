from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.completed_runs import CompletedWorkflowRunModel
from core.database.models.projections import WorkflowOutputProjectionJobModel
from core.storage.persistence.projections import (
    ProjectionJobClaim,
    WorkflowOutputProjectionJobRecord,
    WorkflowOutputProjectionJobStatus,
)
from core.storage.persistence.repositories.postgres_workflow_output_projection_job_repository import (  # noqa: E501 - canonical module path
    PostgresWorkflowOutputProjectionJobRepository,
)


class FakeExecuteResult:
    def __init__(
        self,
        rows: Sequence[object] | None = None,
        rowcount: int | None = None,
    ) -> None:
        self._rows = list(rows or [])
        self.rowcount = rowcount

    def scalar_one(
        self,
    ) -> object:
        if not self._rows:
            raise AssertionError("Expected one row.")
        return self._rows[0]

    def scalar_one_or_none(
        self,
    ) -> object | None:
        if not self._rows:
            return None
        return self._rows[0]

    def scalars(
        self,
    ) -> FakeExecuteResult:
        return self

    def all(
        self,
    ) -> Sequence[object]:
        return tuple(self._rows)


class FakeAsyncSession:
    def __init__(
        self,
        results: Sequence[FakeExecuteResult] | None = None,
        error: SQLAlchemyError | None = None,
    ) -> None:
        self.results = list(results or [])
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

        if self.results:
            return self.results.pop(0)

        return FakeExecuteResult()

    async def commit(
        self,
    ) -> None:
        self.commits += 1

    async def rollback(
        self,
    ) -> None:
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_create_job_uses_idempotent_source_upsert() -> None:
    session = FakeAsyncSession(results=(FakeExecuteResult([_job_model()]),))
    repository = PostgresWorkflowOutputProjectionJobRepository(
        cast(AsyncSession, session)
    )

    record = await repository.create_job(_job_record())

    compiled = _compile(session.executed[0])
    assert record.projection_job_id == "projection-job-1"
    assert session.commits == 1
    assert "INSERT INTO workflow_output_projection_jobs" in compiled
    assert (
        "ON CONFLICT ON CONSTRAINT uq_workflow_output_projection_jobs_source"
        in compiled
    )
    assert "RETURNING" in compiled


@pytest.mark.asyncio
async def test_create_job_rolls_back_on_sqlalchemy_error() -> None:
    session = FakeAsyncSession(error=SQLAlchemyError("database unavailable"))
    repository = PostgresWorkflowOutputProjectionJobRepository(
        cast(AsyncSession, session)
    )

    with pytest.raises(SQLAlchemyError):
        await repository.create_job(_job_record())

    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_claim_next_job_locks_pending_or_failed_job_and_marks_running() -> None:
    running_model = _job_model(
        status=WorkflowOutputProjectionJobStatus.RUNNING,
        attempt_count=2,
    )
    session = FakeAsyncSession(
        results=(
            FakeExecuteResult(
                [_job_model(status=WorkflowOutputProjectionJobStatus.FAILED)]
            ),
            FakeExecuteResult([running_model]),
        )
    )
    repository = PostgresWorkflowOutputProjectionJobRepository(
        cast(AsyncSession, session)
    )

    record = await repository.claim_next_job(
        ProjectionJobClaim(workflow_name="morning_report"),
    )

    select_sql = _compile(session.executed[0])
    update_sql = _compile(session.executed[1])
    assert record is not None
    assert record.status is WorkflowOutputProjectionJobStatus.RUNNING
    assert session.commits == 1
    assert "FOR UPDATE SKIP LOCKED" in select_sql
    assert "LIMIT" in select_sql
    assert "UPDATE workflow_output_projection_jobs" in update_sql
    assert (
        "attempt_count=(workflow_output_projection_jobs.attempt_count +" in update_sql
    )
    assert "RETURNING" in update_sql


@pytest.mark.asyncio
async def test_claim_job_locks_specific_projection_job_and_marks_running() -> None:
    running_model = _job_model(
        status=WorkflowOutputProjectionJobStatus.RUNNING,
        attempt_count=1,
    )
    session = FakeAsyncSession(
        results=(
            FakeExecuteResult(
                [_job_model(status=WorkflowOutputProjectionJobStatus.PENDING)]
            ),
            FakeExecuteResult([running_model]),
        )
    )
    repository = PostgresWorkflowOutputProjectionJobRepository(
        cast(AsyncSession, session)
    )

    record = await repository.claim_job("projection-job-1")

    select_sql = _compile(session.executed[0])
    update_sql = _compile(session.executed[1])
    assert record is not None
    assert record.status is WorkflowOutputProjectionJobStatus.RUNNING
    assert session.commits == 1
    assert "projection_job_id" in select_sql
    assert "FOR UPDATE SKIP LOCKED" in select_sql
    assert "UPDATE workflow_output_projection_jobs" in update_sql
    assert "RETURNING" in update_sql


@pytest.mark.asyncio
async def test_claim_next_job_returns_none_when_no_job_is_available() -> None:
    session = FakeAsyncSession(results=(FakeExecuteResult(),))
    repository = PostgresWorkflowOutputProjectionJobRepository(
        cast(AsyncSession, session)
    )

    record = await repository.claim_next_job()

    assert record is None
    assert session.commits == 0
    assert len(session.executed) == 1


@pytest.mark.asyncio
async def test_mark_succeeded_updates_terminal_status() -> None:
    session = FakeAsyncSession(
        results=(
            FakeExecuteResult(
                [_job_model(status=WorkflowOutputProjectionJobStatus.SUCCEEDED)]
            ),
        )
    )
    repository = PostgresWorkflowOutputProjectionJobRepository(
        cast(AsyncSession, session)
    )

    record = await repository.mark_succeeded("projection-job-1")

    compiled = _compile(session.executed[0])
    assert record is not None
    assert record.status is WorkflowOutputProjectionJobStatus.SUCCEEDED
    assert session.commits == 1
    assert "UPDATE workflow_output_projection_jobs" in compiled
    assert "RETURNING" in compiled


@pytest.mark.asyncio
async def test_mark_failed_requires_error_and_persists_last_error() -> None:
    session = FakeAsyncSession(
        results=(
            FakeExecuteResult(
                [_job_model(status=WorkflowOutputProjectionJobStatus.FAILED)]
            ),
        )
    )
    repository = PostgresWorkflowOutputProjectionJobRepository(
        cast(AsyncSession, session)
    )

    record = await repository.mark_failed("projection-job-1", error="projector failed")

    compiled = _compile(session.executed[0])
    assert record is not None
    assert record.status is WorkflowOutputProjectionJobStatus.FAILED
    assert "last_error" in compiled


@pytest.mark.asyncio
async def test_mark_skipped_persists_optional_reason() -> None:
    session = FakeAsyncSession(
        results=(
            FakeExecuteResult(
                [_job_model(status=WorkflowOutputProjectionJobStatus.SKIPPED)]
            ),
        )
    )
    repository = PostgresWorkflowOutputProjectionJobRepository(
        cast(AsyncSession, session)
    )

    record = await repository.mark_skipped("projection-job-1", reason="not eligible")

    compiled = _compile(session.executed[0])
    assert record is not None
    assert record.status is WorkflowOutputProjectionJobStatus.SKIPPED
    assert "last_error" in compiled


@pytest.mark.asyncio
async def test_list_jobs_applies_filters_statuses_and_limit() -> None:
    session = FakeAsyncSession(results=(FakeExecuteResult([_job_model()]),))
    repository = PostgresWorkflowOutputProjectionJobRepository(
        cast(AsyncSession, session)
    )

    records = await repository.list_jobs(
        workflow_name="morning_report",
        execution_id="exec-1",
        projector_name="technical_projector",
        statuses=(WorkflowOutputProjectionJobStatus.PENDING,),
        limit=10,
    )

    compiled = _compile(session.executed[0])
    assert len(records) == 1
    assert "WHERE" in compiled
    assert "ORDER BY" in compiled
    assert "LIMIT" in compiled


@pytest.mark.asyncio
async def test_recover_stale_running_jobs_marks_jobs_failed() -> None:
    session = FakeAsyncSession(results=(FakeExecuteResult(rowcount=3),))
    repository = PostgresWorkflowOutputProjectionJobRepository(
        cast(AsyncSession, session)
    )

    recovered = await repository.recover_stale_running_jobs(
        started_before=datetime(2026, 7, 9, 12, tzinfo=UTC),
        error="projection worker interrupted",
    )

    compiled = _compile(session.executed[0])
    assert recovered == 3
    assert session.commits == 1
    assert "UPDATE workflow_output_projection_jobs" in compiled
    assert "started_at" in compiled


@pytest.mark.asyncio
async def test_list_runs_missing_projection_jobs_uses_not_exists_query() -> None:
    session = FakeAsyncSession(results=(FakeExecuteResult([_run_model()]),))
    repository = PostgresWorkflowOutputProjectionJobRepository(
        cast(AsyncSession, session)
    )

    records = await repository.list_runs_missing_projection_jobs(
        workflow_name="morning_report",
        limit=5,
    )

    compiled = _compile(session.executed[0])
    assert len(records) == 1
    assert records[0].run_id == "run-1"
    assert "NOT (EXISTS" in compiled
    assert (
        "workflow_output_projection_jobs.run_id = completed_workflow_runs.run_id"
        in compiled
    )
    assert "LIMIT" in compiled


def _job_record() -> WorkflowOutputProjectionJobRecord:
    return WorkflowOutputProjectionJobRecord(
        projection_job_id="projection-job-1",
        run_id="run-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        node_name="technical_analysis",
        projector_name="technical_projector",
        output_contract="polaris.market.technical_analysis",
        output_schema_version=1,
        source_fingerprint="fingerprint-1",
        status=WorkflowOutputProjectionJobStatus.PENDING,
    )


def _job_model(
    *,
    status: WorkflowOutputProjectionJobStatus = (
        WorkflowOutputProjectionJobStatus.PENDING
    ),
    attempt_count: int = 0,
) -> WorkflowOutputProjectionJobModel:
    record = _job_record()
    return WorkflowOutputProjectionJobModel(
        projection_job_id=record.projection_job_id,
        run_id=record.run_id,
        workflow_name=record.workflow_name,
        execution_id=record.execution_id,
        node_name=record.node_name,
        projector_name=record.projector_name,
        output_contract=record.output_contract,
        output_schema_version=record.output_schema_version,
        source_fingerprint=record.source_fingerprint,
        status=status.value,
        attempt_count=attempt_count,
        last_error=None,
        created_at=datetime(2026, 7, 9, 12, tzinfo=UTC),
        started_at=None,
        completed_at=None,
        updated_at=datetime(2026, 7, 9, 12, tzinfo=UTC),
    )


def _run_model() -> CompletedWorkflowRunModel:
    return CompletedWorkflowRunModel(
        run_id="run-1",
        workflow_name="morning_report",
        workflow_id="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        status="succeeded",
        success=True,
        context_json={},
        inputs_json={},
        outputs_json={},
        metadata_payload={},
        errors_json=[],
        completed_at=datetime(2026, 7, 9, 12, tzinfo=UTC),
    )


def _compile(statement: Any) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": False},
        )
    )
