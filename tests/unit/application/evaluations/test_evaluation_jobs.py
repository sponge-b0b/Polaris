from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pytest

from application.evaluations import (
    EvaluationJobProcessor,
    EvaluationJobRequest,
    EvaluationJobStatus,
    EvaluationJobType,
    EvaluationLangfuseProjectionRequest,
    EvaluationLangfuseProjectionResult,
    EvaluationResultService,
    EvaluationRunService,
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
)
from integration.providers.llm_evaluation import (
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


@dataclass(slots=True)
class RecordingProvider:
    requests: list[EvaluationProviderRequest]

    async def evaluate(
        self,
        request: EvaluationProviderRequest,
    ) -> EvaluationProviderResult:
        self.requests.append(request)
        metric_results = tuple(
            EvaluationMetricResult(
                run_id=request.run_id,
                case_id=case.case_id,
                score=EvaluationScore(
                    metric_name=metric.metric_name,
                    score=0.91,
                    threshold=metric.threshold,
                    reason="grounded answer",
                ),
                status=EvaluationStatus.PASSED,
                evaluator_provider="deepeval",
                evaluator_model="qwen3.5:4b",
                duration_ms=12.0,
            )
            for case in request.cases
            for metric in request.metrics
        )
        return EvaluationProviderResult(
            run_id=request.run_id,
            status=EvaluationStatus.PASSED,
            metric_results=metric_results,
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
            duration_ms=12.0,
        )


@dataclass(slots=True)
class RecordingProjectionService:
    requests: list[EvaluationLangfuseProjectionRequest]

    async def project_run_scores(
        self,
        request: EvaluationLangfuseProjectionRequest,
    ) -> EvaluationLangfuseProjectionResult:
        self.requests.append(request)
        return EvaluationLangfuseProjectionResult(
            export_results=(),
            pending_count=len({result.case_id for result in request.metric_results}),
        )


def _repository() -> FakeEvaluationRepository:
    return FakeEvaluationRepository({}, {}, {}, [], [])


def _processor(
    repository: FakeEvaluationRepository,
) -> tuple[EvaluationJobProcessor, RecordingProvider, RecordingProjectionService]:
    provider = RecordingProvider([])
    projection_service = RecordingProjectionService([])
    result_service = EvaluationResultService(repository)
    run_service = EvaluationRunService(provider, repository, projection_service)
    return (
        EvaluationJobProcessor(
            run_service=run_service,
            result_service=result_service,
            projection_service=projection_service,
        ),
        provider,
        projection_service,
    )


def _dataset_record() -> EvaluationDatasetRecord:
    return EvaluationDatasetRecord(
        dataset_id="dataset-1",
        name="golden_rag_questions",
        version="v1",
        target_type=EvaluationTargetType.RAG_ANSWER,
    )


def _case_record(
    target_type: EvaluationTargetType = EvaluationTargetType.RAG_ANSWER,
) -> EvaluationCaseRecord:
    return EvaluationCaseRecord.from_domain(
        EvaluationCase(
            case_id=f"case-{target_type.value}",
            target_type=target_type,
            input_text="What changed?",
            actual_output="The answer is grounded in context.",
            dataset=EvaluationDatasetReference(
                dataset_id="dataset-1",
                name="golden_rag_questions",
                version="v1",
            ),
            rubric="Output must be grounded and professionally written.",
            retrieval_context=("Context A",),
            citation_context_ids=("chunk-1",),
            langfuse_trace_id="trace-1",
            langfuse_observation_id="observation-1",
        )
    )


@pytest.mark.asyncio
async def test_evaluate_rag_result_job_runs_provider_and_persists_results() -> None:
    repository = _repository()
    repository.datasets["dataset-1"] = _dataset_record()
    repository.cases["case-rag_answer"] = _case_record()
    processor, provider, projection_service = _processor(repository)

    result = await processor.process(
        EvaluationJobRequest(
            job_id="job-1",
            job_type=EvaluationJobType.EVALUATE_RAG_RESULT,
            case_id="case-rag_answer",
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
            include_custom_rag_metrics=False,
        )
    )

    assert result.status is EvaluationJobStatus.COMPLETED
    assert result.run_id == "evaluation_run_job-1"
    assert result.case_ids == ("case-rag_answer",)
    assert result.metric_result_count == len(provider.requests[0].metrics)
    assert result.langfuse_pending_count == 1
    assert repository.runs[result.run_id].status is EvaluationStatus.PASSED
    assert repository.metric_results
    assert projection_service.requests


@pytest.mark.asyncio
async def test_evaluate_strategy_output_job_uses_strategy_metric_policy() -> None:
    repository = _repository()
    repository.datasets["dataset-1"] = EvaluationDatasetRecord(
        dataset_id="dataset-1",
        name="strategy_synthesis_quality",
        version="v1",
        target_type=EvaluationTargetType.STRATEGY_SYNTHESIS,
    )
    repository.cases["case-strategy_synthesis"] = _case_record(
        EvaluationTargetType.STRATEGY_SYNTHESIS,
    )
    processor, provider, _projection_service = _processor(repository)

    result = await processor.process(
        EvaluationJobRequest(
            job_id="job-2",
            job_type="evaluate_strategy_output",
            case_id="case-strategy_synthesis",
            run_id="strategy-run-1",
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
        )
    )

    metric_names = {metric.metric_name for metric in provider.requests[0].metrics}
    assert result.status is EvaluationJobStatus.COMPLETED
    assert result.run_id == "strategy-run-1"
    assert "strategy_synthesis_quality" in metric_names
    assert "report_completeness" not in metric_names


@pytest.mark.asyncio
async def test_evaluate_report_job_uses_report_metric_policy() -> None:
    repository = _repository()
    repository.datasets["dataset-1"] = EvaluationDatasetRecord(
        dataset_id="dataset-1",
        name="morning_report_quality",
        version="v1",
        target_type=EvaluationTargetType.MORNING_REPORT,
    )
    repository.cases["case-morning_report"] = _case_record(
        EvaluationTargetType.MORNING_REPORT,
    )
    processor, provider, _projection_service = _processor(repository)

    result = await processor.process(
        EvaluationJobRequest(
            job_id="job-3",
            job_type=EvaluationJobType.EVALUATE_REPORT,
            case_id="case-morning_report",
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
        )
    )

    metric_names = {metric.metric_name for metric in provider.requests[0].metrics}
    assert result.status is EvaluationJobStatus.COMPLETED
    assert "report_completeness" in metric_names
    assert "strategy_synthesis_quality" not in metric_names


@pytest.mark.asyncio
async def test_projection_job_projects_persisted_metric_results() -> None:
    repository = _repository()
    repository.datasets["dataset-1"] = _dataset_record()
    repository.cases["case-rag_answer"] = _case_record()
    processor, _provider, projection_service = _processor(repository)
    evaluation_result = await processor.process(
        EvaluationJobRequest(
            job_id="job-4",
            job_type=EvaluationJobType.EVALUATE_RAG_RESULT,
            case_id="case-rag_answer",
            run_id="run-to-project",
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
            include_custom_rag_metrics=False,
        )
    )
    projection_service.requests.clear()

    projection_result = await processor.process(
        EvaluationJobRequest(
            job_id="job-5",
            job_type=EvaluationJobType.PROJECT_EVAL_SCORES_TO_LANGFUSE,
            run_id=evaluation_result.run_id,
        )
    )

    assert projection_result.status is EvaluationJobStatus.COMPLETED
    assert projection_result.run_id == "run-to-project"
    assert projection_result.metric_result_count == len(repository.metric_results)
    assert projection_result.langfuse_pending_count == 1
    assert projection_service.requests[0].run.run_id == "run-to-project"


@pytest.mark.asyncio
async def test_retry_failed_projection_uses_same_idempotent_projection_boundary() -> (
    None
):
    repository = _repository()
    repository.datasets["dataset-1"] = _dataset_record()
    repository.cases["case-rag_answer"] = _case_record()
    processor, _provider, projection_service = _processor(repository)
    await processor.process(
        EvaluationJobRequest(
            job_id="job-6",
            job_type=EvaluationJobType.EVALUATE_RAG_RESULT,
            case_id="case-rag_answer",
            run_id="run-retry",
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
            include_custom_rag_metrics=False,
        )
    )
    projection_service.requests.clear()

    result = await processor.process(
        EvaluationJobRequest(
            job_id="job-7",
            job_type=EvaluationJobType.RETRY_FAILED_EVAL_PROJECTION,
            run_id="run-retry",
        )
    )

    assert result.status is EvaluationJobStatus.COMPLETED
    assert result.run_id == "run-retry"
    assert projection_service.requests[0].run.run_id == "run-retry"


def test_job_request_validates_required_fields_by_job_type() -> None:
    with pytest.raises(ValueError, match="case_id is required"):
        EvaluationJobRequest(
            job_id="job-invalid",
            job_type=EvaluationJobType.EVALUATE_RAG_RESULT,
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
        )

    with pytest.raises(ValueError, match="run_id is required"):
        EvaluationJobRequest(
            job_id="job-invalid",
            job_type=EvaluationJobType.PROJECT_EVAL_SCORES_TO_LANGFUSE,
        )


@pytest.mark.asyncio
async def test_job_processor_returns_failure_for_mismatched_case_target() -> None:
    repository = _repository()
    repository.cases["case-morning_report"] = _case_record(
        EvaluationTargetType.MORNING_REPORT,
    )
    processor, _provider, _projection_service = _processor(repository)

    result = await processor.process(
        EvaluationJobRequest(
            job_id="job-8",
            job_type=EvaluationJobType.EVALUATE_STRATEGY_OUTPUT,
            case_id="case-morning_report",
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
        )
    )

    assert result.status is EvaluationJobStatus.FAILED
    assert result.error_message is not None
    assert "strategy synthesis case" in result.error_message
