from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

import pytest

from application.projections.workflow_outputs import (
    CompletedRunProjectionNotFoundError,
    WorkflowOutputProjectionOutcome,
    WorkflowOutputProjectionRegistry,
    WorkflowOutputProjectionRequest,
    WorkflowOutputProjectionService,
    WorkflowOutputProjectionStatus,
    WorkflowOutputProjectionTelemetry,
    WorkflowOutputProjectorRegistration,
    WorkflowOutputProjectorRequest,
    calculate_workflow_output_source_fingerprint,
)
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunArchive,
    CompletedRunBundle,
    CompletedRunExecutionMode,
    CompletedRunRecord,
    JsonObject,
)
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.projections import (
    MissingProjectionRunRecord,
    ProjectionJobClaim,
    WorkflowOutputProjectionJobRecord,
    WorkflowOutputProjectionJobStatus,
)
from core.telemetry.observability import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from domain.authority import (
    AiOutputContentType,
    AuthorityEffect,
    CanonicalOwner,
    IntendedSink,
    RiskAuthorityClassificationInput,
    RiskTier,
    SourceOfTruthCategory,
    classify_risk_authority,
)


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
async def test_project_completed_run_creates_claims_invokes_projector_and_marks_success() -> (  # noqa: E501
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
    assert projector.last_request.authority_contract is not None
    assert projector.last_request.authority_contract.risk_tier is RiskTier.ENHANCED
    assert (
        projector.last_request.authority_contract.intended_sink
        is IntendedSink.DURABLE_DOMAIN_RECORD
    )
    assert len(repository.created) == 1
    assert len(repository.claimed) == 1
    assert repository.succeeded == [repository.created[0].projection_job_id]


@pytest.mark.asyncio
async def test_project_completed_run_emits_projection_telemetry() -> None:
    projector = StubProjector()
    repository = FakeProjectionJobRepository()
    observability = ObservabilityManager()
    sink = InMemoryTelemetrySink()
    observability.add_sink(sink)
    service = _service(
        projector=projector,
        repository=repository,
        observability_manager=observability,
    )

    summary = await service.project_completed_run(
        WorkflowOutputProjectionRequest(
            workflow_name="morning_report",
            execution_id="exec-1",
        )
    )

    event_types = [event.event_type for event in sink.events]
    assert summary.success is True
    assert "workflow_output_projection.completed_run_started" in event_types
    assert "workflow_output_projection.projector_started" in event_types
    assert "workflow_output_projection.projector_completed" in event_types
    assert "workflow_output_projection.completed_run_finished" in event_types
    projector_completed = next(
        event
        for event in sink.events
        if event.event_type == "workflow_output_projection.projector_completed"
    )
    assert projector_completed.duration_seconds is not None
    assert projector_completed.attributes["projector_name"] == "technical_projector"
    assert projector_completed.attributes["parent_span_id"] is not None
    metric_names = {point.name for point in observability.metrics_store.points()}
    assert "workflow_output_projection.records.persisted" in metric_names
    assert "workflow_output_projection.jobs.retry_count" in metric_names


@pytest.mark.asyncio
async def test_project_completed_run_emits_unsupported_contract_telemetry() -> None:
    repository = FakeProjectionJobRepository()
    observability = ObservabilityManager()
    sink = InMemoryTelemetrySink()
    observability.add_sink(sink)
    service = WorkflowOutputProjectionService(
        completed_run_archive=FakeCompletedRunArchive(
            _bundle(
                node_outputs=(_node(output_contract="polaris.unsupported.contract"),)
            )
        ),
        projection_job_repository=repository,
        registry=WorkflowOutputProjectionRegistry(()),
        observability_manager=observability,
    )

    summary = await service.project_completed_run(
        WorkflowOutputProjectionRequest(
            workflow_name="morning_report",
            execution_id="exec-1",
        )
    )

    event_types = [event.event_type for event in sink.events]
    metric_names = {point.name for point in observability.metrics_store.points()}
    assert summary.skipped_jobs == 1
    assert "workflow_output_projection.projector_skipped" in event_types
    assert "workflow_output_projection.unsupported_contracts.total" in metric_names


def test_projection_telemetry_records_stale_job_recovery_metric() -> None:
    observability = ObservabilityManager()
    telemetry = WorkflowOutputProjectionTelemetry(observability)

    telemetry.record_stale_jobs_recovered(
        recovered_count=3,
        attributes={"workflow_name": "morning_report"},
    )

    points = observability.metrics_store.points()
    assert points[-1].name == "workflow_output_projection.jobs.stale_recovered"
    assert points[-1].value == 3.0


@pytest.mark.asyncio
async def test_project_completed_run_uses_run_execution_mode_as_canonical_skip_source() -> (  # noqa: E501
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
async def test_project_completed_run_skips_report_and_backtest_boundary_outputs_without_jobs() -> (  # noqa: E501
    None
):
    report_projector = StubProjector(projector_name="report_projector")
    backtest_projector = StubProjector(projector_name="backtest_projector")
    repository = FakeProjectionJobRepository()
    service = WorkflowOutputProjectionService(
        completed_run_archive=FakeCompletedRunArchive(
            _bundle(
                node_outputs=(
                    _node(
                        node_name="morning_report_renderer",
                        output_contract="polaris.report.morning_report_document",
                        outputs={"markdown": "# Morning Report"},
                    ),
                    _node(
                        node_name="backtest_runner",
                        output_contract="polaris.backtest.result_bundle",
                        outputs={"backtest_run_id": "backtest-1"},
                    ),
                )
            )
        ),
        projection_job_repository=repository,
        registry=WorkflowOutputProjectionRegistry(
            (
                WorkflowOutputProjectorRegistration(
                    projector_name="report_projector",
                    output_contract="polaris.report.morning_report_document",
                    output_schema_version=1,
                    projector=report_projector,
                    supported_node_names=("morning_report_renderer",),
                ),
                WorkflowOutputProjectorRegistration(
                    projector_name="backtest_projector",
                    output_contract="polaris.backtest.result_bundle",
                    output_schema_version=1,
                    projector=backtest_projector,
                    supported_node_names=("backtest_runner",),
                ),
            )
        ),
    )

    summary = await service.project_completed_run(
        WorkflowOutputProjectionRequest(
            workflow_name="morning_report",
            execution_id="exec-1",
        )
    )

    assert summary.skipped_jobs == 2
    assert summary.succeeded_jobs == 0
    assert repository.created == []
    assert report_projector.calls == 0
    assert backtest_projector.calls == 0
    assert "MorningReportPersistenceService" in str(summary.outcomes[0].message)
    assert "BacktestPersistenceService" in str(summary.outcomes[1].message)


@pytest.mark.asyncio
async def test_project_completed_run_records_projector_failure_and_continues() -> None:
    projector = StubProjector(should_raise=True)
    repository = FakeProjectionJobRepository()
    observability = ObservabilityManager()
    sink = InMemoryTelemetrySink()
    observability.add_sink(sink)
    service = _service(
        projector=projector,
        repository=repository,
        observability_manager=observability,
    )

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
    event_types = [event.event_type for event in sink.events]
    metric_names = {point.name for point in observability.metrics_store.points()}
    assert "workflow_output_projection.projector_failed" in event_types
    assert "workflow_output_projection.completed_run_failed" in event_types
    assert "workflow_output_projection.runs.failed" in metric_names


@pytest.mark.asyncio
async def test_project_completed_run_isolates_projector_failure_and_projects_remaining_nodes() -> (  # noqa: E501
    None
):
    failing_projector = StubProjector(should_raise=True)
    news_projector = StubProjector(
        projector_name="news_projector",
        records_written=3,
    )
    repository = FakeProjectionJobRepository()
    service = WorkflowOutputProjectionService(
        completed_run_archive=FakeCompletedRunArchive(
            _bundle(
                node_outputs=(
                    _node(
                        node_name="technical_agent",
                        output_contract="polaris.market.technical_analysis",
                    ),
                    _node(
                        node_name="news_agent",
                        output_contract="polaris.news.analysis",
                        outputs={"headline_count": 4},
                    ),
                )
            )
        ),
        projection_job_repository=repository,
        registry=WorkflowOutputProjectionRegistry(
            (
                WorkflowOutputProjectorRegistration(
                    projector_name=failing_projector.projector_name,
                    output_contract="polaris.market.technical_analysis",
                    output_schema_version=1,
                    projector=failing_projector,
                    supported_node_names=("technical_agent",),
                ),
                WorkflowOutputProjectorRegistration(
                    projector_name=news_projector.projector_name,
                    output_contract="polaris.news.analysis",
                    output_schema_version=1,
                    projector=news_projector,
                    supported_node_names=("news_agent",),
                ),
            )
        ),
    )

    summary = await service.project_completed_run(
        WorkflowOutputProjectionRequest(
            workflow_name="morning_report",
            execution_id="exec-1",
        )
    )

    assert summary.success is False
    assert summary.total_jobs == 2
    assert summary.failed_jobs == 1
    assert summary.succeeded_jobs == 1
    assert summary.records_written == 3
    assert failing_projector.calls == 1
    assert news_projector.calls == 1
    assert len(repository.created) == 2
    assert len(repository.failed) == 1
    assert len(repository.succeeded) == 1
    assert summary.outcomes[0].status is WorkflowOutputProjectionStatus.FAILED
    assert summary.outcomes[1].status is WorkflowOutputProjectionStatus.SUCCEEDED


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
    observability = ObservabilityManager()
    sink = InMemoryTelemetrySink()
    observability.add_sink(sink)
    service = WorkflowOutputProjectionService(
        completed_run_archive=archive,
        projection_job_repository=repository,
        registry=_registry(StubProjector()),
        observability_manager=observability,
    )

    with pytest.raises(CompletedRunProjectionNotFoundError):
        await service.project_completed_run(
            WorkflowOutputProjectionRequest(
                workflow_name="morning_report",
                execution_id="missing",
            )
        )

    event_types = [event.event_type for event in sink.events]
    metric_names = {point.name for point in observability.metrics_store.points()}
    assert "workflow_output_projection.completed_run_not_found" in event_types
    assert "workflow_output_projection.archives.missing" in metric_names


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
    observability_manager: ObservabilityManager | None = None,
) -> WorkflowOutputProjectionService:
    return WorkflowOutputProjectionService(
        completed_run_archive=FakeCompletedRunArchive(bundle or _bundle()),
        projection_job_repository=repository,
        registry=_registry(projector),
        observability_manager=observability_manager,
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
    node_name: str = "technical_agent",
    output_contract: str | None = "polaris.market.technical_analysis",
    output_schema_version: int | None = 1,
    outputs: JsonObject | None = None,
    metadata: JsonObject | None = None,
) -> CompletedNodeOutputRecord:
    resolved_metadata = (
        {"risk_authority": _authority_metadata()} if metadata is None else metadata
    )
    return CompletedNodeOutputRecord(
        node_output_id="node-output-1",
        run_id="run-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        node_name=node_name,
        node_type="runtime_node",
        output_contract=output_contract,
        output_schema_version=output_schema_version,
        status="succeeded",
        success=True,
        outputs=outputs or {"technical_score": 0.8},
        metadata=resolved_metadata,
        errors_json=(),
        started_at=datetime(2026, 7, 9, 12, tzinfo=UTC),
        completed_at=datetime(2026, 7, 9, 12, 1, tzinfo=UTC),
        duration_seconds=60.0,
    )


def _authority_metadata() -> JsonObject:
    return cast(
        JsonObject,
        classify_risk_authority(
            RiskAuthorityClassificationInput(
                content_type=AiOutputContentType.DURABLE_RECORD,
                authority_effect=AuthorityEffect.CANONICAL_RECORD,
                canonical_owner=CanonicalOwner.WORKFLOW_OUTPUT_CURATION,
                source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
                intended_sink=IntendedSink.DURABLE_DOMAIN_RECORD,
                durable_authority=True,
            )
        ).to_metadata(),
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
