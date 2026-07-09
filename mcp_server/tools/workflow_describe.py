"""Thin MCP boundary for canonical Polaris workflow descriptions."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, cast

from mcp.server.fastmcp.exceptions import ToolError
from pydantic import JsonValue

from core.security.sensitive_data import sanitize_sensitive_mapping
from core.workflow.execution.workflow_facade import WorkflowFacade

from mcp_server.lifespan import McpApplicationContext
from mcp_server.contracts.models import McpError
from mcp_server.contracts.models import WorkflowDescribeRequest
from mcp_server.contracts.models import WorkflowDescribeResponse
from mcp_server.contracts.models import WorkflowGraphDescription
from mcp_server.contracts.models import WorkflowNodeDescription
from mcp_server.request_scope import mcp_dependency_scope
from mcp_server.telemetry import McpToolFailureCategory

logger = logging.getLogger(__name__)

_TOOL_NAME = "polaris_workflow_describe"
_SAFE_FAILURE_MESSAGE = "Polaris workflow description request failed."
_NOT_FOUND_CODE = "workflow_not_found"
_NOT_FOUND_MESSAGE = "Workflow is not registered."


async def execute_workflow_describe(
    request: WorkflowDescribeRequest,
    application_context: McpApplicationContext,
    *,
    request_id: str | None = None,
) -> WorkflowDescribeResponse:
    """Describe one registered workflow through the canonical workflow facade."""

    invocation = await application_context.telemetry.tool_started(
        tool_name=_TOOL_NAME,
        transport=application_context.settings.transport,
        request_id=request_id,
    )
    try:
        async with mcp_dependency_scope(
            application_context,
            WorkflowFacade,
        ) as facade:
            description = facade.describe_workflow(request.workflow_name)
        response = _to_response(description, requested_name=request.workflow_name)
    except asyncio.CancelledError as exc:
        await application_context.telemetry.tool_failed(
            invocation,
            failure_category=McpToolFailureCategory.CANCELLED,
            error=exc,
        )
        raise
    except KeyError:
        response = _not_found_response(request.workflow_name)
    except Exception as exc:
        await application_context.telemetry.tool_failed(
            invocation,
            failure_category=McpToolFailureCategory.APPLICATION,
            error=exc,
        )
        logger.error(
            "MCP workflow description request failed.",
            extra={
                "request_id": invocation.request_id,
                "error_type": type(exc).__name__,
            },
        )
        raise ToolError(_SAFE_FAILURE_MESSAGE) from exc

    await application_context.telemetry.tool_completed(
        invocation,
        result_status="found" if response.found else "not_found",
    )
    return response


def _to_response(
    description: dict[str, Any],
    *,
    requested_name: str,
) -> WorkflowDescribeResponse:
    workflow_name = str(description.get("workflow_name") or requested_name)
    metadata = _sanitize_metadata(description.get("metadata"))
    definition_payload = description.get("definition")
    definition = _to_graph_description(definition_payload, fallback_name=workflow_name)

    return WorkflowDescribeResponse(
        found=True,
        workflow_name=workflow_name,
        description=str(description.get("description") or ""),
        tags=tuple(str(tag) for tag in description.get("tags") or ()),
        metadata=metadata,
        definition=definition,
    )


def _to_graph_description(
    value: object,
    *,
    fallback_name: str,
) -> WorkflowGraphDescription:
    if not isinstance(value, dict):
        raise ValueError("Workflow definition payload must be a mapping.")

    nodes_payload = value.get("nodes") or ()
    if not isinstance(nodes_payload, list | tuple):
        raise ValueError("Workflow definition nodes must be a sequence.")

    return WorkflowGraphDescription(
        workflow_name=str(value.get("workflow_name") or fallback_name),
        workflow_description=str(value.get("workflow_description") or ""),
        nodes=tuple(_to_node_description(node) for node in nodes_payload),
    )


def _to_node_description(value: object) -> WorkflowNodeDescription:
    if not isinstance(value, dict):
        raise ValueError("Workflow node definition payload must be a mapping.")

    return WorkflowNodeDescription(
        name=str(value.get("name") or ""),
        node_type=str(value.get("node_type") or ""),
        dependencies=tuple(str(item) for item in value.get("dependencies") or ()),
        enabled=bool(value.get("enabled", True)),
        max_retries=int(value.get("max_retries", 0)),
        retry_backoff_seconds=float(value.get("retry_backoff_seconds", 0.0)),
        fail_fast=bool(value.get("fail_fast", False)),
        timeout_seconds=_optional_float(value.get("timeout_seconds")),
        tags=tuple(str(item) for item in value.get("tags") or ()),
        metadata=_sanitize_metadata(value.get("metadata")),
    )


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(cast(str | int | float, value))


def _sanitize_metadata(value: object) -> dict[str, JsonValue]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("Workflow metadata payload must be a mapping.")
    return cast(
        dict[str, JsonValue],
        sanitize_sensitive_mapping(value),
    )


def _not_found_response(workflow_name: str) -> WorkflowDescribeResponse:
    return WorkflowDescribeResponse(
        found=False,
        workflow_name=workflow_name,
        error=McpError(
            code=_NOT_FOUND_CODE,
            message=_NOT_FOUND_MESSAGE,
            retryable=False,
        ),
    )


__all__ = ["execute_workflow_describe"]
