from __future__ import annotations

import pytest

from core.workflow.bootstrap.workflow_bootstrap import (
    build_workflow_runtime,
)


@pytest.mark.asyncio
async def test_plugin_workflow_discovers_loads_registers_and_runs() -> None:
    runtime = build_workflow_runtime()

    load_result = await runtime.facade.load_plugins_from_dir(
        plugin_dir="plugins/example_market_plugin",
        recursive=False,
        overwrite=True,
        register_workflows=True,
    )

    assert load_result.success is True
    assert not load_result.validation_errors

    assert len(load_result.runtime_load_results) == 1
    assert load_result.runtime_load_results[0].success is True
    assert (
        "example_plugin_market_node" in load_result.runtime_load_results[0].loaded_nodes
    )

    assert len(load_result.workflow_load_results) == 1
    assert load_result.workflow_load_results[0].success is True
    assert (
        "example_plugin_workflow"
        in load_result.workflow_load_results[0].loaded_workflows
    )

    assert runtime.facade.workflow_exists(
        "example_plugin_workflow",
    )

    result = await runtime.facade.run_workflow(
        workflow_name="example_plugin_workflow",
        mode="simulation",
        archive_on_completion=False,
        checkpoint_on_completion=False,
    )

    assert result.success is True

    execution_result = result.execution_result

    assert execution_result.success is True
    assert execution_result.error_message is None

    final_context = execution_result.final_context

    assert "plugin_market_node" in final_context.node_outputs

    output = final_context.node_outputs["plugin_market_node"]

    assert output["success"] is True
    assert output["outputs"]["source"] == "example_market_plugin"
    assert output["outputs"]["symbol"] == "SPY"
    assert output["outputs"]["latest_price"] == 743.25
    assert output["outputs"]["signal"] == "neutral"

    plan_node = result.compiled_workflow.execution_plan.nodes["plugin_market_node"]

    assert plan_node.metadata["created_via_factory"] is True
    assert plan_node.node_type == "plugin.example.market"
