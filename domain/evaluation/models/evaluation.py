from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import datetime
from enum import StrEnum
from typing import Any


class EvaluationTargetType(StrEnum):
    """Canonical Polaris targets that can be evaluated by an LLM judge."""

    RAG_ANSWER = "rag_answer"
    RAG_RETRIEVAL = "rag_retrieval"
    RAG_GENERATION = "rag_generation"
    MORNING_REPORT = "morning_report"
    STRATEGY_SYNTHESIS = "strategy_synthesis"
    RECOMMENDATION_EXPLANATION = "recommendation_explanation"
    MCP_TOOL_RESPONSE = "mcp_tool_response"
    AGENT_TASK = "agent_task"


class EvaluationStatus(StrEnum):
    """Lifecycle state for evaluation cases, runs, and metric results."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERRORED = "errored"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class EvaluationDatasetReference:
    """Versioned reference to a canonical evaluation dataset."""

    dataset_id: str
    name: str
    version: str
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_non_empty(self.dataset_id, "dataset_id")
        _require_non_empty(self.name, "name")
        _require_non_empty(self.version, "version")
        object.__setattr__(self, "tags", _clean_tuple(self.tags))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the reference at a persistence, telemetry, or transport boundary."""

        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "version": self.version,
            "tags": list(self.tags),
        }


@dataclass(frozen=True, slots=True)
class EvaluationThreshold:
    """Metric threshold policy for one evaluation metric."""

    metric_name: str
    minimum_score: float
    version: str = "v1"

    def __post_init__(self) -> None:
        _require_non_empty(self.metric_name, "metric_name")
        _require_non_empty(self.version, "version")
        _validate_score(self.minimum_score, "minimum_score")

    def passes(self, score: float) -> bool:
        _validate_score(score, "score")
        return score >= self.minimum_score

    def to_dict(self) -> dict[str, Any]:
        """Serialize the threshold at a persistence, telemetry, or transport boundary."""

        return {
            "metric_name": self.metric_name,
            "minimum_score": self.minimum_score,
            "version": self.version,
        }


@dataclass(frozen=True, slots=True)
class EvaluationScore:
    """Normalized score returned by an evaluator for one metric."""

    metric_name: str
    score: float
    threshold: EvaluationThreshold | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.metric_name, "metric_name")
        _validate_score(self.score, "score")
        _validate_optional_non_empty(self.reason, "reason")
        if (
            self.threshold is not None
            and self.threshold.metric_name != self.metric_name
        ):
            raise ValueError("threshold metric_name must match score metric_name.")

    @property
    def passed(self) -> bool | None:
        if self.threshold is None:
            return None
        return self.threshold.passes(self.score)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the score at a persistence, telemetry, or transport boundary."""

        return {
            "metric_name": self.metric_name,
            "score": self.score,
            "threshold": None if self.threshold is None else self.threshold.to_dict(),
            "passed": self.passed,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    """Canonical, attributable input/output pair prepared for LLM evaluation."""

    case_id: str
    target_type: EvaluationTargetType
    input_text: str
    actual_output: str
    dataset: EvaluationDatasetReference | None = None
    expected_output: str | None = None
    rubric: str | None = None
    source_record_ids: tuple[str, ...] = ()
    workflow_execution_id: str | None = None
    langfuse_trace_id: str | None = None
    langfuse_observation_id: str | None = None
    retrieval_context: tuple[str, ...] = ()
    citation_context_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        _require_non_empty(self.case_id, "case_id")
        _require_non_empty(self.input_text, "input_text")
        _require_non_empty(self.actual_output, "actual_output")
        _validate_optional_non_empty(self.expected_output, "expected_output")
        _validate_optional_non_empty(self.rubric, "rubric")
        if self.expected_output is None and self.rubric is None:
            raise ValueError("expected_output or rubric is required.")
        for field_name in (
            "workflow_execution_id",
            "langfuse_trace_id",
            "langfuse_observation_id",
        ):
            _validate_optional_non_empty(getattr(self, field_name), field_name)
        object.__setattr__(
            self,
            "source_record_ids",
            _clean_tuple(self.source_record_ids),
        )
        object.__setattr__(
            self,
            "retrieval_context",
            _clean_tuple(self.retrieval_context),
        )
        object.__setattr__(
            self,
            "citation_context_ids",
            _clean_tuple(self.citation_context_ids),
        )
        object.__setattr__(self, "tags", _clean_tuple(self.tags))
        object.__setattr__(self, "created_at", _ensure_aware_datetime(self.created_at))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the case at a persistence, telemetry, or transport boundary."""

        return {
            "case_id": self.case_id,
            "target_type": self.target_type.value,
            "input_text": self.input_text,
            "actual_output": self.actual_output,
            "dataset": None if self.dataset is None else self.dataset.to_dict(),
            "expected_output": self.expected_output,
            "rubric": self.rubric,
            "source_record_ids": list(self.source_record_ids),
            "workflow_execution_id": self.workflow_execution_id,
            "langfuse_trace_id": self.langfuse_trace_id,
            "langfuse_observation_id": self.langfuse_observation_id,
            "retrieval_context": list(self.retrieval_context),
            "citation_context_ids": list(self.citation_context_ids),
            "tags": list(self.tags),
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class EvaluationRun:
    """Execution record for evaluating one dataset or set of cases."""

    run_id: str
    target_type: EvaluationTargetType
    status: EvaluationStatus
    evaluator_provider: str
    evaluator_model: str
    dataset: EvaluationDatasetReference | None = None
    case_ids: tuple[str, ...] = ()
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.run_id, "run_id")
        _require_non_empty(self.evaluator_provider, "evaluator_provider")
        _require_non_empty(self.evaluator_model, "evaluator_model")
        object.__setattr__(self, "case_ids", _clean_tuple(self.case_ids))
        object.__setattr__(self, "started_at", _ensure_aware_datetime(self.started_at))
        if self.completed_at is not None:
            object.__setattr__(
                self,
                "completed_at",
                _ensure_aware_datetime(self.completed_at),
            )
        _validate_optional_non_empty(self.error_message, "error_message")

    def to_dict(self) -> dict[str, Any]:
        """Serialize the run at a persistence, telemetry, or transport boundary."""

        return {
            "run_id": self.run_id,
            "target_type": self.target_type.value,
            "status": self.status.value,
            "evaluator_provider": self.evaluator_provider,
            "evaluator_model": self.evaluator_model,
            "dataset": None if self.dataset is None else self.dataset.to_dict(),
            "case_ids": list(self.case_ids),
            "started_at": self.started_at.isoformat(),
            "completed_at": None
            if self.completed_at is None
            else self.completed_at.isoformat(),
            "error_message": self.error_message,
        }


@dataclass(frozen=True, slots=True)
class EvaluationMetricResult:
    """Canonical result for one evaluator metric applied to one case."""

    run_id: str
    case_id: str
    score: EvaluationScore
    status: EvaluationStatus
    evaluator_provider: str
    evaluator_model: str
    duration_ms: float | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        _require_non_empty(self.run_id, "run_id")
        _require_non_empty(self.case_id, "case_id")
        _require_non_empty(self.evaluator_provider, "evaluator_provider")
        _require_non_empty(self.evaluator_model, "evaluator_model")
        if self.duration_ms is not None and self.duration_ms < 0.0:
            raise ValueError("duration_ms cannot be negative.")
        _validate_optional_non_empty(self.error_message, "error_message")
        object.__setattr__(self, "created_at", _ensure_aware_datetime(self.created_at))

    @property
    def passed(self) -> bool | None:
        return self.score.passed

    def to_dict(self) -> dict[str, Any]:
        """Serialize the metric result at a persistence, telemetry, or transport boundary."""

        return {
            "run_id": self.run_id,
            "case_id": self.case_id,
            "metric_name": self.score.metric_name,
            "score": self.score.score,
            "threshold": None
            if self.score.threshold is None
            else self.score.threshold.to_dict(),
            "passed": self.passed,
            "reason": self.score.reason,
            "status": self.status.value,
            "evaluator_provider": self.evaluator_provider,
            "evaluator_model": self.evaluator_model,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
        }


def _clean_tuple(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(value.strip() for value in values if value.strip())


def _require_non_empty(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")


def _validate_optional_non_empty(value: str | None, field_name: str) -> None:
    if value is not None:
        _require_non_empty(value, field_name)


def _validate_score(value: float, field_name: str) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0.")


def _ensure_aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
