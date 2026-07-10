from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Iterable


class WorkflowOutputProjectionJobStatus(str, Enum):
    """Durable workflow-output projection job lifecycle status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class WorkflowOutputProjectionJobRecord:
    """Typed persistence record for one workflow-output projection job."""

    projection_job_id: str
    run_id: str
    workflow_name: str
    execution_id: str
    node_name: str
    projector_name: str
    output_contract: str
    output_schema_version: int
    source_fingerprint: str
    status: WorkflowOutputProjectionJobStatus | str
    attempt_count: int = 0
    last_error: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "projection_job_id",
            _require_non_empty(self.projection_job_id, "projection_job_id"),
        )
        object.__setattr__(
            self,
            "run_id",
            _require_non_empty(self.run_id, "run_id"),
        )
        object.__setattr__(
            self,
            "workflow_name",
            _require_non_empty(self.workflow_name, "workflow_name"),
        )
        object.__setattr__(
            self,
            "execution_id",
            _require_non_empty(self.execution_id, "execution_id"),
        )
        object.__setattr__(
            self,
            "node_name",
            _require_non_empty(self.node_name, "node_name"),
        )
        object.__setattr__(
            self,
            "projector_name",
            _require_non_empty(self.projector_name, "projector_name"),
        )
        object.__setattr__(
            self,
            "output_contract",
            _require_non_empty(self.output_contract, "output_contract"),
        )
        object.__setattr__(
            self,
            "source_fingerprint",
            _require_non_empty(self.source_fingerprint, "source_fingerprint"),
        )
        object.__setattr__(
            self,
            "status",
            _coerce_status(self.status),
        )
        object.__setattr__(
            self,
            "last_error",
            _clean_optional(self.last_error, "last_error"),
        )
        if self.output_schema_version <= 0:
            raise ValueError("output_schema_version must be positive.")
        if self.attempt_count < 0:
            raise ValueError("attempt_count cannot be negative.")


@dataclass(frozen=True, slots=True)
class ProjectionJobClaim:
    """Request for atomically claiming a pending or failed projection job."""

    statuses: tuple[WorkflowOutputProjectionJobStatus | str, ...] = (
        WorkflowOutputProjectionJobStatus.PENDING,
        WorkflowOutputProjectionJobStatus.FAILED,
    )
    workflow_name: str | None = None
    execution_id: str | None = None
    projector_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "statuses", _coerce_statuses(self.statuses))
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
        if not self.statuses:
            raise ValueError("statuses cannot be empty.")


@dataclass(frozen=True, slots=True)
class MissingProjectionRunRecord:
    """Completed run with no durable projection jobs."""

    run_id: str
    workflow_name: str
    execution_id: str
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _require_non_empty(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "workflow_name",
            _require_non_empty(self.workflow_name, "workflow_name"),
        )
        object.__setattr__(
            self,
            "execution_id",
            _require_non_empty(self.execution_id, "execution_id"),
        )


def _coerce_status(
    value: WorkflowOutputProjectionJobStatus | str,
) -> WorkflowOutputProjectionJobStatus:
    if isinstance(value, WorkflowOutputProjectionJobStatus):
        return value
    try:
        return WorkflowOutputProjectionJobStatus(value)
    except ValueError as exc:
        raise ValueError(f"Unsupported projection job status: {value!r}.") from exc


def _coerce_statuses(
    statuses: Iterable[WorkflowOutputProjectionJobStatus | str],
) -> tuple[WorkflowOutputProjectionJobStatus, ...]:
    return tuple(_coerce_status(status) for status in statuses)


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
