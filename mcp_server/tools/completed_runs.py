"""Thin MCP boundary for canonical Polaris completed-run discovery."""

from __future__ import annotations

import asyncio
import logging

from mcp.server.fastmcp.exceptions import ToolError

from core.workflow.execution.workflow_facade import WorkflowFacade
from mcp_server.contracts.models import (
    CompletedRunsListRequest,
    CompletedRunsListResponse,
)
from mcp_server.lifespan import McpApplicationContext
from mcp_server.request_scope import mcp_dependency_scope
from mcp_server.telemetry import McpToolFailureCategory

logger = logging.getLogger(__name__)

_TOOL_NAME = "polaris_completed_runs_list"
_SAFE_FAILURE_MESSAGE = "Polaris completed-run discovery request failed."


class McpCompletedRunsListPolicyError(ValueError):
    """Safe validation failure raised by the completed-run-list boundary."""


async def execute_completed_runs_list(
    request: CompletedRunsListRequest,
    application_context: McpApplicationContext,
    *,
    request_id: str | None = None,
) -> CompletedRunsListResponse:
    """List completed workflow execution IDs through the workflow facade."""

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
            execution_ids = tuple(
                await facade.list_completed_runs(request.workflow_name),
            )
        response = _to_response(execution_ids, request=request)
    except asyncio.CancelledError as exc:
        await application_context.telemetry.tool_failed(
            invocation,
            failure_category=McpToolFailureCategory.CANCELLED,
            error=exc,
        )
        raise
    except McpCompletedRunsListPolicyError as exc:
        await application_context.telemetry.tool_failed(
            invocation,
            failure_category=McpToolFailureCategory.VALIDATION,
            error=exc,
        )
        logger.warning(
            "MCP completed-run discovery request rejected by boundary policy.",
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
            "MCP completed-run discovery request failed.",
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
    request: CompletedRunsListRequest,
    application_context: McpApplicationContext,
) -> None:
    max_page_size = application_context.settings.max_page_size
    if request.limit > max_page_size:
        raise McpCompletedRunsListPolicyError(
            f"limit cannot exceed {max_page_size}.",
        )


def _to_response(
    execution_ids: tuple[str, ...],
    *,
    request: CompletedRunsListRequest,
) -> CompletedRunsListResponse:
    total_count = len(execution_ids)
    page = execution_ids[request.offset : request.offset + request.limit]
    next_offset = request.offset + len(page)
    has_more = next_offset < total_count

    return CompletedRunsListResponse(
        workflow_name=request.workflow_name,
        execution_ids=page,
        total_count=total_count,
        offset=request.offset,
        limit=request.limit,
        has_more=has_more,
        next_offset=next_offset if has_more else None,
    )


__all__ = ["execute_completed_runs_list"]
