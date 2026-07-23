"""Polaris MCP server entrypoint."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Sequence

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from starlette.types import ASGIApp

from mcp_server.auth import protect_streamable_http_app
from mcp_server.contracts.models import (
    CompletedRunGetRequest,
    CompletedRunGetResponse,
    CompletedRunsListRequest,
    CompletedRunsListResponse,
    RagAskRequest,
    RagAskResponse,
    RagStatusRequest,
    RagStatusResponse,
    WorkflowDescribeRequest,
    WorkflowDescribeResponse,
    WorkflowsListRequest,
    WorkflowsListResponse,
)
from mcp_server.lifespan import McpApplicationContext, mcp_application_lifespan
from mcp_server.settings import McpServerSettings, McpTransport
from mcp_server.tools.allowlist import validate_registered_tool_allowlist
from mcp_server.tools.completed_run_get import execute_completed_run_get
from mcp_server.tools.completed_runs import execute_completed_runs_list
from mcp_server.tools.rag import execute_rag_ask
from mcp_server.tools.rag_status import execute_rag_status
from mcp_server.tools.workflow_describe import execute_workflow_describe
from mcp_server.tools.workflows import execute_workflows_list

server = FastMCP[McpApplicationContext](
    name="Polaris",
    instructions="Read-only access to canonical Polaris application services.",
    lifespan=mcp_application_lifespan,
)


@server.tool(
    name="polaris_rag_ask",
    description=(
        "Ask a grounded question through the canonical Polaris RAG application service."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
    structured_output=True,
)
async def polaris_rag_ask(
    request: RagAskRequest,
    context: Context,
) -> RagAskResponse:
    """Delegate one MCP RAG question through a canonical request scope."""

    return await execute_rag_ask(
        request,
        context.request_context.lifespan_context,
        request_id=context.request_id,
    )


@server.tool(
    name="polaris_rag_status",
    description="Inspect canonical Polaris RAG projection and dependency readiness.",
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    structured_output=True,
)
async def polaris_rag_status(
    request: RagStatusRequest,
    context: Context,
) -> RagStatusResponse:
    """Delegate one MCP readiness request through a canonical request scope."""

    return await execute_rag_status(
        request,
        context.request_context.lifespan_context,
        request_id=context.request_id,
    )


@server.tool(
    name="polaris_workflows_list",
    description="List registered Polaris workflows with deterministic pagination.",
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    structured_output=True,
)
async def polaris_workflows_list(
    request: WorkflowsListRequest,
    context: Context,
) -> WorkflowsListResponse:
    """Delegate workflow discovery through the canonical workflow facade."""

    return await execute_workflows_list(
        request,
        context.request_context.lifespan_context,
        request_id=context.request_id,
    )


@server.tool(
    name="polaris_workflow_describe",
    description="Describe one registered Polaris workflow graph definition.",
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    structured_output=True,
)
async def polaris_workflow_describe(
    request: WorkflowDescribeRequest,
    context: Context,
) -> WorkflowDescribeResponse:
    """Delegate workflow description through the canonical workflow facade."""

    return await execute_workflow_describe(
        request,
        context.request_context.lifespan_context,
        request_id=context.request_id,
    )


@server.tool(
    name="polaris_completed_runs_list",
    description=(
        "List completed Polaris workflow execution IDs with deterministic pagination."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    structured_output=True,
)
async def polaris_completed_runs_list(
    request: CompletedRunsListRequest,
    context: Context,
) -> CompletedRunsListResponse:
    """Delegate completed-run discovery through the canonical workflow facade."""

    return await execute_completed_runs_list(
        request,
        context.request_context.lifespan_context,
        request_id=context.request_id,
    )


@server.tool(
    name="polaris_completed_run_get",
    description=(
        "Load one completed Polaris workflow run summary with selected sections."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    structured_output=True,
)
async def polaris_completed_run_get(
    request: CompletedRunGetRequest,
    context: Context,
) -> CompletedRunGetResponse:
    """Delegate completed-run retrieval through the canonical workflow facade."""

    return await execute_completed_run_get(
        request,
        context.request_context.lifespan_context,
        request_id=context.request_id,
    )


validate_registered_tool_allowlist(server._tool_manager.list_tools())


def run_stdio_server(
    settings: McpServerSettings | None = None,
) -> None:
    """Run the shared FastMCP server over trusted parent-process stdio."""

    resolved = McpServerSettings.from_env() if settings is None else settings
    if resolved.transport is not McpTransport.STDIO:
        raise ValueError("The stdio runner only supports stdio transport settings.")
    _configure_stdio_logging()
    server.run(transport="stdio")


def create_streamable_http_app(
    settings: McpServerSettings | None = None,
) -> ASGIApp:
    """Create the authenticated stateless JSON Streamable HTTP ASGI app."""

    resolved = McpServerSettings.from_env() if settings is None else settings
    if resolved.transport is not McpTransport.STREAMABLE_HTTP:
        raise ValueError(
            "The Streamable HTTP app requires streamable-http transport settings.",
        )

    _configure_streamable_http_settings(resolved)
    return protect_streamable_http_app(server.streamable_http_app(), resolved)


def run_streamable_http_server(
    settings: McpServerSettings | None = None,
) -> None:
    """Run the shared FastMCP server over authenticated Streamable HTTP."""

    resolved = McpServerSettings.from_env() if settings is None else settings
    app = create_streamable_http_app(resolved)

    import uvicorn

    uvicorn.run(
        app,
        host=resolved.host,
        port=resolved.port,
        log_level="info",
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Run the MCP server over the configured transport."""

    settings = _settings_from_args(sys.argv[1:] if argv is None else argv)
    if settings.transport is McpTransport.STDIO:
        run_stdio_server(settings)
        return
    run_streamable_http_server(settings)


def _settings_from_args(argv: Sequence[str]) -> McpServerSettings:
    parser = argparse.ArgumentParser(
        prog="polaris-mcp",
        description="Run the Polaris MCP transport boundary.",
    )
    parser.add_argument(
        "--transport",
        choices=[transport.value for transport in McpTransport],
        default=None,
        help="MCP transport to run: stdio or streamable-http.",
    )
    args = parser.parse_args(list(argv))
    env = dict(os.environ)
    if args.transport is not None:
        env["POLARIS_MCP_TRANSPORT"] = args.transport
    return McpServerSettings.from_env(env)


def _configure_stdio_logging() -> None:
    """Ensure process logs never share stdout with the MCP stdio protocol."""

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(stream=sys.stderr)
    for handler in root_logger.handlers:
        if (
            isinstance(handler, logging.StreamHandler)
            and getattr(handler, "stream", None) is sys.stdout
        ):
            handler.setStream(sys.stderr)


def _configure_streamable_http_settings(settings: McpServerSettings) -> None:
    """Apply Polaris HTTP transport settings to the shared FastMCP instance."""

    server.settings.host = settings.host
    server.settings.port = settings.port
    server.settings.streamable_http_path = settings.path
    server.settings.json_response = True
    server.settings.stateless_http = True
    server._session_manager = None
