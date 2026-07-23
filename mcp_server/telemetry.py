"""Safe lifecycle telemetry for the Polaris MCP transport boundary."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from time import perf_counter
from uuid import uuid4

from core.telemetry.events.telemetry_event import TelemetryEvent, TelemetryEventLevel
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.tracing.trace_context import TraceContext
from mcp_server.settings import McpTransport

_TRACEPARENT_PATTERN = re.compile(
    r"^(?P<version>[0-9a-fA-F]{2})-"
    r"(?P<trace_id>[0-9a-fA-F]{32})-"
    r"(?P<span_id>[0-9a-fA-F]{16})-"
    r"(?P<trace_flags>[0-9a-fA-F]{2})$"
)


class McpToolFailureCategory(StrEnum):
    """Stable, non-sensitive failure categories for MCP tool telemetry."""

    VALIDATION = "validation"
    AUTHORIZATION = "authorization"
    CANCELLED = "cancelled"
    APPLICATION = "application"
    INTERNAL = "internal"


@dataclass(frozen=True, slots=True)
class McpToolInvocation:
    """Safe telemetry identity for one bounded MCP tool invocation."""

    tool_name: str
    transport: McpTransport
    request_id: str
    trace_context: TraceContext
    started_at: float
    top_k: int | None = None
    page_size: int | None = None


class McpTelemetry:
    """Emit one safe start/terminal lifecycle for each MCP tool call."""

    def __init__(
        self,
        observability_manager: ObservabilityManager,
        *,
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        self._observability_manager = observability_manager
        self._clock = clock

    async def tool_started(
        self,
        *,
        tool_name: str,
        transport: McpTransport,
        request_id: str | None = None,
        incoming_traceparent: str | None = None,
        top_k: int | None = None,
        page_size: int | None = None,
    ) -> McpToolInvocation:
        """Create the operation trace and emit its non-sensitive start event."""

        normalized_tool_name = _require_text(tool_name, "tool_name")
        normalized_request_id = _request_id(request_id)
        _validate_optional_positive(top_k, "top_k")
        _validate_optional_positive(page_size, "page_size")

        attributes = _safe_attributes(
            tool_name=normalized_tool_name,
            transport=transport,
            request_id=normalized_request_id,
            top_k=top_k,
            page_size=page_size,
        )
        trace_context = self._create_trace_context(
            transport=transport,
            request_id=normalized_request_id,
            incoming_traceparent=incoming_traceparent,
            attributes=attributes,
        )
        invocation = McpToolInvocation(
            tool_name=normalized_tool_name,
            transport=transport,
            request_id=normalized_request_id,
            trace_context=trace_context,
            started_at=self._clock(),
            top_k=top_k,
            page_size=page_size,
        )
        await self._emit(
            event_type="mcp.tool.started",
            invocation=invocation,
            success=None,
        )
        return invocation

    async def tool_completed(
        self,
        invocation: McpToolInvocation,
        *,
        result_status: str,
    ) -> None:
        """Emit the successful terminal event for an MCP tool invocation."""

        await self._emit(
            event_type="mcp.tool.completed",
            invocation=invocation,
            success=True,
            duration_seconds=self._duration(invocation),
            result_status=_require_text(result_status, "result_status"),
        )

    async def tool_failed(
        self,
        invocation: McpToolInvocation,
        *,
        failure_category: McpToolFailureCategory,
        error: BaseException,
        result_status: str = "failed",
    ) -> None:
        """Emit a sanitized failed terminal event without error message contents."""

        await self._emit(
            event_type="mcp.tool.failed",
            invocation=invocation,
            success=False,
            duration_seconds=self._duration(invocation),
            result_status=_require_text(result_status, "result_status"),
            failure_category=failure_category,
            error_type=type(error).__name__,
        )

    def _create_trace_context(
        self,
        *,
        transport: McpTransport,
        request_id: str,
        incoming_traceparent: str | None,
        attributes: dict[str, str | int],
    ) -> TraceContext:
        remote_parent = (
            _parse_traceparent(incoming_traceparent)
            if transport is McpTransport.STREAMABLE_HTTP
            else None
        )
        if remote_parent is None:
            return self._observability_manager.create_trace_context(
                correlation_id=request_id,
                attributes=attributes,
            )

        trace_id, parent_span_id = remote_parent
        return TraceContext(
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            correlation_id=request_id,
            attributes=attributes,
        )

    def _duration(self, invocation: McpToolInvocation) -> float:
        return max(0.0, self._clock() - invocation.started_at)

    async def _emit(
        self,
        *,
        event_type: str,
        invocation: McpToolInvocation,
        success: bool | None,
        duration_seconds: float | None = None,
        result_status: str | None = None,
        failure_category: McpToolFailureCategory | None = None,
        error_type: str | None = None,
    ) -> None:
        attributes: dict[str, str | int] = _safe_attributes(
            tool_name=invocation.tool_name,
            transport=invocation.transport,
            request_id=invocation.request_id,
            top_k=invocation.top_k,
            page_size=invocation.page_size,
        )
        if result_status is not None:
            attributes["result_status"] = result_status
        if failure_category is not None:
            attributes["failure_category"] = failure_category.value
        if error_type is not None:
            attributes["error_type"] = error_type

        await self._observability_manager.emit(
            TelemetryEvent(
                event_type=event_type,
                source="mcp.boundary",
                level=(
                    TelemetryEventLevel.ERROR
                    if success is False
                    else TelemetryEventLevel.INFO
                ),
                correlation_id=invocation.request_id,
                trace_id=invocation.trace_context.trace_id,
                span_id=invocation.trace_context.span_id,
                parent_span_id=invocation.trace_context.parent_span_id,
                duration_seconds=duration_seconds,
                success=success,
                error_count=1 if success is False else 0,
                attributes={
                    **attributes,
                    **invocation.trace_context.telemetry_attributes(),
                },
            )
        )


def _safe_attributes(
    *,
    tool_name: str,
    transport: McpTransport,
    request_id: str,
    top_k: int | None,
    page_size: int | None,
) -> dict[str, str | int]:
    attributes: dict[str, str | int] = {
        "tool_name": tool_name,
        "transport": transport.value,
        "request_id": request_id,
    }
    if top_k is not None:
        attributes["top_k"] = top_k
    if page_size is not None:
        attributes["page_size"] = page_size
    return attributes


def _parse_traceparent(value: str | None) -> tuple[str, str] | None:
    if value is None:
        return None

    match = _TRACEPARENT_PATTERN.fullmatch(value.strip())
    if match is None or match.group("version").lower() == "ff":
        return None

    trace_id = match.group("trace_id").lower()
    span_id = match.group("span_id").lower()
    if trace_id == "0" * 32 or span_id == "0" * 16:
        return None
    return trace_id, span_id


def _request_id(value: str | None) -> str:
    if value is None:
        return f"mcp_request:{uuid4().hex}"
    return _require_text(value, "request_id")


def _require_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty.")
    return normalized


def _validate_optional_positive(value: int | None, field_name: str) -> None:
    if value is not None and value <= 0:
        raise ValueError(f"{field_name} must be positive when provided.")


__all__ = [
    "McpTelemetry",
    "McpToolFailureCategory",
    "McpToolInvocation",
]
