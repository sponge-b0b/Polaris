from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.plugins.lifecycle.plugin_lifecycle_manager import (
    PluginLifecycleManager,
)
from core.plugins.manifests.plugin_manifest import PluginManifest
from core.plugins.runtime.plugin_discovery import (
    PluginDiscovery,
    PluginDiscoveryResult,
)
from core.plugins.runtime.plugin_runtime_loader import (
    PluginRuntimeLoader,
    RuntimePluginLoadResult,
)
from core.plugins.runtime.plugin_workflow_loader import (
    PluginWorkflowLoader,
    PluginWorkflowLoadResult,
)
from core.runtime.policies.policy_engine import PolicyEngine
from core.workflow.models.workflow_graph_definition import (
    WorkflowGraphDefinition,
)


@dataclass(frozen=True, slots=True)
class PluginRuntimeManagerLoadResult:
    """
    Full plugin runtime load result.
    """

    discovery_result: PluginDiscoveryResult

    validation_errors: tuple[dict[str, Any], ...]

    runtime_load_results: tuple[RuntimePluginLoadResult, ...]

    workflow_load_results: tuple[PluginWorkflowLoadResult, ...]

    workflows: tuple[WorkflowGraphDefinition, ...]

    @property
    def success(
        self,
    ) -> bool:
        return (
            self.discovery_result.success
            and not self.validation_errors
            and all(result.success for result in self.runtime_load_results)
            and all(result.success for result in self.workflow_load_results)
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "success": self.success,
            "discovery_result": self.discovery_result.to_dict(),
            "validation_errors": [dict(error) for error in self.validation_errors],
            "runtime_load_results": [
                result.to_dict() for result in self.runtime_load_results
            ],
            "workflow_load_results": [
                result.to_dict() for result in self.workflow_load_results
            ],
            "workflows": [
                {
                    "workflow_name": workflow.workflow_name,
                    "workflow_description": (workflow.workflow_description),
                }
                for workflow in self.workflows
            ],
        }


class PluginRuntimeManager:
    """
    High-level plugin runtime coordinator.

    Coordinates:
    - plugin manifest discovery
    - manifest validation
    - plugin manifest policy checks
    - runtime module loading
    - workflow definition loading
    - plugin lifecycle hooks
    """

    def __init__(
        self,
        runtime_loader: PluginRuntimeLoader,
        workflow_loader: PluginWorkflowLoader | None = None,
        discovery: PluginDiscovery | None = None,
        lifecycle_manager: PluginLifecycleManager | None = None,
        policy_engine: PolicyEngine | None = None,
    ) -> None:
        self.runtime_loader = runtime_loader
        self.workflow_loader = workflow_loader or PluginWorkflowLoader()
        self.discovery = discovery or PluginDiscovery()
        self.lifecycle_manager = lifecycle_manager or PluginLifecycleManager()
        self.policy_engine = policy_engine

    # ========================================================
    # DISCOVER / LOAD ALL
    # ========================================================

    async def discover_and_load(
        self,
        plugin_dir: str | Path | None = None,
        recursive: bool = True,
        overwrite: bool = False,
    ) -> PluginRuntimeManagerLoadResult:
        if plugin_dir is not None:
            self.discovery = PluginDiscovery(
                plugin_dir=plugin_dir,
            )

        await self.lifecycle_manager.before_plugin_discovery(
            plugin_dir=str(self.discovery.plugin_dir),
        )

        discovery_result = self.discovery.discover(
            recursive=recursive,
        )

        await self.lifecycle_manager.after_plugin_discovery(
            discovery_result,
        )

        validation_errors: list[dict[str, Any]] = []
        runtime_load_results: list[RuntimePluginLoadResult] = []
        workflow_load_results: list[PluginWorkflowLoadResult] = []
        workflows: list[WorkflowGraphDefinition] = []

        for manifest in discovery_result.discovered_manifests:
            manifest_errors = await self.validate_manifest(
                manifest,
            )

            validation_errors.extend(
                manifest_errors,
            )

            if manifest_errors:
                continue

            policy_errors = await self.validate_manifest_policy(
                manifest=manifest,
                plugin_dir=str(self.discovery.plugin_dir),
                overwrite=overwrite,
            )

            validation_errors.extend(
                policy_errors,
            )

            if policy_errors:
                continue

            runtime_results = await self.load_runtime_manifest(
                manifest=manifest,
                overwrite=overwrite,
            )

            runtime_load_results.extend(
                runtime_results,
            )

            loaded_workflows, workflow_results = await self.load_workflow_manifest(
                manifest=manifest,
            )

            workflows.extend(
                loaded_workflows,
            )

            workflow_load_results.extend(
                workflow_results,
            )

        return PluginRuntimeManagerLoadResult(
            discovery_result=discovery_result,
            validation_errors=tuple(validation_errors),
            runtime_load_results=tuple(runtime_load_results),
            workflow_load_results=tuple(workflow_load_results),
            workflows=tuple(workflows),
        )

    # ========================================================
    # VALIDATE
    # ========================================================

    async def validate_manifest(
        self,
        manifest: PluginManifest,
    ) -> list[dict[str, Any]]:
        await self.lifecycle_manager.before_plugin_validate(
            manifest,
        )

        errors = self.discovery.validate_imports(
            manifest,
        )

        await self.lifecycle_manager.after_plugin_validate(
            manifest,
            errors,
        )

        return errors

    async def validate_manifest_policy(
        self,
        manifest: PluginManifest,
        plugin_dir: str,
        overwrite: bool,
    ) -> list[dict[str, Any]]:
        if self.policy_engine is None:
            return []

        result = await self.policy_engine.evaluate(
            subject=manifest,
            context={
                "policy_phase": "plugin_manifest_validation",
                "plugin_name": manifest.plugin_name,
                "plugin_version": manifest.version,
                "plugin_dir": plugin_dir,
                "overwrite": overwrite,
            },
        )

        if result.allowed:
            return []

        return [
            {
                "plugin_name": manifest.plugin_name,
                "version": manifest.version,
                "error_type": "PluginPolicyDenied",
                "message": "Plugin manifest denied by policy engine.",
                "policy_result": result.to_dict(),
            }
        ]

    # ========================================================
    # LOAD RUNTIME
    # ========================================================

    async def load_runtime_manifest(
        self,
        manifest: PluginManifest,
        overwrite: bool = False,
    ) -> list[RuntimePluginLoadResult]:
        await self.lifecycle_manager.before_plugin_load(
            manifest,
        )

        results = self.runtime_loader.load_from_manifest(
            manifest=manifest.as_runtime_loader_manifest(),
            overwrite=overwrite,
        )

        await self.lifecycle_manager.after_plugin_load(
            manifest,
            results,
        )

        return results

    async def load_manifest(
        self,
        manifest: PluginManifest,
        overwrite: bool = False,
    ) -> list[RuntimePluginLoadResult]:
        return await self.load_runtime_manifest(
            manifest=manifest,
            overwrite=overwrite,
        )

    def load_manifest_sync(
        self,
        manifest: PluginManifest,
        overwrite: bool = False,
    ) -> list[RuntimePluginLoadResult]:
        return self.runtime_loader.load_from_manifest(
            manifest=manifest.as_runtime_loader_manifest(),
            overwrite=overwrite,
        )

    # ========================================================
    # LOAD WORKFLOWS
    # ========================================================

    async def load_workflow_manifest(
        self,
        manifest: PluginManifest,
    ) -> tuple[
        list[WorkflowGraphDefinition],
        list[PluginWorkflowLoadResult],
    ]:
        workflows, results = self.workflow_loader.load_from_manifest(
            manifest={
                "workflow_modules": list(manifest.workflow_modules),
                "include_imported_classes": (manifest.include_imported_classes),
            },
        )

        return workflows, results

    # ========================================================
    # INSPECTION
    # ========================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "manager": self.__class__.__name__,
            "discovery": {
                "plugin_dir": str(self.discovery.plugin_dir),
            },
            "runtime_loader": self.runtime_loader.to_dict(),
            "workflow_loader": self.workflow_loader.to_dict(),
            "lifecycle_manager": self.lifecycle_manager.to_dict(),
            "policy_engine": (
                self.policy_engine.to_dict() if self.policy_engine is not None else None
            ),
        }
