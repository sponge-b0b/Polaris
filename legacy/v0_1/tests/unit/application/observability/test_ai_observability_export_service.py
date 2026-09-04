from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from application.observability import (
    AiObservabilityCapturePolicy,
    AiObservabilityCorrelationIds,
    AiObservabilityExportQueueService,
    AiObservabilityExportStatus,
    AiObservabilityExportWorker,
    AiObservabilityRetentionService,
    AiObservation,
    AiObservationStatus,
    AiObservationType,
    DurableLangfuseAiObservabilitySink,
    LangfuseObservationMapper,
)
from core.storage.persistence.ai_observability import (
    AiObservabilityExportJobClaim,
    AiObservabilityExportJobRecord,
    AiObservabilityExportJobStatus,
    AiObservabilityExportQueueStatus,
)
from core.telemetry.observability.observability_manager import ObservabilityManager


class InMemoryAiObservabilityExportJobRepository:
    def __init__(self) -> None:
        self.jobs: dict[str, AiObservabilityExportJobRecord] = {}
        self.failed_available_at: datetime | None = None

    async def create_job(
        self,
        record: AiObservabilityExportJobRecord,
    ) -> AiObservabilityExportJobRecord:
        existing = next(
            (
                job
                for job in self.jobs.values()
                if job.idempotency_key == record.idempotency_key
            ),
            None,
        )
        if existing is not None:
            updated = replace(
                existing, payload=record.payload, max_attempts=record.max_attempts
            )
            self.jobs[updated.export_job_id] = updated
            return updated
        self.jobs[record.export_job_id] = record
        return record

    async def get_job(
        self,
        export_job_id: str,
    ) -> AiObservabilityExportJobRecord | None:
        return self.jobs.get(export_job_id)

    async def claim_next_job(
        self,
        claim: AiObservabilityExportJobClaim | None = None,
    ) -> AiObservabilityExportJobRecord | None:
        claim = claim or AiObservabilityExportJobClaim()
        for job in self.jobs.values():
            if job.status not in claim.statuses:
                continue
            if job.attempt_count >= job.max_attempts:
                continue
            if (
                claim.workflow_name is not None
                and job.workflow_name != claim.workflow_name
            ):
                continue
            if (
                claim.execution_id is not None
                and job.execution_id != claim.execution_id
            ):
                continue
            if (
                claim.observation_type is not None
                and job.observation_type != claim.observation_type
            ):
                continue
            claimed = replace(
                job,
                status=AiObservabilityExportJobStatus.RUNNING,
                attempt_count=job.attempt_count + 1,
                started_at=datetime.now(UTC),
                last_error=None,
            )
            self.jobs[claimed.export_job_id] = claimed
            return claimed
        return None

    async def mark_exported(
        self,
        export_job_id: str,
        *,
        external_trace_id: str | None = None,
        external_observation_id: str | None = None,
        exported_at: datetime | None = None,
    ) -> AiObservabilityExportJobRecord | None:
        job = self.jobs.get(export_job_id)
        if job is None:
            return None
        exported = replace(
            job,
            status=AiObservabilityExportJobStatus.EXPORTED,
            external_trace_id=external_trace_id,
            external_observation_id=external_observation_id,
            exported_at=exported_at or datetime.now(UTC),
            last_error=None,
            retry_after_seconds=None,
        )
        self.jobs[exported.export_job_id] = exported
        return exported

    async def mark_failed(
        self,
        export_job_id: str,
        *,
        error: str,
        retry_after_seconds: float | None = None,
        available_at: datetime | None = None,
    ) -> AiObservabilityExportJobRecord | None:
        job = self.jobs.get(export_job_id)
        if job is None:
            return None
        self.failed_available_at = available_at
        failed = replace(
            job,
            status=AiObservabilityExportJobStatus.FAILED,
            last_error=error,
            retry_after_seconds=retry_after_seconds,
            available_at=available_at,
        )
        self.jobs[failed.export_job_id] = failed
        return failed

    async def mark_skipped(
        self,
        export_job_id: str,
        *,
        reason: str | None = None,
    ) -> AiObservabilityExportJobRecord | None:
        job = self.jobs.get(export_job_id)
        if job is None:
            return None
        skipped = replace(
            job,
            status=AiObservabilityExportJobStatus.SKIPPED,
            last_error=reason,
        )
        self.jobs[skipped.export_job_id] = skipped
        return skipped

    async def list_jobs(
        self,
        *,
        statuses: Sequence[AiObservabilityExportJobStatus | str] | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        observation_type: str | None = None,
        limit: int | None = None,
    ) -> Sequence[AiObservabilityExportJobRecord]:
        jobs = list(self.jobs.values())
        if statuses is not None:
            jobs = [job for job in jobs if job.status in statuses]
        if workflow_name is not None:
            jobs = [job for job in jobs if job.workflow_name == workflow_name]
        if execution_id is not None:
            jobs = [job for job in jobs if job.execution_id == execution_id]
        if observation_type is not None:
            jobs = [job for job in jobs if job.observation_type == observation_type]
        if limit is not None:
            jobs = jobs[:limit]
        return tuple(jobs)

    async def get_queue_status(self) -> AiObservabilityExportQueueStatus:
        jobs = tuple(self.jobs.values())
        failed_jobs = tuple(
            job for job in jobs if job.status is AiObservabilityExportJobStatus.FAILED
        )
        return AiObservabilityExportQueueStatus(
            pending_count=sum(
                1
                for job in jobs
                if job.status is AiObservabilityExportJobStatus.PENDING
            ),
            running_count=sum(
                1
                for job in jobs
                if job.status is AiObservabilityExportJobStatus.RUNNING
            ),
            exported_count=sum(
                1
                for job in jobs
                if job.status is AiObservabilityExportJobStatus.EXPORTED
            ),
            failed_count=len(failed_jobs),
            skipped_count=sum(
                1
                for job in jobs
                if job.status is AiObservabilityExportJobStatus.SKIPPED
            ),
            retryable_failed_count=sum(
                1 for job in failed_jobs if job.attempt_count < job.max_attempts
            ),
            exhausted_failed_count=sum(
                1 for job in failed_jobs if job.attempt_count >= job.max_attempts
            ),
            oldest_retryable_available_at=min(
                (
                    job.available_at
                    for job in jobs
                    if job.status is AiObservabilityExportJobStatus.PENDING
                    or (
                        job.status is AiObservabilityExportJobStatus.FAILED
                        and job.attempt_count < job.max_attempts
                    )
                ),
                default=None,
            ),
            latest_failure_at=max(
                (job.updated_at for job in failed_jobs if job.updated_at is not None),
                default=None,
            ),
            latest_exported_at=max(
                (
                    job.exported_at
                    for job in jobs
                    if job.status is AiObservabilityExportJobStatus.EXPORTED
                    and job.exported_at is not None
                ),
                default=None,
            ),
        )

    async def delete_terminal_jobs_before(
        self,
        *,
        cutoff: datetime,
        statuses: Sequence[AiObservabilityExportJobStatus | str] | None = None,
    ) -> int:
        terminal_statuses = tuple(
            AiObservabilityExportJobStatus(status)
            if isinstance(status, str)
            else status
            for status in (
                statuses
                or (
                    AiObservabilityExportJobStatus.EXPORTED,
                    AiObservabilityExportJobStatus.SKIPPED,
                )
            )
        )
        deleted_count = 0
        for job in tuple(self.jobs.values()):
            if job.status not in terminal_statuses:
                continue
            if job.updated_at is None or job.updated_at >= cutoff:
                continue
            del self.jobs[job.export_job_id]
            deleted_count += 1
        return deleted_count

    async def recover_stale_running_jobs(
        self,
        *,
        started_before: datetime,
        error: str,
    ) -> int:
        recovered = 0
        for job in tuple(self.jobs.values()):
            if job.status is not AiObservabilityExportJobStatus.RUNNING:
                continue
            if job.started_at is None or job.started_at >= started_before:
                continue
            self.jobs[job.export_job_id] = replace(
                job,
                status=AiObservabilityExportJobStatus.FAILED,
                last_error=error,
            )
            recovered += 1
        return recovered


class SuccessfulLangfuseClient:
    async def export(self, payload: dict[str, object]) -> object:
        return {
            "external_trace_id": "lf-trace-1",
            "external_observation_id": payload["idempotency_key"],
        }


class FailingLangfuseClient:
    async def export(self, payload: dict[str, object]) -> object:
        raise RuntimeError("langfuse unavailable")


def _observation() -> AiObservation:
    return AiObservation(
        observation_type=AiObservationType.RAG_QUERY,
        name="rag query",
        status=AiObservationStatus.SUCCESS,
        correlation_ids=AiObservabilityCorrelationIds(
            trace_id="trace-1",
            span_id="span-1",
            workflow_name="morning_report",
            execution_id="exec-1",
            runtime_id="runtime-1",
            node_name="rag_node",
            observation_id="obs-1",
            dataset_id="dataset-1",
            case_id="case-1",
            run_id="run-1",
        ),
        metadata={"route": "hybrid"},
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _mapper() -> LangfuseObservationMapper:
    return LangfuseObservationMapper(
        capture_policy=AiObservabilityCapturePolicy(),
        environment="test",
    )


@pytest.mark.asyncio
async def test_queue_service_persists_langfuse_payload_and_correlations() -> None:
    repository = InMemoryAiObservabilityExportJobRepository()
    service = AiObservabilityExportQueueService(repository, _mapper())

    job = await service.enqueue(_observation())

    assert job.status is AiObservabilityExportJobStatus.PENDING
    assert job.workflow_name == "morning_report"
    assert job.execution_id == "exec-1"
    assert job.trace_id == "trace-1"
    assert job.observation_id == "obs-1"
    assert job.dataset_id == "dataset-1"
    assert job.payload["idempotency_key"] == job.idempotency_key
    assert job.payload["prompt_captured"] is False
    assert len(repository.jobs) == 1


@pytest.mark.asyncio
async def test_durable_sink_returns_pending_result_after_queueing() -> None:
    repository = InMemoryAiObservabilityExportJobRepository()
    sink = DurableLangfuseAiObservabilitySink(
        AiObservabilityExportQueueService(repository, _mapper())
    )

    result = await sink.export(_observation())

    assert result.status is AiObservabilityExportStatus.PENDING
    assert result.observation_id == "obs-1"
    assert result.dataset_id == "dataset-1"
    assert len(repository.jobs) == 1


@pytest.mark.asyncio
async def test_export_worker_claims_and_marks_job_exported() -> None:
    repository = InMemoryAiObservabilityExportJobRepository()
    queue_service = AiObservabilityExportQueueService(repository, _mapper())
    job = await queue_service.enqueue(_observation())
    worker = AiObservabilityExportWorker(repository, SuccessfulLangfuseClient())

    result = await worker.process_next()
    stored = await repository.get_job(job.export_job_id)

    assert result is not None
    assert result.status is AiObservabilityExportStatus.EXPORTED
    assert result.external_trace_id == "lf-trace-1"
    assert stored is not None
    assert stored.status is AiObservabilityExportJobStatus.EXPORTED
    assert stored.attempt_count == 1
    assert stored.external_trace_id == "lf-trace-1"


@pytest.mark.asyncio
async def test_export_worker_marks_failed_job_retryable() -> None:
    repository = InMemoryAiObservabilityExportJobRepository()
    queue_service = AiObservabilityExportQueueService(repository, _mapper())
    job = await queue_service.enqueue(_observation())
    worker = AiObservabilityExportWorker(
        repository,
        FailingLangfuseClient(),
        default_retry_delay_seconds=5.0,
    )

    result = await worker.process_next()
    stored = await repository.get_job(job.export_job_id)

    assert result is not None
    assert result.status is AiObservabilityExportStatus.FAILED
    assert result.retry_after_seconds == 5.0
    assert stored is not None
    assert stored.status is AiObservabilityExportJobStatus.FAILED
    assert stored.attempt_count == 1
    assert stored.last_error == "langfuse unavailable"
    assert repository.failed_available_at is not None


@pytest.mark.asyncio
async def test_export_worker_processes_batch_until_queue_empty() -> None:
    repository = InMemoryAiObservabilityExportJobRepository()
    queue_service = AiObservabilityExportQueueService(repository, _mapper())
    await queue_service.enqueue(_observation())
    worker = AiObservabilityExportWorker(repository, SuccessfulLangfuseClient())

    result = await worker.process_batch(limit=3)

    assert result.processed_count == 1
    assert result.exported_count == 1
    assert result.failed_count == 0


def _metric_names(observability_manager: ObservabilityManager) -> set[str]:
    return {point.name for point in observability_manager.metrics_store.points()}


@pytest.mark.asyncio
async def test_queue_service_records_observation_queued_metric() -> None:
    repository = InMemoryAiObservabilityExportJobRepository()
    observability_manager = ObservabilityManager()
    service = AiObservabilityExportQueueService(
        repository,
        _mapper(),
        observability_manager=observability_manager,
    )

    await service.enqueue(_observation())

    assert "application.ai_observability.observations.queued" in _metric_names(
        observability_manager
    )


@pytest.mark.asyncio
async def test_export_worker_records_success_metrics() -> None:
    repository = InMemoryAiObservabilityExportJobRepository()
    observability_manager = ObservabilityManager()
    queue_service = AiObservabilityExportQueueService(repository, _mapper())
    await queue_service.enqueue(_observation())
    worker = AiObservabilityExportWorker(
        repository,
        SuccessfulLangfuseClient(),
        observability_manager=observability_manager,
    )

    await worker.process_next()

    metric_names = _metric_names(observability_manager)
    assert "application.ai_observability.export.attempts" in metric_names
    assert "application.ai_observability.exports" in metric_names
    assert "application.ai_observability.export.duration_seconds" in metric_names
    assert "telemetry.events.total" in metric_names


@pytest.mark.asyncio
async def test_export_worker_records_failure_metrics() -> None:
    repository = InMemoryAiObservabilityExportJobRepository()
    observability_manager = ObservabilityManager()
    queue_service = AiObservabilityExportQueueService(repository, _mapper())
    await queue_service.enqueue(_observation())
    worker = AiObservabilityExportWorker(
        repository,
        FailingLangfuseClient(),
        default_retry_delay_seconds=5.0,
        observability_manager=observability_manager,
    )

    await worker.process_next()

    metric_names = _metric_names(observability_manager)
    assert "application.ai_observability.export.failures" in metric_names
    assert "application.ai_observability.export.retries" in metric_names
    assert "telemetry.events.errors" in metric_names


@pytest.mark.asyncio
async def test_retention_service_deletes_old_terminal_jobs_and_records_metric() -> None:
    repository = InMemoryAiObservabilityExportJobRepository()
    observability_manager = ObservabilityManager()
    now = datetime(2026, 1, 10, tzinfo=UTC)
    cutoff = datetime(2026, 1, 3, tzinfo=UTC)
    old_exported = AiObservabilityExportJobRecord(
        export_job_id="old-exported",
        idempotency_key="old-exported-key",
        observation_type="rag.query",
        observation_name="old exported",
        observation_family="rag",
        observation_status="success",
        payload={"idempotency_key": "old-exported-key"},
        status=AiObservabilityExportJobStatus.EXPORTED,
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    old_skipped = AiObservabilityExportJobRecord(
        export_job_id="old-skipped",
        idempotency_key="old-skipped-key",
        observation_type="rag.query",
        observation_name="old skipped",
        observation_family="rag",
        observation_status="success",
        payload={"idempotency_key": "old-skipped-key"},
        status=AiObservabilityExportJobStatus.SKIPPED,
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    recent_exported = AiObservabilityExportJobRecord(
        export_job_id="recent-exported",
        idempotency_key="recent-exported-key",
        observation_type="rag.query",
        observation_name="recent exported",
        observation_family="rag",
        observation_status="success",
        payload={"idempotency_key": "recent-exported-key"},
        status=AiObservabilityExportJobStatus.EXPORTED,
        updated_at=datetime(2026, 1, 5, tzinfo=UTC),
    )
    old_failed = AiObservabilityExportJobRecord(
        export_job_id="old-failed",
        idempotency_key="old-failed-key",
        observation_type="rag.query",
        observation_name="old failed",
        observation_family="rag",
        observation_status="success",
        payload={"idempotency_key": "old-failed-key"},
        status=AiObservabilityExportJobStatus.FAILED,
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    repository.jobs = {
        job.export_job_id: job
        for job in (old_exported, old_skipped, recent_exported, old_failed)
    }
    service = AiObservabilityRetentionService(
        repository=repository,
        retention_days=7,
        observability_manager=observability_manager,
    )

    result = await service.enforce_terminal_job_retention(now=now)

    assert result.retention_days == 7
    assert result.cutoff == cutoff
    assert result.deleted_count == 2
    assert set(repository.jobs) == {"recent-exported", "old-failed"}
    assert "application.ai_observability.retention.deleted_jobs" in _metric_names(
        observability_manager
    )
