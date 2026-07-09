from __future__ import annotations

from typing import Any

from dishka import AsyncContainer
from dishka import Container
from dishka import Provider
from dishka import make_async_container
from dishka import make_container

from core.bootstrap.workflow_providers import (
    WorkflowInfrastructureProvider,
)


def build_app_container(
    *providers: Provider,
    include_workflow_provider: bool = True,
    context: dict[Any, Any] | None = None,
    skip_validation: bool = False,
) -> Container:
    """
    Build the application-level Dishka container.

    By default, includes WorkflowInfrastructureProvider.
    Pass include_workflow_provider=False for isolated tests.
    """

    final_providers: tuple[Provider, ...]

    if include_workflow_provider:
        final_providers = (
            WorkflowInfrastructureProvider(),
            *providers,
        )
    else:
        final_providers = providers

    return make_container(
        *final_providers,
        context=context,
        skip_validation=skip_validation,
    )


def build_async_app_container(
    *providers: Provider,
    include_workflow_provider: bool = True,
    context: dict[Any, Any] | None = None,
    skip_validation: bool = False,
) -> AsyncContainer:
    """
    Build the application-level async Dishka container.

    By default, includes WorkflowInfrastructureProvider.
    Pass include_workflow_provider=False for isolated tests.
    """

    final_providers: tuple[Provider, ...]

    if include_workflow_provider:
        final_providers = (
            WorkflowInfrastructureProvider(),
            *providers,
        )
    else:
        final_providers = providers

    return make_async_container(
        *final_providers,
        context=context,
        skip_validation=skip_validation,
    )


def get_from_container(
    container: Container | AsyncContainer,
    dependency_type: type[Any],
) -> Any:
    """
    Resolve a dependency from a Dishka container.
    """

    return container.get(
        dependency_type,
    )


__all__ = [
    "build_app_container",
    "build_async_app_container",
    "get_from_container",
]
