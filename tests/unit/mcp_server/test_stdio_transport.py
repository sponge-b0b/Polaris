"""Tests for the trusted local stdio MCP transport entrypoint."""

from __future__ import annotations

from datetime import timedelta
import logging
import tempfile
import sys
from textwrap import dedent

from mcp import ClientSession
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import SecretStr
import pytest

import mcp_server.server as server_module
from mcp_server.settings import McpServerSettings
from mcp_server.settings import McpTransport
from mcp_server.tools.allowlist import APPROVED_MCP_TOOL_NAMES


@pytest.mark.asyncio
async def test_stdio_client_session_lists_and_invokes_fake_backed_tool() -> None:
    script = dedent(
        r"""
        from __future__ import annotations

        from contextlib import asynccontextmanager
        from types import SimpleNamespace

        from core.telemetry.collectors.telemetry_collector import TelemetryCollector
        from core.telemetry.observability.observability_manager import ObservabilityManager
        from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
        from core.workflow.execution.workflow_service import WorkflowSummary
        from mcp_server.lifespan import McpApplicationContext
        from mcp_server.server import run_stdio_server
        from mcp_server.server import server
        from mcp_server.settings import McpServerSettings
        from mcp_server.telemetry import McpTelemetry


        class FakeWorkflowFacade:
            def list_workflow_summaries(self, tag=None):
                return (
                    WorkflowSummary(
                        workflow_name="morning_report",
                        description="Morning report",
                        tags=("builtin",),
                        metadata={"source": "stdio-test"},
                    ),
                )


        class RequestContainer:
            async def get(self, dependency_type):
                assert dependency_type.__name__ == "WorkflowFacade"
                return FakeWorkflowFacade()


        class RequestScope:
            async def __aenter__(self):
                return RequestContainer()

            async def __aexit__(self, *args):
                return None


        class ApplicationContainer:
            def __call__(self):
                return RequestScope()


        @asynccontextmanager
        async def fake_lifespan(_):
            manager = ObservabilityManager(
                collector=TelemetryCollector(sinks=(InMemoryTelemetrySink(),)),
                enable_domain_metrics=False,
            )
            yield McpApplicationContext(
                container=ApplicationContainer(),
                runtime=SimpleNamespace(),
                telemetry=McpTelemetry(manager),
                settings=McpServerSettings(),
            )


        server._mcp_server.lifespan = fake_lifespan
        run_stdio_server(McpServerSettings())
        """,
    )
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-c", script],
    )

    with tempfile.TemporaryFile(mode="w+") as stderr:
        async with stdio_client(parameters, errlog=stderr) as (
            read_stream,
            write_stream,
        ):
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
                "metadata": {"source": "stdio-test"},
            }
        ],
        "total_count": 1,
        "offset": 0,
        "limit": 1,
        "has_more": False,
        "next_offset": None,
    }


def test_stdio_main_accepts_explicit_stdio_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transports: list[str] = []

    def run(*, transport: str) -> None:
        transports.append(transport)

    monkeypatch.setattr(server_module.server, "run", run)

    server_module.main(("--transport", "stdio"))

    assert transports == ["stdio"]


def test_stdio_runner_rejects_streamable_http_transport() -> None:
    settings = McpServerSettings(
        transport=McpTransport.STREAMABLE_HTTP,
        bearer_token=SecretStr("unit-test-token"),
    )

    with pytest.raises(ValueError, match="only supports stdio"):
        server_module.run_stdio_server(settings)


def test_stdio_logging_is_not_written_to_stdout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stdout_handler = logging.StreamHandler(sys.stdout)
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    root_logger.handlers = [stdout_handler]
    monkeypatch.setattr(server_module.server, "run", lambda *, transport: None)

    try:
        server_module.run_stdio_server(McpServerSettings())
        assert stdout_handler.stream is sys.stderr
    finally:
        root_logger.handlers = original_handlers
