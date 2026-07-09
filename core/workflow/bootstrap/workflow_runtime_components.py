from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.plugins.runtime.plugin_runtime_loader import PluginRuntimeLoader
from core.plugins.runtime.plugin_runtime_manager import PluginRuntimeManager
from core.plugins.runtime.plugin_workflow_loader import PluginWorkflowLoader
from core.runtime.artifacts.artifact_manager import ArtifactManager
from core.runtime.artifacts.artifact_store import ArtifactStore
from core.runtime.checkpoints.checkpoint_manager import CheckpointManager
from core.runtime.control import WorkflowControlManager
from core.runtime.events.event_bus import EventBus
from core.runtime.execution.runtime_engine import RuntimeEngine
from core.runtime.factory.runtime_node_factory import RuntimeNodeFactory
from core.runtime.governance.governance_engine import GovernanceEngine
from core.runtime.lifecycle.runtime_lifecycle_manager import RuntimeLifecycleManager
from core.runtime.policies.policy_engine import PolicyEngine
from core.runtime.replay.replay_engine import ReplayEngine
from core.runtime.state.state_manager import StateManager
from core.runtime.telemetry.runtime_telemetry import RuntimeTelemetry
from core.runtime.telemetry.runtime_telemetry_hook import RuntimeTelemetryHook
from core.storage.persistence.completed_run_archive import CompletedRunArchive
from core.storage.persistence.runtime import RuntimePersistenceEventSubscriber
from core.telemetry.integrations.opentelemetry import OpenTelemetryConfig
from core.telemetry.integrations.prometheus import PrometheusMetricsExporter
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.workflow.compiler.workflow_compiler import WorkflowCompiler
from core.workflow.execution.workflow_engine import WorkflowEngine
from core.workflow.execution.workflow_runner import WorkflowRunner
from core.workflow.execution.workflow_service import WorkflowService
from core.workflow.registry.workflow_registry import WorkflowRegistry


@dataclass(frozen=True, slots=True)
class WorkflowFacadeConfig:
    checkpoint_dir: str = "storage/checkpoints"
    artifact_dir: str = "storage/artifacts/runtime"
    enable_checkpoints: bool = True
    enable_artifacts: bool = True
    enable_telemetry: bool = True
    enable_observability: bool = True
    checkpoint_on_wave_completion: bool = False


@dataclass(frozen=True, slots=True)
class WorkflowBootstrapConfig:
    completed_run_retention_max_age_days: int | None = None
    completed_run_retention_max_count: int | None = None
    checkpoint_dir: str = "storage/checkpoints"
    artifact_dir: str = "storage/artifacts/runtime"
    telemetry_jsonl_path: str = "storage/telemetry/runtime_telemetry.jsonl"

    enable_checkpoints: bool = True
    enable_artifacts: bool = True
    enable_telemetry: bool = True
    enable_jsonl_telemetry: bool = True
    enable_observability: bool = True
    enable_core_telemetry_sink: bool = True
    enable_domain_metrics: bool = True
    enable_telemetry_logging: bool = True
    telemetry_logger_name: str = "polaris.telemetry"
    enable_opentelemetry: bool = False
    enable_prometheus_metrics: bool = False
    prometheus_metrics_host: str = "0.0.0.0"
    prometheus_metrics_port: int = 9464
    prometheus_metrics_path: str = "/metrics"

    checkpoint_on_wave_completion: bool = False

    enable_policies: bool = True
    enable_governance: bool = True

    enable_postgres_runtime_persistence: bool = False
    postgres_runtime_persistence_fail_fast: bool = False

    autoload_plugins: bool = False
    plugin_dirs: tuple[str, ...] = ()
    autoload_plugin_overwrite: bool = False
    autoload_plugins_recursive: bool = True
    autoload_register_workflows: bool = True

    def facade_config(self) -> WorkflowFacadeConfig:
        return WorkflowFacadeConfig(
            checkpoint_dir=self.checkpoint_dir,
            artifact_dir=self.artifact_dir,
            enable_checkpoints=self.enable_checkpoints,
            enable_artifacts=self.enable_artifacts,
            enable_telemetry=self.enable_telemetry,
            enable_observability=self.enable_observability,
            checkpoint_on_wave_completion=self.checkpoint_on_wave_completion,
        )


@dataclass(frozen=True, slots=True)
class WorkflowRuntimeOverrides:
    archive: CompletedRunArchive | None = None
    event_bus: EventBus | None = None
    lifecycle_manager: RuntimeLifecycleManager | None = None
    workflow_control_manager: WorkflowControlManager | None = None
    artifact_store: ArtifactStore | None = None
    artifact_manager: ArtifactManager | None = None
    telemetry: RuntimeTelemetry | None = None
    observability_manager: ObservabilityManager | None = None
    runtime_node_factory: RuntimeNodeFactory | None = None
    plugin_runtime_loader: PluginRuntimeLoader | None = None
    plugin_workflow_loader: PluginWorkflowLoader | None = None
    plugin_runtime_manager: PluginRuntimeManager | None = None
    policy_engine: PolicyEngine | None = None
    governance_engine: GovernanceEngine | None = None
    runtime_persistence_subscriber: RuntimePersistenceEventSubscriber | None = None
    opentelemetry_config: OpenTelemetryConfig | None = None
    prometheus_metrics_exporter: PrometheusMetricsExporter | None = None
    di_container: Any | None = None


@dataclass(frozen=True, slots=True)
class WorkflowRuntimeComponents:
    registry: WorkflowRegistry
    compiler: WorkflowCompiler
    runtime_engine: RuntimeEngine
    state_manager: StateManager
    workflow_engine: WorkflowEngine
    runner: WorkflowRunner
    service: WorkflowService
    replay_engine: ReplayEngine | None
    event_bus: EventBus
    workflow_control_manager: WorkflowControlManager
    checkpoint_manager: CheckpointManager | None
    lifecycle_manager: RuntimeLifecycleManager
    artifact_store: ArtifactStore | None
    artifact_manager: ArtifactManager | None
    telemetry: RuntimeTelemetry | None
    telemetry_hook: RuntimeTelemetryHook | None
    observability_manager: ObservabilityManager | None
    prometheus_metrics_exporter: PrometheusMetricsExporter | None
    runtime_node_factory: RuntimeNodeFactory
    plugin_runtime_loader: PluginRuntimeLoader
    plugin_workflow_loader: PluginWorkflowLoader
    plugin_runtime_manager: PluginRuntimeManager
    policy_engine: PolicyEngine | None
    governance_engine: GovernanceEngine | None
    archive: CompletedRunArchive | None
    runtime_persistence_subscriber: RuntimePersistenceEventSubscriber | None
