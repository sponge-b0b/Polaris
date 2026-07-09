from __future__ import annotations

import pytest

from core.plugins.runtime.plugin_runtime_manager import (
    PluginRuntimeManager,
)
from core.plugins.runtime.plugin_workflow_loader import (
    PluginWorkflowLoader,
)
from core.workflow.bootstrap.workflow_bootstrap import (
    build_workflow_runtime,
)


@pytest.mark.asyncio
async def test_plugin_runtime_manager_discovers_loads_runtime_and_workflows() -> None:
    runtime = build_workflow_runtime()

    assert runtime.facade.plugin_runtime_loader is not None

    manager = PluginRuntimeManager(
        runtime_loader=runtime.facade.plugin_runtime_loader,
        workflow_loader=PluginWorkflowLoader(),
    )

    result = await manager.discover_and_load(
        plugin_dir="plugins/example_market_plugin",
        recursive=False,
        overwrite=True,
    )

    assert result.success is True
    assert result.discovery_result.success is True
    assert not result.validation_errors

    assert len(result.runtime_load_results) == 1
    assert result.runtime_load_results[0].success is True
    assert "example_plugin_market_node" in result.runtime_load_results[0].loaded_nodes

    assert len(result.workflow_load_results) == 1
    assert result.workflow_load_results[0].success is True
    assert "example_plugin_workflow" in result.workflow_load_results[0].loaded_workflows

    assert len(result.workflows) == 1
    assert result.workflows[0].workflow_name == "example_plugin_workflow"
