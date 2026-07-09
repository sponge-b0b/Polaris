from __future__ import annotations

import pytest

from core.bootstrap.app_container import build_app_container
from core.runtime.factory.runtime_node_factory import RuntimeNodeFactory
from core.workflow.bootstrap.workflow_bootstrap import build_workflow_runtime_async
from core.workflow.examples.dishka_example_nodes import (
    DishkaMarketDataNode,
    ExampleWorkflowNodeProvider,
)
from core.workflow.models.workflow_graph_definition import (
    WorkflowGraphDefinition,
)
from core.workflow.models.workflow_node_definition import (
    WorkflowNodeDefinition,
)


class DishkaTestWorkflow(WorkflowGraphDefinition):
    @property
    def workflow_name(
        self,
    ) -> str:
        return "dishka_test_workflow"

    @property
    def workflow_description(
        self,
    ) -> str:
        return "Integration test workflow using Dishka DI."

    def build_graph(
        self,
    ) -> list[WorkflowNodeDefinition]:
        return [
            WorkflowNodeDefinition(
                name="market_data",
                node_type=DishkaMarketDataNode,
                dependencies=(),
                enabled=True,
                tags=("test", "dishka"),
            )
        ]


@pytest.mark.asyncio
async def test_dishka_resolved_workflow_runs_successfully() -> None:
    container = build_app_container(
        ExampleWorkflowNodeProvider(),
    )

    runtime_node_factory = RuntimeNodeFactory(
        container=container,
    )

    runtime = await build_workflow_runtime_async(
        workflow_definitions=[
            DishkaTestWorkflow(),
        ],
        runtime_node_factory=runtime_node_factory,
    )

    result = await runtime.facade.run_workflow(
        workflow_name="dishka_test_workflow",
        mode="simulation",
        archive_on_completion=False,
        checkpoint_on_completion=False,
    )

    assert result.success is True

    execution_result = result.execution_result

    assert execution_result.success is True
    assert execution_result.error_message is None

    final_context = execution_result.final_context

    assert "market_data" in final_context.node_outputs

    output = final_context.node_outputs["market_data"]

    assert output["success"] is True
    assert output["outputs"]["symbol"] == "SPY"
    assert output["outputs"]["latest_price"] == 743.25

    plan_node = result.compiled_workflow.execution_plan.nodes["market_data"]

    assert plan_node.metadata["created_via_factory"] is True
    assert plan_node.node_type == "example.market_data"
