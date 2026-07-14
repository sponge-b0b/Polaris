from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Mapping
from typing import Sequence
from typing import TypeAlias
from uuid import uuid4

from domain.evaluation import EvaluationCase
from domain.evaluation import EvaluationDatasetReference
from domain.evaluation import EvaluationMetricResult
from domain.evaluation import EvaluationRun
from domain.evaluation import EvaluationStatus
from domain.evaluation import EvaluationTargetType

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | Mapping[str, "JsonValue"] | Sequence["JsonValue"]
JsonObject: TypeAlias = Mapping[str, JsonValue]
JsonArray: TypeAlias = Sequence[JsonValue]


class LangfuseProjectionStatus(StrEnum):
    """Durable projection lifecycle state for Langfuse evaluation exports."""

    PENDING = "pending"
    PROJECTED = "projected"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class EvaluationDatasetRecord:
    """Persistence-boundary record for a versioned evaluation dataset."""

    dataset_id: str
    name: str
    version: str
    target_type: EvaluationTargetType | str | None = None
    description: str | None = None
    tags: tuple[str, ...] = ()
    source_lineage: tuple[str, ...] = ()
    deterministic_fixture_uri: str | None = None
    threshold_profile: JsonObject | None = None
    active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "dataset_id", _require_non_empty(self.dataset_id, "dataset_id")
        )
        object.__setattr__(self, "name", _require_non_empty(self.name, "name"))
        object.__setattr__(self, "version", _require_non_empty(self.version, "version"))
        object.__setattr__(
            self, "target_type", _coerce_optional_target_type(self.target_type)
        )
        object.__setattr__(
            self, "description", _clean_optional(self.description, "description")
        )
        object.__setattr__(self, "tags", _clean_tuple(self.tags, "tag"))

    @classmethod
    def from_reference(
        cls,
        reference: EvaluationDatasetReference,
        *,
        target_type: EvaluationTargetType | str | None = None,
        description: str | None = None,
        source_lineage: tuple[str, ...] = (),
        deterministic_fixture_uri: str | None = None,
        threshold_profile: JsonObject | None = None,
    ) -> EvaluationDatasetRecord:
        return cls(
            dataset_id=reference.dataset_id,
            name=reference.name,
            version=reference.version,
            target_type=target_type,
            description=description,
            tags=reference.tags,
            source_lineage=source_lineage,
            deterministic_fixture_uri=deterministic_fixture_uri,
            threshold_profile=threshold_profile,
        )


@dataclass(frozen=True, slots=True)
class EvaluationCaseRecord:
    """Persistence-boundary record for one canonical evaluation case."""

    case_id: str
    target_type: EvaluationTargetType | str
    input_text: str
    actual_output: str
    dataset_id: str | None = None
    expected_output: str | None = None
    rubric: str | None = None
    source_record_ids: tuple[str, ...] = ()
    workflow_execution_id: str | None = None
    langfuse_trace_id: str | None = None
    langfuse_observation_id: str | None = None
    retrieval_context: tuple[str, ...] = ()
    citation_context_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _require_non_empty(self.case_id, "case_id"))
        object.__setattr__(self, "target_type", _coerce_target_type(self.target_type))
        object.__setattr__(
            self, "input_text", _require_non_empty(self.input_text, "input_text")
        )
        object.__setattr__(
            self,
            "actual_output",
            _require_non_empty(self.actual_output, "actual_output"),
        )
        object.__setattr__(
            self, "dataset_id", _clean_optional(self.dataset_id, "dataset_id")
        )
        object.__setattr__(
            self,
            "expected_output",
            _clean_optional(self.expected_output, "expected_output"),
        )
        object.__setattr__(self, "rubric", _clean_optional(self.rubric, "rubric"))
        if self.expected_output is None and self.rubric is None:
            raise ValueError("expected_output or rubric is required.")
        for field_name in (
            "workflow_execution_id",
            "langfuse_trace_id",
            "langfuse_observation_id",
        ):
            object.__setattr__(
                self, field_name, _clean_optional(getattr(self, field_name), field_name)
            )
        object.__setattr__(
            self,
            "source_record_ids",
            _clean_tuple(self.source_record_ids, "source_record_id"),
        )
        object.__setattr__(
            self,
            "retrieval_context",
            _clean_tuple(self.retrieval_context, "retrieval_context"),
        )
        object.__setattr__(
            self,
            "citation_context_ids",
            _clean_tuple(self.citation_context_ids, "citation_context_id"),
        )
        object.__setattr__(self, "tags", _clean_tuple(self.tags, "tag"))

    @classmethod
    def from_domain(cls, evaluation_case: EvaluationCase) -> EvaluationCaseRecord:
        return cls(
            case_id=evaluation_case.case_id,
            target_type=evaluation_case.target_type,
            input_text=evaluation_case.input_text,
            actual_output=evaluation_case.actual_output,
            dataset_id=None
            if evaluation_case.dataset is None
            else evaluation_case.dataset.dataset_id,
            expected_output=evaluation_case.expected_output,
            rubric=evaluation_case.rubric,
            source_record_ids=evaluation_case.source_record_ids,
            workflow_execution_id=evaluation_case.workflow_execution_id,
            langfuse_trace_id=evaluation_case.langfuse_trace_id,
            langfuse_observation_id=evaluation_case.langfuse_observation_id,
            retrieval_context=evaluation_case.retrieval_context,
            citation_context_ids=evaluation_case.citation_context_ids,
            tags=evaluation_case.tags,
            created_at=evaluation_case.created_at,
        )


@dataclass(frozen=True, slots=True)
class EvaluationRunRecord:
    """Persistence-boundary record for an evaluation execution."""

    run_id: str
    target_type: EvaluationTargetType | str
    status: EvaluationStatus | str
    evaluator_provider: str
    evaluator_model: str
    dataset_id: str | None = None
    case_ids: tuple[str, ...] = ()
    langfuse_projection_status: LangfuseProjectionStatus | str = (
        LangfuseProjectionStatus.PENDING
    )
    langfuse_export_job_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    error_details: JsonObject | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _require_non_empty(self.run_id, "run_id"))
        object.__setattr__(self, "target_type", _coerce_target_type(self.target_type))
        object.__setattr__(self, "status", _coerce_status(self.status))
        object.__setattr__(
            self,
            "evaluator_provider",
            _require_non_empty(self.evaluator_provider, "evaluator_provider"),
        )
        object.__setattr__(
            self,
            "evaluator_model",
            _require_non_empty(self.evaluator_model, "evaluator_model"),
        )
        object.__setattr__(
            self, "dataset_id", _clean_optional(self.dataset_id, "dataset_id")
        )
        object.__setattr__(self, "case_ids", _clean_tuple(self.case_ids, "case_id"))
        object.__setattr__(
            self,
            "langfuse_projection_status",
            _coerce_langfuse_status(self.langfuse_projection_status),
        )
        object.__setattr__(
            self,
            "langfuse_export_job_id",
            _clean_optional(self.langfuse_export_job_id, "langfuse_export_job_id"),
        )
        object.__setattr__(
            self, "error_message", _clean_optional(self.error_message, "error_message")
        )

    @classmethod
    def from_domain(
        cls,
        evaluation_run: EvaluationRun,
        *,
        langfuse_projection_status: LangfuseProjectionStatus
        | str = LangfuseProjectionStatus.PENDING,
        langfuse_export_job_id: str | None = None,
        error_details: JsonObject | None = None,
    ) -> EvaluationRunRecord:
        return cls(
            run_id=evaluation_run.run_id,
            target_type=evaluation_run.target_type,
            status=evaluation_run.status,
            evaluator_provider=evaluation_run.evaluator_provider,
            evaluator_model=evaluation_run.evaluator_model,
            dataset_id=None
            if evaluation_run.dataset is None
            else evaluation_run.dataset.dataset_id,
            case_ids=evaluation_run.case_ids,
            langfuse_projection_status=langfuse_projection_status,
            langfuse_export_job_id=langfuse_export_job_id,
            started_at=evaluation_run.started_at,
            completed_at=evaluation_run.completed_at,
            error_message=evaluation_run.error_message,
            error_details=error_details,
        )


@dataclass(frozen=True, slots=True)
class EvaluationMetricResultRecord:
    """Persistence-boundary record for one evaluator metric result."""

    metric_result_id: str
    run_id: str
    case_id: str
    metric_name: str
    score: float
    status: EvaluationStatus | str
    evaluator_provider: str
    evaluator_model: str
    threshold: float | None = None
    threshold_version: str | None = None
    passed: bool | None = None
    reason: str | None = None
    duration_ms: float | None = None
    error_message: str | None = None
    error_details: JsonObject | None = None
    langfuse_projection_status: LangfuseProjectionStatus | str = (
        LangfuseProjectionStatus.PENDING
    )
    langfuse_export_job_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "metric_result_id",
            _require_non_empty(self.metric_result_id, "metric_result_id"),
        )
        object.__setattr__(self, "run_id", _require_non_empty(self.run_id, "run_id"))
        object.__setattr__(self, "case_id", _require_non_empty(self.case_id, "case_id"))
        object.__setattr__(
            self, "metric_name", _require_non_empty(self.metric_name, "metric_name")
        )
        _validate_score(self.score, "score")
        if self.threshold is not None:
            _validate_score(self.threshold, "threshold")
        object.__setattr__(self, "status", _coerce_status(self.status))
        object.__setattr__(
            self,
            "evaluator_provider",
            _require_non_empty(self.evaluator_provider, "evaluator_provider"),
        )
        object.__setattr__(
            self,
            "evaluator_model",
            _require_non_empty(self.evaluator_model, "evaluator_model"),
        )
        object.__setattr__(
            self,
            "threshold_version",
            _clean_optional(self.threshold_version, "threshold_version"),
        )
        object.__setattr__(self, "reason", _clean_optional(self.reason, "reason"))
        if self.duration_ms is not None and self.duration_ms < 0.0:
            raise ValueError("duration_ms cannot be negative.")
        object.__setattr__(
            self, "error_message", _clean_optional(self.error_message, "error_message")
        )
        object.__setattr__(
            self,
            "langfuse_projection_status",
            _coerce_langfuse_status(self.langfuse_projection_status),
        )
        object.__setattr__(
            self,
            "langfuse_export_job_id",
            _clean_optional(self.langfuse_export_job_id, "langfuse_export_job_id"),
        )

    @classmethod
    def from_domain(
        cls,
        metric_result: EvaluationMetricResult,
        *,
        metric_result_id: str | None = None,
        langfuse_projection_status: LangfuseProjectionStatus
        | str = LangfuseProjectionStatus.PENDING,
        langfuse_export_job_id: str | None = None,
        error_details: JsonObject | None = None,
    ) -> EvaluationMetricResultRecord:
        threshold = metric_result.score.threshold
        return cls(
            metric_result_id=metric_result_id or new_evaluation_metric_result_id(),
            run_id=metric_result.run_id,
            case_id=metric_result.case_id,
            metric_name=metric_result.score.metric_name,
            score=metric_result.score.score,
            status=metric_result.status,
            evaluator_provider=metric_result.evaluator_provider,
            evaluator_model=metric_result.evaluator_model,
            threshold=None if threshold is None else threshold.minimum_score,
            threshold_version=None if threshold is None else threshold.version,
            passed=metric_result.passed,
            reason=metric_result.score.reason,
            duration_ms=metric_result.duration_ms,
            error_message=metric_result.error_message,
            error_details=error_details,
            langfuse_projection_status=langfuse_projection_status,
            langfuse_export_job_id=langfuse_export_job_id,
            created_at=metric_result.created_at,
        )


@dataclass(frozen=True, slots=True)
class EvaluationArtifactRecord:
    """Persistence-boundary record for an evaluation artifact."""

    artifact_id: str
    run_id: str
    artifact_type: str
    case_id: str | None = None
    uri: str | None = None
    payload: JsonObject | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "artifact_id", _require_non_empty(self.artifact_id, "artifact_id")
        )
        object.__setattr__(self, "run_id", _require_non_empty(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "artifact_type",
            _require_non_empty(self.artifact_type, "artifact_type"),
        )
        object.__setattr__(self, "case_id", _clean_optional(self.case_id, "case_id"))
        object.__setattr__(self, "uri", _clean_optional(self.uri, "uri"))
        if self.uri is None and self.payload is None:
            raise ValueError("uri or payload is required for an evaluation artifact.")


@dataclass(frozen=True, slots=True)
class EvaluationPersistenceBundle:
    """Atomic group of evaluation records to persist together."""

    datasets: tuple[EvaluationDatasetRecord, ...] = ()
    cases: tuple[EvaluationCaseRecord, ...] = ()
    runs: tuple[EvaluationRunRecord, ...] = ()
    metric_results: tuple[EvaluationMetricResultRecord, ...] = ()
    artifacts: tuple[EvaluationArtifactRecord, ...] = ()


@dataclass(frozen=True, slots=True)
class EvaluationPersistenceResult:
    """Write-count summary for evaluation persistence operations."""

    datasets_written: int = 0
    cases_written: int = 0
    runs_written: int = 0
    metric_results_written: int = 0
    artifacts_written: int = 0

    @property
    def records_written(self) -> int:
        return (
            self.datasets_written
            + self.cases_written
            + self.runs_written
            + self.metric_results_written
            + self.artifacts_written
        )


def new_evaluation_metric_result_id() -> str:
    return f"evaluation_metric_result_{uuid4().hex}"


def new_evaluation_artifact_id() -> str:
    return f"evaluation_artifact_{uuid4().hex}"


def _coerce_target_type(value: EvaluationTargetType | str) -> EvaluationTargetType:
    if isinstance(value, EvaluationTargetType):
        return value
    return EvaluationTargetType(value)


def _coerce_optional_target_type(
    value: EvaluationTargetType | str | None,
) -> EvaluationTargetType | None:
    if value is None:
        return None
    return _coerce_target_type(value)


def _coerce_status(value: EvaluationStatus | str) -> EvaluationStatus:
    if isinstance(value, EvaluationStatus):
        return value
    return EvaluationStatus(value)


def _coerce_langfuse_status(
    value: LangfuseProjectionStatus | str,
) -> LangfuseProjectionStatus:
    if isinstance(value, LangfuseProjectionStatus):
        return value
    return LangfuseProjectionStatus(value)


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


def _clean_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    cleaned = tuple(value.strip() for value in values if value.strip())
    if len(cleaned) != len(values):
        raise ValueError(f"{field_name} cannot be empty.")
    return cleaned


def _validate_score(value: float, field_name: str) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0.")
