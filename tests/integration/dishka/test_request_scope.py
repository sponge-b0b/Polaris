from __future__ import annotations

import pytest

from dishka import Provider
from dishka import Scope
from dishka import make_container
from dishka import provide

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.bootstrap.dishka_runtime_adapter import DishkaRuntimeAdapter


class RequestScopedService(RuntimeNode):
    instance_count = 0

    def __init__(
        self,
    ) -> None:
        RequestScopedService.instance_count += 1
        self.instance_id = RequestScopedService.instance_count

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        return RuntimeNodeOutput()


class RequestScopeProvider(Provider):
    scope = Scope.APP

    @provide(scope=Scope.REQUEST)
    def provide_request_scoped_service(
        self,
    ) -> RequestScopedService:
        return RequestScopedService()


@pytest.mark.asyncio
async def test_dishka_request_scope_creates_new_instance_per_scope() -> None:
    RequestScopedService.instance_count = 0

    container = make_container(
        RequestScopeProvider(),
    )

    adapter = DishkaRuntimeAdapter(
        container=container,
        use_scope=True,
    )

    first_service = adapter._resolve(
        RequestScopedService,
    )

    second_service = adapter._resolve(
        RequestScopedService,
    )

    assert first_service.instance_id == 1
    assert second_service.instance_id == 2
    assert RequestScopedService.instance_count == 2


@pytest.mark.asyncio
async def test_dishka_app_container_without_scope_cannot_resolve_request_dependency() -> (
    None
):
    container = make_container(
        RequestScopeProvider(),
    )

    adapter = DishkaRuntimeAdapter(
        container=container,
        use_scope=False,
    )

    with pytest.raises(
        Exception,
    ):
        adapter._resolve(
            RequestScopedService,
        )
