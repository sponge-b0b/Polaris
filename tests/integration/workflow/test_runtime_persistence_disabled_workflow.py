from __future__ import annotations

import pytest

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapConfig
from core.workflow.bootstrap.workflow_bootstrap import build_workflow_runtime_async
from core.workflow.models.workflow_graph_definition import WorkflowGraphDefinition
from core.workflow.models.workflow_node_definition import WorkflowNodeDefinition


class PersistenceDisabledNode(RuntimeNode):
    node_name = "persistence_disabled_node"
    node_type = "test.persistence.disabled.node"
    node_version = "1.0.0"
    parallel_safe = True

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        return RuntimeNodeOutput.success_output(
            outputs={
                "ran_without_postgres": True,
            },
        )


class PersistenceDisabledWorkflow(WorkflowGraphDefinition):
    @property
    def workflow_name(
        self,
    ) -> str:
        return "persistence_disabled_workflow"

    @property
    def workflow_description(
        self,
    ) -> str:
        return "Workflow proving Postgres persistence remains optional."

    def build_graph(
        self,
    ) -> list[WorkflowNodeDefinition]:
        return [
            WorkflowNodeDefinition(
                name="persistence_disabled_node",
                node_type=PersistenceDisabledNode,
                dependencies=(),
            )
        ]


@pytest.mark.asyncio
async def test_workflow_runs_without_postgres_when_persistence_is_disabled() -> None:
    runtime = await build_workflow_runtime_async(
        config=WorkflowBootstrapConfig(
            enable_checkpoints=False,
            enable_artifacts=False,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
            enable_observability=False,
            enable_policies=False,
            enable_governance=False,
            enable_postgres_runtime_persistence=False,
        ),
        workflow_definitions=[
            PersistenceDisabledWorkflow(),
        ],
    )

    result = await runtime.facade.run_workflow(
        workflow_name="persistence_disabled_workflow",
        execution_id="persistence-disabled-exec-1",
        mode="simulation",
        archive_on_completion=False,
        checkpoint_on_completion=False,
    )

    assert runtime.runtime_persistence_subscriber is None
    assert result.success is True
    node_output = result.execution_result.final_context.node_outputs[
        "persistence_disabled_node"
    ]
    assert node_output["success"] is True
    assert node_output["outputs"]["ran_without_postgres"] is True
