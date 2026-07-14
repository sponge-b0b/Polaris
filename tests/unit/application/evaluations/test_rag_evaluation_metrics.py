from __future__ import annotations

import pytest

from application.evaluations import EvaluationMetricDefinition
from application.evaluations import EvaluationMetricEngine
from application.evaluations import RAG_BUILTIN_METRIC_DEFINITIONS
from application.evaluations import RAG_CUSTOM_METRIC_DEFINITIONS
from application.evaluations import RAG_EVALUATION_METRIC_DEFINITIONS
from application.evaluations import RAG_EVALUATION_THRESHOLD_PROFILE_VERSION
from application.evaluations import rag_evaluation_metric_specs
from application.evaluations import rag_threshold_profile
from domain.evaluation import EvaluationTargetType
from domain.evaluation import EvaluationThreshold


def test_rag_metric_definitions_include_required_builtin_and_custom_metrics() -> None:
    metric_names = {
        definition.metric_name for definition in RAG_EVALUATION_METRIC_DEFINITIONS
    }

    assert {
        "faithfulness",
        "answer_relevancy",
        "contextual_relevancy",
        "contextual_precision",
        "contextual_recall",
        "hallucination",
        "citation_support",
        "financial_answer_quality",
        "risk_explanation_quality",
        "unsupported_claim_penalty",
        "refusal_correctness",
        "prompt_injection_resistance",
    }.issubset(metric_names)


def test_rag_builtin_thresholds_match_initial_quality_policy() -> None:
    thresholds = {
        definition.metric_name: definition.threshold.minimum_score
        for definition in RAG_BUILTIN_METRIC_DEFINITIONS
    }

    assert thresholds["faithfulness"] == 0.80
    assert thresholds["answer_relevancy"] == 0.75
    assert thresholds["contextual_relevancy"] == 0.70
    assert thresholds["contextual_precision"] == 0.70
    assert thresholds["contextual_recall"] == 0.70
    assert thresholds["hallucination"] == 0.85


def test_rag_custom_metrics_use_geval_rubrics() -> None:
    assert RAG_CUSTOM_METRIC_DEFINITIONS
    for definition in RAG_CUSTOM_METRIC_DEFINITIONS:
        assert definition.engine is EvaluationMetricEngine.DEEPEVAL_GEVAL
        assert definition.criteria is not None
        assert definition.evaluation_steps
        assert definition.threshold.version == RAG_EVALUATION_THRESHOLD_PROFILE_VERSION


def test_rag_metric_specs_preserve_threshold_versions_and_custom_rubrics() -> None:
    specs = rag_evaluation_metric_specs()
    by_name = {spec.metric_name: spec for spec in specs}

    assert by_name["citation_support"].threshold is not None
    assert (
        by_name["citation_support"].threshold.version
        == RAG_EVALUATION_THRESHOLD_PROFILE_VERSION
    )
    assert by_name["citation_support"].criteria is not None
    assert by_name["citation_support"].evaluation_steps
    assert by_name["faithfulness"].criteria is None


def test_rag_threshold_profile_is_persistence_ready_and_versioned() -> None:
    profile = rag_threshold_profile()

    assert profile["profile_name"] == "rag_quality"
    assert profile["profile_version"] == RAG_EVALUATION_THRESHOLD_PROFILE_VERSION
    assert profile["score_semantics"] == "higher_is_better"
    metrics = profile["metrics"]
    assert isinstance(metrics, list)
    assert len(metrics) == len(RAG_EVALUATION_METRIC_DEFINITIONS)
    assert all(
        metric["threshold_version"] == RAG_EVALUATION_THRESHOLD_PROFILE_VERSION
        for metric in metrics
    )


def test_geval_metric_definition_requires_rubric_details() -> None:
    with pytest.raises(ValueError, match="G-Eval"):
        EvaluationMetricDefinition(
            metric_name="custom_metric",
            display_name="Custom Metric",
            engine=EvaluationMetricEngine.DEEPEVAL_GEVAL,
            threshold=EvaluationThreshold("custom_metric", 0.8),
            target_types=(EvaluationTargetType.RAG_ANSWER,),
            description="Custom metric.",
        )
