from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import datetime
from enum import Enum
from typing import Iterable

from core.storage.persistence.completed_run_archive import CompletedNodeOutputRecord
from core.storage.persistence.projections import MissingProjectionRunRecord
from core.storage.persistence.completed_run_archive import CompletedRunRecord
from core.storage.persistence.completed_run_archive import CompletedRunBundle
from core.storage.persistence.lineage import PersistenceLineage


class WorkflowOutputProjectionStatus(str, Enum):
    """Lifecycle status for a workflow-output projection job or outcome."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class WorkflowOutputProjectionRequest:
    """Request to project archived workflow node outputs into curated records."""

    workflow_name: str
    execution_id: str
    run_id: str | None = None
    requested_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    force_reproject: bool = False
    dry_run: bool = False

    def __post_init__(self) -> None:
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
            "run_id",
            _clean_optional(self.run_id, "run_id"),
        )


@dataclass(frozen=True, slots=True)
class WorkflowOutputProjectorRequest:
    """Typed per-node request passed to one workflow-output projector."""

    run: CompletedRunRecord
    node_output: CompletedNodeOutputRecord
    source_fingerprint: str
    bundle: CompletedRunBundle | None = None
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    requested_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    force_reproject: bool = False
    dry_run: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_fingerprint",
            _require_non_empty(self.source_fingerprint, "source_fingerprint"),
        )


@dataclass(frozen=True, slots=True)
class WorkflowOutputProjectionOutcome:
    """Typed result for one node-output projector invocation."""

    status: WorkflowOutputProjectionStatus | str
    projector_name: str
    node_name: str
    output_contract: str
    output_schema_version: int
    source_fingerprint: str
    records_written: int = 0
    job_id: str | None = None
    message: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "status",
            _coerce_status(self.status),
        )
        object.__setattr__(
            self,
            "projector_name",
            _require_non_empty(self.projector_name, "projector_name"),
        )
        object.__setattr__(
            self,
            "node_name",
            _require_non_empty(self.node_name, "node_name"),
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
            "job_id",
            _clean_optional(self.job_id, "job_id"),
        )
        object.__setattr__(
            self,
            "message",
            _clean_optional(self.message, "message"),
        )
        object.__setattr__(
            self,
            "error_type",
            _clean_optional(self.error_type, "error_type"),
        )
        object.__setattr__(
            self,
            "error_message",
            _clean_optional(self.error_message, "error_message"),
        )
        if self.output_schema_version <= 0:
            raise ValueError("output_schema_version must be positive.")
        if self.records_written < 0:
            raise ValueError("records_written cannot be negative.")

    @property
    def succeeded(self) -> bool:
        return self.status is WorkflowOutputProjectionStatus.SUCCEEDED

    @property
    def failed(self) -> bool:
        return self.status is WorkflowOutputProjectionStatus.FAILED

    @property
    def skipped(self) -> bool:
        return self.status is WorkflowOutputProjectionStatus.SKIPPED


@dataclass(frozen=True, slots=True)
class CompletedRunProjectionSummary:
    """Aggregate projection result for one completed workflow run."""

    workflow_name: str
    execution_id: str
    run_id: str | None = None
    requested_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    outcomes: tuple[WorkflowOutputProjectionOutcome, ...] = ()

    def __post_init__(self) -> None:
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
            "run_id",
            _clean_optional(self.run_id, "run_id"),
        )
        object.__setattr__(
            self,
            "outcomes",
            tuple(self.outcomes),
        )

    @property
    def total_jobs(self) -> int:
        return len(self.outcomes)

    @property
    def succeeded_jobs(self) -> int:
        return sum(outcome.succeeded for outcome in self.outcomes)

    @property
    def failed_jobs(self) -> int:
        return sum(outcome.failed for outcome in self.outcomes)

    @property
    def skipped_jobs(self) -> int:
        return sum(outcome.skipped for outcome in self.outcomes)

    @property
    def records_written(self) -> int:
        return sum(outcome.records_written for outcome in self.outcomes)

    @property
    def success(self) -> bool:
        return self.failed_jobs == 0


@dataclass(frozen=True, slots=True)
class WorkflowOutputProjectionRetryRequest:
    """Request to retry retryable projection jobs."""

    workflow_name: str | None = None
    execution_id: str | None = None
    projector_name: str | None = None
    statuses: tuple[WorkflowOutputProjectionStatus | str, ...] = (
        WorkflowOutputProjectionStatus.FAILED,
    )
    limit: int | None = None
    requested_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    dry_run: bool = False
    stale_running_started_before: datetime | None = None

    def __post_init__(self) -> None:
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
        object.__setattr__(
            self,
            "statuses",
            _coerce_statuses(self.statuses),
        )
        if not self.statuses:
            raise ValueError("statuses cannot be empty.")
        if self.limit is not None and self.limit <= 0:
            raise ValueError("limit must be positive when provided.")


@dataclass(frozen=True, slots=True)
class WorkflowOutputProjectionRetryResult:
    """Summary of a retry operation over projection jobs."""

    requested: WorkflowOutputProjectionRetryRequest
    matched_jobs: int
    retried_jobs: int
    recovered_stale_running_jobs: int = 0
    summaries: tuple[CompletedRunProjectionSummary, ...] = ()

    def __post_init__(self) -> None:
        if self.matched_jobs < 0:
            raise ValueError("matched_jobs cannot be negative.")
        if self.retried_jobs < 0:
            raise ValueError("retried_jobs cannot be negative.")
        if self.retried_jobs > self.matched_jobs:
            raise ValueError("retried_jobs cannot exceed matched_jobs.")
        if self.recovered_stale_running_jobs < 0:
            raise ValueError("recovered_stale_running_jobs cannot be negative.")
        object.__setattr__(self, "summaries", tuple(self.summaries))


@dataclass(frozen=True, slots=True)
class WorkflowOutputProjectionReconciliationRequest:
    """Request to find archived runs missing projection jobs or outcomes."""

    workflow_name: str | None = None
    execution_id: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int | None = None
    requested_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    enqueue_missing_jobs: bool = False
    dry_run: bool = True

    def __post_init__(self) -> None:
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
        if self.limit is not None and self.limit <= 0:
            raise ValueError("limit must be positive when provided.")
        if (
            self.since is not None
            and self.until is not None
            and self.since > self.until
        ):
            raise ValueError("since cannot be later than until.")


@dataclass(frozen=True, slots=True)
class WorkflowOutputProjectionReconciliationResult:
    """Summary of projection reconciliation over completed runs."""

    requested: WorkflowOutputProjectionReconciliationRequest
    scanned_runs: int
    missing_projection_runs: int
    enqueued_jobs: int = 0
    missing_runs: tuple[MissingProjectionRunRecord, ...] = ()
    summaries: tuple[CompletedRunProjectionSummary, ...] = ()

    def __post_init__(self) -> None:
        if self.scanned_runs < 0:
            raise ValueError("scanned_runs cannot be negative.")
        if self.missing_projection_runs < 0:
            raise ValueError("missing_projection_runs cannot be negative.")
        if self.enqueued_jobs < 0:
            raise ValueError("enqueued_jobs cannot be negative.")
        if self.missing_projection_runs > self.scanned_runs:
            raise ValueError("missing_projection_runs cannot exceed scanned_runs.")
        object.__setattr__(self, "missing_runs", tuple(self.missing_runs))
        object.__setattr__(self, "summaries", tuple(self.summaries))


def _coerce_status(
    value: WorkflowOutputProjectionStatus | str,
) -> WorkflowOutputProjectionStatus:
    if isinstance(value, WorkflowOutputProjectionStatus):
        return value
    try:
        return WorkflowOutputProjectionStatus(value)
    except ValueError as exc:
        raise ValueError(
            f"Unsupported workflow output projection status: {value!r}."
        ) from exc


def _coerce_statuses(
    statuses: Iterable[WorkflowOutputProjectionStatus | str],
) -> tuple[WorkflowOutputProjectionStatus, ...]:
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
