"""Application-scope resource ownership for the Polaris MCP server."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from mcp_server.settings import McpServerSettings
from mcp_server.telemetry import McpTelemetry

if TYPE_CHECKING:
    from dishka import AsyncContainer

    from core.bootstrap.workflow_providers import WorkflowInfrastructureProvider
    from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapResult
    from core.workflow.models.workflow_graph_definition import WorkflowGraphDefinition


@dataclass(
    frozen=True,
    slots=True,
)
class McpApplicationContext:
    """Long-lived canonical application resources owned by one MCP server."""

    container: AsyncContainer
    runtime: WorkflowBootstrapResult
    telemetry: McpTelemetry
    settings: McpServerSettings


@asynccontextmanager
async def mcp_application_lifespan(
    _: FastMCP[McpApplicationContext],
) -> AsyncIterator[McpApplicationContext]:
    """Initialize one canonical Polaris application container for the server."""

    from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapResult

    settings = McpServerSettings.from_env()
    workflow_provider, container = _build_application_container()
    workflow_provider.bind_di_container(container)

    try:
        runtime = await container.get(WorkflowBootstrapResult)
        for workflow in _get_builtin_workflows():
            await runtime.facade.register_workflow_async(
                workflow_definition=workflow,
                tags=("builtin",),
                metadata={"source": "workflows.catalog"},
                overwrite=True,
            )
        if runtime.observability_manager is None:
            raise RuntimeError("MCP telemetry requires workflow observability.")
        yield McpApplicationContext(
            container=container,
            runtime=runtime,
            telemetry=McpTelemetry(runtime.observability_manager),
            settings=settings,
        )
    finally:
        # Closing the APP scope finalizes WorkflowInfrastructureProvider, which
        # flushes and shuts down the canonical runtime telemetry exactly once.
        await container.close()


def _build_application_container() -> tuple[
    WorkflowInfrastructureProvider, AsyncContainer
]:
    """Construct one application container with one workflow provider instance."""

    from core.bootstrap.di_providers import get_async_di_container
    from core.bootstrap.workflow_providers import WorkflowInfrastructureProvider

    workflow_provider = WorkflowInfrastructureProvider()
    container = get_async_di_container(workflow_provider=workflow_provider)
    return workflow_provider, container


def _get_builtin_workflows() -> list[WorkflowGraphDefinition]:
    """Load canonical built-in workflows only when the application starts."""

    from workflows.catalog import get_builtin_workflows

    return get_builtin_workflows()
