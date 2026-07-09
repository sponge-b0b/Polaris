"""Contract tests for the exact Polaris MCP V1 tool allowlist."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest
from mcp.types import ToolAnnotations

from mcp_server.contracts.models import TOOL_INPUT_MODELS
from mcp_server.contracts.models import TOOL_OUTPUT_MODELS
from mcp_server.server import server
from mcp_server.tools.allowlist import APPROVED_MCP_TOOL_NAMES
from mcp_server.tools.allowlist import MCP_TOOL_ANNOTATION_REQUIREMENTS
from mcp_server.tools.allowlist import PROHIBITED_MCP_TOOL_NAMES
from mcp_server.tools.allowlist import PROHIBITED_MCP_TOOL_PREFIXES
from mcp_server.tools.allowlist import RegisteredMcpTool
from mcp_server.tools.allowlist import validate_registered_tool_allowlist


def _registered_tools() -> dict[str, RegisteredMcpTool]:
    return {
        tool.name: cast(RegisteredMcpTool, tool)
        for tool in server._tool_manager.list_tools()
    }


def test_server_registers_exact_v1_tool_allowlist() -> None:
    tools = _registered_tools()

    assert frozenset(tools) == APPROVED_MCP_TOOL_NAMES
    validate_registered_tool_allowlist(tools.values())


def test_server_tool_annotations_match_approved_v1_contract() -> None:
    tools = _registered_tools()

    for name, expected in MCP_TOOL_ANNOTATION_REQUIREMENTS.items():
        annotations = tools[name].annotations
        assert annotations is not None
        assert annotations.readOnlyHint is expected.read_only
        assert annotations.destructiveHint is expected.destructive
        assert annotations.idempotentHint is expected.idempotent
        assert annotations.openWorldHint is expected.open_world


def test_server_tool_models_match_boundary_contract_catalog() -> None:
    tools = _registered_tools()

    assert frozenset(TOOL_INPUT_MODELS) == APPROVED_MCP_TOOL_NAMES
    assert frozenset(TOOL_OUTPUT_MODELS) == APPROVED_MCP_TOOL_NAMES
    for name, tool in tools.items():
        output_model = tool.fn_metadata.output_model  # type: ignore[attr-defined]
        assert output_model is TOOL_OUTPUT_MODELS[name]


def test_no_prohibited_v1_operations_are_registered_or_modeled() -> None:
    registered_or_modeled_names = (
        frozenset(_registered_tools())
        | frozenset(TOOL_INPUT_MODELS)
        | frozenset(TOOL_OUTPUT_MODELS)
    )

    assert registered_or_modeled_names.isdisjoint(PROHIBITED_MCP_TOOL_NAMES)
    assert not any(
        name.startswith(PROHIBITED_MCP_TOOL_PREFIXES)
        for name in registered_or_modeled_names
    )


def test_allowlist_validator_rejects_unapproved_tools() -> None:
    tools = [
        SimpleNamespace(
            name="polaris_workflow_run",
            annotations=ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=False,
            ),
        )
    ]

    with pytest.raises(RuntimeError, match="unapproved"):
        validate_registered_tool_allowlist(cast(list[RegisteredMcpTool], tools))


def test_allowlist_validator_rejects_annotation_drift() -> None:
    tools = [
        SimpleNamespace(
            name=name,
            annotations=ToolAnnotations(
                readOnlyHint=requirement.read_only,
                destructiveHint=requirement.destructive,
                idempotentHint=requirement.idempotent,
                openWorldHint=requirement.open_world,
            ),
        )
        for name, requirement in MCP_TOOL_ANNOTATION_REQUIREMENTS.items()
    ]
    tools[0].annotations = ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )

    with pytest.raises(RuntimeError, match="annotations do not match"):
        validate_registered_tool_allowlist(cast(list[RegisteredMcpTool], tools))
