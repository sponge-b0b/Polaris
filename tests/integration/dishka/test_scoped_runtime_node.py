from __future__ import annotations

import pytest
from dishka import Provider, Scope, make_container, provide

from core.bootstrap.dishka_runtime_adapter import DishkaRuntimeAdapter
from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.factory.runtime_node_factory import RuntimeNodeFactory
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.workflow.bootstrap.workflow_bootstrap import build_workflow_runtime_async
from core.workflow.models.workflow_graph_definition import (
    WorkflowGraphDefinition,
)
from core.workflow.models.workflow_node_definition import (
    WorkflowNodeDefinition,
)


class ScopedCounterService:
    instance_count = 0

    def __init__(
        self,
    ) -> None:
        ScopedCounterService.instance_count += 1
        self.instance_id = ScopedCounterService.instance_count


class ScopedRuntimeNode(RuntimeNode):
    node_name = "scoped_runtime_node"
    node_type = "test.dishka.scoped_runtime_node"
    node_version = "1.0.0"

    parallel_safe = True

    def __init__(
        self,
        service: ScopedCounterService,
    ) -> None:
        self.service = service

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        return RuntimeNodeOutput.success_output(
            outputs={
                "service_instance_id": self.service.instance_id,
            },
        )


class ScopedRuntimeNodeProvider(Provider):
    scope = Scope.APP

    @provide(scope=Scope.REQUEST)
    def provide_scoped_counter_service(
        self,
    ) -> ScopedCounterService:
        return ScopedCounterService()

    @provide(scope=Scope.REQUEST)
    def provide_scoped_runtime_node(
        self,
        service: ScopedCounterService,
    ) -> ScopedRuntimeNode:
        return ScopedRuntimeNode(
            service=service,
        )


class ScopedDishkaWorkflow(WorkflowGraphDefinition):
    @property
    def workflow_name(
        self,
    ) -> str:
        return "scoped_dishka_workflow"

    @property
    def workflow_description(
        self,
    ) -> str:
        return "Workflow using a Dishka request-scoped runtime node."

    def build_graph(
        self,
    ) -> list[WorkflowNodeDefinition]:
        return [
            WorkflowNodeDefinition(
                name="scoped_node",
                node_type=ScopedRuntimeNode,
                dependencies=(),
                enabled=True,
                tags=("dishka", "scoped", "test"),
            )
        ]


@pytest.mark.asyncio
async def test_scoped_runtime_node_resolves_through_dishka_request_scope() -> None:
    ScopedCounterService.instance_count = 0

    container = make_container(
        ScopedRuntimeNodeProvider(),
    )

    adapter = DishkaRuntimeAdapter(
        container=container,
        use_scope=True,
    )

    runtime_node_factory = RuntimeNodeFactory(
        container=adapter,
    )

    runtime = await build_workflow_runtime_async(
        workflow_definitions=[
            ScopedDishkaWorkflow(),
        ],
        runtime_node_factory=runtime_node_factory,
    )

    first_result = await runtime.facade.run_workflow(
        workflow_name="scoped_dishka_workflow",
        mode="simulation",
        archive_on_completion=False,
        checkpoint_on_completion=False,
    )

    second_result = await runtime.facade.run_workflow(
        workflow_name="scoped_dishka_workflow",
        mode="simulation",
        archive_on_completion=False,
        checkpoint_on_completion=False,
    )

    assert first_result.success is True
    assert second_result.success is True

    first_output = first_result.execution_result.final_context.node_outputs[
        "scoped_node"
    ]["outputs"]

    second_output = second_result.execution_result.final_context.node_outputs[
        "scoped_node"
    ]["outputs"]

    assert first_output["service_instance_id"] == 1
    assert second_output["service_instance_id"] == 2

    assert ScopedCounterService.instance_count == 2
