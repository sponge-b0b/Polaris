from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Iterable
from typing import Mapping
from typing import Sequence
from typing import TypeAlias
from uuid import uuid4

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | Mapping[str, "JsonValue"] | Sequence["JsonValue"]
JsonObject: TypeAlias = Mapping[str, JsonValue]


class AiObservabilityExportJobStatus(str, Enum):
    """Durable AI-observability export job lifecycle status."""

    PENDING = "pending"
    RUNNING = "running"
    EXPORTED = "exported"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class AiObservabilityExportQueueStatus:
    """Operational summary of the durable AI-observability export queue."""

    pending_count: int = 0
    running_count: int = 0
    exported_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    retryable_failed_count: int = 0
    exhausted_failed_count: int = 0
    oldest_retryable_available_at: datetime | None = None
    latest_failure_at: datetime | None = None
    latest_exported_at: datetime | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "pending_count",
            "running_count",
            "exported_count",
            "failed_count",
            "skipped_count",
            "retryable_failed_count",
            "exhausted_failed_count",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} cannot be negative.")
        if self.retryable_failed_count > self.failed_count:
            raise ValueError("retryable_failed_count cannot exceed failed_count.")
        if self.exhausted_failed_count > self.failed_count:
            raise ValueError("exhausted_failed_count cannot exceed failed_count.")

    @property
    def total_count(self) -> int:
        return (
            self.pending_count
            + self.running_count
            + self.exported_count
            + self.failed_count
            + self.skipped_count
        )

    @property
    def backlog_count(self) -> int:
        return self.pending_count + self.running_count + self.retryable_failed_count

    @property
    def has_retry_pressure(self) -> bool:
        return self.retryable_failed_count > 0 or self.exhausted_failed_count > 0

    def status_counts(self) -> dict[str, int]:
        return {
            AiObservabilityExportJobStatus.PENDING.value: self.pending_count,
            AiObservabilityExportJobStatus.RUNNING.value: self.running_count,
            AiObservabilityExportJobStatus.EXPORTED.value: self.exported_count,
            AiObservabilityExportJobStatus.FAILED.value: self.failed_count,
            AiObservabilityExportJobStatus.SKIPPED.value: self.skipped_count,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "pending_count": self.pending_count,
            "running_count": self.running_count,
            "exported_count": self.exported_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "retryable_failed_count": self.retryable_failed_count,
            "exhausted_failed_count": self.exhausted_failed_count,
            "backlog_count": self.backlog_count,
            "total_count": self.total_count,
            "oldest_retryable_available_at": (
                self.oldest_retryable_available_at.isoformat()
                if self.oldest_retryable_available_at is not None
                else None
            ),
            "latest_failure_at": (
                self.latest_failure_at.isoformat()
                if self.latest_failure_at is not None
                else None
            ),
            "latest_exported_at": (
                self.latest_exported_at.isoformat()
                if self.latest_exported_at is not None
                else None
            ),
        }


@dataclass(frozen=True, slots=True)
class AiObservabilityExportJobRecord:
    """Typed persistence record for one AI-observability export job."""

    export_job_id: str
    idempotency_key: str
    observation_type: str
    observation_name: str
    observation_family: str
    observation_status: str
    payload: JsonObject
    status: AiObservabilityExportJobStatus | str = (
        AiObservabilityExportJobStatus.PENDING
    )
    attempt_count: int = 0
    max_attempts: int = 3
    trace_id: str | None = None
    span_id: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    runtime_id: str | None = None
    node_name: str | None = None
    observation_id: str | None = None
    parent_observation_id: str | None = None
    dataset_id: str | None = None
    case_id: str | None = None
    run_id: str | None = None
    external_trace_id: str | None = None
    external_observation_id: str | None = None
    last_error: str | None = None
    retry_after_seconds: float | None = None
    available_at: datetime | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    exported_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "export_job_id",
            "idempotency_key",
            "observation_type",
            "observation_name",
            "observation_family",
            "observation_status",
        ):
            object.__setattr__(
                self,
                field_name,
                _require_non_empty(getattr(self, field_name), field_name),
            )
        object.__setattr__(self, "status", _coerce_status(self.status))
        object.__setattr__(self, "payload", _freeze_json_object(self.payload))
        for field_name in (
            "trace_id",
            "span_id",
            "workflow_name",
            "execution_id",
            "runtime_id",
            "node_name",
            "observation_id",
            "parent_observation_id",
            "dataset_id",
            "case_id",
            "run_id",
            "external_trace_id",
            "external_observation_id",
            "last_error",
        ):
            object.__setattr__(
                self,
                field_name,
                _clean_optional(getattr(self, field_name), field_name),
            )
        if self.attempt_count < 0:
            raise ValueError("attempt_count cannot be negative.")
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be positive.")
        if self.retry_after_seconds is not None and self.retry_after_seconds < 0.0:
            raise ValueError("retry_after_seconds cannot be negative.")


@dataclass(frozen=True, slots=True)
class AiObservabilityExportJobClaim:
    """Request for atomically claiming a retryable AI-observability export job."""

    statuses: tuple[AiObservabilityExportJobStatus | str, ...] = (
        AiObservabilityExportJobStatus.PENDING,
        AiObservabilityExportJobStatus.FAILED,
    )
    workflow_name: str | None = None
    execution_id: str | None = None
    observation_type: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "statuses", _coerce_statuses(self.statuses))
        for field_name in ("workflow_name", "execution_id", "observation_type"):
            object.__setattr__(
                self,
                field_name,
                _clean_optional(getattr(self, field_name), field_name),
            )
        if not self.statuses:
            raise ValueError("statuses cannot be empty.")


def new_ai_observability_export_job_id() -> str:
    return f"aiobs-export-{uuid4().hex}"


def _coerce_status(
    value: AiObservabilityExportJobStatus | str,
) -> AiObservabilityExportJobStatus:
    if isinstance(value, AiObservabilityExportJobStatus):
        return value
    try:
        return AiObservabilityExportJobStatus(value)
    except ValueError as exc:
        raise ValueError(
            f"Unsupported AI observability export job status: {value!r}."
        ) from exc


def _coerce_statuses(
    statuses: Iterable[AiObservabilityExportJobStatus | str],
) -> tuple[AiObservabilityExportJobStatus, ...]:
    return tuple(_coerce_status(status) for status in statuses)


def _freeze_json_object(value: JsonObject) -> JsonObject:
    return dict(value)


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
