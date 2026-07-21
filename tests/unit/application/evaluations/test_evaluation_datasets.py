from __future__ import annotations

import pytest

from application.evaluations import (
    EVALUATION_DATASET_VERSION,
    MODEL_REGRESSION_REQUIRED_COVERAGE_TAGS,
    canonical_evaluation_dataset_definition_by_name,
    canonical_evaluation_dataset_definitions,
    canonical_evaluation_dataset_registration_requests,
    canonical_evaluation_dataset_slice_definition_by_name,
    canonical_evaluation_dataset_slice_definitions,
)
from domain.evaluation import EvaluationTargetType

EXPECTED_DATASET_NAMES = {
    "golden_rag_questions",
    "rag_citation_support",
    "rag_security_prompt_injection",
    "morning_report_quality",
    "strategy_synthesis_quality",
    "recommendation_explanations",
    "mcp_tool_responses",
    "agent_task_completion",
}


def test_canonical_evaluation_dataset_definitions_cover_required_datasets() -> None:
    definitions = canonical_evaluation_dataset_definitions()
    names = {definition.reference.name for definition in definitions}
    ids = {definition.reference.dataset_id for definition in definitions}

    assert names == EXPECTED_DATASET_NAMES
    assert len(ids) == len(EXPECTED_DATASET_NAMES)
    assert all(
        definition.reference.version == EVALUATION_DATASET_VERSION
        for definition in definitions
    )
    assert all(definition.reference.tags for definition in definitions)
    assert all(definition.source_lineage for definition in definitions)
    assert all(definition.deterministic_fixture_uri for definition in definitions)


def test_canonical_model_regression_slice_is_named_and_bounded() -> None:
    slices = canonical_evaluation_dataset_slice_definitions()
    slice_by_name = {
        slice_definition.name: slice_definition for slice_definition in slices
    }

    assert set(slice_by_name) == {"model_regression"}

    model_regression = slice_by_name["model_regression"]
    assert 20 <= model_regression.case_count <= 30
    assert model_regression.tags == ("model_regression", "golden", "model_gate")
    assert set(MODEL_REGRESSION_REQUIRED_COVERAGE_TAGS) <= set(
        model_regression.coverage_tags
    )
    assert set(model_regression.dataset_names) <= EXPECTED_DATASET_NAMES
    assert all(membership.case_ids for membership in model_regression.memberships)


def test_canonical_evaluation_dataset_slice_by_name_resolves_stable_name() -> None:
    model_regression = canonical_evaluation_dataset_slice_definition_by_name(
        "model_regression"
    )

    assert model_regression.name == "model_regression"
    assert "golden" in model_regression.description.lower()

    with pytest.raises(KeyError):
        canonical_evaluation_dataset_slice_definition_by_name("missing_slice")

    with pytest.raises(ValueError, match="name cannot be empty"):
        canonical_evaluation_dataset_slice_definition_by_name(" ")


def test_canonical_evaluation_dataset_registration_requests_preserve_fields() -> None:
    requests = canonical_evaluation_dataset_registration_requests()
    request_by_name = {request.reference.name: request for request in requests}

    rag_request = request_by_name["golden_rag_questions"]
    assert rag_request.target_type is EvaluationTargetType.RAG_ANSWER
    assert rag_request.threshold_profile is not None
    assert rag_request.source_lineage == (
        "postgres.rag_documents",
        "postgres.rag_chunks",
        "postgres.completed_workflow_runs",
    )
    assert rag_request.deterministic_fixture_uri == (
        "tests/evaluation/fixtures/golden_rag_questions.jsonl"
    )
    assert rag_request.active is True


def test_canonical_evaluation_dataset_definitions_filter_by_target_type() -> None:
    rag_definitions = canonical_evaluation_dataset_definitions(
        target_type=EvaluationTargetType.RAG_ANSWER,
    )

    assert {definition.reference.name for definition in rag_definitions} == {
        "golden_rag_questions",
        "rag_citation_support",
        "rag_security_prompt_injection",
    }


def test_canonical_evaluation_dataset_definition_by_name_resolves_stable_name() -> None:
    definition = canonical_evaluation_dataset_definition_by_name(
        "strategy_synthesis_quality",
    )

    assert definition.target_type is EvaluationTargetType.STRATEGY_SYNTHESIS
    assert definition.reference.dataset_id == "strategy_synthesis_quality_v1"


def test_canonical_evaluation_dataset_definition_by_name_rejects_unknown_name() -> None:
    with pytest.raises(KeyError):
        canonical_evaluation_dataset_definition_by_name("missing_dataset")

    with pytest.raises(ValueError, match="name cannot be empty"):
        canonical_evaluation_dataset_definition_by_name(" ")
