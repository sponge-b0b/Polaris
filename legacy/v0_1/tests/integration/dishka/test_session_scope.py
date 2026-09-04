from __future__ import annotations

import pytest
from dishka import Provider, Scope, make_container, provide
from dishka.exceptions import NoFactoryError


class SessionScopedService:
    instance_count = 0

    def __init__(
        self,
    ) -> None:
        SessionScopedService.instance_count += 1
        self.instance_id = SessionScopedService.instance_count


class SessionScopeProvider(Provider):
    scope = Scope.APP

    @provide(scope=Scope.SESSION)
    def provide_session_scoped_service(
        self,
    ) -> SessionScopedService:
        return SessionScopedService()


@pytest.mark.asyncio
async def test_dishka_session_scope_reuses_instance_within_session() -> None:
    SessionScopedService.instance_count = 0

    container = make_container(
        SessionScopeProvider(),
    )

    with container(scope=Scope.SESSION) as session_container:
        first_service = session_container.get(
            SessionScopedService,
        )

        second_service = session_container.get(
            SessionScopedService,
        )

    assert first_service.instance_id == 1
    assert second_service.instance_id == 1
    assert first_service is second_service
    assert SessionScopedService.instance_count == 1


@pytest.mark.asyncio
async def test_dishka_session_scope_creates_new_instance_per_session() -> None:
    SessionScopedService.instance_count = 0

    container = make_container(
        SessionScopeProvider(),
    )

    with container(scope=Scope.SESSION) as first_session:
        first_service = first_session.get(
            SessionScopedService,
        )

    with container(scope=Scope.SESSION) as second_session:
        second_service = second_session.get(
            SessionScopedService,
        )

    assert first_service.instance_id == 1
    assert second_service.instance_id == 2
    assert SessionScopedService.instance_count == 2


@pytest.mark.asyncio
async def test_app_scope_cannot_directly_resolve_session_dependency() -> None:
    container = make_container(
        SessionScopeProvider(),
    )

    with pytest.raises(NoFactoryError):
        container.get(
            SessionScopedService,
        )
