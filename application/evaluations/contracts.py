from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from application.observability.ai_observability_contracts import (
    AiObservabilityExportResult,
)
from core.storage.persistence.evaluation import EvaluationArtifactRecord
from core.storage.persistence.evaluation import EvaluationCaseRecord
from core.storage.persistence.evaluation import EvaluationMetricResultRecord
from core.storage.persistence.evaluation import JsonObject
from core.storage.persistence.evaluation import EvaluationPersistenceResult
from core.storage.persistence.evaluation import EvaluationRunRecord
from domain.evaluation import EvaluationCase
from domain.evaluation import EvaluationDatasetReference
from domain.evaluation import EvaluationMetricResult
from domain.evaluation import EvaluationRun
from domain.evaluation import EvaluationTargetType
from integration.providers.llm_evaluation import EvaluationMetricSpec


@dataclass(frozen=True, slots=True)
class EvaluationCaseBuildRequest:
    """Typed application request for constructing an evaluation case."""

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
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class EvaluationDatasetRegistrationRequest:
    """Application request for registering a versioned evaluation dataset."""

    reference: EvaluationDatasetReference
    target_type: EvaluationTargetType | None = None
    description: str | None = None
    source_lineage: tuple[str, ...] = ()
    deterministic_fixture_uri: str | None = None
    threshold_profile: JsonObject | None = None
    active: bool = True


@dataclass(frozen=True, slots=True)
class EvaluationDatasetSeedRequest:
    """Application request for seeding canonical evaluation datasets."""

    dataset_name: str | None = None
    dry_run: bool = False

    def __post_init__(self) -> None:
        if self.dataset_name is None:
            return
        cleaned_name = self.dataset_name.strip()
        if not cleaned_name:
            raise ValueError("dataset_name cannot be empty when provided.")
        object.__setattr__(self, "dataset_name", cleaned_name)


@dataclass(frozen=True, slots=True)
class EvaluationDatasetSeedItem:
    """Seed summary for one canonical evaluation dataset fixture."""

    name: str
    dataset_id: str
    fixture_uri: str
    case_count: int
    persisted: bool


@dataclass(frozen=True, slots=True)
class EvaluationDatasetSeedResult:
    """Application result for canonical evaluation dataset seeding."""

    dry_run: bool
    items: tuple[EvaluationDatasetSeedItem, ...]
    datasets_written: int = 0
    cases_written: int = 0

    @property
    def dataset_count(self) -> int:
        return len(self.items)

    @property
    def case_count(self) -> int:
        return sum(item.case_count for item in self.items)


@dataclass(frozen=True, slots=True)
class EvaluationRunServiceRequest:
    """Application request for executing one evaluation run."""

    run_id: str
    target_type: EvaluationTargetType
    cases: Sequence[EvaluationCase]
    metrics: Sequence[EvaluationMetricSpec]
    evaluator_provider: str
    evaluator_model: str
    dataset: EvaluationDatasetReference | None = None
    timeout_seconds: float | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.run_id, "run_id")
        _require_non_empty(self.evaluator_provider, "evaluator_provider")
        _require_non_empty(self.evaluator_model, "evaluator_model")
        if not self.cases:
            raise ValueError("cases cannot be empty.")
        if not self.metrics:
            raise ValueError("metrics cannot be empty.")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be greater than 0.0.")


@dataclass(frozen=True, slots=True)
class EvaluationRunServiceResult:
    """Application result for one evaluation run execution."""

    run: EvaluationRun
    metric_results: tuple[EvaluationMetricResult, ...]
    persistence_result: EvaluationPersistenceResult
    langfuse_projection_result: EvaluationLangfuseProjectionResult | None = None

    @property
    def metric_result_count(self) -> int:
        return len(self.metric_results)

    @property
    def langfuse_projection_attempted(self) -> bool:
        return self.langfuse_projection_result is not None


@dataclass(frozen=True, slots=True)
class EvaluationResultBundle:
    """Read model for a persisted evaluation run and its supporting records."""

    run: EvaluationRunRecord
    metric_results: tuple[EvaluationMetricResultRecord, ...]
    artifacts: tuple[EvaluationArtifactRecord, ...] = ()

    @property
    def metric_result_count(self) -> int:
        return len(self.metric_results)


@dataclass(frozen=True, slots=True)
class EvaluationLangfuseProjectionRequest:
    """Application request for projecting persisted evaluation scores to Langfuse."""

    run: EvaluationRunRecord
    metric_results: Sequence[EvaluationMetricResultRecord]
    cases: Sequence[EvaluationCaseRecord] = ()


@dataclass(frozen=True, slots=True)
class EvaluationLangfuseProjectionResult:
    """Summary of Langfuse score-projection attempts."""

    export_results: tuple[AiObservabilityExportResult, ...]
    exported_count: int = 0
    pending_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0

    @property
    def accepted_count(self) -> int:
        return self.exported_count + self.pending_count


def utc_now() -> datetime:
    return datetime.now(UTC)


def _require_non_empty(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
