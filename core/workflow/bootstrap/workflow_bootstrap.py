from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from core.plugins.runtime.plugin_runtime_loader import PluginRuntimeLoader
from core.plugins.runtime.plugin_runtime_manager import PluginRuntimeManager
from core.plugins.runtime.plugin_workflow_loader import PluginWorkflowLoader
from core.runtime.control import WorkflowControlManager
from core.runtime.events.event_bus import EventBus
from core.runtime.factory.runtime_node_factory import RuntimeNodeFactory
from core.runtime.governance.governance_engine import GovernanceEngine
from core.runtime.lifecycle.runtime_lifecycle_manager import (
    RuntimeLifecycleManager,
)
from core.runtime.policies.policy_engine import PolicyEngine
from core.runtime.replay.replay_engine import ReplayEngine
from core.runtime.telemetry.runtime_telemetry import RuntimeTelemetry
from core.storage.persistence.completed_run_archive import CompletedRunArchive
from core.storage.persistence.runtime import RuntimePersistenceEventSubscriber
from core.telemetry.integrations.opentelemetry import (
    OpenTelemetryConfig,
)
from core.telemetry.integrations.prometheus import (
    PrometheusMetricsExporter,
)
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)
from core.workflow.bootstrap.workflow_runtime_assembler import (
    WorkflowRuntimeAssembler,
)
from core.workflow.bootstrap.workflow_runtime_components import (
    WorkflowBootstrapConfig,
    WorkflowRuntimeOverrides,
)
from core.workflow.execution.workflow_facade import WorkflowFacade
from core.workflow.models.workflow_graph_definition import (
    WorkflowGraphDefinition,
)


@dataclass(frozen=True, slots=True)
class WorkflowBootstrapResult:
    facade: WorkflowFacade
    event_bus: EventBus
    archive: CompletedRunArchive
    lifecycle_manager: RuntimeLifecycleManager
    workflow_control_manager: WorkflowControlManager
    telemetry: RuntimeTelemetry | None
    observability_manager: ObservabilityManager | None
    prometheus_metrics_exporter: PrometheusMetricsExporter | None
    runtime_node_factory: RuntimeNodeFactory
    plugin_runtime_loader: PluginRuntimeLoader
    plugin_workflow_loader: PluginWorkflowLoader
    plugin_runtime_manager: PluginRuntimeManager
    policy_engine: PolicyEngine | None
    governance_engine: GovernanceEngine | None
    runtime_persistence_subscriber: RuntimePersistenceEventSubscriber | None
    replay_engine: ReplayEngine | None
    config: WorkflowBootstrapConfig

    def force_flush_telemetry(
        self,
    ) -> None:
        if self.observability_manager is not None:
            self.observability_manager.force_flush()

    def shutdown_telemetry(
        self,
    ) -> None:
        if self.prometheus_metrics_exporter is not None:
            self.prometheus_metrics_exporter.stop()

        if self.observability_manager is not None:
            self.observability_manager.shutdown()


class WorkflowBootstrap:
    def __init__(
        self,
        config: WorkflowBootstrapConfig | None = None,
        event_bus: EventBus | None = None,
        archive: CompletedRunArchive | None = None,
        lifecycle_manager: RuntimeLifecycleManager | None = None,
        workflow_control_manager: WorkflowControlManager | None = None,
        telemetry: RuntimeTelemetry | None = None,
        observability_manager: ObservabilityManager | None = None,
        runtime_node_factory: RuntimeNodeFactory | None = None,
        plugin_runtime_loader: PluginRuntimeLoader | None = None,
        plugin_workflow_loader: PluginWorkflowLoader | None = None,
        plugin_runtime_manager: PluginRuntimeManager | None = None,
        policy_engine: PolicyEngine | None = None,
        governance_engine: GovernanceEngine | None = None,
        runtime_persistence_subscriber: RuntimePersistenceEventSubscriber | None = None,
        opentelemetry_config: OpenTelemetryConfig | None = None,
        prometheus_metrics_exporter: PrometheusMetricsExporter | None = None,
        di_container: Any | None = None,
    ) -> None:
        self.config = config or WorkflowBootstrapConfig()
        self.overrides = WorkflowRuntimeOverrides(
            archive=archive,
            event_bus=event_bus,
            lifecycle_manager=lifecycle_manager,
            workflow_control_manager=workflow_control_manager,
            telemetry=telemetry,
            observability_manager=observability_manager,
            runtime_node_factory=runtime_node_factory,
            plugin_runtime_loader=plugin_runtime_loader,
            plugin_workflow_loader=plugin_workflow_loader,
            plugin_runtime_manager=plugin_runtime_manager,
            policy_engine=policy_engine,
            governance_engine=governance_engine,
            runtime_persistence_subscriber=runtime_persistence_subscriber,
            opentelemetry_config=opentelemetry_config,
            prometheus_metrics_exporter=prometheus_metrics_exporter,
            di_container=di_container,
        )

    def assemble(self) -> WorkflowBootstrapResult:
        """Compose the shared runtime graph without registering edge workflows."""
        return self._build_runtime(
            workflow_definitions=None,
            workflow_tags=None,
            workflow_metadata=None,
            overwrite=False,
        )

    def build(
        self,
        workflow_definitions: list[WorkflowGraphDefinition] | None = None,
        workflow_tags: dict[str, tuple[str, ...]] | None = None,
        workflow_metadata: dict[str, dict[str, Any]] | None = None,
        overwrite: bool = False,
    ) -> WorkflowBootstrapResult:
        result = self._build_runtime(
            workflow_definitions=workflow_definitions,
            workflow_tags=workflow_tags,
            workflow_metadata=workflow_metadata,
            overwrite=overwrite,
        )

        if self.config.autoload_plugins:
            self._autoload_plugins_sync(result)

        return result

    async def build_async(
        self,
        workflow_definitions: list[WorkflowGraphDefinition] | None = None,
        workflow_tags: dict[str, tuple[str, ...]] | None = None,
        workflow_metadata: dict[str, dict[str, Any]] | None = None,
        overwrite: bool = False,
    ) -> WorkflowBootstrapResult:
        result = self._build_runtime(
            workflow_definitions=None,
            workflow_tags=workflow_tags,
            workflow_metadata=workflow_metadata,
            overwrite=overwrite,
        )

        for workflow_definition in workflow_definitions or []:
            workflow_name = workflow_definition.workflow_name

            await result.facade.register_workflow_async(
                workflow_definition=workflow_definition,
                tags=(workflow_tags or {}).get(workflow_name, ()),
                metadata=(workflow_metadata or {}).get(workflow_name, {}),
                overwrite=overwrite,
            )

        if self.config.autoload_plugins:
            await self._autoload_plugins_async(result)

        return result

    def _build_runtime(
        self,
        workflow_definitions: list[WorkflowGraphDefinition] | None,
        workflow_tags: dict[str, tuple[str, ...]] | None,
        workflow_metadata: dict[str, dict[str, Any]] | None,
        overwrite: bool,
    ) -> WorkflowBootstrapResult:
        components = WorkflowRuntimeAssembler().assemble_bootstrap(
            config=self.config,
            overrides=self.overrides,
        )
        facade = WorkflowFacade._from_components(components)

        for workflow_definition in workflow_definitions or []:
            workflow_name = workflow_definition.workflow_name
            facade.register_workflow(
                workflow_definition=workflow_definition,
                tags=(workflow_tags or {}).get(workflow_name, ()),
                metadata=(workflow_metadata or {}).get(workflow_name, {}),
                overwrite=overwrite,
            )

        return WorkflowBootstrapResult(
            facade=facade,
            event_bus=components.event_bus,
            archive=self._require_archive(components.archive),
            lifecycle_manager=components.lifecycle_manager,
            workflow_control_manager=components.workflow_control_manager,
            telemetry=components.telemetry,
            observability_manager=components.observability_manager,
            prometheus_metrics_exporter=components.prometheus_metrics_exporter,
            runtime_node_factory=components.runtime_node_factory,
            plugin_runtime_loader=components.plugin_runtime_loader,
            plugin_workflow_loader=components.plugin_workflow_loader,
            plugin_runtime_manager=components.plugin_runtime_manager,
            policy_engine=components.policy_engine,
            governance_engine=components.governance_engine,
            runtime_persistence_subscriber=components.runtime_persistence_subscriber,
            replay_engine=components.replay_engine,
            config=self.config,
        )

    @staticmethod
    def _require_archive(
        archive: CompletedRunArchive | None,
    ) -> CompletedRunArchive:
        if archive is None:
            raise RuntimeError("WorkflowBootstrap did not initialize an archive.")
        return archive

    def _autoload_plugins_sync(
        self,
        result: WorkflowBootstrapResult,
    ) -> None:
        try:
            loop = asyncio.get_running_loop()

        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            raise RuntimeError(
                "WorkflowBootstrap.build() cannot autoload plugins while "
                "an event loop is already running. Use build_async() instead."
            )

        asyncio.run(self._autoload_plugins_async(result))

    async def _autoload_plugins_async(
        self,
        result: WorkflowBootstrapResult,
    ) -> None:
        if not result.config.plugin_dirs:
            return

        for plugin_dir in result.config.plugin_dirs:
            await result.facade.load_plugins_from_dir(
                plugin_dir=plugin_dir,
                recursive=result.config.autoload_plugins_recursive,
                overwrite=result.config.autoload_plugin_overwrite,
                register_workflows=(result.config.autoload_register_workflows),
            )


def build_workflow_runtime(
    workflow_definitions: list[WorkflowGraphDefinition] | None = None,
    config: WorkflowBootstrapConfig | None = None,
    event_bus: EventBus | None = None,
    archive: CompletedRunArchive | None = None,
    lifecycle_manager: RuntimeLifecycleManager | None = None,
    workflow_control_manager: WorkflowControlManager | None = None,
    telemetry: RuntimeTelemetry | None = None,
    observability_manager: ObservabilityManager | None = None,
    runtime_node_factory: RuntimeNodeFactory | None = None,
    plugin_runtime_loader: PluginRuntimeLoader | None = None,
    plugin_workflow_loader: PluginWorkflowLoader | None = None,
    plugin_runtime_manager: PluginRuntimeManager | None = None,
    policy_engine: PolicyEngine | None = None,
    governance_engine: GovernanceEngine | None = None,
    runtime_persistence_subscriber: RuntimePersistenceEventSubscriber | None = None,
    opentelemetry_config: OpenTelemetryConfig | None = None,
    prometheus_metrics_exporter: PrometheusMetricsExporter | None = None,
    di_container: Any | None = None,
    workflow_tags: dict[str, tuple[str, ...]] | None = None,
    workflow_metadata: dict[str, dict[str, Any]] | None = None,
    overwrite: bool = False,
) -> WorkflowBootstrapResult:
    bootstrap = WorkflowBootstrap(
        config=config,
        event_bus=event_bus,
        archive=archive,
        lifecycle_manager=lifecycle_manager,
        workflow_control_manager=workflow_control_manager,
        telemetry=telemetry,
        observability_manager=observability_manager,
        runtime_node_factory=runtime_node_factory,
        plugin_runtime_loader=plugin_runtime_loader,
        plugin_workflow_loader=plugin_workflow_loader,
        plugin_runtime_manager=plugin_runtime_manager,
        policy_engine=policy_engine,
        governance_engine=governance_engine,
        runtime_persistence_subscriber=runtime_persistence_subscriber,
        opentelemetry_config=opentelemetry_config,
        prometheus_metrics_exporter=prometheus_metrics_exporter,
        di_container=di_container,
    )

    return bootstrap.build(
        workflow_definitions=workflow_definitions,
        workflow_tags=workflow_tags,
        workflow_metadata=workflow_metadata,
        overwrite=overwrite,
    )


async def build_workflow_runtime_async(
    workflow_definitions: list[WorkflowGraphDefinition] | None = None,
    config: WorkflowBootstrapConfig | None = None,
    event_bus: EventBus | None = None,
    archive: CompletedRunArchive | None = None,
    lifecycle_manager: RuntimeLifecycleManager | None = None,
    workflow_control_manager: WorkflowControlManager | None = None,
    telemetry: RuntimeTelemetry | None = None,
    observability_manager: ObservabilityManager | None = None,
    runtime_node_factory: RuntimeNodeFactory | None = None,
    plugin_runtime_loader: PluginRuntimeLoader | None = None,
    plugin_workflow_loader: PluginWorkflowLoader | None = None,
    plugin_runtime_manager: PluginRuntimeManager | None = None,
    policy_engine: PolicyEngine | None = None,
    governance_engine: GovernanceEngine | None = None,
    runtime_persistence_subscriber: RuntimePersistenceEventSubscriber | None = None,
    opentelemetry_config: OpenTelemetryConfig | None = None,
    prometheus_metrics_exporter: PrometheusMetricsExporter | None = None,
    di_container: Any | None = None,
    workflow_tags: dict[str, tuple[str, ...]] | None = None,
    workflow_metadata: dict[str, dict[str, Any]] | None = None,
    overwrite: bool = False,
) -> WorkflowBootstrapResult:
    bootstrap = WorkflowBootstrap(
        config=config,
        event_bus=event_bus,
        archive=archive,
        lifecycle_manager=lifecycle_manager,
        workflow_control_manager=workflow_control_manager,
        telemetry=telemetry,
        observability_manager=observability_manager,
        runtime_node_factory=runtime_node_factory,
        plugin_runtime_loader=plugin_runtime_loader,
        plugin_workflow_loader=plugin_workflow_loader,
        plugin_runtime_manager=plugin_runtime_manager,
        policy_engine=policy_engine,
        governance_engine=governance_engine,
        runtime_persistence_subscriber=runtime_persistence_subscriber,
        opentelemetry_config=opentelemetry_config,
        prometheus_metrics_exporter=prometheus_metrics_exporter,
        di_container=di_container,
    )

    return await bootstrap.build_async(
        workflow_definitions=workflow_definitions,
        workflow_tags=workflow_tags,
        workflow_metadata=workflow_metadata,
        overwrite=overwrite,
    )
