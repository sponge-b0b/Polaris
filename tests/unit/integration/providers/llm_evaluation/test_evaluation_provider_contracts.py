from __future__ import annotations

import pytest

from domain.evaluation import EvaluationCase
from domain.evaluation import EvaluationStatus
from domain.evaluation import EvaluationTargetType
from domain.evaluation import EvaluationThreshold
from integration.providers.llm_evaluation import EvaluationMetricSpec
from integration.providers.llm_evaluation import EvaluationProviderRequest
from integration.providers.llm_evaluation import EvaluationProviderResult


def test_metric_spec_requires_matching_threshold_metric() -> None:
    with pytest.raises(ValueError, match="threshold metric_name"):
        EvaluationMetricSpec(
            metric_name="faithfulness",
            threshold=EvaluationThreshold(
                metric_name="answer_relevancy",
                minimum_score=0.7,
            ),
        )


def test_provider_request_requires_cases_and_metrics() -> None:
    case = _case("case-1")
    metric = EvaluationMetricSpec(metric_name="faithfulness")

    with pytest.raises(ValueError, match="run_id"):
        EvaluationProviderRequest(run_id=" ", cases=(case,), metrics=(metric,))
    with pytest.raises(ValueError, match="cases"):
        EvaluationProviderRequest(run_id="run-1", cases=(), metrics=(metric,))
    with pytest.raises(ValueError, match="metrics"):
        EvaluationProviderRequest(run_id="run-1", cases=(case,), metrics=())
    with pytest.raises(ValueError, match="timeout_seconds"):
        EvaluationProviderRequest(
            run_id="run-1",
            cases=(case,),
            metrics=(metric,),
            timeout_seconds=0.0,
        )


def test_provider_result_validates_duration() -> None:
    with pytest.raises(ValueError, match="duration_ms"):
        EvaluationProviderResult(
            run_id="run-1",
            status=EvaluationStatus.PASSED,
            metric_results=(),
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
            duration_ms=-1.0,
        )


def _case(case_id: str) -> EvaluationCase:
    return EvaluationCase(
        case_id=case_id,
        target_type=EvaluationTargetType.RAG_ANSWER,
        input_text="What happened?",
        actual_output="Risk was reduced.",
        rubric="Answer should be grounded.",
    )
