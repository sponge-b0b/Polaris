"""Tests for the authenticated Streamable HTTP MCP transport."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace
from typing import Any, cast

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from pydantic import SecretStr
import pytest
from starlette.applications import Starlette

from core.telemetry.collectors.telemetry_collector import TelemetryCollector
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from core.workflow.execution.workflow_service import WorkflowSummary
from mcp_server.auth import McpHttpAuthenticationBoundary
from mcp_server.lifespan import McpApplicationContext
from mcp_server.server import create_streamable_http_app
import mcp_server.server as server_module
from mcp_server.settings import McpServerSettings
from mcp_server.settings import McpTransport
from mcp_server.telemetry import McpTelemetry
from mcp_server.tools.allowlist import APPROVED_MCP_TOOL_NAMES


class FakeWorkflowFacade:
    def list_workflow_summaries(
        self, tag: str | None = None
    ) -> tuple[WorkflowSummary, ...]:
        return (
            WorkflowSummary(
                workflow_name="morning_report",
                description="Morning report",
                tags=("builtin",),
                metadata={"source": "http-test", "tag": tag},
            ),
        )


class RequestContainer:
    async def get(self, dependency_type: type[object]) -> FakeWorkflowFacade:
        assert dependency_type.__name__ == "WorkflowFacade"
        return FakeWorkflowFacade()


class RequestScope:
    async def __aenter__(self) -> RequestContainer:
        return RequestContainer()

    async def __aexit__(self, *args: object) -> None:
        return None


class ApplicationContainer:
    def __call__(self) -> RequestScope:
        return RequestScope()


@pytest.fixture
def http_settings() -> McpServerSettings:
    return McpServerSettings(
        transport=McpTransport.STREAMABLE_HTTP,
        path="/mcp-test",
        bearer_token=SecretStr("unit-test-token"),
    )


@pytest.fixture
def patched_lifespan(
    monkeypatch: pytest.MonkeyPatch,
) -> list[str]:
    events: list[str] = []

    @asynccontextmanager
    async def fake_lifespan(_: object) -> AsyncIterator[McpApplicationContext]:
        events.append("started")
        manager = ObservabilityManager(
            collector=TelemetryCollector(sinks=(InMemoryTelemetrySink(),)),
            enable_domain_metrics=False,
        )
        try:
            yield McpApplicationContext(
                container=cast(Any, ApplicationContainer()),
                runtime=cast(Any, SimpleNamespace()),
                telemetry=McpTelemetry(manager),
                settings=McpServerSettings(),
            )
        finally:
            events.append("closed")

    monkeypatch.setattr(server_module.server._mcp_server, "lifespan", fake_lifespan)
    return events


@pytest.mark.asyncio
async def test_streamable_http_client_session_lists_and_invokes_fake_backed_tool(
    http_settings: McpServerSettings,
    patched_lifespan: list[str],
) -> None:
    app = create_streamable_http_app(http_settings)
    transport = httpx.ASGITransport(app=app)
    headers = {"Authorization": "Bearer unit-test-token"}
    authenticated_app = cast(McpHttpAuthenticationBoundary, app)
    inner_app = cast(Starlette, authenticated_app._app)

    async with inner_app.router.lifespan_context(inner_app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://localhost:8000",
            headers=headers,
        ) as http_client:
            async with streamable_http_client(
                "http://localhost:8000/mcp-test",
                http_client=http_client,
            ) as (read_stream, write_stream, _):
                async with ClientSession(
                    read_stream,
                    write_stream,
                    read_timeout_seconds=timedelta(seconds=10),
                ) as session:
                    initialized = await session.initialize()
                    listed = await session.list_tools()
                    result = await session.call_tool(
                        "polaris_workflows_list",
                        {"request": {"limit": 1}},
                        read_timeout_seconds=timedelta(seconds=10),
                    )

    assert initialized.serverInfo.name == "Polaris"
    assert {tool.name for tool in listed.tools} == APPROVED_MCP_TOOL_NAMES
    assert result.isError is False
    assert result.structuredContent == {
        "workflows": [
            {
                "workflow_name": "morning_report",
                "description": "Morning report",
                "tags": ["builtin"],
                "metadata": {"source": "http-test", "tag": None},
            }
        ],
        "total_count": 1,
        "offset": 0,
        "limit": 1,
        "has_more": False,
        "next_offset": None,
    }
    assert patched_lifespan.count("started") >= 1
    assert patched_lifespan.count("started") == patched_lifespan.count("closed")
    assert patched_lifespan[-1] == "closed"


@pytest.mark.asyncio
async def test_streamable_http_rejects_missing_and_invalid_bearer_tokens(
    http_settings: McpServerSettings,
    patched_lifespan: list[str],
) -> None:
    app = create_streamable_http_app(http_settings)
    transport = httpx.ASGITransport(app=app)
    authenticated_app = cast(McpHttpAuthenticationBoundary, app)
    inner_app = cast(Starlette, authenticated_app._app)

    async with inner_app.router.lifespan_context(inner_app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://localhost:8000",
        ) as http_client:
            missing = await http_client.post("/mcp-test", json={})
            invalid = await http_client.post(
                "/mcp-test",
                json={},
                headers={"Authorization": "Bearer wrong-token"},
            )

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert missing.json() == {"error": "unauthorized"}
    assert invalid.json() == {"error": "unauthorized"}
    assert missing.headers["WWW-Authenticate"] == "Bearer"
    assert invalid.headers["WWW-Authenticate"] == "Bearer"
    assert patched_lifespan == []


@pytest.mark.asyncio
async def test_streamable_http_healthz_is_process_ready_without_auth(
    http_settings: McpServerSettings,
) -> None:
    app = create_streamable_http_app(http_settings)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://localhost:8000",
    ) as http_client:
        response = await http_client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_streamable_http_app_configures_stateless_json_path_and_auth(
    http_settings: McpServerSettings,
) -> None:
    app = create_streamable_http_app(http_settings)

    assert app is not server_module.server.streamable_http_app()
    assert server_module.server.settings.streamable_http_path == "/mcp-test"
    assert server_module.server.settings.json_response is True
    assert server_module.server.settings.stateless_http is True


def test_streamable_http_app_rejects_stdio_settings() -> None:
    with pytest.raises(ValueError, match="requires streamable-http"):
        create_streamable_http_app(McpServerSettings())


def test_streamable_http_main_accepts_explicit_streamable_http_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[McpServerSettings] = []

    def run(settings: McpServerSettings | None = None) -> None:
        assert settings is not None
        captured.append(settings)

    monkeypatch.setenv("POLARIS_MCP_BEARER_TOKEN", "unit-test-token")
    monkeypatch.setattr(server_module, "run_streamable_http_server", run)

    server_module.main(("--transport", "streamable-http"))

    assert [settings.transport for settings in captured] == [
        McpTransport.STREAMABLE_HTTP,
    ]


def test_streamable_http_runner_uses_configured_uvicorn_server(
    http_settings: McpServerSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def run(app: object, *, host: str, port: int, log_level: str) -> None:
        calls.append(
            {
                "app": app,
                "host": host,
                "port": port,
                "log_level": log_level,
            }
        )

    monkeypatch.setattr("uvicorn.run", run)

    server_module.run_streamable_http_server(http_settings)

    assert calls == [
        {
            "app": calls[0]["app"],
            "host": "127.0.0.1",
            "port": 8000,
            "log_level": "info",
        }
    ]
