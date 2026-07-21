"""Tests for the typed Polaris MCP tool boundary contracts."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from mcp_server.contracts.models import (
    TOOL_INPUT_MODELS,
    TOOL_OUTPUT_MODELS,
    CompletedRunGetRequest,
    CompletedRunSection,
    McpError,
    RagAskRequest,
    RagAskResponse,
    RagCitation,
    RagRetrievedContext,
    WorkflowDescribeResponse,
)

_SCHEMA_SNAPSHOT = Path(__file__).parent / "snapshots" / "tool_input_schemas.json"
_EXPECTED_TOOLS = {
    "polaris_completed_run_get",
    "polaris_completed_runs_list",
    "polaris_rag_ask",
    "polaris_rag_status",
    "polaris_workflow_describe",
    "polaris_workflows_list",
}


def test_tool_catalog_has_exactly_six_typed_input_and_output_contracts() -> None:
    assert set(TOOL_INPUT_MODELS) == _EXPECTED_TOOLS
    assert set(TOOL_OUTPUT_MODELS) == _EXPECTED_TOOLS


def test_tool_input_json_schemas_match_snapshot() -> None:
    expected = json.loads(_SCHEMA_SNAPSHOT.read_text(encoding="utf-8"))
    actual = {
        tool_name: model.model_json_schema()
        for tool_name, model in sorted(TOOL_INPUT_MODELS.items())
    }

    assert actual == expected


def test_rag_ask_parses_iso_datetimes_and_preserves_full_query() -> None:
    query = "Explain every material portfolio risk without truncating the answer."
    request = RagAskRequest.model_validate(
        {
            "query": query,
            "as_of_start": "2026-07-01T00:00:00Z",
            "as_of_end": "2026-07-08T00:00:00Z",
        },
    )

    assert request.query == query
    assert request.as_of_start == datetime(2026, 7, 1, tzinfo=UTC)
    assert request.as_of_end == datetime(2026, 7, 8, tzinfo=UTC)
    assert request.top_k == 8
    assert request.allow_web is False
    assert request.include_contexts is False


def test_rag_ask_rejects_reversed_time_window() -> None:
    with pytest.raises(ValidationError, match="as_of_start cannot be after"):
        RagAskRequest(
            query="market outlook",
            as_of_start=datetime(2026, 7, 8, tzinfo=UTC),
            as_of_end=datetime(2026, 7, 1, tzinfo=UTC),
        )


def test_completed_run_node_names_require_node_outputs_section() -> None:
    with pytest.raises(ValidationError, match="node_names requires node_outputs"):
        CompletedRunGetRequest(
            workflow_name="morning_report",
            execution_id="execution-1",
            node_names=("technical_analysis",),
        )

    request = CompletedRunGetRequest(
        workflow_name="morning_report",
        execution_id="execution-1",
        include=frozenset({CompletedRunSection.NODE_OUTPUTS}),
        node_names=("technical_analysis",),
    )
    assert request.node_names == ("technical_analysis",)


def test_workflow_not_found_requires_structured_error() -> None:
    with pytest.raises(ValidationError, match="error is required"):
        WorkflowDescribeResponse(
            found=False,
            workflow_name="missing_workflow",
        )


def test_mcp_error_contract_strips_reasoning_trace_from_public_message() -> None:
    error = McpError(
        code="application_error",
        message="<think>private error reasoning</think>\nSafe failure.",
    )

    assert error.message == "Safe failure."
    assert "private error reasoning" not in error.model_dump_json()


def test_boundary_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RagAskRequest.model_validate(
            {
                "query": "market outlook",
                "route": "vector_only",
            },
        )


def test_mcp_rag_response_contract_strips_reasoning_traces_from_public_fields() -> None:
    citation = RagCitation(
        source_table="curated_rag_documents",
        source_id="doc-1",
        source_type="morning_report",
        document_id="rag-doc-1",
        title="<think>private citation reasoning</think>\nMorning Report",
        metadata={
            "symbol": "SPY",
            "chain_of_thought": "private citation metadata",
            "nested": {"scratchpad": "private nested metadata", "safe": "retained"},
        },
    )
    response = RagAskResponse(
        query_id="query-1",
        answer_text="<think>private answer reasoning</think>\nGrounded answer.",
        status="answered",
        route="hybrid",
        citations=(citation,),
        contexts=(
            RagRetrievedContext(
                context_id="context-1",
                text=(
                    "```reasoning\nprivate context reasoning\n```\nRetrieved evidence."
                ),
                source=citation,
                score=0.91,
                rank=0,
                retrieval_route="hybrid",
            ),
        ),
        corrective_actions=(
            "Chain of thought: private action reasoning.\n"
            "Final answer: Cite curated evidence.",
        ),
        error="<think>private error reasoning</think>\nSafe refusal.",
        generated_at=datetime(2026, 7, 8, tzinfo=UTC),
    )

    assert response.answer_text == "Grounded answer."
    assert response.citations[0].title == "Morning Report"
    assert response.citations[0].metadata == {
        "symbol": "SPY",
        "nested": {"safe": "retained"},
    }
    assert response.contexts is not None
    assert response.contexts[0].text == "Retrieved evidence."
    assert response.corrective_actions == ("Cite curated evidence.",)
    assert response.error == "Safe refusal."
    serialized = response.model_dump_json()
    assert "private answer reasoning" not in serialized
    assert "private citation reasoning" not in serialized
    assert "private citation metadata" not in serialized
    assert "private nested metadata" not in serialized
    assert "private context reasoning" not in serialized
    assert "private action reasoning" not in serialized
    assert "private error reasoning" not in serialized


def test_mcp_rag_response_contract_rejects_unsafe_reasoning_trace() -> None:
    with pytest.raises(ValidationError, match="mcp.rag_response.answer_text"):
        RagAskResponse(
            query_id="query-1",
            answer_text="<think>private answer reasoning without a closing tag",
            status="answered",
            route="hybrid",
            generated_at=datetime(2026, 7, 8, tzinfo=UTC),
        )
