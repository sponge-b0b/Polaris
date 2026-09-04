"""Thin MCP boundary for canonical Polaris workflow discovery."""

from __future__ import annotations

import asyncio
import logging
from typing import cast

from mcp.server.fastmcp.exceptions import ToolError
from pydantic import JsonValue

from core.security.sensitive_data import sanitize_sensitive_mapping
from core.workflow.execution.workflow_facade import WorkflowFacade
from core.workflow.execution.workflow_service import (
    WorkflowSummary as DomainWorkflowSummary,
)
from mcp_server.contracts.models import (
    WorkflowsListRequest,
    WorkflowsListResponse,
    WorkflowSummary,
)
from mcp_server.lifespan import McpApplicationContext
from mcp_server.request_scope import mcp_dependency_scope
from mcp_server.telemetry import McpToolFailureCategory

logger = logging.getLogger(__name__)

_TOOL_NAME = "polaris_workflows_list"
_SAFE_FAILURE_MESSAGE = "Polaris workflow discovery request failed."


class McpWorkflowListPolicyError(ValueError):
    """Safe validation failure raised by the workflow-list boundary."""


async def execute_workflows_list(
    request: WorkflowsListRequest,
    application_context: McpApplicationContext,
    *,
    request_id: str | None = None,
) -> WorkflowsListResponse:
    """List canonical workflow summaries with deterministic pagination."""

    invocation = await application_context.telemetry.tool_started(
        tool_name=_TOOL_NAME,
        transport=application_context.settings.transport,
        request_id=request_id,
        page_size=request.limit,
    )
    try:
        _validate_request_policy(request, application_context)
        async with mcp_dependency_scope(
            application_context,
            WorkflowFacade,
        ) as facade:
            summaries = tuple(facade.list_workflow_summaries(tag=request.tag))
        response = _to_response(summaries, request=request)
    except asyncio.CancelledError as exc:
        await application_context.telemetry.tool_failed(
            invocation,
            failure_category=McpToolFailureCategory.CANCELLED,
            error=exc,
        )
        raise
    except McpWorkflowListPolicyError as exc:
        await application_context.telemetry.tool_failed(
            invocation,
            failure_category=McpToolFailureCategory.VALIDATION,
            error=exc,
        )
        logger.warning(
            "MCP workflow discovery request rejected by boundary policy.",
            extra={"request_id": invocation.request_id},
        )
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        await application_context.telemetry.tool_failed(
            invocation,
            failure_category=McpToolFailureCategory.APPLICATION,
            error=exc,
        )
        logger.error(
            "MCP workflow discovery request failed.",
            extra={
                "request_id": invocation.request_id,
                "error_type": type(exc).__name__,
            },
        )
        raise ToolError(_SAFE_FAILURE_MESSAGE) from exc

    await application_context.telemetry.tool_completed(
        invocation,
        result_status="succeeded",
    )
    return response


def _validate_request_policy(
    request: WorkflowsListRequest,
    application_context: McpApplicationContext,
) -> None:
    max_page_size = application_context.settings.max_page_size
    if request.limit > max_page_size:
        raise McpWorkflowListPolicyError(
            f"limit cannot exceed {max_page_size}.",
        )


def _to_response(
    summaries: tuple[DomainWorkflowSummary, ...],
    *,
    request: WorkflowsListRequest,
) -> WorkflowsListResponse:
    total_count = len(summaries)
    page = summaries[request.offset : request.offset + request.limit]
    next_offset = request.offset + len(page)
    has_more = next_offset < total_count

    return WorkflowsListResponse(
        workflows=tuple(_to_summary(summary) for summary in page),
        total_count=total_count,
        offset=request.offset,
        limit=request.limit,
        has_more=has_more,
        next_offset=next_offset if has_more else None,
    )


def _to_summary(summary: DomainWorkflowSummary) -> WorkflowSummary:
    metadata = cast(
        dict[str, JsonValue],
        sanitize_sensitive_mapping(summary.metadata or {}),
    )
    return WorkflowSummary(
        workflow_name=summary.workflow_name,
        description=summary.description,
        tags=summary.tags,
        metadata=metadata,
    )


__all__ = ["execute_workflows_list"]
