"""Per-invocation Dishka request scopes for MCP tools."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TypeVar

from mcp_server.lifespan import McpApplicationContext

DependencyT = TypeVar("DependencyT")


@asynccontextmanager
async def mcp_dependency_scope(
    application_context: McpApplicationContext,
    dependency_type: type[DependencyT],
) -> AsyncIterator[DependencyT]:
    """Resolve one dependency inside a newly owned MCP request scope."""

    async with application_context.container() as request_container:
        yield await request_container.get(dependency_type)
