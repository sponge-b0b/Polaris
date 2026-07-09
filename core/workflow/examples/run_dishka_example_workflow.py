from __future__ import annotations

import asyncio

from core.bootstrap.app_container import build_app_container
from core.runtime.factory.runtime_node_factory import RuntimeNodeFactory
from core.workflow.bootstrap.workflow_bootstrap import build_workflow_runtime
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


class DishkaExampleWorkflow(WorkflowGraphDefinition):
    @property
    def workflow_name(
        self,
    ) -> str:
        return "dishka_example_workflow"

    @property
    def workflow_description(
        self,
    ) -> str:
        return "Example workflow using Dishka-resolved RuntimeNode."

    def build_graph(
        self,
    ) -> list[WorkflowNodeDefinition]:
        return [
            WorkflowNodeDefinition(
                name="market_data",
                node_type=DishkaMarketDataNode,
                dependencies=(),
                enabled=True,
                tags=("example", "dishka"),
            )
        ]


async def main() -> None:
    container = build_app_container(
        ExampleWorkflowNodeProvider(),
    )

    runtime_node_factory = RuntimeNodeFactory(
        container=container,
    )

    runtime = build_workflow_runtime(
        workflow_definitions=[
            DishkaExampleWorkflow(),
        ],
        runtime_node_factory=runtime_node_factory,
    )

    result = await runtime.facade.run_workflow(
        workflow_name="dishka_example_workflow",
        mode="simulation",
        checkpoint_on_completion=True,
    )

    print(result.to_dict())


if __name__ == "__main__":
    asyncio.run(main())
