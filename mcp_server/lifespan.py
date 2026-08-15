"""Application-scope resource ownership for the Polaris MCP server."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from application.projections.workflow_outputs import (
    subscribe_default_workflow_output_projection,
)
from mcp_server.settings import McpServerSettings
from mcp_server.telemetry import McpTelemetry

if TYPE_CHECKING:
    from dishka import AsyncContainer

    from core.bootstrap.workflow_providers import WorkflowInfrastructureProvider
    from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapResult
    from workflows.catalog import BuiltinWorkflowRegistration


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
        subscribe_default_workflow_output_projection(
            event_bus=runtime.event_bus,
            workflow_registry=runtime.facade.registry,
            observability_manager=runtime.observability_manager,
        )
        for registration in _get_builtin_workflow_registrations():
            await runtime.facade.register_workflow_async(
                workflow_definition=registration.definition,
                tags=("builtin",),
                metadata={"source": "workflows.catalog"},
                risk_authority_contract=registration.authority,
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


def _get_builtin_workflow_registrations() -> tuple[BuiltinWorkflowRegistration, ...]:
    """Load canonical built-in workflows only when the application starts."""

    from workflows.catalog import get_builtin_workflow_registrations

    return get_builtin_workflow_registrations()
