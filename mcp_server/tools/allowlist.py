"""Exact V1 MCP tool allowlist and annotation contract."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from mcp.types import ToolAnnotations


@dataclass(frozen=True, slots=True)
class McpToolAnnotationRequirement:
    """Required MCP annotation flags for one approved tool."""

    read_only: bool
    destructive: bool
    idempotent: bool
    open_world: bool


class RegisteredMcpTool(Protocol):
    """Minimal FastMCP tool surface needed for allowlist validation."""

    name: str
    annotations: ToolAnnotations | None


APPROVED_MCP_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "polaris_rag_ask",
        "polaris_rag_status",
        "polaris_workflows_list",
        "polaris_workflow_describe",
        "polaris_completed_runs_list",
        "polaris_completed_run_get",
    }
)

MCP_TOOL_ANNOTATION_REQUIREMENTS: dict[str, McpToolAnnotationRequirement] = {
    "polaris_rag_ask": McpToolAnnotationRequirement(
        read_only=True,
        destructive=False,
        idempotent=False,
        open_world=True,
    ),
    "polaris_rag_status": McpToolAnnotationRequirement(
        read_only=True,
        destructive=False,
        idempotent=True,
        open_world=False,
    ),
    "polaris_workflows_list": McpToolAnnotationRequirement(
        read_only=True,
        destructive=False,
        idempotent=True,
        open_world=False,
    ),
    "polaris_workflow_describe": McpToolAnnotationRequirement(
        read_only=True,
        destructive=False,
        idempotent=True,
        open_world=False,
    ),
    "polaris_completed_runs_list": McpToolAnnotationRequirement(
        read_only=True,
        destructive=False,
        idempotent=True,
        open_world=False,
    ),
    "polaris_completed_run_get": McpToolAnnotationRequirement(
        read_only=True,
        destructive=False,
        idempotent=True,
        open_world=False,
    ),
}

PROHIBITED_MCP_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "polaris_workflow_run",
        "polaris_workflow_pause",
        "polaris_workflow_resume",
        "polaris_workflow_cancel",
        "polaris_rag_ingest",
        "polaris_rag_process_embeddings",
        "polaris_rag_process_graph",
        "polaris_rag_rebuild_projection",
        "polaris_completed_run_delete",
        "polaris_completed_runs_cleanup",
        "polaris_sql_query",
        "polaris_cypher_query",
        "polaris_qdrant_query",
        "polaris_provider_call",
        "polaris_firecrawl_search",
        "polaris_shell_exec",
        "polaris_filesystem_read",
        "polaris_filesystem_write",
        "polaris_plugin_install",
        "polaris_plugin_manage",
    }
)

PROHIBITED_MCP_TOOL_PREFIXES: tuple[str, ...] = (
    "polaris_sql_",
    "polaris_cypher_",
    "polaris_qdrant_",
    "polaris_neo4j_",
    "polaris_firecrawl_",
    "polaris_shell_",
    "polaris_filesystem_",
    "polaris_plugin_",
)


def validate_registered_tool_allowlist(
    tools: Iterable[RegisteredMcpTool],
) -> None:
    """Fail closed if the server registers anything outside the V1 catalog."""

    tools_by_name = {tool.name: tool for tool in tools}
    names = frozenset(tools_by_name)
    if names != APPROVED_MCP_TOOL_NAMES:
        missing = sorted(APPROVED_MCP_TOOL_NAMES - names)
        unapproved = sorted(names - APPROVED_MCP_TOOL_NAMES)
        raise RuntimeError(
            "MCP tool registration does not match the approved V1 allowlist "
            f"(missing={missing}, unapproved={unapproved})."
        )

    prohibited = sorted(
        name
        for name in names
        if name in PROHIBITED_MCP_TOOL_NAMES
        or name.startswith(PROHIBITED_MCP_TOOL_PREFIXES)
    )
    if prohibited:
        raise RuntimeError(
            "MCP tool registration includes explicitly prohibited tools "
            f"(prohibited={prohibited})."
        )

    for name, expected in MCP_TOOL_ANNOTATION_REQUIREMENTS.items():
        annotations = tools_by_name[name].annotations
        if annotations is None:
            raise RuntimeError(f"MCP tool {name!r} is missing annotations.")
        actual = McpToolAnnotationRequirement(
            read_only=bool(annotations.readOnlyHint),
            destructive=bool(annotations.destructiveHint),
            idempotent=bool(annotations.idempotentHint),
            open_world=bool(annotations.openWorldHint),
        )
        if actual != expected:
            raise RuntimeError(
                f"MCP tool {name!r} annotations do not match the approved V1 "
                f"contract (expected={expected}, actual={actual})."
            )


__all__ = [
    "APPROVED_MCP_TOOL_NAMES",
    "MCP_TOOL_ANNOTATION_REQUIREMENTS",
    "PROHIBITED_MCP_TOOL_NAMES",
    "PROHIBITED_MCP_TOOL_PREFIXES",
    "McpToolAnnotationRequirement",
    "validate_registered_tool_allowlist",
]
