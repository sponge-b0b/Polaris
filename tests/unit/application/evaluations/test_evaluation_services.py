from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pytest

from application.evaluations import EvaluationDatasetRegistrationRequest
from application.evaluations import EvaluationLangfuseProjectionRequest
from application.evaluations import EvaluationLangfuseProjectionResult
from application.evaluations import EvaluationDatasetService
from application.evaluations import EvaluationResultService
from application.evaluations import EvaluationRunService
from application.evaluations import EvaluationTelemetry
from application.evaluations import EvaluationRunServiceRequest
from core.storage.persistence.evaluation import EvaluationArtifactRecord
from core.storage.persistence.evaluation import EvaluationCaseRecord
from core.storage.persistence.evaluation import EvaluationDatasetRecord
from core.storage.persistence.evaluation import EvaluationMetricResultRecord
from core.storage.persistence.evaluation import EvaluationPersistenceBundle
from core.storage.persistence.evaluation import EvaluationPersistenceResult
from core.storage.persistence.evaluation import EvaluationRunRecord
from core.telemetry.observability import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from domain.evaluation import EvaluationCase
from domain.evaluation import EvaluationDatasetReference
from domain.evaluation import EvaluationMetricResult
from domain.evaluation import EvaluationRun
from domain.evaluation import EvaluationScore
from domain.evaluation import EvaluationStatus
from domain.evaluation import EvaluationTargetType
from domain.evaluation import EvaluationThreshold
from integration.providers.llm_evaluation import EvaluationMetricSpec
from integration.providers.llm_evaluation import EvaluationProviderRequest
from integration.providers.llm_evaluation import EvaluationProviderResult


@dataclass(slots=True)
class FakeEvaluationRepository:
    datasets: dict[str, EvaluationDatasetRecord]
    cases: dict[str, EvaluationCaseRecord]
    runs: dict[str, EvaluationRunRecord]
    metric_results: list[EvaluationMetricResultRecord]
    artifacts: list[EvaluationArtifactRecord]

    async def persist_evaluation_bundle(
        self,
        bundle: EvaluationPersistenceBundle,
    ) -> EvaluationPersistenceResult:
        for dataset in bundle.datasets:
            self.datasets[dataset.dataset_id] = dataset
        for case in bundle.cases:
            self.cases[case.case_id] = case
        for run in bundle.runs:
            self.runs[run.run_id] = run
        self.metric_results.extend(bundle.metric_results)
        self.artifacts.extend(bundle.artifacts)
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

    async def upsert_case(
        self,
        record: EvaluationCaseRecord,
    ) -> EvaluationCaseRecord:
        self.cases[record.case_id] = record
        return record

    async def upsert_run(
        self,
        record: EvaluationRunRecord,
    ) -> EvaluationRunRecord:
        self.runs[record.run_id] = record
        return record

    async def upsert_metric_result(
        self,
        record: EvaluationMetricResultRecord,
    ) -> EvaluationMetricResultRecord:
        self.metric_results.append(record)
        return record

    async def create_artifact(
        self,
        record: EvaluationArtifactRecord,
    ) -> EvaluationArtifactRecord:
        self.artifacts.append(record)
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
        cases = tuple(
            case for case in self.cases.values() if case.dataset_id == dataset_id
        )
        return cases if limit is None else cases[:limit]

    async def list_cases_by_target_type(
        self,
        target_type: EvaluationTargetType,
        *,
        limit: int | None = None,
    ) -> Sequence[EvaluationCaseRecord]:
        cases = tuple(
            case for case in self.cases.values() if case.target_type is target_type
        )
        return cases if limit is None else cases[:limit]

    async def list_metric_results(
        self,
        run_id: str,
    ) -> Sequence[EvaluationMetricResultRecord]:
        return tuple(
            result for result in self.metric_results if result.run_id == run_id
        )

    async def list_artifacts(self, run_id: str) -> Sequence[EvaluationArtifactRecord]:
        return tuple(
            artifact for artifact in self.artifacts if artifact.run_id == run_id
        )


@dataclass(frozen=True, slots=True)
class FakeProvider:
    status: EvaluationStatus = EvaluationStatus.PASSED
    fail: bool = False

    async def evaluate(
        self,
        request: EvaluationProviderRequest,
    ) -> EvaluationProviderResult:
        if self.fail:
            raise RuntimeError("judge unavailable")
        metric_results = tuple(
            EvaluationMetricResult(
                run_id=request.run_id,
                case_id=case.case_id,
                score=EvaluationScore(
                    metric_name=request.metrics[0].metric_name,
                    score=0.91,
                    threshold=request.metrics[0].threshold,
                    reason="grounded answer",
                ),
                status=self.status,
                evaluator_provider="deepeval",
                evaluator_model="qwen3.5:4b",
                duration_ms=12.0,
            )
            for case in request.cases
        )
        return EvaluationProviderResult(
            run_id=request.run_id,
            status=self.status,
            metric_results=metric_results,
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
            duration_ms=12.0,
        )


@dataclass(slots=True)
class FakeProjectionService:
    requests: list[EvaluationLangfuseProjectionRequest]
    fail: bool = False

    async def project_run_scores(
        self,
        request: EvaluationLangfuseProjectionRequest,
    ) -> EvaluationLangfuseProjectionResult:
        self.requests.append(request)
        if self.fail:
            raise RuntimeError("langfuse unavailable")
        return EvaluationLangfuseProjectionResult(
            export_results=(),
            pending_count=len({result.case_id for result in request.metric_results}),
        )


def _repository() -> FakeEvaluationRepository:
    return FakeEvaluationRepository({}, {}, {}, [], [])


def _case(dataset: EvaluationDatasetReference) -> EvaluationCase:
    return EvaluationCase(
        case_id="case-1",
        target_type=EvaluationTargetType.RAG_ANSWER,
        input_text="Question?",
        actual_output="Answer.",
        dataset=dataset,
        rubric="Answer must be grounded.",
    )


def _metric() -> EvaluationMetricSpec:
    return EvaluationMetricSpec(
        metric_name="faithfulness",
        threshold=EvaluationThreshold("faithfulness", 0.8),
    )


@pytest.mark.asyncio
async def test_dataset_service_registers_dataset() -> None:
    repository = _repository()
    reference = EvaluationDatasetReference("dataset-1", "golden", "v1")

    record = await EvaluationDatasetService(repository).register_dataset(
        EvaluationDatasetRegistrationRequest(
            reference=reference,
            target_type=EvaluationTargetType.RAG_ANSWER,
            description="Golden cases",
            source_lineage=("postgres.rag_documents",),
            deterministic_fixture_uri="tests/evaluation/fixtures/golden.jsonl",
            threshold_profile={"profile_version": "v1"},
        )
    )

    assert record.dataset_id == "dataset-1"
    assert record.source_lineage == ("postgres.rag_documents",)
    assert record.deterministic_fixture_uri == "tests/evaluation/fixtures/golden.jsonl"
    assert record.threshold_profile == {"profile_version": "v1"}
    assert await EvaluationDatasetService(repository).get_dataset("dataset-1") == record


@pytest.mark.asyncio
async def test_run_service_persists_cases_running_run_and_results() -> None:
    repository = _repository()
    dataset = EvaluationDatasetReference("dataset-1", "golden", "v1")
    service = EvaluationRunService(
        FakeProvider(), repository, FakeProjectionService([])
    )

    result = await service.run_evaluation(
        EvaluationRunServiceRequest(
            run_id="run-1",
            target_type=EvaluationTargetType.RAG_ANSWER,
            cases=(_case(dataset),),
            metrics=(_metric(),),
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
            dataset=dataset,
        )
    )

    assert result.run.status is EvaluationStatus.PASSED
    assert result.metric_result_count == 1
    assert (
        repository.datasets["dataset-1"].target_type is EvaluationTargetType.RAG_ANSWER
    )
    assert repository.cases["case-1"].dataset_id == "dataset-1"
    assert repository.runs["run-1"].status is EvaluationStatus.PASSED
    assert repository.metric_results[0].metric_name == "faithfulness"


@pytest.mark.asyncio
async def test_run_service_records_evaluation_observability() -> None:
    repository = _repository()
    dataset = EvaluationDatasetReference("dataset-1", "golden", "v1")
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    service = EvaluationRunService(
        FakeProvider(),
        repository,
        FakeProjectionService([]),
        telemetry=EvaluationTelemetry(observability),
    )

    result = await service.run_evaluation(
        EvaluationRunServiceRequest(
            run_id="run-1",
            target_type=EvaluationTargetType.RAG_ANSWER,
            cases=(_case(dataset),),
            metrics=(_metric(),),
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
            dataset=dataset,
        )
    )

    event_types = [event.event_type for event in sink.events]
    metric_names = [point.name for point in observability.metrics_store.points()]

    assert result.run.status is EvaluationStatus.PASSED
    assert event_types == ["evaluation.run.started", "evaluation.run.completed"]
    assert "evaluation_runs_total" in metric_names
    assert "evaluation_cases_evaluated_total" in metric_names
    assert "evaluation_metric_duration_seconds" in metric_names


@pytest.mark.asyncio
async def test_run_service_persists_errored_run_when_provider_fails() -> None:
    repository = _repository()
    dataset = EvaluationDatasetReference("dataset-1", "golden", "v1")
    service = EvaluationRunService(
        FakeProvider(fail=True), repository, FakeProjectionService([])
    )

    result = await service.run_evaluation(
        EvaluationRunServiceRequest(
            run_id="run-1",
            target_type=EvaluationTargetType.RAG_ANSWER,
            cases=(_case(dataset),),
            metrics=(_metric(),),
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
            dataset=dataset,
        )
    )

    assert result.run.status is EvaluationStatus.ERRORED
    assert result.run.error_message == "judge unavailable"
    assert repository.runs["run-1"].status is EvaluationStatus.ERRORED
    assert repository.metric_results == []


@pytest.mark.asyncio
async def test_result_service_returns_run_result_bundle() -> None:
    repository = _repository()
    run = EvaluationRunRecord.from_domain(
        EvaluationRun(
            run_id="run-1",
            target_type=EvaluationTargetType.RAG_ANSWER,
            status=EvaluationStatus.PASSED,
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
        )
    )
    repository.runs["run-1"] = run

    bundle = await EvaluationResultService(repository).get_run_results("run-1")

    assert bundle is not None
    assert bundle.run == run
    assert bundle.metric_result_count == 0


@pytest.mark.asyncio
async def test_run_service_projects_persisted_results_to_langfuse() -> None:
    repository = _repository()
    projection_service = FakeProjectionService([])
    dataset = EvaluationDatasetReference("dataset-1", "golden", "v1")
    service = EvaluationRunService(
        FakeProvider(),
        repository,
        projection_service=projection_service,
    )

    result = await service.run_evaluation(
        EvaluationRunServiceRequest(
            run_id="run-1",
            target_type=EvaluationTargetType.RAG_ANSWER,
            cases=(_case(dataset),),
            metrics=(_metric(),),
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
            dataset=dataset,
        )
    )

    assert result.langfuse_projection_attempted is True
    assert result.langfuse_projection_result is not None
    assert result.langfuse_projection_result.pending_count == 1
    assert len(projection_service.requests) == 1
    projection_request = projection_service.requests[0]
    assert projection_request.run.run_id == "run-1"
    assert projection_request.run.dataset_id == "dataset-1"
    assert projection_request.metric_results[0].metric_name == "faithfulness"
    assert projection_request.cases[0].case_id == "case-1"
    assert repository.metric_results[0].run_id == "run-1"


@pytest.mark.asyncio
async def test_run_service_preserves_persistence_when_langfuse_projection_fails() -> (
    None
):
    repository = _repository()
    projection_service = FakeProjectionService([], fail=True)
    dataset = EvaluationDatasetReference("dataset-1", "golden", "v1")
    service = EvaluationRunService(
        FakeProvider(),
        repository,
        projection_service=projection_service,
    )

    result = await service.run_evaluation(
        EvaluationRunServiceRequest(
            run_id="run-1",
            target_type=EvaluationTargetType.RAG_ANSWER,
            cases=(_case(dataset),),
            metrics=(_metric(),),
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
            dataset=dataset,
        )
    )

    assert result.run.status is EvaluationStatus.PASSED
    assert result.langfuse_projection_result is not None
    assert result.langfuse_projection_result.failed_count == 1
    assert repository.runs["run-1"].status is EvaluationStatus.PASSED
    assert repository.metric_results[0].metric_name == "faithfulness"


@pytest.mark.asyncio
async def test_result_service_lists_cases_by_dataset_and_target_type() -> None:
    repository = _repository()
    case = EvaluationCaseRecord(
        case_id="case-1",
        dataset_id="dataset-1",
        target_type=EvaluationTargetType.RAG_ANSWER,
        input_text="Question?",
        actual_output="Answer.",
        rubric="Answer must be grounded.",
    )
    repository.cases[case.case_id] = case

    service = EvaluationResultService(repository)

    assert await service.list_dataset_cases("dataset-1") == (case,)
    assert await service.list_latest_cases(EvaluationTargetType.RAG_ANSWER) == (case,)
