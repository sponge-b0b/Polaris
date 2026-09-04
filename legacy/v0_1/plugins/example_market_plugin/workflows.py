from __future__ import annotations

from core.workflow.models.workflow_graph_definition import (
    WorkflowGraphDefinition,
)
from core.workflow.models.workflow_node_definition import (
    WorkflowNodeDefinition,
)
from plugins.example_market_plugin.runtime_nodes import (
    ExamplePluginMarketNode,
)


class ExamplePluginWorkflow(WorkflowGraphDefinition):
    @property
    def workflow_name(
        self,
    ) -> str:
        return "example_plugin_workflow"

    @property
    def workflow_description(
        self,
    ) -> str:
        return "Example workflow contributed by plugin package."

    def build_graph(
        self,
    ) -> list[WorkflowNodeDefinition]:
        return [
            WorkflowNodeDefinition(
                name="plugin_market_node",
                node_type=ExamplePluginMarketNode,
                dependencies=(),
                enabled=True,
                tags=("plugin", "example", "market"),
            )
        ]
