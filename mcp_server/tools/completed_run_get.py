"""Thin MCP boundary for canonical Polaris completed-run retrieval."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping, Sequence
from dataclasses import is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, cast

from mcp.server.fastmcp.exceptions import ToolError
from pydantic import JsonValue

from core.runtime.state.runtime_context import RuntimeContext
from core.security.sensitive_data import sanitize_sensitive_value
from core.telemetry.tracing.trace_context import TraceContext
from core.workflow.execution.workflow_facade import WorkflowFacade

from mcp_server.lifespan import McpApplicationContext
from mcp_server.contracts.models import CompletedNodeOutput
from mcp_server.contracts.models import CompletedRunGetRequest
from mcp_server.contracts.models import CompletedRunGetResponse
from mcp_server.contracts.models import CompletedRunSection
from mcp_server.contracts.models import McpError
from mcp_server.contracts.models import TraceContextResponse
from mcp_server.request_scope import mcp_dependency_scope
from mcp_server.telemetry import McpToolFailureCategory

logger = logging.getLogger(__name__)

_TOOL_NAME = "polaris_completed_run_get"
_SAFE_FAILURE_MESSAGE = "Polaris completed-run retrieval request failed."
_NOT_FOUND_CODE = "completed_run_not_found"
_NOT_FOUND_MESSAGE = "Completed workflow run was not found."


async def execute_completed_run_get(
    request: CompletedRunGetRequest,
    application_context: McpApplicationContext,
    *,
    request_id: str | None = None,
) -> CompletedRunGetResponse:
    """Load one completed run and expose only explicitly requested sections."""

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
            context = await facade.load_completed_run(
                request.workflow_name,
                request.execution_id,
            )
        response = _to_response(context, request=request)
    except asyncio.CancelledError as exc:
        await application_context.telemetry.tool_failed(
            invocation,
            failure_category=McpToolFailureCategory.CANCELLED,
            error=exc,
        )
        raise
    except Exception as exc:
        await application_context.telemetry.tool_failed(
            invocation,
            failure_category=McpToolFailureCategory.APPLICATION,
            error=exc,
        )
        logger.error(
            "MCP completed-run retrieval request failed.",
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
    context: RuntimeContext | None,
    *,
    request: CompletedRunGetRequest,
) -> CompletedRunGetResponse:
    if context is None:
        return CompletedRunGetResponse(
            found=False,
            execution_id=request.execution_id,
            error=McpError(
                code=_NOT_FOUND_CODE,
                message=_NOT_FOUND_MESSAGE,
                retryable=False,
            ),
        )

    kwargs: dict[str, Any] = {}
    if CompletedRunSection.WORKFLOW_INPUTS in request.include:
        kwargs["workflow_inputs"] = _json_mapping(context.workflow_inputs)
    if CompletedRunSection.NODE_OUTPUTS in request.include:
        kwargs["node_outputs"] = _node_outputs(context, request=request)
    if CompletedRunSection.ERRORS in request.include:
        kwargs["errors"] = tuple(_json_mapping(error) for error in context.errors)
    if CompletedRunSection.ARTIFACT_REFS in request.include:
        kwargs["artifact_refs"] = _json_mapping(context.artifact_refs)
    if CompletedRunSection.TRACE_CONTEXT in request.include:
        kwargs["trace_context"] = _trace_context(context.trace_context)

    return CompletedRunGetResponse(
        found=True,
        workflow_id=context.workflow_id,
        execution_id=context.execution_id,
        runtime_id=context.runtime_id,
        mode=context.mode,
        created_at=context.created_at,
        simulation_time=context.simulation_time,
        context_version=context.context_version,
        node_output_count=len(context.node_outputs),
        error_count=len(context.errors),
        artifact_count=len(context.artifact_refs),
        **kwargs,
    )


def _node_outputs(
    context: RuntimeContext,
    *,
    request: CompletedRunGetRequest,
) -> tuple[CompletedNodeOutput, ...]:
    names = request.node_names or tuple(context.node_outputs)
    return tuple(
        _node_output(name, payload)
        for name in names
        if (payload := context.node_outputs.get(name)) is not None
    )


def _node_output(
    node_name: str,
    payload: Any,
) -> CompletedNodeOutput:
    if not isinstance(payload, Mapping):
        payload = {"outputs": payload}

    return CompletedNodeOutput(
        node_name=node_name,
        success=_optional_bool(payload.get("success")),
        skipped=_optional_bool(payload.get("skipped")),
        stop_propagation=_optional_bool(payload.get("stop_propagation")),
        outputs=_json_mapping(payload.get("outputs")),
        artifacts=_json_mapping(payload.get("artifacts")),
        emitted_events=tuple(
            _json_mapping(event) for event in _sequence(payload.get("emitted_events"))
        ),
        errors=tuple(
            _json_mapping(error) for error in _sequence(payload.get("errors"))
        ),
        execution_metadata=_json_mapping(payload.get("execution_metadata")),
    )


def _trace_context(
    trace_context: TraceContext | None,
) -> TraceContextResponse | None:
    if trace_context is None:
        return None
    return TraceContextResponse(
        trace_id=trace_context.trace_id,
        span_id=trace_context.span_id,
        parent_span_id=trace_context.parent_span_id,
        correlation_id=trace_context.correlation_id,
        workflow_id=trace_context.workflow_id,
        execution_id=trace_context.execution_id,
        runtime_id=trace_context.runtime_id,
        node_name=trace_context.node_name,
        created_at=trace_context.created_at,
        attributes=_json_mapping(trace_context.attributes),
    )


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _sequence(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, str | bytes | bytearray):
        return (value,)
    if isinstance(value, Sequence):
        return tuple(value)
    return (value,)


def _json_mapping(value: Any) -> dict[str, JsonValue]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return cast(
            dict[str, JsonValue],
            {
                str(key): _json_value(
                    item,
                    key=str(key),
                )
                for key, item in value.items()
            },
        )
    return {"value": _json_value(value)}


def _json_value(
    value: Any,
    *,
    key: str | None = None,
) -> JsonValue:
    sanitized = sanitize_sensitive_value(value, key=key)

    if sanitized is None or isinstance(sanitized, str | int | float | bool):
        return sanitized
    if isinstance(sanitized, datetime | date):
        return sanitized.isoformat()
    if isinstance(sanitized, Enum):
        return _json_value(sanitized.value)
    if isinstance(sanitized, Mapping):
        return {
            str(nested_key): _json_value(nested_value, key=str(nested_key))
            for nested_key, nested_value in sanitized.items()
        }
    if isinstance(sanitized, tuple | list | frozenset | set):
        return [_json_value(item) for item in sanitized]
    to_dict = getattr(sanitized, "to_dict", None)
    if callable(to_dict):
        return _json_value(to_dict())
    if is_dataclass(sanitized):
        return _json_value(str(sanitized))
    return str(sanitized)


__all__ = ["execute_completed_run_get"]
