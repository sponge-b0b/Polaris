from __future__ import annotations

import logging
from time import perf_counter
from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from application.observability.ai_observability_contracts import AiObservation
from application.observability.ai_observability_contracts import (
    AiObservabilityExportResult,
)
from application.observability.ai_observability_contracts import (
    AiObservabilityExportStatus,
)
from application.observability.langfuse_projection import AiObservabilitySink
from application.observability.langfuse_projection import LangfuseExportClient
from application.observability.langfuse_projection import LangfuseObservationMapper
from application.observability.langfuse_projection import LangfusePayload
from core.storage.persistence.ai_observability import AiObservabilityExportJobClaim
from core.storage.persistence.ai_observability import AiObservabilityExportJobRecord
from core.storage.persistence.ai_observability import AiObservabilityExportJobRepository
from core.storage.persistence.ai_observability import JsonObject
from core.storage.persistence.ai_observability import JsonValue
from core.storage.persistence.ai_observability import new_ai_observability_export_job_id
from core.telemetry.events.telemetry_event import TelemetryEvent
from core.telemetry.events.telemetry_event import TelemetryEventLevel
from core.telemetry.events.telemetry_exception_details import TelemetryExceptionDetails
from core.telemetry.observability.observability_manager import ObservabilityManager

logger = logging.getLogger(__name__)

DEFAULT_LANGFUSE_EXPORT_RETRY_SECONDS = 60.0


@dataclass(frozen=True, slots=True)
class AiObservabilityExportBatchResult:
    """Summary of a durable AI-observability export worker batch."""

    processed_count: int
    exported_count: int
    failed_count: int

    def __post_init__(self) -> None:
        for field_name in ("processed_count", "exported_count", "failed_count"):
            value = getattr(self, field_name)
            if value < 0:
                raise ValueError(f"{field_name} cannot be negative.")
        if self.exported_count + self.failed_count > self.processed_count:
            raise ValueError(
                "exported and failed counts cannot exceed processed count."
            )


@dataclass(frozen=True, slots=True)
class AiObservabilityRetentionResult:
    """Result of enforcing terminal AI-observability export-job retention."""

    retention_days: int
    cutoff: datetime
    deleted_count: int

    def __post_init__(self) -> None:
        if self.retention_days <= 0:
            raise ValueError("retention_days must be positive.")
        if self.deleted_count < 0:
            raise ValueError("deleted_count cannot be negative.")


@dataclass(frozen=True, slots=True)
class AiObservabilityRetentionService:
    """Enforce PostgreSQL retention for terminal Langfuse export jobs."""

    repository: AiObservabilityExportJobRepository
    retention_days: int
    observability_manager: ObservabilityManager | None = None

    def __post_init__(self) -> None:
        if self.retention_days <= 0:
            raise ValueError("retention_days must be positive.")

    async def enforce_terminal_job_retention(
        self,
        *,
        now: datetime | None = None,
    ) -> AiObservabilityRetentionResult:
        effective_now = now or datetime.now(UTC)
        cutoff = effective_now - timedelta(days=self.retention_days)
        deleted_count = await self.repository.delete_terminal_jobs_before(cutoff=cutoff)
        _record_ai_observability_metric(
            self.observability_manager,
            "application.ai_observability.retention.deleted_jobs",
            attributes={
                "component_name": "LangfuseAiObservabilityRetention",
                "operation": "delete_terminal_export_jobs",
                "outcome": "completed",
                "retention_days": self.retention_days,
            },
        )
        return AiObservabilityRetentionResult(
            retention_days=self.retention_days,
            cutoff=cutoff,
            deleted_count=deleted_count,
        )


@dataclass(frozen=True, slots=True)
class AiObservabilityExportQueueService:
    """Create durable export jobs from typed Polaris AI observations."""

    repository: AiObservabilityExportJobRepository
    mapper: LangfuseObservationMapper
    max_attempts: int = 3
    observability_manager: ObservabilityManager | None = None

    def __post_init__(self) -> None:
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be positive.")

    async def enqueue(
        self,
        observation: AiObservation,
    ) -> AiObservabilityExportJobRecord:
        payload = self.mapper.to_payload(observation)
        correlation_ids = observation.correlation_ids
        record = AiObservabilityExportJobRecord(
            export_job_id=new_ai_observability_export_job_id(),
            idempotency_key=observation.idempotency_key(),
            observation_type=observation.observation_type.value,
            observation_name=observation.name,
            observation_family=observation.family.value,
            observation_status=observation.status.value,
            payload=_json_object_from_payload(payload),
            max_attempts=self.max_attempts,
            trace_id=correlation_ids.trace_id,
            span_id=correlation_ids.span_id,
            workflow_name=correlation_ids.workflow_name,
            execution_id=correlation_ids.execution_id,
            runtime_id=correlation_ids.runtime_id,
            node_name=correlation_ids.node_name,
            observation_id=correlation_ids.observation_id,
            parent_observation_id=correlation_ids.parent_observation_id,
            dataset_id=correlation_ids.dataset_id,
            case_id=correlation_ids.case_id,
            run_id=correlation_ids.run_id,
            available_at=observation.created_at,
            created_at=observation.created_at,
        )
        job = await self.repository.create_job(record)
        _record_ai_observability_metric(
            self.observability_manager,
            "application.ai_observability.observations.queued",
            attributes={
                "component_name": "LangfuseAiObservabilityExportQueue",
                "operation": "enqueue_observation",
                "outcome": "queued",
                "observation_type": job.observation_type,
                "observation_family": job.observation_family,
            },
        )
        return job


@dataclass(frozen=True, slots=True)
class DurableLangfuseAiObservabilitySink(AiObservabilitySink):
    """Sink that durably queues Langfuse AI-observability exports."""

    queue_service: AiObservabilityExportQueueService

    async def export(self, observation: AiObservation) -> AiObservabilityExportResult:
        job = await self.queue_service.enqueue(observation)
        return AiObservabilityExportResult(
            status=AiObservabilityExportStatus.PENDING,
            idempotency_key=job.idempotency_key,
            observation_id=job.observation_id,
            dataset_id=job.dataset_id,
            case_id=job.case_id,
            run_id=job.run_id,
        )


@dataclass(frozen=True, slots=True)
class AiObservabilityExportWorker:
    """Drain durable Langfuse AI-observability export jobs."""

    repository: AiObservabilityExportJobRepository
    client: LangfuseExportClient
    default_retry_delay_seconds: float = DEFAULT_LANGFUSE_EXPORT_RETRY_SECONDS
    observability_manager: ObservabilityManager | None = None

    def __post_init__(self) -> None:
        if self.default_retry_delay_seconds < 0.0:
            raise ValueError("default_retry_delay_seconds cannot be negative.")

    async def process_next(
        self,
        claim: AiObservabilityExportJobClaim | None = None,
    ) -> AiObservabilityExportResult | None:
        job = await self.repository.claim_next_job(claim)
        if job is None:
            return None

        start = perf_counter()
        await _emit_ai_observability_export_event(
            self.observability_manager,
            job,
            event_type="application.ai_observability.export.started",
            level=TelemetryEventLevel.INFO,
            success=None,
            outcome="started",
        )
        _record_ai_observability_metric(
            self.observability_manager,
            "application.ai_observability.export.attempts",
            attributes=_export_metric_attributes(job, outcome="started"),
        )

        try:
            response = await self.client.export(dict(job.payload))
        except Exception as exc:
            retry_after_seconds = self.default_retry_delay_seconds
            retry_at = datetime.now(UTC) + timedelta(seconds=retry_after_seconds)
            logger.exception(
                "Durable Langfuse AI-observability export failed.",
                extra={
                    "export_job_id": job.export_job_id,
                    "idempotency_key": job.idempotency_key,
                    "observation_type": job.observation_type,
                    "observation_name": job.observation_name,
                    "attempt_count": job.attempt_count,
                    "max_attempts": job.max_attempts,
                },
            )
            failed_job = await self.repository.mark_failed(
                job.export_job_id,
                error=str(exc),
                retry_after_seconds=retry_after_seconds,
                available_at=retry_at,
            )
            duration_seconds = perf_counter() - start
            retry_outcome = (
                "retry_scheduled"
                if job.attempt_count < job.max_attempts
                else "retry_exhausted"
            )
            _record_ai_observability_metric(
                self.observability_manager,
                "application.ai_observability.export.failures",
                attributes=_export_metric_attributes(job, outcome=retry_outcome),
            )
            _record_ai_observability_metric(
                self.observability_manager,
                "application.ai_observability.export.retries",
                attributes=_export_metric_attributes(job, outcome=retry_outcome),
            )
            await _emit_ai_observability_export_event(
                self.observability_manager,
                failed_job or job,
                event_type="application.ai_observability.export.failed",
                level=TelemetryEventLevel.ERROR,
                success=False,
                outcome=retry_outcome,
                duration_seconds=duration_seconds,
                error=exc,
            )
            return AiObservabilityExportResult.failed(
                idempotency_key=job.idempotency_key,
                error_message=str(exc),
                retry_after_seconds=retry_after_seconds,
            )

        external_trace_id = _optional_string_from_response(
            response,
            "external_trace_id",
            "trace_id",
        )
        external_observation_id = _optional_string_from_response(
            response,
            "external_observation_id",
            "observation_id",
        )
        exported_job = await self.repository.mark_exported(
            job.export_job_id,
            external_trace_id=external_trace_id,
            external_observation_id=external_observation_id,
        )
        duration_seconds = perf_counter() - start
        exported_record = exported_job or job
        _record_ai_observability_metric(
            self.observability_manager,
            "application.ai_observability.exports",
            attributes=_export_metric_attributes(exported_record, outcome="exported"),
        )
        _observe_ai_observability_metric(
            self.observability_manager,
            "application.ai_observability.export.duration_seconds",
            duration_seconds,
            attributes=_export_metric_attributes(exported_record, outcome="exported"),
        )
        delivery_latency = _delivery_latency_seconds(exported_record)
        if delivery_latency is not None:
            _observe_ai_observability_metric(
                self.observability_manager,
                "application.ai_observability.export.delivery_latency_seconds",
                delivery_latency,
                attributes=_export_metric_attributes(
                    exported_record, outcome="exported"
                ),
            )
        await _emit_ai_observability_export_event(
            self.observability_manager,
            exported_record,
            event_type="application.ai_observability.export.completed",
            level=TelemetryEventLevel.INFO,
            success=True,
            outcome="exported",
            duration_seconds=duration_seconds,
        )
        return AiObservabilityExportResult.exported(
            idempotency_key=job.idempotency_key,
            observation_id=job.observation_id,
            external_trace_id=external_trace_id,
            external_observation_id=external_observation_id,
            dataset_id=(exported_job.dataset_id if exported_job else job.dataset_id),
            case_id=(exported_job.case_id if exported_job else job.case_id),
            run_id=(exported_job.run_id if exported_job else job.run_id),
        )

    async def process_batch(
        self,
        *,
        limit: int,
        claim: AiObservabilityExportJobClaim | None = None,
    ) -> AiObservabilityExportBatchResult:
        if limit <= 0:
            raise ValueError("limit must be positive.")

        exported_count = 0
        failed_count = 0
        processed_count = 0
        for _ in range(limit):
            result = await self.process_next(claim)
            if result is None:
                break
            processed_count += 1
            if result.status is AiObservabilityExportStatus.EXPORTED:
                exported_count += 1
            elif result.status is AiObservabilityExportStatus.FAILED:
                failed_count += 1
        return AiObservabilityExportBatchResult(
            processed_count=processed_count,
            exported_count=exported_count,
            failed_count=failed_count,
        )


def _json_object_from_payload(payload: LangfusePayload) -> JsonObject:
    return {key: _json_value(value) for key, value in payload.items()}


def _json_value(value: object) -> JsonValue:
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    if isinstance(value, Mapping):
        return {
            str(key): _json_value(nested_value) for key, nested_value in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return tuple(_json_value(item) for item in value)
    return str(value)


def _optional_string_from_response(
    response: object,
    primary_key: str,
    fallback_key: str,
) -> str | None:
    response_map = response if isinstance(response, dict) else {}
    return _optional_string(
        response_map.get(primary_key) or response_map.get(fallback_key)
    )


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value or None
    return str(value)


def _record_ai_observability_metric(
    observability_manager: ObservabilityManager | None,
    name: str,
    *,
    attributes: Mapping[str, object] | None = None,
) -> None:
    if observability_manager is None:
        return
    try:
        observability_manager.increment(
            name,
            attributes=dict(attributes or {}),
        )
    except Exception:
        logger.exception(
            "Failed to record AI-observability metric.",
            extra={"metric_name": name},
        )


def _observe_ai_observability_metric(
    observability_manager: ObservabilityManager | None,
    name: str,
    value: float,
    *,
    attributes: Mapping[str, object] | None = None,
) -> None:
    if observability_manager is None:
        return
    try:
        observability_manager.observe(
            name,
            value,
            attributes=dict(attributes or {}),
        )
    except Exception:
        logger.exception(
            "Failed to observe AI-observability metric.",
            extra={"metric_name": name},
        )


def _export_metric_attributes(
    job: AiObservabilityExportJobRecord,
    *,
    outcome: str,
) -> dict[str, object]:
    return {
        "component_name": "LangfuseAiObservabilityExportWorker",
        "operation": "export_observation",
        "outcome": outcome,
        "observation_type": job.observation_type,
        "observation_family": job.observation_family,
        "observation_status": job.observation_status,
        "workflow_name": job.workflow_name or "unknown",
    }


async def _emit_ai_observability_export_event(
    observability_manager: ObservabilityManager | None,
    job: AiObservabilityExportJobRecord,
    *,
    event_type: str,
    level: TelemetryEventLevel,
    success: bool | None,
    outcome: str,
    duration_seconds: float | None = None,
    error: BaseException | None = None,
) -> None:
    if observability_manager is None:
        return
    event = TelemetryEvent(
        event_type=event_type,
        source="application.observability.langfuse_export",
        level=level,
        workflow_id=None,
        execution_id=job.execution_id,
        runtime_id=job.runtime_id,
        node_name=job.node_name,
        correlation_id=job.observation_id or job.idempotency_key,
        trace_id=job.trace_id,
        span_id=job.span_id,
        duration_seconds=duration_seconds,
        success=success,
        error_count=1 if error is not None else 0,
        exception_details=(
            TelemetryExceptionDetails.from_exception(error)
            if error is not None
            else None
        ),
        attributes={
            **_export_metric_attributes(job, outcome=outcome),
            "export_job_id": job.export_job_id,
            "idempotency_key": job.idempotency_key,
        },
        payload={
            "external_trace_id": job.external_trace_id,
            "external_observation_id": job.external_observation_id,
            "dataset_id": job.dataset_id,
            "case_id": job.case_id,
            "run_id": job.run_id,
            "attempt_count": job.attempt_count,
            "max_attempts": job.max_attempts,
            "workflow_name": job.workflow_name,
        },
    )
    try:
        await observability_manager.emit(event)
    except Exception:
        logger.exception(
            "Failed to emit AI-observability export telemetry event.",
            extra={"event_type": event_type, "export_job_id": job.export_job_id},
        )


def _delivery_latency_seconds(
    job: AiObservabilityExportJobRecord,
) -> float | None:
    if job.created_at is None or job.exported_at is None:
        return None
    return max(0.0, (job.exported_at - job.created_at).total_seconds())
