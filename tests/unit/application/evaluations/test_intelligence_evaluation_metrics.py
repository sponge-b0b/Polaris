from __future__ import annotations

from application.evaluations import INTELLIGENCE_EVALUATION_METRIC_DEFINITIONS
from application.evaluations import INTELLIGENCE_EVALUATION_THRESHOLD_PROFILE_VERSION
from application.evaluations import EvaluationMetricEngine
from application.evaluations import intelligence_evaluation_metric_specs
from application.evaluations import intelligence_threshold_profile
from domain.evaluation import EvaluationTargetType


def test_intelligence_metric_definitions_include_required_structured_metrics() -> None:
    metric_names = {
        definition.metric_name
        for definition in INTELLIGENCE_EVALUATION_METRIC_DEFINITIONS
    }

    assert metric_names == {
        "strategy_synthesis_quality",
        "recommendation_rationale_quality",
        "report_completeness",
        "risk_assessment_quality",
        "portfolio_context_alignment",
        "reasoning_consistency",
        "unsupported_financial_claims",
    }


def test_intelligence_metrics_use_geval_rubrics_and_versioned_thresholds() -> None:
    for definition in INTELLIGENCE_EVALUATION_METRIC_DEFINITIONS:
        assert definition.engine is EvaluationMetricEngine.DEEPEVAL_GEVAL
        assert definition.criteria is not None
        assert definition.evaluation_steps
        assert (
            definition.threshold.version
            == INTELLIGENCE_EVALUATION_THRESHOLD_PROFILE_VERSION
        )
        assert not any(
            target.value.startswith("rag_") for target in definition.target_types
        )


def test_intelligence_metric_specs_can_be_filtered_by_structured_target_type() -> None:
    strategy_specs = intelligence_evaluation_metric_specs(
        EvaluationTargetType.STRATEGY_SYNTHESIS,
    )
    recommendation_specs = intelligence_evaluation_metric_specs(
        EvaluationTargetType.RECOMMENDATION_EXPLANATION,
    )
    report_specs = intelligence_evaluation_metric_specs(
        EvaluationTargetType.MORNING_REPORT,
    )

    assert {spec.metric_name for spec in strategy_specs} == {
        "strategy_synthesis_quality",
        "risk_assessment_quality",
        "portfolio_context_alignment",
        "reasoning_consistency",
        "unsupported_financial_claims",
    }
    assert {spec.metric_name for spec in recommendation_specs} == {
        "recommendation_rationale_quality",
        "risk_assessment_quality",
        "portfolio_context_alignment",
        "reasoning_consistency",
        "unsupported_financial_claims",
    }
    assert {spec.metric_name for spec in report_specs} == {
        "report_completeness",
        "risk_assessment_quality",
        "portfolio_context_alignment",
        "unsupported_financial_claims",
    }


def test_intelligence_metric_specs_preserve_custom_rubrics() -> None:
    specs = intelligence_evaluation_metric_specs()
    by_name = {spec.metric_name: spec for spec in specs}

    assert by_name["strategy_synthesis_quality"].threshold is not None
    assert (
        by_name["strategy_synthesis_quality"].threshold.version
        == INTELLIGENCE_EVALUATION_THRESHOLD_PROFILE_VERSION
    )
    assert by_name["strategy_synthesis_quality"].criteria is not None
    assert by_name["strategy_synthesis_quality"].evaluation_steps
    assert by_name["unsupported_financial_claims"].threshold is not None
    assert by_name["unsupported_financial_claims"].threshold.minimum_score == 0.85


def test_intelligence_threshold_profile_is_persistence_ready_and_versioned() -> None:
    profile = intelligence_threshold_profile()

    assert profile["profile_name"] == "intelligence_quality"
    assert (
        profile["profile_version"] == INTELLIGENCE_EVALUATION_THRESHOLD_PROFILE_VERSION
    )
    assert profile["score_semantics"] == "higher_is_better"
    metrics = profile["metrics"]
    assert isinstance(metrics, list)
    assert len(metrics) == len(INTELLIGENCE_EVALUATION_METRIC_DEFINITIONS)
    assert all(
        metric["threshold_version"] == INTELLIGENCE_EVALUATION_THRESHOLD_PROFILE_VERSION
        for metric in metrics
    )
