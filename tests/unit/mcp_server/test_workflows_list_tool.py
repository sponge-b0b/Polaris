"""Tests for the thin ``polaris_workflows_list`` MCP boundary."""

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
from core.workflow.execution.workflow_service import WorkflowSummary
from mcp_server.lifespan import McpApplicationContext
from mcp_server.contracts.models import WorkflowsListRequest
from mcp_server.settings import McpServerSettings
from mcp_server.telemetry import McpTelemetry
from mcp_server.tools.workflows import execute_workflows_list


def _credential_url(password: str) -> str:
    return "postgresql://user:" + password + "@localhost/polaris"


class _FakeWorkflowFacade:
    def __init__(
        self,
        result: tuple[WorkflowSummary, ...] | BaseException,
    ) -> None:
        self._result = result
        self.tags: list[str | None] = []

    def list_workflow_summaries(
        self,
        tag: str | None = None,
    ) -> list[WorkflowSummary]:
        self.tags.append(tag)
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


def _summaries(*names: str) -> tuple[WorkflowSummary, ...]:
    return tuple(
        WorkflowSummary(
            workflow_name=name,
            description=f"{name} workflow",
            tags=("builtin",),
            metadata={"source": "workflows.catalog"},
        )
        for name in names
    )


@pytest.mark.asyncio
async def test_workflows_list_filters_registered_builtin_workflows_by_tag() -> None:
    facade = _FakeWorkflowFacade(_summaries("morning_report"))
    context, sink, container = _context(facade)

    response = await execute_workflows_list(
        WorkflowsListRequest(tag="builtin"),
        context,
        request_id="workflow-list-1",
    )

    assert facade.tags == ["builtin"]
    assert [summary.workflow_name for summary in response.workflows] == [
        "morning_report",
    ]
    assert response.workflows[0].metadata == {"source": "workflows.catalog"}
    assert response.total_count == 1
    assert response.has_more is False
    assert response.next_offset is None
    assert container.scopes[0].closed is True
    assert [event.event_type for event in sink.events] == [
        "mcp.tool.started",
        "mcp.tool.completed",
    ]
    assert all(event.correlation_id == "workflow-list-1" for event in sink.events)


@pytest.mark.asyncio
async def test_workflows_list_returns_an_empty_page() -> None:
    facade = _FakeWorkflowFacade(())
    context, _, _ = _context(facade)

    response = await execute_workflows_list(WorkflowsListRequest(), context)

    assert response.workflows == ()
    assert response.total_count == 0
    assert response.offset == 0
    assert response.limit == 50
    assert response.has_more is False
    assert response.next_offset is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("offset", "expected_names", "has_more", "next_offset"),
    (
        (1, ("beta", "gamma"), True, 3),
        (3, ("omega",), False, None),
        (5, (), False, None),
    ),
)
async def test_workflows_list_applies_deterministic_boundary_pagination(
    offset: int,
    expected_names: tuple[str, ...],
    has_more: bool,
    next_offset: int | None,
) -> None:
    facade = _FakeWorkflowFacade(_summaries("alpha", "beta", "gamma", "omega"))
    context, _, _ = _context(facade)

    response = await execute_workflows_list(
        WorkflowsListRequest(offset=offset, limit=2),
        context,
    )

    assert tuple(item.workflow_name for item in response.workflows) == expected_names
    assert response.total_count == 4
    assert response.offset == offset
    assert response.limit == 2
    assert response.has_more is has_more
    assert response.next_offset == next_offset


@pytest.mark.asyncio
async def test_workflows_list_sanitizes_metadata_without_mutating_source() -> None:
    metadata = {
        "password": "secret",
        "nested": {"api_key": "provider-secret"},
        "database": _credential_url("password"),
        "authorization": "Bearer token-value",
        "safe": "retained",
    }
    facade = _FakeWorkflowFacade(
        (
            WorkflowSummary(
                workflow_name="morning_report",
                metadata=metadata,
            ),
        )
    )
    context, _, _ = _context(facade)

    response = await execute_workflows_list(WorkflowsListRequest(), context)

    serialized = response.model_dump_json()
    assert "secret" not in serialized
    assert "provider-secret" not in serialized
    assert "password@" not in serialized
    assert "token-value" not in serialized
    assert "[REDACTED]" in serialized
    assert response.workflows[0].metadata["safe"] == "retained"
    assert metadata["password"] == "secret"
    assert metadata["nested"] == {"api_key": "provider-secret"}


@pytest.mark.asyncio
async def test_workflows_list_rejects_page_size_before_resolving_facade() -> None:
    facade = _FakeWorkflowFacade(())
    context, sink, container = _context(
        facade,
        settings=McpServerSettings(max_page_size=2),
    )

    with pytest.raises(ToolError, match="limit cannot exceed 2"):
        await execute_workflows_list(
            WorkflowsListRequest(limit=3),
            context,
        )

    assert facade.tags == []
    assert container.scopes == []
    assert sink.events[-1].event_type == "mcp.tool.failed"
    assert sink.events[-1].attributes["failure_category"] == "validation"


@pytest.mark.asyncio
async def test_workflows_list_sanitizes_application_failure_and_closes_scope() -> None:
    secret = _credential_url("password")
    facade = _FakeWorkflowFacade(RuntimeError(secret))
    context, sink, container = _context(facade)

    with pytest.raises(
        ToolError, match="Polaris workflow discovery request failed"
    ) as caught:
        await execute_workflows_list(WorkflowsListRequest(), context)

    assert secret not in str(caught.value)
    assert container.scopes[0].closed is True
    assert sink.events[-1].event_type == "mcp.tool.failed"
    assert sink.events[-1].attributes["failure_category"] == "application"
    assert sink.events[-1].attributes["error_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_workflows_list_preserves_cancellation_and_closes_scope() -> None:
    facade = _FakeWorkflowFacade(asyncio.CancelledError())
    context, sink, container = _context(facade)

    with pytest.raises(asyncio.CancelledError):
        await execute_workflows_list(WorkflowsListRequest(), context)

    assert container.scopes[0].closed is True
    assert sink.events[-1].event_type == "mcp.tool.failed"
    assert sink.events[-1].attributes["failure_category"] == "cancelled"


def test_workflows_list_is_registered_as_read_only_idempotent_tool() -> None:
    from mcp_server.server import server

    tools = {tool.name: tool for tool in server._tool_manager.list_tools()}

    tool = tools["polaris_workflows_list"]
    assert tool.annotations is not None
    assert tool.annotations.readOnlyHint is True
    assert tool.annotations.destructiveHint is False
    assert tool.annotations.idempotentHint is True
    assert tool.annotations.openWorldHint is False
    assert tool.fn_metadata.output_model is not None
    assert tool.fn_metadata.output_model.__name__ == "WorkflowsListResponse"
