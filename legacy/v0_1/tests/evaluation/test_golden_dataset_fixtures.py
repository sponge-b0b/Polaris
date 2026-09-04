from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from application.evaluations import (
    MODEL_REGRESSION_REQUIRED_COVERAGE_TAGS,
    canonical_evaluation_dataset_definition_by_name,
    canonical_evaluation_dataset_definitions,
    canonical_evaluation_dataset_slice_definition_by_name,
)
from core.storage.persistence.evaluation import EvaluationCaseRecord
from domain.evaluation import EvaluationTargetType
from tests.evaluation._helpers import evaluation_case_from_row

LoadJsonlFixture = Callable[[Path], tuple[dict[str, Any], ...]]

pytestmark = pytest.mark.evaluation

EXPECTED_DATASET_COUNTS: dict[str, int] = {
    "golden_rag_questions": 25,
    "rag_citation_support": 12,
    "rag_security_prompt_injection": 13,
    "morning_report_quality": 15,
    "strategy_synthesis_quality": 15,
    "recommendation_explanations": 12,
    "mcp_tool_responses": 4,
    "agent_task_completion": 4,
}
EXPECTED_TOTAL_CASES = 100
WORKFLOW_DERIVED_DATASETS = {
    "morning_report_quality",
    "strategy_synthesis_quality",
    "recommendation_explanations",
}


def test_golden_fixture_inventory_matches_canonical_dataset_definitions(
    evaluation_fixture_dir: Path,
    load_jsonl_fixture: LoadJsonlFixture,
) -> None:
    definitions = canonical_evaluation_dataset_definitions()
    seen_case_ids: set[str] = set()
    total_cases = 0

    assert {definition.reference.name for definition in definitions} == set(
        EXPECTED_DATASET_COUNTS
    )

    for definition in definitions:
        fixture_uri = definition.deterministic_fixture_uri
        assert fixture_uri is not None
        fixture_path = evaluation_fixture_dir / Path(fixture_uri).name
        rows = load_jsonl_fixture(fixture_path)

        assert len(rows) == EXPECTED_DATASET_COUNTS[definition.reference.name]
        total_cases += len(rows)

        for row in rows:
            case = evaluation_case_from_row(row, dataset=definition.reference)
            assert case.case_id not in seen_case_ids
            seen_case_ids.add(case.case_id)
            assert case.dataset == definition.reference
            assert case.target_type is definition.target_type
            assert case.expected_output is not None or case.rubric is not None
            assert case.source_record_ids
            assert case.retrieval_context

            record = EvaluationCaseRecord.from_domain(case)
            assert record.case_id == case.case_id
            assert record.dataset_id == definition.reference.dataset_id
            assert record.source_record_ids == case.source_record_ids
            assert record.workflow_execution_id == case.workflow_execution_id
            assert record.langfuse_trace_id == case.langfuse_trace_id
            assert record.langfuse_observation_id == case.langfuse_observation_id
            assert record.retrieval_context == case.retrieval_context
            assert record.citation_context_ids == case.citation_context_ids

    assert total_cases == EXPECTED_TOTAL_CASES
    assert len(seen_case_ids) == EXPECTED_TOTAL_CASES


def test_model_regression_slice_is_fixture_backed_and_preserves_active_membership(
    evaluation_fixture_dir: Path,
    load_jsonl_fixture: LoadJsonlFixture,
) -> None:
    model_regression = canonical_evaluation_dataset_slice_definition_by_name(
        "model_regression"
    )
    seen_case_ids: set[str] = set()
    seen_coverage_tags: set[str] = set()

    assert 20 <= model_regression.case_count <= 30

    for membership in model_regression.memberships:
        definition = canonical_evaluation_dataset_definition_by_name(
            membership.dataset_name
        )
        fixture_uri = definition.deterministic_fixture_uri
        assert fixture_uri is not None
        rows = load_jsonl_fixture(evaluation_fixture_dir / Path(fixture_uri).name)
        rows_by_case_id = {str(row["case_id"]): row for row in rows}

        assert set(membership.case_ids) <= set(rows_by_case_id)
        for case_id in membership.case_ids:
            row = rows_by_case_id[case_id]
            case = evaluation_case_from_row(row, dataset=definition.reference)
            seen_case_ids.add(case.case_id)
            seen_coverage_tags.update(str(tag) for tag in row["tags"])

            assert "model_regression" in row["tags"]
            assert case.dataset == definition.reference
            assert case.target_type is definition.target_type

    assert len(seen_case_ids) == model_regression.case_count
    assert set(model_regression.case_ids) == seen_case_ids
    assert set(MODEL_REGRESSION_REQUIRED_COVERAGE_TAGS) <= seen_coverage_tags


def test_citation_and_security_fixtures_include_required_golden_metadata(
    evaluation_fixture_dir: Path,
    load_jsonl_fixture: LoadJsonlFixture,
) -> None:
    citation_rows = load_jsonl_fixture(
        evaluation_fixture_dir / "rag_citation_support.jsonl"
    )
    security_rows = load_jsonl_fixture(
        evaluation_fixture_dir / "rag_security_prompt_injection.jsonl"
    )

    assert citation_rows
    assert all(row["citation_context_ids"] for row in citation_rows)
    assert all(row["retrieval_context"] for row in citation_rows)
    assert all("citations" in row["tags"] for row in citation_rows)

    assert security_rows
    assert all("prompt_injection" in row["tags"] for row in security_rows)
    assert all(row["retrieval_context"] for row in security_rows)
    assert any("ignore" in row["input_text"].lower() for row in security_rows)
    assert any("bypass" in row["input_text"].lower() for row in security_rows)


def test_workflow_derived_fixtures_include_workflow_execution_ids(
    evaluation_fixture_dir: Path,
    load_jsonl_fixture: LoadJsonlFixture,
) -> None:
    definitions = canonical_evaluation_dataset_definitions()

    for definition in definitions:
        if definition.reference.name not in WORKFLOW_DERIVED_DATASETS:
            continue
        fixture_uri = definition.deterministic_fixture_uri
        assert fixture_uri is not None
        rows = load_jsonl_fixture(evaluation_fixture_dir / Path(fixture_uri).name)
        assert rows
        assert all(row["workflow_execution_id"] for row in rows)


def test_evaluation_case_from_row_preserves_supported_durable_metadata() -> None:
    row: dict[str, object] = {
        "case_id": "metadata-preservation-001",
        "target_type": EvaluationTargetType.RAG_ANSWER.value,
        "input_text": "Explain the risk posture using only cited context.",
        "actual_output": (
            "The risk posture is defensive because drawdown risk is elevated."
        ),
        "expected_output": "Use cited context and preserve the defensive risk posture.",
        "source_record_ids": ["curated-risk-record-001"],
        "workflow_execution_id": "workflow-eval-001",
        "langfuse_trace_id": "trace-eval-001",
        "langfuse_observation_id": "observation-eval-001",
        "retrieval_context": ["Risk posture: defensive."],
        "citation_context_ids": ["risk-context-001"],
        "tags": ["rag", "metadata"],
    }

    case = evaluation_case_from_row(row)
    record = EvaluationCaseRecord.from_domain(case)

    assert case.source_record_ids == ("curated-risk-record-001",)
    assert case.workflow_execution_id == "workflow-eval-001"
    assert case.langfuse_trace_id == "trace-eval-001"
    assert case.langfuse_observation_id == "observation-eval-001"
    assert record.source_record_ids == case.source_record_ids
    assert record.workflow_execution_id == case.workflow_execution_id
    assert record.langfuse_trace_id == case.langfuse_trace_id
    assert record.langfuse_observation_id == case.langfuse_observation_id
