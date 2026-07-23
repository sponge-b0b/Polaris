from __future__ import annotations

import asyncio
import importlib

from core.plugins.runtime.plugin_discovery import PluginDiscovery
from core.workflow.bootstrap.workflow_bootstrap import build_workflow_runtime

PLUGIN_DIR = "plugins/example_market_plugin"


async def main() -> None:
    runtime = build_workflow_runtime()

    discovery = PluginDiscovery(
        plugin_dir=PLUGIN_DIR,
    )

    discovery_result = discovery.discover(
        recursive=False,
    )

    if not discovery_result.success:
        raise RuntimeError(
            discovery_result.to_dict(),
        )

    for manifest in discovery_result.discovered_manifests:
        load_results = runtime.facade.load_runtime_plugin_manifest(
            manifest=manifest.as_runtime_loader_manifest(),
            overwrite=True,
        )

        print([result.to_dict() for result in load_results])

        for workflow_module_name in manifest.workflow_modules:
            workflow_module = importlib.import_module(
                workflow_module_name,
            )

            workflow_definition = workflow_module.ExamplePluginWorkflow()

            runtime.facade.register_workflow(
                workflow_definition=workflow_definition,
                tags=manifest.tags,
                metadata={
                    "plugin_name": manifest.plugin_name,
                    "plugin_version": manifest.version,
                },
                overwrite=True,
            )

    result = await runtime.facade.run_workflow(
        workflow_name="example_plugin_workflow",
        mode="simulation",
        checkpoint_on_completion=True,
    )

    print(
        result.to_dict(),
    )


if __name__ == "__main__":
    asyncio.run(
        main(),
    )
