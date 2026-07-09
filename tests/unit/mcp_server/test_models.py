"""Tests for the typed Polaris MCP tool boundary contracts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from mcp_server.contracts.models import CompletedRunGetRequest, CompletedRunSection
from mcp_server.contracts.models import (
    RagAskRequest,
    TOOL_INPUT_MODELS,
    TOOL_OUTPUT_MODELS,
)
from mcp_server.contracts.models import WorkflowDescribeResponse

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
    assert request.as_of_start == datetime(2026, 7, 1, tzinfo=timezone.utc)
    assert request.as_of_end == datetime(2026, 7, 8, tzinfo=timezone.utc)
    assert request.top_k == 8
    assert request.allow_web is False
    assert request.include_contexts is False


def test_rag_ask_rejects_reversed_time_window() -> None:
    with pytest.raises(ValidationError, match="as_of_start cannot be after"):
        RagAskRequest(
            query="market outlook",
            as_of_start=datetime(2026, 7, 8, tzinfo=timezone.utc),
            as_of_end=datetime(2026, 7, 1, tzinfo=timezone.utc),
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


def test_boundary_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RagAskRequest.model_validate(
            {
                "query": "market outlook",
                "route": "vector_only",
            },
        )
