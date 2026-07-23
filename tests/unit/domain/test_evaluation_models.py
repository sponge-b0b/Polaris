from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

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


def test_evaluation_case_preserves_canonical_identifiers_and_context() -> None:
    dataset = EvaluationDatasetReference(
        dataset_id="golden-rag-v1",
        name="golden_rag_questions",
        version="2026-07-14",
        tags=(" rag ", "quality"),
    )

    case = EvaluationCase(
        case_id="case-1",
        target_type=EvaluationTargetType.RAG_ANSWER,
        input_text="What changed in the portfolio?",
        actual_output="The portfolio reduced risk exposure.",
        dataset=dataset,
        rubric="Answer must cite retrieved context and avoid unsupported claims.",
        source_record_ids=("report:123", " ", "recommendation:456"),
        workflow_execution_id="execution-1",
        langfuse_trace_id="trace-1",
        langfuse_observation_id="observation-1",
        retrieval_context=("chunk-a", "chunk-b"),
        citation_context_ids=("chunk-a",),
        tags=("morning_report", "rag"),
        created_at=datetime(2026, 7, 14, 12, 0, 0),
    )

    assert case.dataset == dataset
    assert case.source_record_ids == ("report:123", "recommendation:456")
    assert case.created_at.tzinfo is UTC
    assert case.to_dict()["target_type"] == "rag_answer"
    assert case.to_dict()["dataset"] == dataset.to_dict()


def test_evaluation_case_requires_expected_output_or_rubric() -> None:
    with pytest.raises(ValueError, match="expected_output or rubric"):
        EvaluationCase(
            case_id="case-1",
            target_type=EvaluationTargetType.RAG_ANSWER,
            input_text="question",
            actual_output="answer",
        )


def test_evaluation_threshold_and_score_compute_pass_fail() -> None:
    threshold = EvaluationThreshold(
        metric_name="faithfulness",
        minimum_score=0.8,
        version="v2",
    )

    passing = EvaluationScore(
        metric_name="faithfulness",
        score=0.85,
        threshold=threshold,
        reason="Grounded in retrieved context.",
    )
    failing = EvaluationScore(
        metric_name="faithfulness",
        score=0.5,
        threshold=threshold,
    )

    assert threshold.passes(0.8) is True
    assert passing.passed is True
    assert failing.passed is False
    assert passing.to_dict()["threshold"] == threshold.to_dict()


def test_evaluation_score_rejects_mismatched_threshold_metric() -> None:
    threshold = EvaluationThreshold(metric_name="faithfulness", minimum_score=0.8)

    with pytest.raises(ValueError, match="threshold metric_name"):
        EvaluationScore(
            metric_name="answer_relevancy",
            score=0.9,
            threshold=threshold,
        )


def test_evaluation_run_and_metric_result_are_serializable() -> None:
    dataset = EvaluationDatasetReference(
        dataset_id="strategy-v1",
        name="strategy_synthesis_quality",
        version="v1",
    )
    run = EvaluationRun(
        run_id="run-1",
        target_type=EvaluationTargetType.STRATEGY_SYNTHESIS,
        status=EvaluationStatus.RUNNING,
        evaluator_provider="deepeval",
        evaluator_model="qwen3.5:4b",
        dataset=dataset,
        case_ids=("case-1", "case-2"),
    )
    result = EvaluationMetricResult(
        run_id=run.run_id,
        case_id="case-1",
        score=EvaluationScore(
            metric_name="strategy_synthesis_quality",
            score=0.91,
            threshold=EvaluationThreshold(
                metric_name="strategy_synthesis_quality",
                minimum_score=0.75,
            ),
        ),
        status=EvaluationStatus.PASSED,
        evaluator_provider="deepeval",
        evaluator_model="qwen3.5:4b",
        duration_ms=125.5,
    )

    assert run.to_dict()["dataset"] == dataset.to_dict()
    assert run.to_dict()["status"] == "running"
    assert result.passed is True
    assert result.to_dict()["metric_name"] == "strategy_synthesis_quality"
    assert result.to_dict()["duration_ms"] == 125.5


def test_evaluation_models_are_immutable() -> None:
    dataset = EvaluationDatasetReference(
        dataset_id="dataset-1",
        name="dataset",
        version="v1",
    )

    with pytest.raises(FrozenInstanceError):
        field_name = "name"
        setattr(dataset, field_name, "replacement")


def test_score_bounds_are_validated() -> None:
    with pytest.raises(ValueError, match="score"):
        EvaluationScore(metric_name="faithfulness", score=1.1)
    with pytest.raises(ValueError, match="minimum_score"):
        EvaluationThreshold(metric_name="faithfulness", minimum_score=-0.1)
