from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, cast

from application.evaluations.contracts import (
    EvaluationLangfuseProjectionRequest,
    EvaluationLangfuseProjectionResult,
)
from core.storage.persistence.evaluation import (
    EvaluationArtifactRecord,
    EvaluationCaseRecord,
    EvaluationDatasetRecord,
    EvaluationMetricResultRecord,
    EvaluationPersistenceBundle,
    EvaluationPersistenceResult,
    EvaluationRunRecord,
)
from domain.evaluation import (
    EvaluationCase,
    EvaluationDatasetReference,
    EvaluationMetricResult,
    EvaluationScore,
    EvaluationStatus,
    EvaluationTargetType,
    EvaluationThreshold,
)
from integration.providers.llm_evaluation import (
    EvaluationMetricSpec,
    EvaluationProviderRequest,
    EvaluationProviderResult,
)

JsonRow = dict[str, Any]


@dataclass(slots=True)
class InMemoryEvaluationRepository:
    """Deterministic in-memory repository for CI evaluation smoke tests."""

    datasets: dict[str, EvaluationDatasetRecord] = field(default_factory=dict)
    cases: dict[str, EvaluationCaseRecord] = field(default_factory=dict)
    runs: dict[str, EvaluationRunRecord] = field(default_factory=dict)
    metric_results: dict[str, EvaluationMetricResultRecord] = field(
        default_factory=dict
    )
    artifacts: dict[str, EvaluationArtifactRecord] = field(default_factory=dict)

    async def persist_evaluation_bundle(
        self,
        bundle: EvaluationPersistenceBundle,
    ) -> EvaluationPersistenceResult:
        for dataset_record in bundle.datasets:
            self.datasets[dataset_record.dataset_id] = dataset_record
        for case_record in bundle.cases:
            self.cases[case_record.case_id] = case_record
        for run_record in bundle.runs:
            self.runs[run_record.run_id] = run_record
        for metric_result_record in bundle.metric_results:
            self.metric_results[metric_result_record.metric_result_id] = (
                metric_result_record
            )
        for artifact_record in bundle.artifacts:
            self.artifacts[artifact_record.artifact_id] = artifact_record
        return EvaluationPersistenceResult(
            datasets_written=len(bundle.datasets),
            cases_written=len(bundle.cases),
            runs_written=len(bundle.runs),
            metric_results_written=len(bundle.metric_results),
            artifacts_written=len(bundle.artifacts),
        )

    async def upsert_dataset(
        self,
        record: EvaluationDatasetRecord,
    ) -> EvaluationDatasetRecord:
        self.datasets[record.dataset_id] = record
        return record

    async def upsert_case(self, record: EvaluationCaseRecord) -> EvaluationCaseRecord:
        self.cases[record.case_id] = record
        return record

    async def upsert_run(self, record: EvaluationRunRecord) -> EvaluationRunRecord:
        self.runs[record.run_id] = record
        return record

    async def upsert_metric_result(
        self,
        record: EvaluationMetricResultRecord,
    ) -> EvaluationMetricResultRecord:
        self.metric_results[record.metric_result_id] = record
        return record

    async def create_artifact(
        self,
        record: EvaluationArtifactRecord,
    ) -> EvaluationArtifactRecord:
        self.artifacts[record.artifact_id] = record
        return record

    async def get_dataset(self, dataset_id: str) -> EvaluationDatasetRecord | None:
        return self.datasets.get(dataset_id)

    async def get_case(self, case_id: str) -> EvaluationCaseRecord | None:
        return self.cases.get(case_id)

    async def get_run(self, run_id: str) -> EvaluationRunRecord | None:
        return self.runs.get(run_id)

    async def list_cases_by_dataset(
        self,
        dataset_id: str,
        *,
        limit: int | None = None,
    ) -> Sequence[EvaluationCaseRecord]:
        records = tuple(
            record for record in self.cases.values() if record.dataset_id == dataset_id
        )
        return records if limit is None else records[:limit]

    async def list_cases_by_target_type(
        self,
        target_type: EvaluationTargetType,
        *,
        limit: int | None = None,
    ) -> Sequence[EvaluationCaseRecord]:
        records = tuple(
            record
            for record in self.cases.values()
            if record.target_type is target_type
        )
        return records if limit is None else records[:limit]

    async def list_metric_results(
        self,
        run_id: str,
    ) -> Sequence[EvaluationMetricResultRecord]:
        return tuple(
            record for record in self.metric_results.values() if record.run_id == run_id
        )

    async def list_artifacts(self, run_id: str) -> Sequence[EvaluationArtifactRecord]:
        return tuple(
            record for record in self.artifacts.values() if record.run_id == run_id
        )


@dataclass(frozen=True, slots=True)
class PassingEvaluationProvider:
    """Deterministic provider that exercises the service without a live judge model."""

    score: float = 0.95

    async def evaluate(
        self,
        request: EvaluationProviderRequest,
    ) -> EvaluationProviderResult:
        metric_results = tuple(
            self._metric_result(request.run_id, case, metric)
            for case in request.cases
            for metric in request.metrics
        )
        return EvaluationProviderResult(
            run_id=request.run_id,
            status=EvaluationStatus.PASSED,
            metric_results=metric_results,
            evaluator_provider="deterministic_ci",
            evaluator_model="fixture_judge",
            duration_ms=1.0,
        )

    def _metric_result(
        self,
        run_id: str,
        case: EvaluationCase,
        metric: EvaluationMetricSpec,
    ) -> EvaluationMetricResult:
        threshold = metric.threshold or EvaluationThreshold(metric.metric_name, 0.7)
        score = EvaluationScore(
            metric_name=metric.metric_name,
            score=self.score,
            threshold=threshold,
            reason="deterministic CI evaluation passed",
        )
        return EvaluationMetricResult(
            run_id=run_id,
            case_id=case.case_id,
            score=score,
            status=EvaluationStatus.PASSED,
            evaluator_provider="deterministic_ci",
            evaluator_model="fixture_judge",
            duration_ms=1.0,
        )


@dataclass(slots=True)
class RecordingProjectionService:
    """Records score-projection requests without exporting to Langfuse."""

    requests: list[EvaluationLangfuseProjectionRequest] = field(default_factory=list)

    async def project_run_scores(
        self,
        request: EvaluationLangfuseProjectionRequest,
    ) -> EvaluationLangfuseProjectionResult:
        self.requests.append(request)
        return EvaluationLangfuseProjectionResult(
            export_results=(),
            skipped_count=len(request.metric_results),
        )


def evaluation_case_from_row(
    row: JsonRow,
    *,
    dataset: EvaluationDatasetReference | None = None,
) -> EvaluationCase:
    return EvaluationCase(
        case_id=_required_str(row, "case_id"),
        target_type=EvaluationTargetType(_required_str(row, "target_type")),
        input_text=_required_str(row, "input_text"),
        actual_output=_required_str(row, "actual_output"),
        dataset=dataset,
        expected_output=_optional_str(row, "expected_output"),
        rubric=_optional_str(row, "rubric"),
        source_record_ids=_string_tuple(row, "source_record_ids"),
        workflow_execution_id=_optional_str(row, "workflow_execution_id"),
        langfuse_trace_id=_optional_str(row, "langfuse_trace_id"),
        langfuse_observation_id=_optional_str(row, "langfuse_observation_id"),
        retrieval_context=_string_tuple(row, "retrieval_context"),
        citation_context_ids=_string_tuple(row, "citation_context_ids"),
        tags=_string_tuple(row, "tags"),
    )


def _required_str(row: JsonRow, key: str) -> str:
    value = row[key]
    if not isinstance(value, str) or not value.strip():
        raise AssertionError(f"{key} must be a non-empty string")
    return value


def _optional_str(row: JsonRow, key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise AssertionError(f"{key} must be a non-empty string when present")
    return value


def _string_tuple(row: JsonRow, key: str) -> tuple[str, ...]:
    values = row.get(key, [])
    if not isinstance(values, list):
        raise AssertionError(f"{key} must be a list")
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise AssertionError(f"{key} entries must be non-empty strings")
    return tuple(cast("list[str]", values))
