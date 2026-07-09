from __future__ import annotations

from collections.abc import Mapping

import asyncio

from datetime import datetime
from pathlib import Path
from typing import Any

from core.plugins.runtime.plugin_runtime_loader import PluginRuntimeLoader
from core.plugins.runtime.plugin_runtime_manager import (
    PluginRuntimeManager,
    PluginRuntimeManagerLoadResult,
)
from core.plugins.runtime.plugin_workflow_loader import PluginWorkflowLoader
from core.runtime.artifacts.artifact_manager import ArtifactManager
from core.runtime.artifacts.artifact_store import ArtifactStore
from core.runtime.checkpoints.checkpoint_manager import CheckpointManager
from core.runtime.control import WorkflowControlManager
from core.runtime.control import WorkflowControlSnapshot
from core.runtime.control import WorkflowControlState
from core.runtime.events.event_bus import EventBus
from core.runtime.execution.runtime_engine import RuntimeEngine
from core.runtime.factory.runtime_node_factory import RuntimeNodeFactory
from core.runtime.governance.governance_engine import GovernanceEngine
from core.runtime.lifecycle.runtime_lifecycle_manager import (
    RuntimeLifecycleManager,
)
from core.runtime.policies.policy_engine import PolicyEngine
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.state_manager import StateManager
from core.runtime.telemetry.runtime_telemetry import RuntimeTelemetry
from core.runtime.telemetry.runtime_telemetry_hook import RuntimeTelemetryHook
from core.storage.persistence.completed_run_archive import CompletedRunArchive
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)
from core.workflow.bootstrap.workflow_runtime_assembler import (
    WorkflowRuntimeAssembler,
)
from core.workflow.bootstrap.workflow_runtime_components import (
    WorkflowFacadeConfig,
)
from core.workflow.bootstrap.workflow_runtime_components import (
    WorkflowRuntimeComponents,
)
from core.workflow.bootstrap.workflow_runtime_components import (
    WorkflowRuntimeOverrides,
)
from core.workflow.compiler.workflow_compiler import CompiledWorkflow
from core.workflow.compiler.workflow_compiler import WorkflowCompiler
from core.workflow.execution.workflow_engine import WorkflowEngine
from core.workflow.execution.workflow_runner import WorkflowRunResult
from core.workflow.execution.workflow_runner import WorkflowRunner
from core.workflow.execution.workflow_service import WorkflowService
from core.workflow.execution.workflow_service import WorkflowSummary
from core.workflow.models.destructive_operation_confirmation import (
    DestructiveOperationConfirmation,
)
from core.workflow.models.destructive_operation_confirmation import (
    DestructiveWorkflowOperation,
)
from core.workflow.models.workflow_graph_definition import WorkflowGraphDefinition
from core.workflow.registry.workflow_registry import WorkflowRegistry


class WorkflowFacade:
    def __init__(
        self,
        registry: WorkflowRegistry,
        compiler: WorkflowCompiler,
        runtime_engine: RuntimeEngine,
        state_manager: StateManager,
        workflow_engine: WorkflowEngine,
        runner: WorkflowRunner,
        service: WorkflowService,
        event_bus: EventBus | None = None,
        workflow_control_manager: WorkflowControlManager | None = None,
        checkpoint_manager: CheckpointManager | None = None,
        lifecycle_manager: RuntimeLifecycleManager | None = None,
        artifact_store: ArtifactStore | None = None,
        artifact_manager: ArtifactManager | None = None,
        telemetry: RuntimeTelemetry | None = None,
        telemetry_hook: RuntimeTelemetryHook | None = None,
        observability_manager: ObservabilityManager | None = None,
        runtime_node_factory: RuntimeNodeFactory | None = None,
        plugin_runtime_loader: PluginRuntimeLoader | None = None,
        plugin_workflow_loader: PluginWorkflowLoader | None = None,
        plugin_runtime_manager: PluginRuntimeManager | None = None,
        policy_engine: PolicyEngine | None = None,
        governance_engine: GovernanceEngine | None = None,
    ) -> None:
        self.registry = registry
        self.compiler = compiler
        self.runtime_engine = runtime_engine
        self.state_manager = state_manager
        self.workflow_engine = workflow_engine
        self.runner = runner
        self.service = service
        self.event_bus = event_bus
        self.workflow_control_manager = workflow_control_manager
        self.checkpoint_manager = checkpoint_manager
        self.lifecycle_manager = lifecycle_manager
        self.artifact_store = artifact_store
        self.artifact_manager = artifact_manager
        self.telemetry = telemetry
        self.telemetry_hook = telemetry_hook
        self.observability_manager = observability_manager
        self.runtime_node_factory = runtime_node_factory
        self.plugin_runtime_loader = plugin_runtime_loader
        self.plugin_workflow_loader = plugin_workflow_loader
        self.plugin_runtime_manager = plugin_runtime_manager
        self.policy_engine = policy_engine
        self.governance_engine = governance_engine

    @classmethod
    def create(
        cls,
        archive: CompletedRunArchive | None = None,
        event_bus: EventBus | None = None,
        workflow_control_manager: WorkflowControlManager | None = None,
        config: WorkflowFacadeConfig | None = None,
        lifecycle_manager: RuntimeLifecycleManager | None = None,
        artifact_store: ArtifactStore | None = None,
        artifact_manager: ArtifactManager | None = None,
        telemetry: RuntimeTelemetry | None = None,
        observability_manager: ObservabilityManager | None = None,
        runtime_node_factory: RuntimeNodeFactory | None = None,
        plugin_runtime_loader: PluginRuntimeLoader | None = None,
        plugin_workflow_loader: PluginWorkflowLoader | None = None,
        plugin_runtime_manager: PluginRuntimeManager | None = None,
        policy_engine: PolicyEngine | None = None,
        governance_engine: GovernanceEngine | None = None,
        di_container: Any | None = None,
    ) -> WorkflowFacade:
        components = WorkflowRuntimeAssembler().assemble_facade(
            config=config or WorkflowFacadeConfig(),
            overrides=WorkflowRuntimeOverrides(
                archive=archive,
                event_bus=event_bus,
                lifecycle_manager=lifecycle_manager,
                workflow_control_manager=workflow_control_manager,
                artifact_store=artifact_store,
                artifact_manager=artifact_manager,
                telemetry=telemetry,
                observability_manager=observability_manager,
                runtime_node_factory=runtime_node_factory,
                plugin_runtime_loader=plugin_runtime_loader,
                plugin_workflow_loader=plugin_workflow_loader,
                plugin_runtime_manager=plugin_runtime_manager,
                policy_engine=policy_engine,
                governance_engine=governance_engine,
                di_container=di_container,
            ),
        )
        return cls._from_components(components)

    @classmethod
    def _from_components(
        cls,
        components: WorkflowRuntimeComponents,
    ) -> WorkflowFacade:
        return cls(
            registry=components.registry,
            compiler=components.compiler,
            runtime_engine=components.runtime_engine,
            state_manager=components.state_manager,
            workflow_engine=components.workflow_engine,
            runner=components.runner,
            service=components.service,
            event_bus=components.event_bus,
            workflow_control_manager=components.workflow_control_manager,
            checkpoint_manager=components.checkpoint_manager,
            lifecycle_manager=components.lifecycle_manager,
            artifact_store=components.artifact_store,
            artifact_manager=components.artifact_manager,
            telemetry=components.telemetry,
            telemetry_hook=components.telemetry_hook,
            observability_manager=components.observability_manager,
            runtime_node_factory=components.runtime_node_factory,
            plugin_runtime_loader=components.plugin_runtime_loader,
            plugin_workflow_loader=components.plugin_workflow_loader,
            plugin_runtime_manager=components.plugin_runtime_manager,
            policy_engine=components.policy_engine,
            governance_engine=components.governance_engine,
        )

    # ========================================================
    # PLUGINS
    # ========================================================

    async def load_plugins_from_dir(
        self,
        plugin_dir: str | Path = "plugins",
        recursive: bool = True,
        overwrite: bool = False,
        register_workflows: bool = True,
    ) -> PluginRuntimeManagerLoadResult:
        if self.plugin_runtime_manager is None:
            raise RuntimeError("PluginRuntimeManager is not configured.")

        await self._require_governance_allowed_async(
            subject={
                "operation": "load_plugins_from_dir",
                "plugin_dir": str(plugin_dir),
                "recursive": recursive,
                "overwrite": overwrite,
                "register_workflows": register_workflows,
            },
            context={
                "governance_phase": "plugin_load_preflight",
            },
        )

        await self._require_policy_allowed_async(
            subject={
                "operation": "load_plugins_from_dir",
                "plugin_dir": str(plugin_dir),
                "recursive": recursive,
                "overwrite": overwrite,
                "register_workflows": register_workflows,
            },
            context={
                "policy_phase": "plugin_load_preflight",
            },
        )

        result = await self.plugin_runtime_manager.discover_and_load(
            plugin_dir=plugin_dir,
            recursive=recursive,
            overwrite=overwrite,
        )

        if register_workflows:
            for workflow in result.workflows:
                await self.register_workflow_async(
                    workflow_definition=workflow,
                    overwrite=overwrite,
                    metadata={
                        "source": "plugin",
                    },
                )

        return result

    def load_runtime_plugin_module(
        self,
        module_name: str,
        overwrite: bool = False,
        include_imported_classes: bool = False,
    ) -> Any:
        if self.plugin_runtime_loader is None:
            raise RuntimeError("PluginRuntimeLoader is not configured.")

        return self.plugin_runtime_loader.load_module(
            module_name=module_name,
            overwrite=overwrite,
            include_imported_classes=include_imported_classes,
        )

    def load_runtime_plugin_modules(
        self,
        module_names: list[str],
        overwrite: bool = False,
        include_imported_classes: bool = False,
    ) -> list[Any]:
        if self.plugin_runtime_loader is None:
            raise RuntimeError("PluginRuntimeLoader is not configured.")

        return self.plugin_runtime_loader.load_modules(
            module_names=module_names,
            overwrite=overwrite,
            include_imported_classes=include_imported_classes,
        )

    def load_runtime_plugin_manifest(
        self,
        manifest: dict[str, Any],
        overwrite: bool = False,
    ) -> list[Any]:
        if self.plugin_runtime_loader is None:
            raise RuntimeError("PluginRuntimeLoader is not configured.")

        return self.plugin_runtime_loader.load_from_manifest(
            manifest=manifest,
            overwrite=overwrite,
        )

    # ========================================================
    # REGISTRATION
    # ========================================================

    def register_workflow(
        self,
        workflow_definition: WorkflowGraphDefinition,
        tags: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
        overwrite: bool = False,
    ) -> None:
        self._require_governance_allowed_sync(
            subject=workflow_definition,
            context={
                "governance_phase": "workflow_registration",
                "workflow_name": workflow_definition.workflow_name,
                "tags": tags,
                "metadata": metadata or {},
                "overwrite": overwrite,
            },
        )

        self._require_policy_allowed_sync(
            subject=workflow_definition,
            context={
                "policy_phase": "workflow_registration",
                "workflow_name": workflow_definition.workflow_name,
                "tags": tags,
                "metadata": metadata or {},
                "overwrite": overwrite,
            },
        )

        self.service.register_workflow(
            workflow_definition=workflow_definition,
            tags=tags,
            metadata=metadata,
            overwrite=overwrite,
        )

    async def register_workflow_async(
        self,
        workflow_definition: WorkflowGraphDefinition,
        tags: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
        overwrite: bool = False,
    ) -> None:
        await self._require_governance_allowed_async(
            subject=workflow_definition,
            context={
                "governance_phase": "workflow_registration",
                "workflow_name": workflow_definition.workflow_name,
                "tags": tags,
                "metadata": metadata or {},
                "overwrite": overwrite,
            },
        )

        await self._require_policy_allowed_async(
            subject=workflow_definition,
            context={
                "policy_phase": "workflow_registration",
                "workflow_name": workflow_definition.workflow_name,
                "tags": tags,
                "metadata": metadata or {},
                "overwrite": overwrite,
            },
        )

        self.service.register_workflow(
            workflow_definition=workflow_definition,
            tags=tags,
            metadata=metadata,
            overwrite=overwrite,
        )

    def unregister_workflow(
        self,
        workflow_name: str,
        *,
        confirmation: DestructiveOperationConfirmation,
    ) -> None:
        confirmation.require(
            operation=DestructiveWorkflowOperation.UNREGISTER_WORKFLOW,
            target=workflow_name,
        )
        self._require_governance_allowed_sync(
            subject=confirmation,
            context={
                "governance_phase": "workflow_unregister_preflight",
                "workflow_name": workflow_name,
            },
        )
        self._require_policy_allowed_sync(
            subject=confirmation,
            context={
                "policy_phase": "workflow_unregister_preflight",
                "workflow_name": workflow_name,
            },
        )
        self.registry.unregister(
            workflow_name,
        )

    # ========================================================
    # DISCOVERY
    # ========================================================

    def list_workflows(
        self,
        tag: str | None = None,
    ) -> list[str]:
        return self.service.list_workflows(
            tag=tag,
        )

    def list_workflow_summaries(
        self,
        tag: str | None = None,
    ) -> list[WorkflowSummary]:
        return self.service.list_workflow_summaries(
            tag=tag,
        )

    def describe_workflow(
        self,
        workflow_name: str,
    ) -> dict[str, Any]:
        return self.service.describe_workflow(
            workflow_name,
        )

    def workflow_exists(
        self,
        workflow_name: str,
    ) -> bool:
        return self.service.workflow_exists(
            workflow_name,
        )

    # ========================================================
    # COMPILE
    # ========================================================

    def compile_workflow(
        self,
        workflow_name: str,
        execution_id: str | None = None,
    ) -> CompiledWorkflow:
        return self.service.compile_workflow(
            workflow_name=workflow_name,
            execution_id=execution_id,
        )

    # ========================================================
    # EXECUTION
    # ========================================================

    async def run_workflow(
        self,
        workflow_name: str,
        execution_id: str | None = None,
        mode: str = "live",
        workflow_inputs: Mapping[str, Any] | None = None,
        simulation_time: datetime | None = None,
        archive_on_completion: bool = True,
        checkpoint_on_completion: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowRunResult:
        await self._require_governance_allowed_async(
            subject={
                "operation": "run_workflow",
                "workflow_name": workflow_name,
                "execution_id": execution_id,
                "mode": mode,
                "archive_on_completion": archive_on_completion,
                "checkpoint_on_completion": checkpoint_on_completion,
                "metadata": metadata or {},
            },
            context={
                "governance_phase": "workflow_run_preflight",
                "workflow_name": workflow_name,
                "execution_id": execution_id,
                "mode": mode,
            },
        )

        await self._require_policy_allowed_async(
            subject={
                "operation": "run_workflow",
                "workflow_name": workflow_name,
                "execution_id": execution_id,
                "mode": mode,
                "archive_on_completion": archive_on_completion,
                "checkpoint_on_completion": checkpoint_on_completion,
                "metadata": metadata or {},
            },
            context={
                "policy_phase": "workflow_run_preflight",
                "workflow_name": workflow_name,
                "execution_id": execution_id,
                "mode": mode,
            },
        )

        return await self.service.run_workflow(
            workflow_name=workflow_name,
            execution_id=execution_id,
            mode=mode,
            workflow_inputs=workflow_inputs,
            simulation_time=simulation_time,
            archive_on_completion=archive_on_completion,
            checkpoint_on_completion=checkpoint_on_completion,
            metadata=metadata,
        )

    async def run_from_context(
        self,
        workflow_name: str,
        context: RuntimeContext,
        archive_on_completion: bool = True,
        checkpoint_on_completion: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowRunResult:
        await self._require_governance_allowed_async(
            subject={
                "operation": "run_from_context",
                "workflow_name": workflow_name,
                "runtime_id": context.runtime_id,
                "execution_id": context.execution_id,
                "archive_on_completion": archive_on_completion,
                "checkpoint_on_completion": checkpoint_on_completion,
                "metadata": metadata or {},
            },
            context={
                "governance_phase": "workflow_run_from_context_preflight",
                "workflow_name": workflow_name,
                "runtime_id": context.runtime_id,
                "execution_id": context.execution_id,
            },
        )

        await self._require_policy_allowed_async(
            subject={
                "operation": "run_from_context",
                "workflow_name": workflow_name,
                "runtime_id": context.runtime_id,
                "execution_id": context.execution_id,
                "archive_on_completion": archive_on_completion,
                "checkpoint_on_completion": checkpoint_on_completion,
                "metadata": metadata or {},
            },
            context={
                "policy_phase": "workflow_run_from_context_preflight",
                "workflow_name": workflow_name,
                "runtime_id": context.runtime_id,
                "execution_id": context.execution_id,
            },
        )

        return await self.service.run_from_context(
            workflow_name=workflow_name,
            context=context,
            archive_on_completion=archive_on_completion,
            checkpoint_on_completion=checkpoint_on_completion,
            metadata=metadata,
        )

    # ========================================================
    # WORKFLOW CONTROL
    # ========================================================

    async def pause_workflow(
        self,
        execution_id: str,
        reason: str | None = None,
        requested_by: str | None = "workflow_facade",
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowControlSnapshot:
        await self._require_control_operation_allowed(
            operation="pause_workflow",
            execution_id=execution_id,
            reason=reason,
            requested_by=requested_by,
            metadata=metadata,
        )
        return await self._require_workflow_control_manager().request_pause(
            execution_id=execution_id,
            reason=reason,
            requested_by=requested_by,
            metadata=metadata,
        )

    async def resume_workflow(
        self,
        execution_id: str,
        reason: str | None = None,
        requested_by: str | None = "workflow_facade",
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowControlSnapshot:
        await self._require_control_operation_allowed(
            operation="resume_workflow",
            execution_id=execution_id,
            reason=reason,
            requested_by=requested_by,
            metadata=metadata,
        )
        return await self._require_workflow_control_manager().request_resume(
            execution_id=execution_id,
            reason=reason,
            requested_by=requested_by,
            metadata=metadata,
        )

    async def cancel_workflow(
        self,
        execution_id: str,
        reason: str | None = None,
        requested_by: str | None = "workflow_facade",
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowControlSnapshot:
        await self._require_control_operation_allowed(
            operation="cancel_workflow",
            execution_id=execution_id,
            reason=reason,
            requested_by=requested_by,
            metadata=metadata,
        )
        return await self._require_workflow_control_manager().request_cancel(
            execution_id=execution_id,
            reason=reason,
            requested_by=requested_by,
            metadata=metadata,
        )

    def get_workflow_state(
        self,
        execution_id: str,
    ) -> WorkflowControlState:
        return self._require_workflow_control_manager().get_state(
            execution_id,
        )

    def get_workflow_control_snapshot(
        self,
        execution_id: str,
    ) -> WorkflowControlSnapshot:
        return self._require_workflow_control_manager().get_snapshot(
            execution_id,
        )

    async def _require_control_operation_allowed(
        self,
        *,
        operation: str,
        execution_id: str,
        reason: str | None,
        requested_by: str | None,
        metadata: dict[str, Any] | None,
    ) -> None:
        subject = {
            "operation": operation,
            "execution_id": execution_id,
            "reason": reason,
            "requested_by": requested_by,
            "metadata": metadata or {},
        }
        await self._require_governance_allowed_async(
            subject=subject,
            context={
                "governance_phase": "workflow_control_preflight",
                "control_operation": operation,
                "execution_id": execution_id,
            },
        )
        await self._require_policy_allowed_async(
            subject=subject,
            context={
                "policy_phase": "workflow_control_preflight",
                "control_operation": operation,
                "execution_id": execution_id,
            },
        )

    def _require_workflow_control_manager(
        self,
    ) -> WorkflowControlManager:
        if self.workflow_control_manager is None:
            raise RuntimeError("WorkflowControlManager is not configured.")
        return self.workflow_control_manager

    # ========================================================
    # CHECKPOINTS
    # ========================================================

    async def restore_context_from_checkpoint(
        self,
        checkpoint_file: str,
    ) -> RuntimeContext:
        subject = {
            "operation": "restore_context_from_checkpoint",
            "checkpoint_file": checkpoint_file,
        }
        await self._require_governance_allowed_async(
            subject=subject,
            context={
                "governance_phase": "checkpoint_restore_preflight",
            },
        )
        await self._require_policy_allowed_async(
            subject=subject,
            context={
                "policy_phase": "checkpoint_restore_preflight",
            },
        )
        return await self.service.restore_context_from_checkpoint(
            checkpoint_file,
        )

    # ========================================================
    # COMPLETED RUN ARCHIVE
    # ========================================================

    async def list_completed_runs(
        self,
        workflow_name: str,
    ) -> list[str]:
        return await self.service.list_completed_runs(
            workflow_name,
        )

    async def load_completed_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> RuntimeContext | None:
        return await self.service.load_completed_run(
            workflow_name,
            execution_id,
        )

    async def delete_completed_run(
        self,
        workflow_name: str,
        execution_id: str,
        *,
        confirmation: DestructiveOperationConfirmation,
    ) -> None:
        target = f"{workflow_name}:{execution_id}"
        confirmation.require(
            operation=DestructiveWorkflowOperation.DELETE_COMPLETED_RUN,
            target=target,
        )
        await self._require_destructive_operation_allowed(
            confirmation=confirmation,
            phase="completed_run_delete_preflight",
        )
        await self.service.delete_completed_run(
            workflow_name,
            execution_id,
        )

    async def cleanup_completed_runs(
        self,
        max_age_days: int | None = None,
        max_count: int | None = None,
        *,
        confirmation: DestructiveOperationConfirmation,
    ) -> int:
        confirmation.require(
            operation=DestructiveWorkflowOperation.CLEANUP_COMPLETED_RUNS,
            target="completed_runs",
        )
        await self._require_destructive_operation_allowed(
            confirmation=confirmation,
            phase="completed_run_cleanup_preflight",
        )
        return await self.service.cleanup_completed_runs(
            max_age_days=max_age_days,
            max_count=max_count,
        )

    async def _require_destructive_operation_allowed(
        self,
        *,
        confirmation: DestructiveOperationConfirmation,
        phase: str,
    ) -> None:
        await self._require_governance_allowed_async(
            subject=confirmation,
            context={
                "governance_phase": phase,
                "operation": confirmation.operation.value,
                "target": confirmation.target,
                "requested_by": confirmation.requested_by,
            },
        )
        await self._require_policy_allowed_async(
            subject=confirmation,
            context={
                "policy_phase": phase,
                "operation": confirmation.operation.value,
                "target": confirmation.target,
                "requested_by": confirmation.requested_by,
            },
        )

    # ========================================================
    # POLICY HELPERS
    # ========================================================

    async def _require_policy_allowed_async(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> None:
        if self.policy_engine is None:
            return

        await self.policy_engine.require_allowed(
            subject=subject,
            context=context,
        )

    def _require_policy_allowed_sync(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> None:
        if self.policy_engine is None:
            return

        try:
            loop = asyncio.get_running_loop()

        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            raise RuntimeError(
                "Synchronous workflow policy enforcement cannot run while "
                "an event loop is already active. Use an async registration "
                "path or register workflows before entering the event loop."
            )

        asyncio.run(
            self.policy_engine.require_allowed(
                subject=subject,
                context=context,
            )
        )

    # ========================================================
    # GOVERNANCE HELPERS
    # ========================================================

    async def _require_governance_allowed_async(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> None:
        if self.governance_engine is None:
            return

        await self.governance_engine.require_allowed(
            subject=subject,
            context=context,
        )

    def _require_governance_allowed_sync(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> None:
        if self.governance_engine is None:
            return

        try:
            loop = asyncio.get_running_loop()

        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            raise RuntimeError(
                "Synchronous workflow governance enforcement cannot run while "
                "an event loop is already active. Use an async registration "
                "path or register workflows before entering the event loop."
            )

        asyncio.run(
            self.governance_engine.require_allowed(
                subject=subject,
                context=context,
            )
        )
