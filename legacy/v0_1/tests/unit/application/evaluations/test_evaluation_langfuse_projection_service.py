from __future__ import annotations

from dataclasses import dataclass

import pytest

from application.evaluations import (
    EvaluationLangfuseProjectionRequest,
    EvaluationLangfuseProjectionService,
)
from application.observability.ai_observability_contracts import (
    AiEvaluationObservation,
    AiObservabilityExportResult,
    AiObservabilityExportStatus,
)
from core.storage.persistence.evaluation import (
    EvaluationCaseRecord,
    EvaluationMetricResultRecord,
    EvaluationRunRecord,
)
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


@dataclass(slots=True)
class FakeProjector:
    observations: list[AiEvaluationObservation]
    fail: bool = False

    async def project(
        self,
        observation: AiEvaluationObservation,
    ) -> AiObservabilityExportResult:
        self.observations.append(observation)
        if self.fail:
            raise RuntimeError("langfuse unavailable")
        return AiObservabilityExportResult(
            status=AiObservabilityExportStatus.PENDING,
            idempotency_key=observation.idempotency_key(),
            observation_id=observation.correlation_ids.observation_id,
            dataset_id=observation.correlation_ids.dataset_id,
            case_id=observation.correlation_ids.case_id,
            run_id=observation.correlation_ids.run_id,
        )


def _run_record() -> EvaluationRunRecord:
    return EvaluationRunRecord.from_domain(
        EvaluationRun(
            run_id="run-1",
            target_type=EvaluationTargetType.RAG_ANSWER,
            status=EvaluationStatus.PASSED,
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
            dataset=EvaluationDatasetReference("dataset-1", "golden", "v1"),
            case_ids=("case-1",),
        )
    )


def _case_record() -> EvaluationCaseRecord:
    return EvaluationCaseRecord.from_domain(
        EvaluationCase(
            case_id="case-1",
            target_type=EvaluationTargetType.RAG_ANSWER,
            input_text="Question?",
            actual_output="Answer.",
            dataset=EvaluationDatasetReference("dataset-1", "golden", "v1"),
            rubric="Answer must be grounded.",
            langfuse_trace_id="trace-1",
            langfuse_observation_id="observation-1",
        )
    )


def _metric_record() -> EvaluationMetricResultRecord:
    return EvaluationMetricResultRecord.from_domain(
        EvaluationMetricResult(
            run_id="run-1",
            case_id="case-1",
            score=EvaluationScore(
                metric_name="faithfulness",
                score=0.92,
                threshold=EvaluationThreshold("faithfulness", 0.8),
                reason="grounded",
            ),
            status=EvaluationStatus.PASSED,
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
            duration_ms=10.0,
        )
    )


@pytest.mark.asyncio
async def test_projection_service_projects_case_scores_to_langfuse() -> None:
    projector = FakeProjector([])
    service = EvaluationLangfuseProjectionService(projector)

    result = await service.project_run_scores(
        EvaluationLangfuseProjectionRequest(
            run=_run_record(),
            metric_results=(_metric_record(),),
            cases=(_case_record(),),
        )
    )

    assert result.pending_count == 1
    assert result.accepted_count == 1
    observation = projector.observations[0]
    assert observation.correlation_ids.trace_id == "trace-1"
    assert observation.correlation_ids.parent_observation_id == "observation-1"
    assert observation.correlation_ids.dataset_id == "dataset-1"
    assert observation.correlation_ids.case_id == "case-1"
    assert observation.correlation_ids.run_id == "run-1"
    assert observation.evaluated_observation_id == "observation-1"
    score = observation.scores[0]
    assert score.metric_name == "faithfulness"
    assert score.score == 0.92
    assert score.threshold == 0.8
    assert score.reason == "grounded"
    assert score.evaluator_model == "qwen3.5:4b"
    assert score.evaluator_provider == "deepeval"
    assert score.result.value == "pass"


@pytest.mark.asyncio
async def test_projection_service_reports_projector_failures_without_raising() -> None:
    projector = FakeProjector([], fail=True)
    service = EvaluationLangfuseProjectionService(projector)

    result = await service.project_run_scores(
        EvaluationLangfuseProjectionRequest(
            run=_run_record(),
            metric_results=(_metric_record(),),
            cases=(_case_record(),),
        )
    )

    assert result.failed_count == 1
    assert result.export_results[0].status is AiObservabilityExportStatus.FAILED
    assert projector.observations


@pytest.mark.asyncio
async def test_projection_service_uses_stable_idempotency_keys_for_retries() -> None:
    request = EvaluationLangfuseProjectionRequest(
        run=_run_record(),
        metric_results=(_metric_record(),),
        cases=(_case_record(),),
    )
    first_projector = FakeProjector([])
    second_projector = FakeProjector([])

    first_result = await EvaluationLangfuseProjectionService(
        first_projector
    ).project_run_scores(request)
    second_result = await EvaluationLangfuseProjectionService(
        second_projector
    ).project_run_scores(request)

    assert first_result.export_results[0].idempotency_key == (
        second_result.export_results[0].idempotency_key
    )
    assert first_projector.observations[0].idempotency_key() == (
        second_projector.observations[0].idempotency_key()
    )
