"""Tests for the MCP server-owned Polaris application lifespan."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.telemetry.observability.observability_manager import ObservabilityManager

import mcp_server.lifespan as lifespan_module
from mcp_server.lifespan import McpApplicationContext
from mcp_server.lifespan import mcp_application_lifespan
from mcp_server.server import server
from mcp_server.settings import McpServerSettings
from mcp_server.telemetry import McpTelemetry


@pytest.mark.asyncio
async def test_lifespan_owns_one_container_runtime_and_workflow_registration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle: list[str] = []
    workflows = (object(), object())

    class FakeFacade:
        async def register_workflow_async(
            self,
            *,
            workflow_definition: object,
            tags: tuple[str, ...],
            metadata: dict[str, str],
            overwrite: bool,
        ) -> None:
            workflow_index = workflows.index(workflow_definition)
            lifecycle.append(f"workflow_{workflow_index}_registered")
            assert tags == ("builtin",)
            assert metadata == {"source": "workflows.catalog"}
            assert overwrite is True

    observability_manager = ObservabilityManager()
    event_bus = object()
    runtime = SimpleNamespace(
        event_bus=event_bus,
        facade=FakeFacade(),
        observability_manager=observability_manager,
    )

    class FakeContainer:
        get_calls = 0
        close_calls = 0

        async def get(self, dependency_type: type[object]) -> object:
            assert dependency_type.__name__ == "WorkflowBootstrapResult"
            self.get_calls += 1
            lifecycle.append("runtime_resolved")
            return runtime

        async def close(self) -> None:
            self.close_calls += 1
            lifecycle.extend(("telemetry_flushed", "telemetry_shutdown", "app_closed"))

    container = FakeContainer()

    class FakeWorkflowProvider:
        bind_calls = 0

        def bind_di_container(self, bound_container: object) -> None:
            assert bound_container is container
            self.bind_calls += 1
            lifecycle.append("container_bound")

    provider = FakeWorkflowProvider()
    monkeypatch.setattr(
        lifespan_module,
        "_build_application_container",
        lambda: (provider, container),
    )
    monkeypatch.setattr(
        lifespan_module,
        "_get_builtin_workflows",
        lambda: list(workflows),
    )

    def fake_subscribe_default_workflow_output_projection(
        *,
        event_bus: object,
        observability_manager: ObservabilityManager | None = None,
    ) -> bool:
        assert event_bus is runtime.event_bus
        assert observability_manager is runtime.observability_manager
        lifecycle.append("projection_subscribed")
        return True

    monkeypatch.setattr(
        lifespan_module,
        "subscribe_default_workflow_output_projection",
        fake_subscribe_default_workflow_output_projection,
    )

    async with mcp_application_lifespan(server) as context:
        assert isinstance(context, McpApplicationContext)
        assert context.container is container
        assert context.runtime is runtime
        assert isinstance(context.telemetry, McpTelemetry)
        assert context.settings == McpServerSettings()
        assert lifecycle == [
            "container_bound",
            "runtime_resolved",
            "projection_subscribed",
            "workflow_0_registered",
            "workflow_1_registered",
        ]

    assert provider.bind_calls == 1
    assert container.get_calls == 1
    assert container.close_calls == 1
    assert lifecycle[-3:] == [
        "telemetry_flushed",
        "telemetry_shutdown",
        "app_closed",
    ]


@pytest.mark.asyncio
async def test_lifespan_closes_container_when_startup_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle: list[str] = []

    class FakeContainer:
        async def get(self, dependency_type: type[object]) -> object:
            assert dependency_type.__name__ == "WorkflowBootstrapResult"
            lifecycle.append("runtime_resolution_failed")
            raise RuntimeError("startup failed")

        async def close(self) -> None:
            lifecycle.append("app_closed")

    container = FakeContainer()

    class FakeWorkflowProvider:
        def bind_di_container(self, bound_container: object) -> None:
            assert bound_container is container
            lifecycle.append("container_bound")

    monkeypatch.setattr(
        lifespan_module,
        "_build_application_container",
        lambda: (FakeWorkflowProvider(), container),
    )

    with pytest.raises(RuntimeError, match="startup failed"):
        async with mcp_application_lifespan(server):
            pytest.fail("lifespan yielded after startup failure")

    assert lifecycle == [
        "container_bound",
        "runtime_resolution_failed",
        "app_closed",
    ]


def test_server_uses_canonical_application_lifespan() -> None:
    assert server.settings.lifespan is mcp_application_lifespan
