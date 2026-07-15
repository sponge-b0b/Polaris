from __future__ import annotations

from pathlib import Path
from typing import Any
from collections.abc import Callable

import pytest

from application.evaluations import canonical_evaluation_dataset_definition_by_name
from application.evaluations import intelligence_evaluation_metric_specs
from domain.evaluation import EvaluationTargetType

LoadJsonlFixture = Callable[[Path], tuple[dict[str, Any], ...]]

pytestmark = pytest.mark.eval_strategy_synthesis


def test_strategy_synthesis_dataset_is_structured_hypothesis_aware(
    evaluation_fixture_dir: Path,
    load_jsonl_fixture: LoadJsonlFixture,
) -> None:
    definition = canonical_evaluation_dataset_definition_by_name(
        "strategy_synthesis_quality"
    )
    rows = load_jsonl_fixture(
        evaluation_fixture_dir / "strategy_synthesis_quality.jsonl"
    )

    assert definition.target_type is EvaluationTargetType.STRATEGY_SYNTHESIS
    assert definition.active is True
    assert "postgres.curated_strategy_records" in definition.source_lineage
    assert rows
    assert all(
        row["target_type"] == EvaluationTargetType.STRATEGY_SYNTHESIS.value
        for row in rows
    )
    assert any(
        "perspective" in row.get("rubric", "").lower()
        or "perspective" in row.get("expected_output", "").lower()
        for row in rows
    )
    assert all("strategy" in row["tags"] for row in rows)


def test_strategy_synthesis_metrics_cover_quality_consistency_and_claim_control() -> (
    None
):
    metric_names = {
        metric.metric_name
        for metric in intelligence_evaluation_metric_specs(
            EvaluationTargetType.STRATEGY_SYNTHESIS
        )
    }

    assert {
        "strategy_synthesis_quality",
        "risk_assessment_quality",
        "portfolio_context_alignment",
        "reasoning_consistency",
        "unsupported_financial_claims",
    } <= metric_names
