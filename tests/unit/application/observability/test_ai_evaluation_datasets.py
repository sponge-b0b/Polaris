from __future__ import annotations

import pytest

from application.observability import (
    AiEvaluationDatasetBuildService,
    AiEvaluationDatasetKind,
    AiObservationType,
    AiScoreResult,
)


def test_build_service_creates_canonical_regression_dataset_cases() -> None:
    service = AiEvaluationDatasetBuildService()

    dataset = service.build_default_regression_dataset()

    assert dataset.dataset_id == "polaris-regression-ai-evaluation-v1"
    assert len(dataset.cases) == 5
    assert {case.kind for case in dataset.cases} == {
        AiEvaluationDatasetKind.RAG_ANSWER_QUALITY,
        AiEvaluationDatasetKind.RAG_CITATION_GROUNDEDNESS,
        AiEvaluationDatasetKind.REPORT_QA,
        AiEvaluationDatasetKind.STRATEGY_RATIONALE,
        AiEvaluationDatasetKind.PROMPT_INJECTION_RESISTANCE,
    }
    assert all(case.evaluation_criteria for case in dataset.cases)


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.91, AiScoreResult.PASS),
        (0.65, AiScoreResult.WARN),
        (0.25, AiScoreResult.FAIL),
    ],
)
def test_build_service_maps_quality_scores_to_results(
    score: float,
    expected: AiScoreResult,
) -> None:
    service = AiEvaluationDatasetBuildService()

    result = service.score(
        metric_name="faithfulness",
        score=score,
        threshold=0.8,
        warn_threshold=0.5,
        reason="deterministic evaluation reason",
    )

    assert result.result is expected
    assert result.threshold == 0.8
    assert result.evaluator_provider == "deepeval"


def test_build_service_projects_case_scores_to_evaluation_observation() -> None:
    service = AiEvaluationDatasetBuildService()
    case = service.build_default_regression_dataset().cases[0]
    score = service.score(metric_name="faithfulness", score=0.91)

    observation = service.observation_for_case(
        case=case,
        run_id="run-1",
        observation_type=AiObservationType.RAG_ANSWER_QUALITY,
        name="answer_quality_eval",
        scores=(score,),
        trace_id="trace-1",
        evaluated_observation_id="generation-1",
    )

    assert observation.correlation_ids.dataset_id == case.dataset_id
    assert observation.correlation_ids.case_id == case.case_id
    assert observation.correlation_ids.run_id == "run-1"
    assert observation.evaluated_observation_id == "generation-1"
    assert observation.scores == (score,)
    assert observation.metadata["dataset_kind"] == case.kind.value
