from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from application.evaluations import (
    canonical_evaluation_dataset_definitions,
    rag_evaluation_metric_specs,
    rag_threshold_profile,
)
from domain.evaluation import EvaluationTargetType

LoadJsonlFixture = Callable[[Path], tuple[dict[str, Any], ...]]

pytestmark = pytest.mark.eval_rag_regression


def test_rag_datasets_have_active_fixtures_and_matching_target_types(
    evaluation_fixture_dir: Path,
    load_jsonl_fixture: LoadJsonlFixture,
) -> None:
    rag_definitions = canonical_evaluation_dataset_definitions(
        target_type=EvaluationTargetType.RAG_ANSWER
    )

    assert {definition.reference.name for definition in rag_definitions} >= {
        "golden_rag_questions",
        "rag_citation_support",
        "rag_security_prompt_injection",
    }
    for definition in rag_definitions:
        assert definition.active is True
        assert definition.deterministic_fixture_uri is not None
        fixture_path = Path(definition.deterministic_fixture_uri)
        assert fixture_path.parts[:3] == ("tests", "evaluation", "fixtures")
        rows = load_jsonl_fixture(evaluation_fixture_dir / fixture_path.name)
        assert rows
        assert all(row["target_type"] == definition.target_type.value for row in rows)


def test_rag_regression_metrics_include_builtin_grounding_and_custom_quality() -> None:
    metric_names = {metric.metric_name for metric in rag_evaluation_metric_specs()}

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
    } <= metric_names


def test_rag_threshold_profile_is_release_gate_ready() -> None:
    profile = rag_threshold_profile()

    assert profile["profile_name"] == "rag_quality"
    assert profile["score_semantics"] == "higher_is_better"
    metrics = profile["metrics"]
    assert isinstance(metrics, list)
    assert len(metrics) == len(rag_evaluation_metric_specs())
