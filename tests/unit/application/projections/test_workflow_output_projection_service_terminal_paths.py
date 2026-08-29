from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import cast

import pytest

from application.projections.workflow_outputs import (
    WorkflowOutputProjectionOutcome,
    WorkflowOutputProjectionRegistry,
    WorkflowOutputProjectionRequest,
    WorkflowOutputProjectionService,
    WorkflowOutputProjectionStatus,
    WorkflowOutputProjectorRegistration,
    WorkflowOutputProjectorRequest,
)
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunArchive,
    CompletedRunBundle,
    CompletedRunExecutionMode,
    CompletedRunRecord,
)
from core.storage.persistence.projections import (
    WorkflowOutputProjectionJobRecord,
    WorkflowOutputProjectionJobRepository,
    WorkflowOutputProjectionJobStatus,
)
from core.telemetry.observability import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink


@dataclass(slots=True)
class TerminalOutcomeProjector:
    status: WorkflowOutputProjectionStatus
    projector_name: str = "terminal_outcome_projector"
    calls: int = 0

    async def project(
        self,
        request: WorkflowOutputProjectorRequest,
    ) -> WorkflowOutputProjectionOutcome:
        self.calls += 1
        message = "Projector returned a terminal outcome."
        return WorkflowOutputProjectionOutcome(
            status=self.status,
            projector_name=self.projector_name,
            node_name=request.node_output.node_name,
            output_contract=request.node_output.output_contract or "unsupported",
            output_schema_version=request.node_output.output_schema_version or 1,
            source_fingerprint=request.source_fingerprint,
            message=message,
            error_message=(
                message
                if self.status is WorkflowOutputProjectionStatus.FAILED
                else None
            ),
        )


class TerminalPathProjectionJobRepository:
    def __init__(self, *, claimable: bool) -> None:
        self.claimable = claimable
        self.created: list[WorkflowOutputProjectionJobRecord] = []
        self.claimed: list[str] = []
        self.succeeded: list[str] = []
        self.skipped: list[tuple[str, str | None]] = []
        self.failed: list[tuple[str, str]] = []

    async def create_job(
        self,
        record: WorkflowOutputProjectionJobRecord,
    ) -> WorkflowOutputProjectionJobRecord:
        self.created.append(record)
        return record

    async def claim_job(
        self,
        projection_job_id: str,
        *,
        statuses: tuple[WorkflowOutputProjectionJobStatus | str, ...] | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None:
        del statuses
        self.claimed.append(projection_job_id)
        if not self.claimable:
            return None
        return replace(
            self.created[-1],
            status=WorkflowOutputProjectionJobStatus.RUNNING,
            started_at=datetime.now(UTC),
        )

    async def mark_succeeded(
        self,
        projection_job_id: str,
        *,
        completed_at: datetime | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None:
        del completed_at
        self.succeeded.append(projection_job_id)
        return None

    async def mark_skipped(
        self,
        projection_job_id: str,
        *,
        reason: str | None = None,
        completed_at: datetime | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None:
        del completed_at
        self.skipped.append((projection_job_id, reason))
        return None

    async def mark_failed(
        self,
        projection_job_id: str,
        *,
        error: str,
        completed_at: datetime | None = None,
    ) -> WorkflowOutputProjectionJobRecord | None:
        del completed_at
        self.failed.append((projection_job_id, error))
        return None


class TerminalPathCompletedRunArchive:
    def __init__(self, bundle: CompletedRunBundle) -> None:
        self.bundle = bundle

    async def load_archived_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> CompletedRunBundle | None:
        del workflow_name, execution_id
        return self.bundle


@pytest.mark.asyncio
async def test_project_completed_run_treats_unclaimable_job_as_skip() -> None:
    service, projector, repository = _service(
        status=WorkflowOutputProjectionStatus.SUCCEEDED,
        claimable=False,
    )

    summary = await service.project_completed_run(_request())

    assert summary.skipped_jobs == 1
    assert projector.calls == 0
    assert len(repository.created) == 1
    assert repository.claimed == [repository.created[0].projection_job_id]
    assert repository.succeeded == []
    assert repository.skipped == []
    assert repository.failed == []
    assert "not claimable" in str(summary.outcomes[0].message)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "terminal_event"),
    (
        (
            WorkflowOutputProjectionStatus.SKIPPED,
            "workflow_output_projection.projector_skipped",
        ),
        (
            WorkflowOutputProjectionStatus.FAILED,
            "workflow_output_projection.projector_failed",
        ),
    ),
)
async def test_project_completed_run_persists_and_emits_projector_terminal_outcome(
    status: WorkflowOutputProjectionStatus,
    terminal_event: str,
) -> None:
    observability = ObservabilityManager()
    sink = InMemoryTelemetrySink()
    observability.add_sink(sink)
    service, projector, repository = _service(
        status=status,
        claimable=True,
        observability_manager=observability,
    )

    summary = await service.project_completed_run(_request())

    job_id = repository.created[0].projection_job_id
    assert projector.calls == 1
    assert repository.claimed == [job_id]
    assert repository.succeeded == []
    assert [event.event_type for event in sink.events].count(terminal_event) == 1

    if status is WorkflowOutputProjectionStatus.SKIPPED:
        assert summary.skipped_jobs == 1
        assert repository.skipped == [
            (job_id, "Projector returned a terminal outcome.")
        ]
        assert repository.failed == []
    else:
        assert summary.failed_jobs == 1
        assert repository.failed == [(job_id, "Projector returned a terminal outcome.")]
        assert repository.skipped == []


def _service(
    *,
    status: WorkflowOutputProjectionStatus,
    claimable: bool,
    observability_manager: ObservabilityManager | None = None,
) -> tuple[
    WorkflowOutputProjectionService,
    TerminalOutcomeProjector,
    TerminalPathProjectionJobRepository,
]:
    projector = TerminalOutcomeProjector(status=status)
    registration = WorkflowOutputProjectorRegistration(
        projector_name=projector.projector_name,
        output_contract="polaris.market.technical_analysis",
        output_schema_version=1,
        projector=projector,
        supported_node_names=("technical_agent",),
    )
    node_output = _node_output(
        authority_metadata=registration.expected_authority_contract.to_metadata()
    )
    repository = TerminalPathProjectionJobRepository(claimable=claimable)
    archive = TerminalPathCompletedRunArchive(
        CompletedRunBundle(run=_run(), node_outputs=(node_output,))
    )
    service = WorkflowOutputProjectionService(
        completed_run_archive=cast(CompletedRunArchive, archive),
        projection_job_repository=cast(
            WorkflowOutputProjectionJobRepository,
            repository,
        ),
        registry=WorkflowOutputProjectionRegistry((registration,)),
        observability_manager=observability_manager,
    )
    return service, projector, repository


def _request() -> WorkflowOutputProjectionRequest:
    return WorkflowOutputProjectionRequest(
        workflow_name="morning_report",
        execution_id="exec-1",
    )


def _run() -> CompletedRunRecord:
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
        metadata={},
        errors_json=(),
        started_at=datetime(2026, 8, 29, 1, tzinfo=UTC),
        completed_at=datetime(2026, 8, 29, 1, 5, tzinfo=UTC),
        duration_seconds=300.0,
        node_count=1,
        completed_node_count=1,
        failed_node_count=0,
        execution_mode=CompletedRunExecutionMode.NORMAL,
    )


def _node_output(*, authority_metadata: dict[str, object]) -> CompletedNodeOutputRecord:
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
        outputs={"technical_score": 0.8},
        metadata={"risk_authority": authority_metadata},
        errors_json=(),
        started_at=datetime(2026, 8, 29, 1, tzinfo=UTC),
        completed_at=datetime(2026, 8, 29, 1, 1, tzinfo=UTC),
        duration_seconds=60.0,
    )
