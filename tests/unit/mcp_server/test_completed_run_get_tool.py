"""Tests for the thin ``polaris_completed_run_get`` MCP boundary."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast

import pytest
from dishka import AsyncContainer
from mcp.server.fastmcp.exceptions import ToolError

from core.runtime.state.runtime_context import RuntimeContext
from core.telemetry.collectors.telemetry_collector import TelemetryCollector
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from core.telemetry.tracing.trace_context import TraceContext
from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapResult
from mcp_server.contracts.models import CompletedRunGetRequest, CompletedRunSection
from mcp_server.lifespan import McpApplicationContext
from mcp_server.settings import McpServerSettings
from mcp_server.telemetry import McpTelemetry
from mcp_server.tools.completed_run_get import execute_completed_run_get


class _FakeWorkflowFacade:
    def __init__(
        self,
        result: RuntimeContext | None | BaseException,
    ) -> None:
        self._result = result
        self.calls: list[tuple[str, str]] = []

    async def load_completed_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> RuntimeContext | None:
        self.calls.append((workflow_name, execution_id))
        if isinstance(self._result, BaseException):
            raise self._result
        return self._result


class _RequestContainer:
    def __init__(self, facade: object) -> None:
        self._facade = facade

    async def get(self, dependency_type: type[object]) -> object:
        assert dependency_type.__name__ == "WorkflowFacade"
        return self._facade


class _RequestScope:
    def __init__(self, facade: object) -> None:
        self._container = _RequestContainer(facade)
        self.closed = False

    async def __aenter__(self) -> _RequestContainer:
        return self._container

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: object,
    ) -> None:
        self.closed = True


class _ApplicationContainer:
    def __init__(self, facade: object) -> None:
        self._facade = facade
        self.scopes: list[_RequestScope] = []

    def __call__(self) -> _RequestScope:
        scope = _RequestScope(self._facade)
        self.scopes.append(scope)
        return scope


def _context(
    facade: object,
) -> tuple[McpApplicationContext, InMemoryTelemetrySink, _ApplicationContainer]:
    sink = InMemoryTelemetrySink()
    manager = ObservabilityManager(
        collector=TelemetryCollector(sinks=(sink,)),
        enable_domain_metrics=False,
    )
    container = _ApplicationContainer(facade)
    return (
        McpApplicationContext(
            container=cast(AsyncContainer, container),
            runtime=cast(WorkflowBootstrapResult, SimpleNamespace()),
            telemetry=McpTelemetry(manager),
            settings=McpServerSettings(),
        ),
        sink,
        container,
    )


def _runtime_context() -> RuntimeContext:
    created_at = datetime(2026, 7, 8, 14, 30, tzinfo=UTC)
    simulation_time = datetime(2026, 7, 8, 13, 30, tzinfo=UTC)
    trace_created_at = datetime(2026, 7, 8, 14, 31, tzinfo=UTC)
    long_analysis = "This is the complete long LLM response. " * 100
    return RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="execution-1",
        mode="live",
        created_at=created_at,
        simulation_time=simulation_time,
        context_version=7,
        workflow_inputs={
            "symbols": ["AAPL", "MSFT"],
            "password": "input-secret",
        },
        artifact_refs={
            "report_markdown": {
                "artifact_id": "artifact-1",
                "authorization": "Bearer artifact-token",
            },
        },
        node_outputs={
            "technical_analysis": {
                "success": True,
                "skipped": False,
                "stop_propagation": False,
                "outputs": {
                    "analysis": long_analysis,
                    "generated_at": created_at,
                    "nested": {"api_key": "node-secret", "safe": "retained"},
                },
                "artifacts": {
                    "markdown": {
                        "artifact_id": "artifact-2",
                        "secret": "artifact-secret",
                    },
                },
                "emitted_events": (
                    {
                        "event_type": "analysis.completed",
                        "payload": {"token": "event-token"},
                    },
                ),
                "errors": (
                    {
                        "message": "provider returned password=provider-secret",
                    },
                ),
                "execution_metadata": {
                    "duration_seconds": 1.25,
                    "access_token": "metadata-token",
                },
            },
            "macro_analysis": {
                "success": True,
                "outputs": {"summary": "macro output"},
            },
        },
        errors=[
            {
                "node_name": "technical_analysis",
                "message": "node error password=node-error-secret",
            }
        ],
        trace_context=TraceContext(
            trace_id="trace-1",
            span_id="span-1",
            parent_span_id="parent-1",
            correlation_id="correlation-1",
            workflow_id="morning_report",
            execution_id="execution-1",
            runtime_id="runtime-1",
            node_name="workflow",
            created_at=trace_created_at,
            attributes={
                "authorization": "Bearer trace-token",
                "safe": "trace-safe",
            },
        ),
    )


@pytest.mark.asyncio
async def test_completed_run_get_returns_default_summary_only() -> None:
    facade = _FakeWorkflowFacade(_runtime_context())
    context, sink, container = _context(facade)

    response = await execute_completed_run_get(
        CompletedRunGetRequest(
            workflow_name="morning_report",
            execution_id="execution-1",
        ),
        context,
        request_id="completed-run-get-1",
    )

    assert facade.calls == [("morning_report", "execution-1")]
    assert response.found is True
    assert response.workflow_id == "morning_report"
    assert response.execution_id == "execution-1"
    assert response.runtime_id == "runtime-1"
    assert response.context_version == 7
    assert response.node_output_count == 2
    assert response.error_count == 1
    assert response.artifact_count == 1
    assert response.workflow_inputs is None
    assert response.node_outputs is None
    assert response.errors is None
    assert response.artifact_refs is None
    assert response.trace_context is None
    assert container.scopes[0].closed is True
    assert [event.event_type for event in sink.events] == [
        "mcp.tool.started",
        "mcp.tool.completed",
    ]
    assert all(event.correlation_id == "completed-run-get-1" for event in sink.events)
    assert sink.events[-1].attributes["result_status"] == "found"


@pytest.mark.asyncio
async def test_completed_run_get_returns_sections_without_truncation() -> None:
    facade = _FakeWorkflowFacade(_runtime_context())
    context, _, _ = _context(facade)

    response = await execute_completed_run_get(
        CompletedRunGetRequest(
            workflow_name="morning_report",
            execution_id="execution-1",
            include=frozenset(
                {
                    CompletedRunSection.WORKFLOW_INPUTS,
                    CompletedRunSection.NODE_OUTPUTS,
                    CompletedRunSection.ERRORS,
                    CompletedRunSection.ARTIFACT_REFS,
                    CompletedRunSection.TRACE_CONTEXT,
                }
            ),
            node_names=("technical_analysis", "missing_node"),
        ),
        context,
    )

    assert response.workflow_inputs == {
        "symbols": ["AAPL", "MSFT"],
        "password": "[REDACTED]",
    }
    assert response.node_outputs is not None
    assert len(response.node_outputs) == 1
    node_output = response.node_outputs[0]
    assert node_output.node_name == "technical_analysis"
    assert node_output.success is True
    assert node_output.outputs["analysis"] == (
        "This is the complete long LLM response. " * 100
    )
    assert node_output.outputs["generated_at"] == "2026-07-08T14:30:00+00:00"
    assert node_output.outputs["nested"] == {
        "api_key": "[REDACTED]",
        "safe": "retained",
    }
    assert node_output.artifacts["markdown"] == {
        "artifact_id": "artifact-2",
        "secret": "[REDACTED]",
    }
    assert node_output.emitted_events[0]["payload"] == {"token": "[REDACTED]"}
    assert node_output.errors[0]["message"] == ("provider returned password=[REDACTED]")
    assert node_output.execution_metadata == {
        "duration_seconds": 1.25,
        "access_token": "[REDACTED]",
    }
    assert response.errors == (
        {
            "node_name": "technical_analysis",
            "message": "node error password=[REDACTED]",
        },
    )
    assert response.artifact_refs == {
        "report_markdown": {
            "artifact_id": "artifact-1",
            "authorization": "[REDACTED]",
        },
    }
    assert response.trace_context is not None
    assert response.trace_context.trace_id == "trace-1"
    assert response.trace_context.parent_span_id == "parent-1"
    assert response.trace_context.attributes == {
        "authorization": "[REDACTED]",
        "safe": "trace-safe",
    }
    serialized = response.model_dump_json()
    assert "input-secret" not in serialized
    assert "node-secret" not in serialized
    assert "artifact-secret" not in serialized
    assert "event-token" not in serialized
    assert "provider-secret" not in serialized
    assert "metadata-token" not in serialized
    assert "node-error-secret" not in serialized
    assert "artifact-token" not in serialized
    assert "trace-token" not in serialized


@pytest.mark.asyncio
async def test_completed_run_get_returns_empty_node_outputs_for_unknowns() -> None:
    facade = _FakeWorkflowFacade(_runtime_context())
    context, _, _ = _context(facade)

    response = await execute_completed_run_get(
        CompletedRunGetRequest(
            workflow_name="morning_report",
            execution_id="execution-1",
            include=frozenset({CompletedRunSection.NODE_OUTPUTS}),
            node_names=("not_a_node",),
        ),
        context,
    )

    assert response.node_output_count == 2
    assert response.node_outputs == ()


@pytest.mark.asyncio
async def test_completed_run_get_converts_missing_run_to_typed_not_found() -> None:
    facade = _FakeWorkflowFacade(None)
    context, sink, container = _context(facade)

    response = await execute_completed_run_get(
        CompletedRunGetRequest(
            workflow_name="morning_report",
            execution_id="missing-execution",
        ),
        context,
    )

    assert response.found is False
    assert response.execution_id == "missing-execution"
    assert response.error is not None
    assert response.error.code == "completed_run_not_found"
    assert response.error.retryable is False
    assert container.scopes[0].closed is True
    assert sink.events[-1].event_type == "mcp.tool.completed"
    assert sink.events[-1].attributes["result_status"] == "not_found"


@pytest.mark.asyncio
async def test_completed_run_get_sanitizes_application_failure_and_closes_scope() -> (
    None
):
    sensitive_error = "api_key=secret-value"
    facade = _FakeWorkflowFacade(RuntimeError(sensitive_error))
    context, sink, container = _context(facade)

    with pytest.raises(
        ToolError, match="Polaris completed-run retrieval request failed"
    ) as caught:
        await execute_completed_run_get(
            CompletedRunGetRequest(
                workflow_name="morning_report",
                execution_id="execution-1",
            ),
            context,
        )

    assert sensitive_error not in str(caught.value)
    assert container.scopes[0].closed is True
    assert sink.events[-1].event_type == "mcp.tool.failed"
    assert sink.events[-1].attributes["failure_category"] == "application"
    assert sink.events[-1].attributes["error_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_completed_run_get_preserves_cancellation_and_closes_scope() -> None:
    facade = _FakeWorkflowFacade(asyncio.CancelledError())
    context, sink, container = _context(facade)

    with pytest.raises(asyncio.CancelledError):
        await execute_completed_run_get(
            CompletedRunGetRequest(
                workflow_name="morning_report",
                execution_id="execution-1",
            ),
            context,
        )

    assert container.scopes[0].closed is True
    assert sink.events[-1].event_type == "mcp.tool.failed"
    assert sink.events[-1].attributes["failure_category"] == "cancelled"


def test_completed_run_get_is_registered_as_read_only_idempotent_tool() -> None:
    from mcp_server.server import server

    tools = {tool.name: tool for tool in server._tool_manager.list_tools()}

    tool = tools["polaris_completed_run_get"]
    assert tool.annotations is not None
    assert tool.annotations.readOnlyHint is True
    assert tool.annotations.destructiveHint is False
    assert tool.annotations.idempotentHint is True
    assert tool.annotations.openWorldHint is False
    assert tool.fn_metadata.output_model is not None
    assert tool.fn_metadata.output_model.__name__ == "CompletedRunGetResponse"


@pytest.mark.asyncio
async def test_completed_run_get_excludes_reasoning_traces_from_mcp_boundary() -> None:
    context_record = _runtime_context()
    context_record.node_outputs["reasoning_node"] = {
        "success": True,
        "outputs": {
            "analysis": "<think>private node reasoning</think>\nVisible analysis.",
            "reasoning_trace": "private reasoning payload",
            "nested": {
                "scratchpad": "private nested reasoning",
                "safe": "retained",
            },
        },
        "execution_metadata": {
            "thinking": "private execution metadata",
            "quality": "reviewed",
        },
    }
    facade = _FakeWorkflowFacade(context_record)
    context, _, _ = _context(facade)

    response = await execute_completed_run_get(
        CompletedRunGetRequest(
            workflow_name="morning_report",
            execution_id="execution-1",
            include=frozenset({CompletedRunSection.NODE_OUTPUTS}),
            node_names=("reasoning_node",),
        ),
        context,
    )

    assert response.node_outputs is not None
    node_output = response.node_outputs[0]
    assert node_output.outputs == {
        "analysis": "Visible analysis.",
        "nested": {"safe": "retained"},
    }
    assert node_output.execution_metadata == {"quality": "reviewed"}
    serialized = response.model_dump_json()
    assert "private node reasoning" not in serialized
    assert "private reasoning payload" not in serialized
    assert "private nested reasoning" not in serialized
    assert "private execution metadata" not in serialized
