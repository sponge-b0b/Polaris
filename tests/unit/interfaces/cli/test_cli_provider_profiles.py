from __future__ import annotations

import pytest

from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)
from interfaces.cli.bootstrap.container import cli_runtime_scope
from workflows.catalog import get_builtin_workflows


def test_shared_builtin_workflow_catalog_contains_morning_report() -> None:
    workflows = get_builtin_workflows()

    assert [workflow.workflow_name for workflow in workflows] == ["morning_report"]


@pytest.mark.asyncio
async def test_cli_runtime_accepts_backtest_provider_profile_without_runtime_changes() -> (
    None
):
    async with cli_runtime_scope(
        provider_profile="backtest_synthetic",
    ) as scope:
        runtime = scope.runtime

        assert "morning_report" in runtime.facade.list_workflows()
        assert runtime.runtime_node_factory.container is not None
        assert scope.get(ObservabilityManager) is runtime.observability_manager
        assert (
            runtime.facade.runtime_engine.observability_manager
            is runtime.observability_manager
        )


@pytest.mark.asyncio
async def test_cli_runtime_accepts_backtest_postgres_profile_without_runtime_changes() -> (
    None
):
    async with cli_runtime_scope(
        provider_profile="backtest_postgres",
    ) as scope:
        runtime = scope.runtime

        assert "morning_report" in runtime.facade.list_workflows()


@pytest.mark.asyncio
async def test_cli_runtime_scope_closes_canonical_scope_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from contextlib import contextmanager
    from typing import Iterator

    import interfaces.cli.bootstrap.container as cli_container

    lifecycle: list[str] = []

    class FakeFacade:
        async def register_workflow_async(self, **_: object) -> None:
            return None

    class FakeRuntime:
        facade = FakeFacade()
        config = type(
            "Config",
            (),
            {
                "autoload_plugins": False,
            },
        )()

    class FakeRequestContainer:
        def get(self, _: type[object]) -> FakeRuntime:
            return FakeRuntime()

    @contextmanager
    def fake_application_scope(*_: object, **__: object) -> Iterator[object]:
        lifecycle.append("scope_entered")
        try:
            yield FakeRequestContainer()
        finally:
            lifecycle.append("scope_closed")

    monkeypatch.setattr(
        cli_container,
        "application_sync_request_scope",
        fake_application_scope,
    )
    monkeypatch.setattr(
        cli_container,
        "get_builtin_workflows",
        lambda: (),
    )

    with pytest.raises(RuntimeError, match="scope failure"):
        async with cli_runtime_scope():
            raise RuntimeError("scope failure")

    assert lifecycle == ["scope_entered", "scope_closed"]
