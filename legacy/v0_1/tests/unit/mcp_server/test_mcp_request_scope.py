"""Tests for MCP per-invocation Dishka request-scope ownership."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from types import SimpleNamespace
from typing import cast

import pytest
from dishka import AsyncContainer

from application.rag.operations.rag_status_operations import RagStatusOperationsService
from application.rag.rag_service import RagService
from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapResult
from core.workflow.execution.workflow_facade import WorkflowFacade
from mcp_server.lifespan import McpApplicationContext
from mcp_server.request_scope import mcp_dependency_scope
from mcp_server.settings import McpServerSettings
from mcp_server.telemetry import McpTelemetry


@dataclass(frozen=True, slots=True)
class _ResolvedDependency:
    dependency_type: type[object]
    scope_number: int


class _FakeRequestContainer:
    def __init__(
        self,
        *,
        dependency_factory: Callable[[type[object]], object],
        lifecycle: list[tuple[str, object]],
    ) -> None:
        self._dependency_factory = dependency_factory
        self._lifecycle = lifecycle

    async def get(self, dependency_type: type[object]) -> object:
        self._lifecycle.append(("resolve", dependency_type))
        return self._dependency_factory(dependency_type)


class _FakeRequestContext:
    def __init__(
        self,
        *,
        request_container: _FakeRequestContainer,
        lifecycle: list[tuple[str, object]],
    ) -> None:
        self._request_container = request_container
        self._lifecycle = lifecycle

    async def __aenter__(self) -> _FakeRequestContainer:
        self._lifecycle.append(("enter", self._request_container))
        return self._request_container

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: object,
    ) -> None:
        self._lifecycle.append(("exit", exception_type))


class _FakeApplicationContainer:
    def __init__(self) -> None:
        self.lifecycle: list[tuple[str, object]] = []
        self.request_scopes = 0

    def __call__(self) -> _FakeRequestContext:
        self.request_scopes += 1
        request_container = _FakeRequestContainer(
            dependency_factory=lambda dependency_type: _ResolvedDependency(
                dependency_type=dependency_type,
                scope_number=self.request_scopes,
            ),
            lifecycle=self.lifecycle,
        )
        return _FakeRequestContext(
            request_container=request_container,
            lifecycle=self.lifecycle,
        )


def _application_context(
    container: _FakeApplicationContainer,
) -> McpApplicationContext:
    return McpApplicationContext(
        container=cast(AsyncContainer, container),
        runtime=cast(WorkflowBootstrapResult, SimpleNamespace()),
        telemetry=cast(McpTelemetry, SimpleNamespace()),
        settings=McpServerSettings(),
    )


@pytest.mark.asyncio
async def test_each_tool_invocation_resolves_from_a_fresh_request_scope() -> None:
    container = _FakeApplicationContainer()
    application_context = _application_context(container)

    resolved_dependencies: list[_ResolvedDependency] = []
    for dependency_type in (
        RagService,
        RagStatusOperationsService,
        WorkflowFacade,
    ):
        async with mcp_dependency_scope(
            application_context,
            dependency_type,
        ) as dependency:
            resolved_dependency = cast(_ResolvedDependency, dependency)
            resolved_dependencies.append(resolved_dependency)
            assert resolved_dependency.dependency_type is dependency_type

    assert container.request_scopes == 3
    assert [dependency.scope_number for dependency in resolved_dependencies] == [
        1,
        2,
        3,
    ]
    assert [event for event, _ in container.lifecycle] == [
        "enter",
        "resolve",
        "exit",
        "enter",
        "resolve",
        "exit",
        "enter",
        "resolve",
        "exit",
    ]


@pytest.mark.asyncio
async def test_request_scope_closes_after_validation_failure() -> None:
    container = _FakeApplicationContainer()

    with pytest.raises(ValueError, match="invalid tool input"):
        async with mcp_dependency_scope(
            _application_context(container),
            RagService,
        ):
            raise ValueError("invalid tool input")

    assert container.lifecycle[-1] == ("exit", ValueError)


@pytest.mark.asyncio
async def test_request_scope_closes_after_tool_exception() -> None:
    container = _FakeApplicationContainer()

    with pytest.raises(RuntimeError, match="tool failed"):
        async with mcp_dependency_scope(
            _application_context(container),
            RagStatusOperationsService,
        ):
            raise RuntimeError("tool failed")

    assert container.lifecycle[-1] == ("exit", RuntimeError)


@pytest.mark.asyncio
async def test_request_scope_closes_after_tool_cancellation() -> None:
    container = _FakeApplicationContainer()
    scope_entered = asyncio.Event()

    async def invoke_tool() -> None:
        async with mcp_dependency_scope(
            _application_context(container),
            WorkflowFacade,
        ):
            scope_entered.set()
            await asyncio.Event().wait()

    task = asyncio.create_task(invoke_tool())
    await scope_entered.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert container.lifecycle[-1] == ("exit", asyncio.CancelledError)
