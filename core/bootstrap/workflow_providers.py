from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from dishka import Provider, Scope, provide

from core.bootstrap.dishka_runtime_adapter import DishkaRuntimeAdapter
from core.plugins.lifecycle.plugin_lifecycle_manager import PluginLifecycleManager
from core.plugins.runtime.plugin_runtime_loader import PluginRuntimeLoader
from core.plugins.runtime.plugin_runtime_manager import PluginRuntimeManager
from core.plugins.runtime.plugin_workflow_loader import PluginWorkflowLoader
from core.runtime.control import WorkflowControlManager
from core.runtime.events.event_bus import EventBus
from core.runtime.factory.runtime_node_factory import RuntimeNodeFactory
from core.runtime.governance.governance_engine import GovernanceEngine
from core.runtime.lifecycle.runtime_lifecycle_manager import RuntimeLifecycleManager
from core.runtime.policies.policy_engine import PolicyEngine
from core.runtime.telemetry.runtime_telemetry import RuntimeTelemetry
from core.storage.persistence.completed_run_archive import CompletedRunArchive
from core.telemetry.integrations.opentelemetry import OpenTelemetryConfig
from core.telemetry.integrations.prometheus import PrometheusMetricsExporter
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.workflow.bootstrap.workflow_bootstrap import (
    WorkflowBootstrap,
    WorkflowBootstrapConfig,
    WorkflowBootstrapResult,
)
from core.workflow.execution.workflow_facade import WorkflowFacade, WorkflowFacadeConfig


class WorkflowInfrastructureProvider(Provider):
    """Dishka accessors for one canonical WorkflowBootstrap runtime."""

    scope = Scope.APP

    def __init__(
        self,
        config: WorkflowBootstrapConfig | None = None,
        opentelemetry_config: OpenTelemetryConfig | None = None,
    ) -> None:
        super().__init__()
        self.config = config or WorkflowBootstrapConfig()
        self.opentelemetry_config = opentelemetry_config
        self.prometheus_metrics_exporter: PrometheusMetricsExporter | None = None
        self.di_container: Any | None = None

    def bind_di_container(
        self,
        container: Any,
    ) -> None:
        """Bind the completed Dishka container before lazy runtime resolution."""
        self.di_container = container

    @provide
    def provide_workflow_bootstrap_config(self) -> WorkflowBootstrapConfig:
        return self.config

    @provide
    def provide_workflow_runtime(
        self,
        config: WorkflowBootstrapConfig,
    ) -> Iterator[WorkflowBootstrapResult]:
        runtime = WorkflowBootstrap(
            config=config,
            opentelemetry_config=self.opentelemetry_config,
            di_container=self.di_container,
        ).assemble()
        self.prometheus_metrics_exporter = runtime.prometheus_metrics_exporter
        try:
            yield runtime
        finally:
            runtime.force_flush_telemetry()
            runtime.shutdown_telemetry()

    @provide
    def provide_event_bus(self, runtime: WorkflowBootstrapResult) -> EventBus:
        return runtime.event_bus

    @provide
    def provide_workflow_control_manager(
        self,
        runtime: WorkflowBootstrapResult,
    ) -> WorkflowControlManager:
        return runtime.workflow_control_manager

    @provide
    def provide_completed_run_archive(
        self,
        runtime: WorkflowBootstrapResult,
    ) -> CompletedRunArchive:
        return runtime.archive

    @provide
    def provide_runtime_lifecycle_manager(
        self,
        runtime: WorkflowBootstrapResult,
    ) -> RuntimeLifecycleManager:
        return runtime.lifecycle_manager

    @provide
    def provide_observability_manager(
        self,
        runtime: WorkflowBootstrapResult,
    ) -> ObservabilityManager:
        if runtime.observability_manager is None:
            raise RuntimeError("Workflow observability is disabled.")
        return runtime.observability_manager

    @provide
    def provide_policy_engine(
        self,
        runtime: WorkflowBootstrapResult,
    ) -> PolicyEngine:
        if runtime.policy_engine is None:
            raise RuntimeError("Workflow policies are disabled.")
        return runtime.policy_engine

    @provide
    def provide_governance_engine(
        self,
        runtime: WorkflowBootstrapResult,
    ) -> GovernanceEngine:
        if runtime.governance_engine is None:
            raise RuntimeError("Workflow governance is disabled.")
        return runtime.governance_engine

    @provide
    def provide_runtime_telemetry(
        self,
        runtime: WorkflowBootstrapResult,
    ) -> RuntimeTelemetry:
        if runtime.telemetry is None:
            raise RuntimeError("Workflow telemetry is disabled.")
        return runtime.telemetry

    @provide
    def provide_runtime_node_factory(
        self,
        runtime: WorkflowBootstrapResult,
    ) -> RuntimeNodeFactory:
        return runtime.runtime_node_factory

    @provide
    def provide_plugin_runtime_loader(
        self,
        runtime: WorkflowBootstrapResult,
    ) -> PluginRuntimeLoader:
        return runtime.plugin_runtime_loader

    @provide
    def provide_plugin_workflow_loader(
        self,
        runtime: WorkflowBootstrapResult,
    ) -> PluginWorkflowLoader:
        return runtime.plugin_workflow_loader

    @provide
    def provide_plugin_lifecycle_manager(
        self,
        runtime: WorkflowBootstrapResult,
    ) -> PluginLifecycleManager:
        return runtime.plugin_runtime_manager.lifecycle_manager

    @provide
    def provide_plugin_runtime_manager(
        self,
        runtime: WorkflowBootstrapResult,
    ) -> PluginRuntimeManager:
        return runtime.plugin_runtime_manager

    @provide
    def provide_workflow_facade_config(
        self,
        config: WorkflowBootstrapConfig,
    ) -> WorkflowFacadeConfig:
        return config.facade_config()

    @provide
    def provide_workflow_facade(
        self,
        runtime: WorkflowBootstrapResult,
    ) -> WorkflowFacade:
        return runtime.facade


class DishkaRuntimeNodeProvider(Provider):
    """
    Provider for exposing DishkaRuntimeAdapter.

    Use this when RuntimeNodeFactory should resolve RuntimeNode instances
    from a Dishka container.
    """

    scope = Scope.APP

    def __init__(
        self,
        container: Any,
        use_scope: bool = False,
    ) -> None:
        super().__init__()

        self.container = container
        self.use_scope = use_scope

    @provide
    def provide_dishka_runtime_adapter(
        self,
    ) -> DishkaRuntimeAdapter:
        return DishkaRuntimeAdapter(
            container=self.container,
            use_scope=self.use_scope,
        )
