"""Tests for the thin ``polaris_workflow_describe`` MCP boundary."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, cast

import pytest
from dishka import AsyncContainer
from mcp.server.fastmcp.exceptions import ToolError

from core.telemetry.collectors.telemetry_collector import TelemetryCollector
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapResult
from mcp_server.contracts.models import WorkflowDescribeRequest
from mcp_server.lifespan import McpApplicationContext
from mcp_server.settings import McpServerSettings
from mcp_server.telemetry import McpTelemetry
from mcp_server.tools.workflow_describe import execute_workflow_describe


def _credential_url(password: str) -> str:
    return "postgresql://user:" + password + "@localhost/polaris"


class _FakeWorkflowFacade:
    def __init__(self, result: dict[str, Any] | BaseException) -> None:
        self._result = result
        self.workflow_names: list[str] = []

    def describe_workflow(self, workflow_name: str) -> dict[str, Any]:
        self.workflow_names.append(workflow_name)
        if isinstance(self._result, BaseException):
            raise self._result
        return self._result


class _RequestContainer:
    def __init__(self, facade: _FakeWorkflowFacade) -> None:
        self._facade = facade

    async def get(self, dependency_type: type[object]) -> object:
        assert dependency_type.__name__ == "WorkflowFacade"
        return self._facade


class _RequestScope:
    def __init__(self, facade: _FakeWorkflowFacade) -> None:
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
    def __init__(self, facade: _FakeWorkflowFacade) -> None:
        self._facade = facade
        self.scopes: list[_RequestScope] = []

    def __call__(self) -> _RequestScope:
        scope = _RequestScope(self._facade)
        self.scopes.append(scope)
        return scope


def _context(
    facade: _FakeWorkflowFacade,
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


def _workflow_description() -> dict[str, Any]:
    return {
        "workflow_name": "morning_report",
        "description": "Daily market intelligence workflow.",
        "tags": ["builtin", "report"],
        "metadata": {"source": "workflows.catalog"},
        "definition": {
            "workflow_name": "morning_report",
            "workflow_description": "Daily market intelligence workflow.",
            "nodes": [
                {
                    "name": "market_context",
                    "node_type": "MarketContextNode",
                    "dependencies": [],
                    "enabled": True,
                    "max_retries": 2,
                    "retry_backoff_seconds": 1.5,
                    "fail_fast": False,
                    "timeout_seconds": 30.0,
                    "tags": ["market"],
                    "metadata": {"tier": "source"},
                },
                {
                    "name": "strategy_synthesis",
                    "node_type": "StrategySynthesisNode",
                    "dependencies": ["market_context"],
                    "enabled": True,
                    "max_retries": 1,
                    "retry_backoff_seconds": 0.0,
                    "fail_fast": True,
                    "timeout_seconds": None,
                    "tags": ["strategy"],
                    "metadata": {"tier": "synthesis"},
                },
            ],
        },
    }


@pytest.mark.asyncio
async def test_workflow_describe_returns_complete_registered_graph_definition() -> None:
    facade = _FakeWorkflowFacade(_workflow_description())
    context, sink, container = _context(facade)

    response = await execute_workflow_describe(
        WorkflowDescribeRequest(workflow_name="morning_report"),
        context,
        request_id="workflow-describe-1",
    )

    assert facade.workflow_names == ["morning_report"]
    assert response.found is True
    assert response.workflow_name == "morning_report"
    assert response.description == "Daily market intelligence workflow."
    assert response.tags == ("builtin", "report")
    assert response.metadata == {"source": "workflows.catalog"}
    assert response.definition is not None
    assert response.definition.workflow_name == "morning_report"
    assert response.definition.workflow_description == (
        "Daily market intelligence workflow."
    )
    assert len(response.definition.nodes) == 2
    first_node = response.definition.nodes[0]
    assert first_node.name == "market_context"
    assert first_node.node_type == "MarketContextNode"
    assert first_node.dependencies == ()
    assert first_node.enabled is True
    assert first_node.max_retries == 2
    assert first_node.retry_backoff_seconds == pytest.approx(1.5)
    assert first_node.fail_fast is False
    assert first_node.timeout_seconds == pytest.approx(30.0)
    assert first_node.tags == ("market",)
    assert first_node.metadata == {"tier": "source"}
    second_node = response.definition.nodes[1]
    assert second_node.dependencies == ("market_context",)
    assert second_node.fail_fast is True
    assert second_node.timeout_seconds is None
    assert container.scopes[0].closed is True
    assert [event.event_type for event in sink.events] == [
        "mcp.tool.started",
        "mcp.tool.completed",
    ]
    assert all(event.correlation_id == "workflow-describe-1" for event in sink.events)
    assert sink.events[-1].attributes["result_status"] == "found"


@pytest.mark.asyncio
async def test_workflow_describe_converts_missing_workflow_to_typed_not_found() -> None:
    facade = _FakeWorkflowFacade(KeyError("Workflow not registered: missing"))
    context, sink, container = _context(facade)

    response = await execute_workflow_describe(
        WorkflowDescribeRequest(workflow_name="missing"),
        context,
    )

    assert facade.workflow_names == ["missing"]
    assert response.found is False
    assert response.workflow_name == "missing"
    assert response.definition is None
    assert response.error is not None
    assert response.error.code == "workflow_not_found"
    assert response.error.message == "Workflow is not registered."
    assert response.error.retryable is False
    assert container.scopes[0].closed is True
    assert sink.events[-1].event_type == "mcp.tool.completed"
    assert sink.events[-1].attributes["result_status"] == "not_found"


@pytest.mark.asyncio
async def test_workflow_describe_sanitizes_workflow_and_node_metadata() -> None:
    description = _workflow_description()
    description["metadata"] = {
        "password": "secret",
        "database": _credential_url("password"),
        "safe": "retained",
    }
    node_metadata = {
        "api_key": "provider-secret",
        "authorization": "Bearer token-value",
        "safe_node": "retained-node",
    }
    description["definition"]["nodes"][0]["metadata"] = node_metadata
    facade = _FakeWorkflowFacade(description)
    context, _, _ = _context(facade)

    response = await execute_workflow_describe(
        WorkflowDescribeRequest(workflow_name="morning_report"),
        context,
    )

    serialized = response.model_dump_json()
    assert "secret" not in serialized
    assert "provider-secret" not in serialized
    assert "password@" not in serialized
    assert "token-value" not in serialized
    assert "[REDACTED]" in serialized
    assert response.metadata["safe"] == "retained"
    assert response.definition is not None
    assert response.definition.nodes[0].metadata["safe_node"] == "retained-node"
    assert description["metadata"]["password"] == "secret"
    assert node_metadata["api_key"] == "provider-secret"


@pytest.mark.asyncio
async def test_workflow_describe_sanitizes_application_failure_and_closes_scope() -> (
    None
):
    secret = _credential_url("password")
    facade = _FakeWorkflowFacade(RuntimeError(secret))
    context, sink, container = _context(facade)

    with pytest.raises(
        ToolError,
        match="Polaris workflow description request failed",
    ) as caught:
        await execute_workflow_describe(
            WorkflowDescribeRequest(workflow_name="morning_report"),
            context,
        )

    assert secret not in str(caught.value)
    assert container.scopes[0].closed is True
    assert sink.events[-1].event_type == "mcp.tool.failed"
    assert sink.events[-1].attributes["failure_category"] == "application"
    assert sink.events[-1].attributes["error_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_workflow_describe_preserves_cancellation_and_closes_scope() -> None:
    facade = _FakeWorkflowFacade(asyncio.CancelledError())
    context, sink, container = _context(facade)

    with pytest.raises(asyncio.CancelledError):
        await execute_workflow_describe(
            WorkflowDescribeRequest(workflow_name="morning_report"),
            context,
        )

    assert container.scopes[0].closed is True
    assert sink.events[-1].event_type == "mcp.tool.failed"
    assert sink.events[-1].attributes["failure_category"] == "cancelled"


def test_workflow_describe_is_registered_as_read_only_idempotent_tool() -> None:
    from mcp_server.server import server

    tools = {tool.name: tool for tool in server._tool_manager.list_tools()}

    tool = tools["polaris_workflow_describe"]
    assert tool.annotations is not None
    assert tool.annotations.readOnlyHint is True
    assert tool.annotations.destructiveHint is False
    assert tool.annotations.idempotentHint is True
    assert tool.annotations.openWorldHint is False
    assert tool.fn_metadata.output_model is not None
    assert tool.fn_metadata.output_model.__name__ == "WorkflowDescribeResponse"
