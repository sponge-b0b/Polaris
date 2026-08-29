from __future__ import annotations

import pytest

from application.persistence.diagnostics import DiagnosticsPersistenceService
from config.settings import Settings
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)
from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapConfig
from core.workflow.registry.workflow_registry import WorkflowRegistry
from interfaces.cli.bootstrap.container import cli_runtime_scope
from workflows.catalog import get_builtin_workflows


def test_shared_builtin_workflow_catalog_contains_morning_report() -> None:
    workflows = get_builtin_workflows()

    assert [workflow.workflow_name for workflow in workflows] == ["morning_report"]


@pytest.mark.asyncio
async def test_cli_runtime_accepts_backtest_provider_profile_without_runtime_changes() -> (  # noqa: E501 - descriptive pytest node id
    None
):
    async with cli_runtime_scope(
        provider_profile="backtest_synthetic",
    ) as scope:
        runtime = scope.runtime

        assert "morning_report" in runtime.facade.list_workflows()
        assert runtime.runtime_node_factory.container is not None
        assert await scope.get(ObservabilityManager) is runtime.observability_manager
        assert (
            runtime.facade.runtime_engine.observability_manager
            is runtime.observability_manager
        )


@pytest.mark.asyncio
async def test_cli_runtime_accepts_backtest_postgres_profile_without_runtime_changes() -> (  # noqa: E501 - descriptive pytest node id
    None
):
    async with cli_runtime_scope(
        provider_profile="backtest_postgres",
    ) as scope:
        runtime = scope.runtime

        assert "morning_report" in runtime.facade.list_workflows()


@pytest.mark.asyncio
async def test_cli_runtime_scope_resolves_persistence_diagnostics_service() -> None:
    async with cli_runtime_scope(
        provider_profile="backtest_synthetic",
    ) as scope:
        diagnostics_service = await scope.get(
            DiagnosticsPersistenceService,
        )

    assert isinstance(
        diagnostics_service,
        DiagnosticsPersistenceService,
    )


@pytest.mark.asyncio
async def test_cli_runtime_scope_closes_canonical_scope_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from collections.abc import AsyncIterator
    from contextlib import asynccontextmanager

    import interfaces.cli.bootstrap.container as cli_container

    lifecycle: list[str] = []

    class FakeFacade:
        registry = WorkflowRegistry()

        async def register_builtin_workflow_async(
            self,
            *,
            workflow_name: str,
            tags: tuple[str, ...] = (),
            metadata: dict[str, object] | None = None,
            overwrite: bool = False,
        ) -> None:
            assert workflow_name
            assert tags == ("builtin",)
            assert metadata == {"source": "workflows.catalog"}
            assert overwrite is True
            return None

    class FakeRuntime:
        facade = FakeFacade()
        event_bus = object()
        observability_manager = object()
        config = type(
            "Config",
            (),
            {
                "autoload_plugins": False,
            },
        )()

    class FakeRequestContainer:
        async def get(self, dependency_type: type[object]) -> FakeRuntime:
            return FakeRuntime()

    def fake_subscribe_default_workflow_output_projection(
        *,
        event_bus: object,
        workflow_registry: WorkflowRegistry,
        observability_manager: object,
    ) -> None:
        assert event_bus is not None
        assert isinstance(workflow_registry, WorkflowRegistry)
        assert observability_manager is not None

    @asynccontextmanager
    async def fake_application_scope(
        settings: Settings | None = None,
        *,
        workflow_config: WorkflowBootstrapConfig | None = None,
    ) -> AsyncIterator[FakeRequestContainer]:
        assert settings is not None
        assert workflow_config is not None
        lifecycle.append("scope_entered")
        try:
            yield FakeRequestContainer()
        finally:
            lifecycle.append("scope_closed")

    monkeypatch.setattr(
        cli_container,
        "application_request_scope",
        fake_application_scope,
    )
    monkeypatch.setattr(
        cli_container,
        "get_builtin_workflow_registrations",
        lambda: (),
    )
    monkeypatch.setattr(
        cli_container,
        "subscribe_default_workflow_output_projection",
        fake_subscribe_default_workflow_output_projection,
    )

    with pytest.raises(RuntimeError, match="scope failure"):
        async with cli_runtime_scope():
            raise RuntimeError("scope failure")

    assert lifecycle == ["scope_entered", "scope_closed"]
