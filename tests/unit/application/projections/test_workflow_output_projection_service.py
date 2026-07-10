from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from typing import Sequence

import pytest

from application.projections.workflow_outputs import CompletedRunProjectionNotFoundError
from application.projections.workflow_outputs import WorkflowOutputProjectionOutcome
from application.projections.workflow_outputs import WorkflowOutputProjectionRegistry
from application.projections.workflow_outputs import WorkflowOutputProjectionRequest
from application.projections.workflow_outputs import WorkflowOutputProjectionService
from application.projections.workflow_outputs import WorkflowOutputProjectionStatus
from application.projections.workflow_outputs import WorkflowOutputProjectorRegistration
from application.projections.workflow_outputs import WorkflowOutputProjectorRequest
from application.projections.workflow_outputs import (
    calculate_workflow_output_source_fingerprint,
)
from core.storage.persistence.completed_run_archive import CompletedNodeOutputRecord
from core.storage.persistence.completed_run_archive import CompletedRunArchive
from core.storage.persistence.completed_run_archive import CompletedRunBundle
from core.storage.persistence.completed_run_archive import CompletedRunExecutionMode
from core.storage.persistence.completed_run_archive import CompletedRunRecord
from core.storage.persistence.completed_run_archive import JsonObject
from core.storage.persistence.projections import MissingProjectionRunRecord
from core.storage.persistence.projections import ProjectionJobClaim
from core.storage.persistence.projections import WorkflowOutputProjectionJobRecord
from core.storage.persistence.projections import WorkflowOutputProjectionJobStatus
from core.storage.persistence.lineage import PersistenceLineage


@dataclass(slots=True)
class StubProjector:
    projector_name: str = "technical_projector"
    records_written: int = 2
    should_raise: bool = False
    calls: int = 0
    last_request: WorkflowOutputProjectorRequest | None = None

    async def project(
        self,
        request: WorkflowOutputProjectorRequest,
    ) -> WorkflowOutputProjectionOutcome:
        self.calls += 1
        self.last_request = request
        if self.should_raise:
            raise RuntimeError("projector exploded")
        return WorkflowOutputProjectionOutcome(
            status=WorkflowOutputProjectionStatus.SUCCEEDED,
            projector_name=self.projector_name,
            node_name=request.node_output.node_name,
            output_contract=request.node_output.output_contract or "unsupported",
            output_schema_version=request.node_output.output_schema_version or 1,
            source_fingerprint=request.source_fingerprint,
            records_written=self.records_written,
        )


class FakeCompletedRunArchive(CompletedRunArchive):
    def __init__(self, bundle: CompletedRunBundle | None) -> None:
        self.bundle = bundle
        self.loaded: list[tuple[str, str]] = []

    async def archive_run(self, bundle: CompletedRunBundle) -> None:
        self.bundle = bundle

    async def load_archived_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> CompletedRunBundle | None:
        self.loaded.append((workflow_name, execution_id))
        return self.bundle

    async def list_archived_runs(self, workflow_name: str) -> list[str]:
        return []

    async def delete_archived_run(self, workflow_name: str, execution_id: str) -> None:
        return None

    async def cleanup_archived_runs(
        self,
        max_age_days: int | None = None,
        max_count: int | None = None,
    ) -> int:
        return 0


class FakeProjectionJobRepository:
    def __init__(
        self, initial_status: WorkflowOutputProjectionJobStatus | None = None
    ) -> None:
        self.initial_status = initial_status
        self.created: list[WorkflowOutputProjectionJobRecord] = []
        self.claimed: list[
            tuple[str, tuple[WorkflowOutputProjectionJobStatus | str, ...] | None]
        ] = []
        self.succeeded: list[str] = []
        self.failed: list[tuple[str, str]] = []
        self.skipped: list[tuple[str, str | None]] = []

    async def create_job(
        self,
        record: WorkflowOutputProjectionJobRecord,
    ) -> WorkflowOutputProjectionJobRecord:
        self.created.append(record)
        if self.initial_status is None:
            return record
        return _job_record(
            status=self.initial_status, projection_job_id=record.projection_job_id
        )

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
        self.claimed.append((projection_job_id, tuple(statuses) if statuses else None))
        if self.initial_status is WorkflowOutputProjectionJobStatus.RUNNING:
            return None
        return _job_record(
            status=WorkflowOutputProjectionJobStatus.RUNNING,
            projection_job_id=projection_job_id,
        )

    async def mark_succeeded(
        self,
        projection_job_id: str,
        *,
        completed_at: datetime | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None:
        self.succeeded.append(projection_job_id)
        return _job_record(
            status=WorkflowOutputProjectionJobStatus.SUCCEEDED,
            projection_job_id=projection_job_id,
        )

    async def mark_failed(
        self,
        projection_job_id: str,
        *,
        error: str,
        completed_at: datetime | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None:
        self.failed.append((projection_job_id, error))
        return _job_record(
            status=WorkflowOutputProjectionJobStatus.FAILED,
            projection_job_id=projection_job_id,
            last_error=error,
        )

    async def mark_skipped(
        self,
        projection_job_id: str,
        *,
        reason: str | None = None,
        completed_at: datetime | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None:
        self.skipped.append((projection_job_id, reason))
        return _job_record(
            status=WorkflowOutputProjectionJobStatus.SKIPPED,
            projection_job_id=projection_job_id,
            last_error=reason,
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
        return ()

    async def recover_stale_running_jobs(
        self,
        *,
        started_before: datetime,
        error: str,
    ) -> int:
        return 0

    async def list_runs_missing_projection_jobs(
        self,
        *,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        limit: int | None = None,
    ) -> Sequence[MissingProjectionRunRecord]:
        return ()


@pytest.mark.asyncio
async def test_project_completed_run_creates_claims_invokes_projector_and_marks_success() -> (
    None
):
    projector = StubProjector()
    repository = FakeProjectionJobRepository()
    service = _service(projector=projector, repository=repository)

    summary = await service.project_completed_run(
        WorkflowOutputProjectionRequest(
            workflow_name="morning_report",
            execution_id="exec-1",
        )
    )

    assert summary.success is True
    assert summary.total_jobs == 1
    assert summary.succeeded_jobs == 1
    assert summary.records_written == 2
    assert projector.calls == 1
    assert projector.last_request is not None
    assert projector.last_request.lineage == PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="technical_agent",
    )
    assert len(repository.created) == 1
    assert len(repository.claimed) == 1
    assert repository.succeeded == [repository.created[0].projection_job_id]


@pytest.mark.asyncio
async def test_project_completed_run_uses_run_execution_mode_as_canonical_skip_source() -> (
    None
):
    projector = StubProjector()
    repository = FakeProjectionJobRepository()
    bundle = _bundle(
        run=_run(
            execution_mode=CompletedRunExecutionMode.BACKTEST,
            metadata={"execution_mode": "normal"},
        )
    )
    service = _service(projector=projector, repository=repository, bundle=bundle)

    summary = await service.project_completed_run(
        WorkflowOutputProjectionRequest(
            workflow_name="morning_report",
            execution_id="exec-1",
        )
    )

    assert summary.skipped_jobs == 1
    assert projector.calls == 0
    assert repository.created == []
    assert "backtest" in str(summary.outcomes[0].message)


@pytest.mark.asyncio
async def test_project_completed_run_records_projector_failure_and_continues() -> None:
    projector = StubProjector(should_raise=True)
    repository = FakeProjectionJobRepository()
    service = _service(projector=projector, repository=repository)

    summary = await service.project_completed_run(
        WorkflowOutputProjectionRequest(
            workflow_name="morning_report",
            execution_id="exec-1",
        )
    )

    assert summary.success is False
    assert summary.failed_jobs == 1
    assert projector.calls == 1
    assert repository.failed
    assert "RuntimeError" in repository.failed[0][1]
    assert summary.outcomes[0].error_type == "RuntimeError"


@pytest.mark.asyncio
async def test_project_completed_run_skips_already_succeeded_job_without_force() -> (
    None
):
    projector = StubProjector()
    repository = FakeProjectionJobRepository(
        initial_status=WorkflowOutputProjectionJobStatus.SUCCEEDED,
    )
    service = _service(projector=projector, repository=repository)

    summary = await service.project_completed_run(
        WorkflowOutputProjectionRequest(
            workflow_name="morning_report",
            execution_id="exec-1",
        )
    )

    assert summary.skipped_jobs == 1
    assert projector.calls == 0
    assert repository.claimed == []
    assert "already succeeded" in str(summary.outcomes[0].message)


@pytest.mark.asyncio
async def test_project_completed_run_force_reprojects_terminal_job() -> None:
    projector = StubProjector()
    repository = FakeProjectionJobRepository(
        initial_status=WorkflowOutputProjectionJobStatus.SUCCEEDED,
    )
    service = _service(projector=projector, repository=repository)

    summary = await service.project_completed_run(
        WorkflowOutputProjectionRequest(
            workflow_name="morning_report",
            execution_id="exec-1",
            force_reproject=True,
        )
    )

    assert summary.succeeded_jobs == 1
    assert projector.calls == 1
    assert repository.claimed
    assert WorkflowOutputProjectionJobStatus.SUCCEEDED in repository.claimed[0][1]


@pytest.mark.asyncio
async def test_project_completed_run_missing_archive_raises_not_found() -> None:
    repository = FakeProjectionJobRepository()
    archive = FakeCompletedRunArchive(bundle=None)
    service = WorkflowOutputProjectionService(
        completed_run_archive=archive,
        projection_job_repository=repository,
        registry=_registry(StubProjector()),
    )

    with pytest.raises(CompletedRunProjectionNotFoundError):
        await service.project_completed_run(
            WorkflowOutputProjectionRequest(
                workflow_name="morning_report",
                execution_id="missing",
            )
        )


def test_source_fingerprint_is_deterministic_and_changes_with_output_data() -> None:
    run = _run()
    node = _node(outputs={"technical_score": 0.8})

    first = calculate_workflow_output_source_fingerprint(run=run, node_output=node)
    second = calculate_workflow_output_source_fingerprint(run=run, node_output=node)
    changed = calculate_workflow_output_source_fingerprint(
        run=run,
        node_output=_node(outputs={"technical_score": 0.9}),
    )

    assert first == second
    assert first != changed


def _service(
    *,
    projector: StubProjector,
    repository: FakeProjectionJobRepository,
    bundle: CompletedRunBundle | None = None,
) -> WorkflowOutputProjectionService:
    return WorkflowOutputProjectionService(
        completed_run_archive=FakeCompletedRunArchive(bundle or _bundle()),
        projection_job_repository=repository,
        registry=_registry(projector),
    )


def _registry(projector: StubProjector) -> WorkflowOutputProjectionRegistry:
    return WorkflowOutputProjectionRegistry(
        (
            WorkflowOutputProjectorRegistration(
                projector_name=projector.projector_name,
                output_contract="polaris.market.technical_analysis",
                output_schema_version=1,
                projector=projector,
                supported_node_names=("technical_agent",),
            ),
        )
    )


def _bundle(
    *,
    run: CompletedRunRecord | None = None,
    node_outputs: tuple[CompletedNodeOutputRecord, ...] | None = None,
) -> CompletedRunBundle:
    return CompletedRunBundle(
        run=run or _run(),
        node_outputs=node_outputs or (_node(),),
    )


def _run(
    *,
    execution_mode: CompletedRunExecutionMode = CompletedRunExecutionMode.NORMAL,
    metadata: JsonObject | None = None,
) -> CompletedRunRecord:
    return CompletedRunRecord(
        run_id="run-1",
        workflow_name="morning_report",
        workflow_id="workflow-1",
        execution_id="exec-1",
        runtime_id="runtime-1",
        status="succeeded",
        success=True,
        context_json={},
        inputs_json={},
        outputs_json={},
        metadata=metadata or {},
        errors_json=(),
        started_at=datetime(2026, 7, 9, 12, tzinfo=UTC),
        completed_at=datetime(2026, 7, 9, 12, 5, tzinfo=UTC),
        duration_seconds=300.0,
        node_count=1,
        completed_node_count=1,
        failed_node_count=0,
        execution_mode=execution_mode,
    )


def _node(
    *,
    outputs: JsonObject | None = None,
) -> CompletedNodeOutputRecord:
    return CompletedNodeOutputRecord(
        node_output_id="node-output-1",
        run_id="run-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        node_name="technical_agent",
        node_type="runtime_node",
        output_contract="polaris.market.technical_analysis",
        output_schema_version=1,
        status="succeeded",
        success=True,
        outputs=outputs or {"technical_score": 0.8},
        metadata={},
        errors_json=(),
        started_at=datetime(2026, 7, 9, 12, tzinfo=UTC),
        completed_at=datetime(2026, 7, 9, 12, 1, tzinfo=UTC),
        duration_seconds=60.0,
    )


def _job_record(
    *,
    status: WorkflowOutputProjectionJobStatus,
    projection_job_id: str = "projection-job-1",
    last_error: str | None = None,
) -> WorkflowOutputProjectionJobRecord:
    return WorkflowOutputProjectionJobRecord(
        projection_job_id=projection_job_id,
        run_id="run-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        node_name="technical_agent",
        projector_name="technical_projector",
        output_contract="polaris.market.technical_analysis",
        output_schema_version=1,
        source_fingerprint="source-fingerprint-1",
        status=status,
        attempt_count=1,
        last_error=last_error,
    )
