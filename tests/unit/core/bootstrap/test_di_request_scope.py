from __future__ import annotations

from collections.abc import Sequence
from types import TracebackType
from typing import Any

import pytest
from dishka import Provider

import core.bootstrap.di_providers as di_providers
from config.settings import Settings


@pytest.mark.asyncio
async def test_application_request_scope_closes_request_and_app_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle: list[str] = []

    class FakeRequestContext:
        async def __aenter__(self) -> str:
            lifecycle.append("request_entered")
            return "request-container"

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            traceback: TracebackType | None,
        ) -> None:
            lifecycle.append("request_closed")

    class FakeContainer:
        def __call__(self) -> FakeRequestContext:
            return FakeRequestContext()

        async def close(self) -> None:
            lifecycle.append("app_closed")

    class FakeWorkflowProvider:
        def __init__(self, *, config: object | None = None) -> None:
            assert config is None

        def bind_di_container(self, container: Any) -> None:
            assert container == "request-container"
            lifecycle.append("container_bound")

    def fake_get_async_di_container(
        settings: Settings | None = None,
        *,
        workflow_provider: object | None = None,
        extra_providers: Sequence[Provider] = (),
    ) -> FakeContainer:
        assert settings is None
        assert workflow_provider is not None
        assert extra_providers == ()
        return FakeContainer()

    monkeypatch.setattr(
        di_providers,
        "WorkflowInfrastructureProvider",
        FakeWorkflowProvider,
    )
    monkeypatch.setattr(
        di_providers,
        "get_async_di_container",
        fake_get_async_di_container,
    )

    async with di_providers.application_request_scope() as request_container:
        assert request_container == "request-container"

    assert lifecycle == [
        "request_entered",
        "container_bound",
        "request_closed",
        "app_closed",
    ]


def test_application_sync_request_scope_closes_request_and_app_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle: list[str] = []

    class FakeRequestContext:
        def __enter__(self) -> str:
            lifecycle.append("request_entered")
            return "request-container"

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            traceback: TracebackType | None,
        ) -> None:
            lifecycle.append("request_closed")

    class FakeContainer:
        def __call__(self) -> FakeRequestContext:
            return FakeRequestContext()

        def close(self) -> None:
            lifecycle.append("app_closed")

    class FakeWorkflowProvider:
        def __init__(self, *, config: object | None = None) -> None:
            assert config is None

        def bind_di_container(self, container: Any) -> None:
            assert container == "request-container"
            lifecycle.append("container_bound")

    def fake_get_di_container(
        settings: Settings | None = None,
        *,
        workflow_provider: object | None = None,
        extra_providers: Sequence[Provider] = (),
    ) -> FakeContainer:
        assert settings is None
        assert workflow_provider is not None
        assert extra_providers == ()
        return FakeContainer()

    monkeypatch.setattr(
        di_providers,
        "WorkflowInfrastructureProvider",
        FakeWorkflowProvider,
    )
    monkeypatch.setattr(
        di_providers,
        "get_di_container",
        fake_get_di_container,
    )

    with di_providers.application_sync_request_scope() as request_container:
        assert request_container == "request-container"

    assert lifecycle == [
        "request_entered",
        "container_bound",
        "request_closed",
        "app_closed",
    ]


def test_sync_application_container_owns_in_memory_portfolio_repository() -> None:
    from core.bootstrap.workflow_providers import WorkflowInfrastructureProvider
    from core.storage.persistence.portfolio import (
        InMemoryPortfolioExpansionPersistenceRepository,
        PortfolioExpansionPersistenceRepository,
    )
    from core.storage.persistence.portfolio.in_memory_portfolio_state_repository import (  # noqa: E501 - canonical module path
        InMemoryPortfolioStateRepository,
    )
    from core.storage.persistence.portfolio.portfolio_state_repository import (
        PortfolioStateRepository,
    )

    workflow_provider = WorkflowInfrastructureProvider()
    container = di_providers.get_di_container(
        workflow_provider=workflow_provider,
    )
    workflow_provider.bind_di_container(container)
    try:
        with container() as request_container:
            repository = request_container.get(PortfolioStateRepository)
            expansion_repository = request_container.get(
                PortfolioExpansionPersistenceRepository
            )
            assert isinstance(repository, InMemoryPortfolioStateRepository)
            assert isinstance(
                expansion_repository,
                InMemoryPortfolioExpansionPersistenceRepository,
            )
    finally:
        container.close()
