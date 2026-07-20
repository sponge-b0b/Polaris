from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

import pytest

from application.evaluations import (
    EvaluationDatasetRegistrationRequest,
    EvaluationDatasetSeedRequest,
    EvaluationDatasetService,
    EvaluationLangfuseProjectionRequest,
    EvaluationLangfuseProjectionResult,
    EvaluationResultService,
    EvaluationRunService,
    EvaluationRunServiceRequest,
    EvaluationTelemetry,
    canonical_evaluation_dataset_definition_by_name,
    canonical_evaluation_dataset_slice_definition_by_name,
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
from core.telemetry.observability import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from domain.evaluation import (
    EvaluationCase,
    EvaluationDatasetReference,
    EvaluationMetricResult,
    EvaluationRun,
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
        for replacement in bundle.dataset_case_replacements:
            allowed_case_ids = set(replacement.case_ids)
            for case_id, case in tuple(self.cases.items()):
                if (
                    case.dataset_id == replacement.dataset_id
                    and case_id not in allowed_case_ids
                ):
                    self.cases[case_id] = replace(case, dataset_id=None)
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


@pytest.mark.asyncio
async def test_dataset_service_dry_run_counts_canonical_fixtures() -> None:
    repository = _repository()

    result = await EvaluationDatasetService(repository).seed_canonical_datasets(
        EvaluationDatasetSeedRequest(dry_run=True)
    )

    assert result.dry_run is True
    assert result.dataset_count == 8
    assert result.case_count == 100
    assert result.datasets_written == 0
    assert result.cases_written == 0
    assert repository.datasets == {}
    assert repository.cases == {}


@pytest.mark.asyncio
async def test_dataset_service_seeds_model_regression_cases_as_active_membership() -> (
    None
):
    repository = _repository()
    model_regression = canonical_evaluation_dataset_slice_definition_by_name(
        "model_regression"
    )

    result = await EvaluationDatasetService(repository).seed_canonical_datasets(
        EvaluationDatasetSeedRequest()
    )

    assert result.dataset_count == 8
    assert result.case_count == 100
    for membership in model_regression.memberships:
        definition = canonical_evaluation_dataset_definition_by_name(
            membership.dataset_name
        )
        active_cases = await repository.list_cases_by_dataset(
            definition.reference.dataset_id
        )
        active_case_ids = {case.case_id for case in active_cases}

        assert set(membership.case_ids) <= active_case_ids


@pytest.mark.asyncio
async def test_dataset_service_seeds_selected_dataset_idempotently() -> None:
    repository = _repository()
    service = EvaluationDatasetService(repository)

    first = await service.seed_canonical_datasets(
        EvaluationDatasetSeedRequest(dataset_name="golden_rag_questions")
    )
    second = await service.seed_canonical_datasets(
        EvaluationDatasetSeedRequest(dataset_name="golden_rag_questions")
    )

    assert first.dataset_count == 1
    assert first.case_count == 25
    assert first.datasets_written == 1
    assert first.cases_written == 25
    assert second.datasets_written == 1
    assert second.cases_written == 25
    assert set(repository.datasets) == {"golden_rag_questions_v1"}
    assert len(repository.cases) == 25
    seeded_case = repository.cases["golden-rag-answer-001"]
    assert seeded_case.dataset_id == "golden_rag_questions_v1"
    assert seeded_case.source_record_ids
    assert seeded_case.retrieval_context


@pytest.mark.asyncio
async def test_dataset_service_replaces_stale_dataset_membership() -> None:
    repository = _repository()
    stale_case = EvaluationCaseRecord(
        case_id="stale-golden-case",
        dataset_id="golden_rag_questions_v1",
        target_type=EvaluationTargetType.RAG_ANSWER,
        input_text="Obsolete question?",
        actual_output="Obsolete answer.",
        rubric="Should no longer be active dataset membership.",
    )
    repository.cases[stale_case.case_id] = stale_case

    result = await EvaluationDatasetService(repository).seed_canonical_datasets(
        EvaluationDatasetSeedRequest(dataset_name="golden_rag_questions")
    )

    active_cases = await repository.list_cases_by_dataset("golden_rag_questions_v1")
    assert result.case_count == 25
    assert len(active_cases) == 25
    assert repository.cases[stale_case.case_id].dataset_id is None
    assert repository.cases[stale_case.case_id].rubric == stale_case.rubric
