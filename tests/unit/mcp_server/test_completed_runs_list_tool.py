"""Tests for the thin ``polaris_completed_runs_list`` MCP boundary."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import cast

from dishka import AsyncContainer
from mcp.server.fastmcp.exceptions import ToolError
import pytest

from core.telemetry.collectors.telemetry_collector import TelemetryCollector
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapResult
from mcp_server.tools.completed_runs import execute_completed_runs_list
from mcp_server.lifespan import McpApplicationContext
from mcp_server.contracts.models import CompletedRunsListRequest
from mcp_server.settings import McpServerSettings
from mcp_server.telemetry import McpTelemetry


class _FakeWorkflowFacade:
    def __init__(
        self,
        result: tuple[str, ...] | BaseException,
    ) -> None:
        self._result = result
        self.workflow_names: list[str] = []

    async def list_completed_runs(
        self,
        workflow_name: str,
    ) -> list[str]:
        self.workflow_names.append(workflow_name)
        if isinstance(self._result, BaseException):
            raise self._result
        return list(self._result)


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
    *,
    settings: McpServerSettings | None = None,
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
            settings=settings or McpServerSettings(),
        ),
        sink,
        container,
    )


@pytest.mark.asyncio
async def test_completed_runs_list_returns_execution_ids_in_canonical_order() -> None:
    facade = _FakeWorkflowFacade(("run-003", "run-002", "run-001"))
    context, sink, container = _context(facade)

    response = await execute_completed_runs_list(
        CompletedRunsListRequest(workflow_name="morning_report"),
        context,
        request_id="completed-runs-1",
    )

    assert facade.workflow_names == ["morning_report"]
    assert response.workflow_name == "morning_report"
    assert response.execution_ids == ("run-003", "run-002", "run-001")
    assert response.total_count == 3
    assert response.has_more is False
    assert response.next_offset is None
    assert container.scopes[0].closed is True
    assert [event.event_type for event in sink.events] == [
        "mcp.tool.started",
        "mcp.tool.completed",
    ]
    assert all(event.correlation_id == "completed-runs-1" for event in sink.events)


@pytest.mark.asyncio
async def test_completed_runs_list_returns_empty_archive_page() -> None:
    facade = _FakeWorkflowFacade(())
    context, _, _ = _context(facade)

    response = await execute_completed_runs_list(
        CompletedRunsListRequest(workflow_name="morning_report"),
        context,
    )

    assert response.execution_ids == ()
    assert response.total_count == 0
    assert response.offset == 0
    assert response.limit == 20
    assert response.has_more is False
    assert response.next_offset is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("offset", "expected_ids", "has_more", "next_offset"),
    (
        (1, ("run-002", "run-003"), True, 3),
        (3, ("run-004",), False, None),
        (5, (), False, None),
    ),
)
async def test_completed_runs_list_applies_boundary_pagination(
    offset: int,
    expected_ids: tuple[str, ...],
    has_more: bool,
    next_offset: int | None,
) -> None:
    facade = _FakeWorkflowFacade(("run-001", "run-002", "run-003", "run-004"))
    context, _, _ = _context(facade)

    response = await execute_completed_runs_list(
        CompletedRunsListRequest(
            workflow_name="morning_report",
            offset=offset,
            limit=2,
        ),
        context,
    )

    assert response.execution_ids == expected_ids
    assert response.total_count == 4
    assert response.offset == offset
    assert response.limit == 2
    assert response.has_more is has_more
    assert response.next_offset == next_offset


@pytest.mark.asyncio
async def test_completed_runs_list_rejects_page_size_before_resolving_facade() -> None:
    facade = _FakeWorkflowFacade(())
    context, sink, container = _context(
        facade,
        settings=McpServerSettings(max_page_size=2),
    )

    with pytest.raises(ToolError, match="limit cannot exceed 2"):
        await execute_completed_runs_list(
            CompletedRunsListRequest(workflow_name="morning_report", limit=3),
            context,
        )

    assert facade.workflow_names == []
    assert container.scopes == []
    assert sink.events[-1].event_type == "mcp.tool.failed"
    assert sink.events[-1].attributes["failure_category"] == "validation"


@pytest.mark.asyncio
async def test_completed_runs_list_sanitizes_application_failure_and_closes_scope() -> (
    None
):
    sensitive_error = "api_key=secret-value"
    facade = _FakeWorkflowFacade(RuntimeError(sensitive_error))
    context, sink, container = _context(facade)

    with pytest.raises(
        ToolError, match="Polaris completed-run discovery request failed"
    ) as caught:
        await execute_completed_runs_list(
            CompletedRunsListRequest(workflow_name="morning_report"),
            context,
        )

    assert sensitive_error not in str(caught.value)
    assert container.scopes[0].closed is True
    assert sink.events[-1].event_type == "mcp.tool.failed"
    assert sink.events[-1].attributes["failure_category"] == "application"
    assert sink.events[-1].attributes["error_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_completed_runs_list_preserves_cancellation_and_closes_scope() -> None:
    facade = _FakeWorkflowFacade(asyncio.CancelledError())
    context, sink, container = _context(facade)

    with pytest.raises(asyncio.CancelledError):
        await execute_completed_runs_list(
            CompletedRunsListRequest(workflow_name="morning_report"),
            context,
        )

    assert container.scopes[0].closed is True
    assert sink.events[-1].event_type == "mcp.tool.failed"
    assert sink.events[-1].attributes["failure_category"] == "cancelled"


def test_completed_runs_list_is_registered_as_read_only_idempotent_tool() -> None:
    from mcp_server.server import server

    tools = {tool.name: tool for tool in server._tool_manager.list_tools()}

    tool = tools["polaris_completed_runs_list"]
    assert tool.annotations is not None
    assert tool.annotations.readOnlyHint is True
    assert tool.annotations.destructiveHint is False
    assert tool.annotations.idempotentHint is True
    assert tool.annotations.openWorldHint is False
    assert tool.fn_metadata.output_model is not None
    assert tool.fn_metadata.output_model.__name__ == "CompletedRunsListResponse"
