from __future__ import annotations

import pytest

from application.evaluations import (
    RAG_CUSTOM_METRIC_DEFINITIONS,
    canonical_evaluation_dataset_definition_by_name,
)
from domain.evaluation import EvaluationTargetType

pytestmark = pytest.mark.eval_security


def test_security_dataset_is_explicitly_curated_not_ambient_metadata() -> None:
    definition = canonical_evaluation_dataset_definition_by_name(
        "rag_security_prompt_injection"
    )

    assert definition.target_type is EvaluationTargetType.RAG_ANSWER
    assert definition.active is True
    assert "external.security_fixtures" in definition.source_lineage
    assert definition.deterministic_fixture_uri == (
        "tests/evaluation/fixtures/rag_security_prompt_injection.jsonl"
    )
    assert "prompt_injection" in definition.reference.tags


def test_security_metric_targets_rag_answer_quality() -> None:
    metric = next(
        definition
        for definition in RAG_CUSTOM_METRIC_DEFINITIONS
        if definition.metric_name == "prompt_injection_resistance"
    )

    assert EvaluationTargetType.RAG_ANSWER in metric.target_types
    assert metric.threshold.minimum_score >= 0.90
    assert "policy" in " ".join(metric.evaluation_steps)
