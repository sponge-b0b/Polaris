from __future__ import annotations

import pytest

from core.workflow.bootstrap.workflow_bootstrap import (
    WorkflowBootstrapConfig,
    build_workflow_runtime_async,
)


@pytest.mark.asyncio
async def test_workflow_bootstrap_autoloads_plugins_and_registers_workflows() -> None:
    runtime = await build_workflow_runtime_async(
        config=WorkflowBootstrapConfig(
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
            autoload_plugins=True,
            plugin_dirs=("plugins/example_market_plugin",),
            autoload_plugins_recursive=False,
            autoload_plugin_overwrite=True,
            autoload_register_workflows=True,
        ),
    )

    assert runtime.plugin_runtime_manager is not None
    assert runtime.facade.plugin_runtime_manager is not None

    assert runtime.facade.workflow_exists(
        "example_plugin_workflow",
    )

    run_result = await runtime.facade.run_workflow(
        workflow_name="example_plugin_workflow",
        mode="simulation",
        archive_on_completion=False,
        checkpoint_on_completion=False,
    )

    assert run_result.success is True

    execution_result = run_result.execution_result

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

    compiled_workflow = run_result.compiled_workflow

    plan_node = compiled_workflow.execution_plan.nodes["plugin_market_node"]

    assert plan_node.metadata["created_via_factory"] is True
    assert plan_node.node_type == "plugin.example.market"
