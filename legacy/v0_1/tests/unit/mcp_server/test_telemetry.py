"""Tests for safe MCP boundary lifecycle telemetry."""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest

from core.telemetry.collectors.telemetry_collector import TelemetryCollector
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from mcp_server.settings import McpTransport
from mcp_server.telemetry import McpTelemetry, McpToolFailureCategory


def _credential_url(password: str) -> str:
    return "postgresql://user:" + password + "@localhost/polaris"


class FakeClock:
    def __init__(self, *values: float) -> None:
        self._values: Iterator[float] = iter(values)

    def __call__(self) -> float:
        return next(self._values)


def _telemetry(*clock_values: float) -> tuple[McpTelemetry, InMemoryTelemetrySink]:
    sink = InMemoryTelemetrySink()
    manager = ObservabilityManager(
        collector=TelemetryCollector(sinks=(sink,)),
        enable_domain_metrics=False,
    )
    return McpTelemetry(manager, clock=FakeClock(*clock_values)), sink


@pytest.mark.asyncio
async def test_stdio_tool_lifecycle_records_safe_fields_and_duration() -> None:
    telemetry, sink = _telemetry(10.0, 10.25)

    invocation = await telemetry.tool_started(
        tool_name="polaris_rag_ask",
        transport=McpTransport.STDIO,
        request_id="rag_query:test-request",
        top_k=8,
    )
    await telemetry.tool_completed(invocation, result_status="succeeded")

    assert len(sink.events) == 2
    started, completed = sink.events
    assert started.event_type == "mcp.tool.started"
    assert started.success is None
    assert completed.event_type == "mcp.tool.completed"
    assert completed.success is True
    assert completed.duration_seconds == pytest.approx(0.25)
    assert (
        started.correlation_id == completed.correlation_id == "rag_query:test-request"
    )
    assert started.trace_id == completed.trace_id == invocation.trace_context.trace_id
    assert started.span_id == completed.span_id == invocation.trace_context.span_id
    assert started.attributes == {
        "tool_name": "polaris_rag_ask",
        "transport": "stdio",
        "request_id": "rag_query:test-request",
        "top_k": 8,
        "trace_id": invocation.trace_context.trace_id,
        "span_id": invocation.trace_context.span_id,
    }
    assert completed.attributes["result_status"] == "succeeded"
    assert completed.payload == {}


@pytest.mark.asyncio
async def test_failed_tool_lifecycle_does_not_record_sensitive_error_contents() -> None:
    telemetry, sink = _telemetry(20.0, 20.5)
    secret = "Bearer secret-token"
    query = "show my private portfolio"
    database_url = _credential_url("password")

    invocation = await telemetry.tool_started(
        tool_name="polaris_completed_run_get",
        transport=McpTransport.STDIO,
        page_size=20,
    )
    await telemetry.tool_failed(
        invocation,
        failure_category=McpToolFailureCategory.APPLICATION,
        error=RuntimeError(f"{secret}; {query}; {database_url}"),
    )

    assert len(sink.events) == 2
    failed = sink.events[-1]
    assert failed.event_type == "mcp.tool.failed"
    assert failed.level.value == "error"
    assert failed.success is False
    assert failed.error_count == 1
    assert failed.duration_seconds == pytest.approx(0.5)
    assert failed.attributes["failure_category"] == "application"
    assert failed.attributes["error_type"] == "RuntimeError"
    assert failed.attributes["result_status"] == "failed"
    serialized = json.dumps(failed.to_dict())
    assert secret not in serialized
    assert query not in serialized
    assert database_url not in serialized
    assert failed.exception_details is None
    assert failed.payload == {}


@pytest.mark.asyncio
async def test_valid_http_traceparent_becomes_remote_parent() -> None:
    telemetry, sink = _telemetry(30.0)
    trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    remote_span_id = "00f067aa0ba902b7"

    invocation = await telemetry.tool_started(
        tool_name="polaris_rag_status",
        transport=McpTransport.STREAMABLE_HTTP,
        incoming_traceparent=f"00-{trace_id}-{remote_span_id}-01",
    )

    event = sink.events[0]
    assert invocation.trace_context.trace_id == trace_id
    assert invocation.trace_context.parent_span_id == remote_span_id
    assert invocation.trace_context.span_id != remote_span_id
    assert event.trace_id == trace_id
    assert event.parent_span_id == remote_span_id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "traceparent",
    (
        "not-a-traceparent",
        "ff-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        "00-00000000000000000000000000000000-00f067aa0ba902b7-01",
        "00-4bf92f3577b34da6a3ce929d0e0e4736-0000000000000000-01",
    ),
)
async def test_invalid_http_traceparent_creates_local_trace(traceparent: str) -> None:
    telemetry, sink = _telemetry(40.0)

    invocation = await telemetry.tool_started(
        tool_name="polaris_rag_status",
        transport=McpTransport.STREAMABLE_HTTP,
        incoming_traceparent=traceparent,
    )

    assert invocation.trace_context.parent_span_id is None
    assert len(invocation.trace_context.trace_id) == 32
    assert sink.events[0].parent_span_id is None


@pytest.mark.asyncio
async def test_stdio_ignores_incoming_http_trace_context() -> None:
    telemetry, _ = _telemetry(50.0)

    invocation = await telemetry.tool_started(
        tool_name="polaris_workflows_list",
        transport=McpTransport.STDIO,
        incoming_traceparent=(
            "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        ),
        page_size=50,
    )

    assert invocation.trace_context.trace_id != "4bf92f3577b34da6a3ce929d0e0e4736"
    assert invocation.trace_context.parent_span_id is None


@pytest.mark.asyncio
async def test_tool_started_generates_request_id_when_missing() -> None:
    telemetry, sink = _telemetry(60.0)

    invocation = await telemetry.tool_started(
        tool_name="polaris_workflow_describe",
        transport=McpTransport.STDIO,
    )

    assert invocation.request_id.startswith("mcp_request:")
    assert sink.events[0].correlation_id == invocation.request_id
    assert sink.events[0].attributes["request_id"] == invocation.request_id


@pytest.mark.asyncio
async def test_tool_telemetry_rejects_invalid_safe_dimensions() -> None:
    telemetry, sink = _telemetry()

    with pytest.raises(ValueError, match="tool_name cannot be empty"):
        await telemetry.tool_started(
            tool_name=" ",
            transport=McpTransport.STDIO,
        )
    with pytest.raises(ValueError, match="top_k must be positive"):
        await telemetry.tool_started(
            tool_name="polaris_rag_ask",
            transport=McpTransport.STDIO,
            top_k=0,
        )
    with pytest.raises(ValueError, match="page_size must be positive"):
        await telemetry.tool_started(
            tool_name="polaris_completed_runs_list",
            transport=McpTransport.STDIO,
            page_size=-1,
        )

    assert sink.events == []
