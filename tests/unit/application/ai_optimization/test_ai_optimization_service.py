from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pytest

from application.ai_optimization import (
    AiOptimizationRequest,
    AiOptimizationService,
    AiOptimizationStatus,
    AiOptimizationTarget,
)
from application.evaluations import (
    EvaluationLangfuseProjectionResult,
    EvaluationRunServiceRequest,
    EvaluationRunServiceResult,
)
from application.observability.ai_observability_contracts import (
    AiObservabilityExportResult,
)
from core.storage.persistence.ai_artifacts import (
    AiArtifactApprovalStatus,
    AiArtifactPersistenceRepository,
    AiArtifactType,
    AiPromptProgramArtifactRecord,
)
from core.storage.persistence.evaluation import (
    EvaluationArtifactRecord,
    EvaluationCaseRecord,
    EvaluationDatasetRecord,
    EvaluationMetricResultRecord,
    EvaluationPersistenceBundle,
    EvaluationPersistenceRepository,
    EvaluationPersistenceResult,
    EvaluationRunRecord,
)
from domain.evaluation import (
    EvaluationDatasetReference,
    EvaluationMetricResult,
    EvaluationRun,
    EvaluationScore,
    EvaluationStatus,
    EvaluationTargetType,
    EvaluationThreshold,
)
from integration.providers.ai_optimization import (
    DspyOptimizationProviderRequest,
    DspyOptimizationProviderResult,
    DspyOptimizedArtifact,
    DspyOptimizedCaseOutput,
)
from integration.providers.llm_evaluation import EvaluationMetricSpec


@dataclass(slots=True)
class FakeEvaluationRepository(EvaluationPersistenceRepository):
    dataset: EvaluationDatasetRecord | None
    cases: tuple[EvaluationCaseRecord, ...]

    async def persist_evaluation_bundle(
        self,
        bundle: EvaluationPersistenceBundle,
    ) -> EvaluationPersistenceResult:
        return EvaluationPersistenceResult()

    async def upsert_dataset(
        self,
        record: EvaluationDatasetRecord,
    ) -> EvaluationDatasetRecord:
        return record

    async def upsert_case(self, record: EvaluationCaseRecord) -> EvaluationCaseRecord:
        return record

    async def upsert_run(self, record: EvaluationRunRecord) -> EvaluationRunRecord:
        return record

    async def upsert_metric_result(
        self,
        record: EvaluationMetricResultRecord,
    ) -> EvaluationMetricResultRecord:
        return record

    async def create_artifact(
        self,
        record: EvaluationArtifactRecord,
    ) -> EvaluationArtifactRecord:
        return record

    async def get_dataset(self, dataset_id: str) -> EvaluationDatasetRecord | None:
        if self.dataset is None or self.dataset.dataset_id != dataset_id:
            return None
        return self.dataset

    async def get_case(self, case_id: str) -> EvaluationCaseRecord | None:
        return next((case for case in self.cases if case.case_id == case_id), None)

    async def get_run(self, run_id: str) -> EvaluationRunRecord | None:
        return None

    async def list_cases_by_dataset(
        self,
        dataset_id: str,
        *,
        limit: int | None = None,
    ) -> Sequence[EvaluationCaseRecord]:
        cases = tuple(case for case in self.cases if case.dataset_id == dataset_id)
        return cases if limit is None else cases[:limit]

    async def list_cases_by_target_type(
        self,
        target_type: EvaluationTargetType,
        *,
        limit: int | None = None,
    ) -> Sequence[EvaluationCaseRecord]:
        cases = tuple(case for case in self.cases if case.target_type is target_type)
        return cases if limit is None else cases[:limit]

    async def list_metric_results(
        self,
        run_id: str,
    ) -> Sequence[EvaluationMetricResultRecord]:
        return ()

    async def list_artifacts(self, run_id: str) -> Sequence[EvaluationArtifactRecord]:
        return ()


@dataclass(slots=True)
class FakeArtifactRepository(AiArtifactPersistenceRepository):
    records: list[AiPromptProgramArtifactRecord]

    async def upsert_artifact(
        self,
        record: AiPromptProgramArtifactRecord,
    ) -> AiPromptProgramArtifactRecord:
        self.records.append(record)
        return record

    async def get_artifact(
        self,
        artifact_id: str,
    ) -> AiPromptProgramArtifactRecord | None:
        return next(
            (record for record in self.records if record.artifact_id == artifact_id),
            None,
        )

    async def list_artifacts(
        self,
        *,
        target_component: str | None = None,
        artifact_type: AiArtifactType | str | None = None,
        active: bool | None = None,
        limit: int | None = None,
    ) -> Sequence[AiPromptProgramArtifactRecord]:
        return tuple(self.records if limit is None else self.records[:limit])

    async def get_active_artifact(
        self,
        target_component: str,
        *,
        artifact_type: AiArtifactType | str | None = None,
    ) -> AiPromptProgramArtifactRecord | None:
        return next((record for record in self.records if record.active), None)

    async def approve_artifact(
        self,
        artifact_id: str,
        *,
        approved_by: str,
        approved_at,
    ) -> AiPromptProgramArtifactRecord | None:
        return None

    async def deactivate_artifact(
        self,
        artifact_id: str,
    ) -> AiPromptProgramArtifactRecord | None:
        return None


@dataclass(slots=True)
class FakeDspyProvider:
    requests: list[DspyOptimizationProviderRequest]

    async def optimize(
        self,
        request: DspyOptimizationProviderRequest,
    ) -> DspyOptimizationProviderResult:
        self.requests.append(request)
        return DspyOptimizationProviderResult(
            optimization_id=request.optimization_id,
            target_component=request.target_component,
            provider_name="dspy",
            model_name=request.model_name,
            artifact=DspyOptimizedArtifact(
                artifact_name=request.artifact_name,
                artifact_version=request.artifact_version,
                prompt_reference=(
                    f"dspy://{request.target_component}/"
                    f"{request.artifact_name}/{request.artifact_version}/abc123"
                ),
                prompt_hash="a" * 64,
                program_text="program",
            ),
            case_outputs=tuple(
                DspyOptimizedCaseOutput(
                    case_id=case.case_id,
                    actual_output=f"optimized {case.actual_output}",
                )
                for case in request.cases
            ),
            candidate_count=1,
            selected_candidate_id="candidate-1",
        )


@dataclass(slots=True)
class FakeEvaluationRunner:
    requests: list[EvaluationRunServiceRequest]
    status: EvaluationStatus = EvaluationStatus.PASSED

    async def run_evaluation(
        self,
        request: EvaluationRunServiceRequest,
    ) -> EvaluationRunServiceResult:
        self.requests.append(request)
        dataset = EvaluationDatasetReference("dataset-1", "golden", "v1")
        metric = request.metrics[0]
        return EvaluationRunServiceResult(
            run=EvaluationRun(
                run_id=request.run_id,
                target_type=request.target_type,
                status=self.status,
                evaluator_provider=request.evaluator_provider,
                evaluator_model=request.evaluator_model,
                dataset=dataset,
                case_ids=tuple(case.case_id for case in request.cases),
            ),
            metric_results=tuple(
                EvaluationMetricResult(
                    run_id=request.run_id,
                    case_id=case.case_id,
                    score=EvaluationScore(
                        metric_name=metric.metric_name,
                        score=0.93,
                        threshold=metric.threshold,
                        reason="candidate passed",
                    ),
                    status=self.status,
                    evaluator_provider=request.evaluator_provider,
                    evaluator_model=request.evaluator_model,
                    duration_ms=10.0,
                )
                for case in request.cases
            ),
            persistence_result=EvaluationPersistenceResult(
                runs_written=1,
                metric_results_written=len(request.cases),
            ),
            langfuse_projection_result=EvaluationLangfuseProjectionResult(
                export_results=(
                    AiObservabilityExportResult.exported(
                        idempotency_key="evaluation-score-1",
                        external_trace_id="langfuse-trace-1",
                        run_id=request.run_id,
                    ),
                ),
                exported_count=1,
            ),
        )


def _metric() -> EvaluationMetricSpec:
    return EvaluationMetricSpec(
        metric_name="answer_relevancy",
        threshold=EvaluationThreshold("answer_relevancy", 0.8),
    )


def _dataset() -> EvaluationDatasetRecord:
    return EvaluationDatasetRecord(
        dataset_id="dataset-1",
        name="golden",
        version="v1",
        target_type=EvaluationTargetType.RAG_GENERATION,
    )


def _case() -> EvaluationCaseRecord:
    return EvaluationCaseRecord(
        case_id="case-1",
        target_type=EvaluationTargetType.RAG_GENERATION,
        input_text="What changed in risk?",
        actual_output="Risk increased.",
        dataset_id="dataset-1",
        expected_output="Risk increased because volatility widened.",
    )


@pytest.mark.asyncio
async def test_optimization_service_scores_and_persists_draft_artifact() -> None:
    evaluation_repository = FakeEvaluationRepository(_dataset(), (_case(),))
    artifact_repository = FakeArtifactRepository([])
    provider = FakeDspyProvider([])
    runner = FakeEvaluationRunner([])
    service = AiOptimizationService(
        evaluation_repository=evaluation_repository,
        artifact_repository=artifact_repository,
        optimization_provider=provider,
        evaluation_runner=runner,
    )

    result = await service.optimize(
        AiOptimizationRequest(
            optimization_id="opt-1",
            target=AiOptimizationTarget.RAG_ANSWER_GENERATION,
            dataset_id="dataset-1",
            metrics=(_metric(),),
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
            model_name="qwen2.5:7b",
            prompt_name="rag-answer",
            prompt_version="v1",
            artifact_name="rag-answer-dspy",
            artifact_version="v1",
        )
    )

    assert result.status is AiOptimizationStatus.SUCCEEDED
    assert result.artifact_persisted is True
    assert result.artifact is not None
    assert result.artifact.artifact_type is AiArtifactType.DSPY_COMPILED_PROMPT
    assert result.artifact.approval_status is AiArtifactApprovalStatus.DRAFT
    assert result.artifact.active is False
    assert result.artifact.evaluation_run_id == "opt-1-evaluation"
    assert result.artifact.evaluation_dataset_id == "dataset-1"
    assert result.artifact.langfuse_trace_id == "langfuse-trace-1"
    assert result.artifact.deepeval_score_summary is not None
    assert result.artifact.deepeval_score_summary["average_score"] == 0.93
    assert artifact_repository.records == [result.artifact]
    assert provider.requests[0].target_component == "rag_answer_generation"
    assert runner.requests[0].target_type is EvaluationTargetType.RAG_GENERATION
    assert runner.requests[0].cases[0].actual_output == "optimized Risk increased."


@pytest.mark.asyncio
async def test_optimization_service_does_not_persist_artifact_when_evaluation_errors() -> (  # noqa: E501
    None
):
    service = AiOptimizationService(
        evaluation_repository=FakeEvaluationRepository(_dataset(), (_case(),)),
        artifact_repository=FakeArtifactRepository([]),
        optimization_provider=FakeDspyProvider([]),
        evaluation_runner=FakeEvaluationRunner([], status=EvaluationStatus.ERRORED),
    )

    result = await service.optimize(
        AiOptimizationRequest(
            optimization_id="opt-1",
            target="rag_answer_generation",
            dataset_id="dataset-1",
            metrics=(_metric(),),
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
            model_name="qwen2.5:7b",
            prompt_name="rag-answer",
            prompt_version="v1",
            artifact_name="rag-answer-dspy",
            artifact_version="v1",
        )
    )

    assert result.status is AiOptimizationStatus.FAILED
    assert result.artifact is None
