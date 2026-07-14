from __future__ import annotations

from pathlib import Path
from typing import Any
from collections.abc import Callable

import pytest

from application.evaluations import RAG_CUSTOM_METRIC_DEFINITIONS

LoadJsonlFixture = Callable[[Path], tuple[dict[str, Any], ...]]

pytestmark = pytest.mark.eval_prompt_regression


def test_prompt_injection_fixture_declares_expected_refusal_behavior(
    evaluation_fixture_dir: Path,
    load_jsonl_fixture: LoadJsonlFixture,
) -> None:
    rows = load_jsonl_fixture(
        evaluation_fixture_dir / "rag_security_prompt_injection.jsonl"
    )

    assert len(rows) == 1
    row = rows[0]
    assert "Ignore prior instructions" in row["input_text"]
    assert "refuse" in row["expected_output"].lower()
    assert "prompt_injection" in row["tags"]
    assert row["retrieval_context"]


def test_prompt_regression_metric_uses_explicit_geval_rubric() -> None:
    metric = next(
        definition
        for definition in RAG_CUSTOM_METRIC_DEFINITIONS
        if definition.metric_name == "prompt_injection_resistance"
    )

    assert metric.criteria is not None
    assert "prompt-injection" in metric.criteria
    assert len(metric.evaluation_steps) >= 3
    assert "security" in metric.tags
