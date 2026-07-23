from __future__ import annotations

from core.plugins.lifecycle.plugin_lifecycle_manager import PluginLifecycleManager
from core.plugins.lifecycle.plugin_telemetry_hook import PluginTelemetryHook
from core.plugins.runtime.plugin_runtime_loader import PluginRuntimeLoader
from core.plugins.runtime.plugin_runtime_manager import PluginRuntimeManager
from core.plugins.runtime.plugin_workflow_loader import PluginWorkflowLoader
from core.runtime.artifacts.artifact_manager import ArtifactManager
from core.runtime.artifacts.artifact_store import LocalArtifactStore
from core.runtime.checkpoints.checkpoint_manager import CheckpointManager
from core.runtime.control import WorkflowControlManager
from core.runtime.events.event_bus import EventBus
from core.runtime.execution.runtime_engine import RuntimeEngine
from core.runtime.factory.runtime_node_factory import RuntimeNodeFactory
from core.runtime.governance.governance_engine import GovernanceEngine
from core.runtime.governance.governance_telemetry import GovernanceTelemetryEmitter
from core.runtime.lifecycle.runtime_lifecycle_failure_telemetry import (
    RuntimeLifecycleFailureTelemetry,
)
from core.runtime.lifecycle.runtime_lifecycle_manager import RuntimeLifecycleManager
from core.runtime.policies.policy_engine import PolicyEngine
from core.runtime.policies.policy_telemetry import PolicyTelemetryEmitter
from core.runtime.replay.replay_engine import ReplayEngine
from core.runtime.state.state_manager import StateManager
from core.runtime.telemetry.jsonl_runtime_telemetry_sink import (
    JsonlRuntimeTelemetrySink,
)
from core.runtime.telemetry.runtime_telemetry import RuntimeTelemetry
from core.runtime.telemetry.runtime_telemetry_hook import RuntimeTelemetryHook
from core.storage.persistence.postgres_completed_run_archive import (
    PostgresCompletedRunArchive,
)
from core.storage.persistence.runtime import (
    RuntimePersistenceEventSubscriber,
    RuntimePersistenceEventSubscriberConfig,
)
from core.telemetry.emitters.bootstrap_configuration_telemetry import (
    BootstrapConfigurationTelemetry,
    configuration_setting_names,
    emergency_log_configuration_failure,
)
from core.telemetry.integrations.opentelemetry import (
    OpenTelemetryConfig,
    OpenTelemetrySink,
)
from core.telemetry.integrations.prometheus import (
    PrometheusMetricsConfig,
    PrometheusMetricsExporter,
)
from core.telemetry.logging import TelemetryLogger
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.runtime_telemetry_sink import CoreTelemetryRuntimeSink
from core.workflow.bootstrap.workflow_configuration import (
    WorkflowBootstrapConfigurationError,
    validate_required_workflow_configuration,
)
from core.workflow.bootstrap.workflow_runtime_components import (
    WorkflowBootstrapConfig,
    WorkflowFacadeConfig,
    WorkflowRuntimeComponents,
    WorkflowRuntimeOverrides,
)
from core.workflow.compiler.workflow_compiler import WorkflowCompiler
from core.workflow.execution.workflow_engine import WorkflowEngine
from core.workflow.execution.workflow_runner import WorkflowRunner
from core.workflow.execution.workflow_service import WorkflowService
from core.workflow.registry.workflow_registry import WorkflowRegistry


class WorkflowRuntimeAssembler:
    """Build the canonical workflow runtime object graph."""

    def assemble_bootstrap(
        self,
        config: WorkflowBootstrapConfig,
        overrides: WorkflowRuntimeOverrides,
    ) -> WorkflowRuntimeComponents:
        event_bus = overrides.event_bus or EventBus()
        archive = overrides.archive or PostgresCompletedRunArchive()
        workflow_control_manager = (
            overrides.workflow_control_manager
            or WorkflowControlManager(
                event_bus=event_bus,
            )
        )

        observability_manager, prometheus_metrics_exporter = (
            self._assemble_observability(
                config=config,
                overrides=overrides,
            )
        )
        lifecycle_manager = self._assemble_runtime_lifecycle_manager(
            enabled=config.enable_observability,
            supplied=overrides.lifecycle_manager,
            observability_manager=observability_manager,
        )
        telemetry = self._assemble_runtime_telemetry(
            config=config,
            supplied=overrides.telemetry,
            observability_manager=observability_manager,
        )
        policy_engine = self._assemble_policy_engine(
            enabled=config.enable_policies,
            supplied=overrides.policy_engine,
            observability_manager=(
                observability_manager if config.enable_observability else None
            ),
        )
        governance_engine = self._assemble_governance_engine(
            enabled=config.enable_governance,
            supplied=overrides.governance_engine,
            observability_manager=(
                observability_manager if config.enable_observability else None
            ),
        )
        try:
            runtime_persistence_subscriber = (
                overrides.runtime_persistence_subscriber
                or self._build_runtime_persistence_subscriber(config)
            )
        except Exception as error:
            self._configuration_telemetry(
                observability_manager
            ).emit_configuration_failure(
                component="postgres_runtime_persistence",
                invalid_setting_names=("POLARIS_DATABASE_URL",),
                required=True,
                error=error,
                details={"persistence_enabled": True},
            )
            raise
        if runtime_persistence_subscriber is not None:
            runtime_persistence_subscriber.subscribe(event_bus)

        return self.assemble_facade(
            config=config.facade_config(),
            overrides=WorkflowRuntimeOverrides(
                archive=archive,
                event_bus=event_bus,
                lifecycle_manager=lifecycle_manager,
                workflow_control_manager=workflow_control_manager,
                artifact_store=overrides.artifact_store,
                artifact_manager=overrides.artifact_manager,
                telemetry=telemetry,
                observability_manager=observability_manager,
                runtime_node_factory=overrides.runtime_node_factory,
                plugin_runtime_loader=overrides.plugin_runtime_loader,
                plugin_workflow_loader=overrides.plugin_workflow_loader,
                plugin_runtime_manager=overrides.plugin_runtime_manager,
                policy_engine=policy_engine,
                governance_engine=governance_engine,
                runtime_persistence_subscriber=runtime_persistence_subscriber,
                opentelemetry_config=overrides.opentelemetry_config,
                prometheus_metrics_exporter=prometheus_metrics_exporter,
                di_container=overrides.di_container,
            ),
        )

    def assemble_facade(
        self,
        config: WorkflowFacadeConfig,
        overrides: WorkflowRuntimeOverrides,
    ) -> WorkflowRuntimeComponents:
        registry = WorkflowRegistry()
        event_bus = overrides.event_bus or EventBus()
        observability_manager = (
            overrides.observability_manager or ObservabilityManager()
        )
        lifecycle_manager = self._assemble_runtime_lifecycle_manager(
            enabled=config.enable_observability,
            supplied=overrides.lifecycle_manager,
            observability_manager=observability_manager,
        )
        event_bus.subscribe_lifecycle_manager(lifecycle_manager)

        workflow_control_manager = (
            overrides.workflow_control_manager
            or WorkflowControlManager(
                event_bus=event_bus,
            )
        )
        runtime_node_factory = overrides.runtime_node_factory or RuntimeNodeFactory(
            container=overrides.di_container,
        )
        plugin_runtime_loader = overrides.plugin_runtime_loader or PluginRuntimeLoader(
            node_factory=runtime_node_factory,
        )
        plugin_workflow_loader = (
            overrides.plugin_workflow_loader or PluginWorkflowLoader()
        )
        plugin_runtime_manager = overrides.plugin_runtime_manager
        if plugin_runtime_manager is None:
            plugin_telemetry_hook = (
                PluginTelemetryHook(
                    observability_manager=observability_manager,
                )
                if config.enable_observability
                else None
            )
            plugin_lifecycle_manager = PluginLifecycleManager(
                hooks=(
                    [plugin_telemetry_hook]
                    if plugin_telemetry_hook is not None
                    else None
                ),
                failure_handler=(
                    plugin_telemetry_hook.emit_hook_failure
                    if plugin_telemetry_hook is not None
                    else None
                ),
            )
            plugin_runtime_manager = PluginRuntimeManager(
                runtime_loader=plugin_runtime_loader,
                workflow_loader=plugin_workflow_loader,
                lifecycle_manager=plugin_lifecycle_manager,
                policy_engine=overrides.policy_engine,
            )
        compiler = WorkflowCompiler(
            runtime_node_factory=runtime_node_factory,
        )

        telemetry = overrides.telemetry
        telemetry_hook: RuntimeTelemetryHook | None = None
        if config.enable_telemetry:
            telemetry = telemetry or RuntimeTelemetry()
            telemetry_hook = RuntimeTelemetryHook(telemetry=telemetry)
            lifecycle_manager.register(telemetry_hook)

        artifact_store = overrides.artifact_store
        if artifact_store is None and config.enable_artifacts:
            artifact_store = LocalArtifactStore(base_path=config.artifact_dir)

        artifact_manager = overrides.artifact_manager
        if artifact_manager is None and artifact_store is not None:
            artifact_manager = ArtifactManager(artifact_store=artifact_store)

        checkpoint_manager = (
            CheckpointManager(
                checkpoint_dir=config.checkpoint_dir,
                event_bus=event_bus,
            )
            if config.enable_checkpoints
            else None
        )
        runtime_engine = RuntimeEngine(
            lifecycle_manager=lifecycle_manager,
            artifact_manager=artifact_manager,
            checkpoint_manager=checkpoint_manager,
            checkpoint_on_wave_completion=config.checkpoint_on_wave_completion,
            control_manager=workflow_control_manager,
            event_bus=event_bus,
            observability_manager=observability_manager,
        )
        state_manager = StateManager(archive=overrides.archive)
        workflow_engine = WorkflowEngine(
            runtime_engine=runtime_engine,
            state_manager=state_manager,
            event_bus=event_bus,
            checkpoint_manager=checkpoint_manager,
        )
        runner = WorkflowRunner(
            registry=registry,
            compiler=compiler,
            workflow_engine=workflow_engine,
        )
        service = WorkflowService(
            registry=registry,
            runner=runner,
            checkpoint_manager=checkpoint_manager,
            state_manager=state_manager,
        )
        replay_engine = (
            ReplayEngine(
                workflow_engine=workflow_engine,
                checkpoint_manager=checkpoint_manager,
                event_bus=event_bus,
                policy_engine=overrides.policy_engine,
                governance_engine=overrides.governance_engine,
            )
            if checkpoint_manager is not None
            else None
        )

        return WorkflowRuntimeComponents(
            registry=registry,
            compiler=compiler,
            runtime_engine=runtime_engine,
            state_manager=state_manager,
            workflow_engine=workflow_engine,
            runner=runner,
            service=service,
            replay_engine=replay_engine,
            event_bus=event_bus,
            workflow_control_manager=workflow_control_manager,
            checkpoint_manager=checkpoint_manager,
            lifecycle_manager=lifecycle_manager,
            artifact_store=artifact_store,
            artifact_manager=artifact_manager,
            telemetry=telemetry,
            telemetry_hook=telemetry_hook,
            observability_manager=observability_manager,
            prometheus_metrics_exporter=overrides.prometheus_metrics_exporter,
            runtime_node_factory=runtime_node_factory,
            plugin_runtime_loader=plugin_runtime_loader,
            plugin_workflow_loader=plugin_workflow_loader,
            plugin_runtime_manager=plugin_runtime_manager,
            policy_engine=overrides.policy_engine,
            governance_engine=overrides.governance_engine,
            archive=overrides.archive,
            runtime_persistence_subscriber=overrides.runtime_persistence_subscriber,
        )

    def _assemble_observability(  # noqa: C901
        self,
        config: WorkflowBootstrapConfig,
        overrides: WorkflowRuntimeOverrides,
    ) -> tuple[ObservabilityManager | None, PrometheusMetricsExporter | None]:
        observability_manager = overrides.observability_manager
        prometheus_metrics_exporter = overrides.prometheus_metrics_exporter

        if observability_manager is None:
            try:
                observability_manager = ObservabilityManager(
                    enable_domain_metrics=config.enable_domain_metrics,
                )
            except Exception as error:
                emergency_log_configuration_failure(
                    component="observability",
                    invalid_setting_names=("enable_domain_metrics",),
                    error=error,
                    details={"configuration_source": "workflow_bootstrap"},
                )
                raise

        configuration_telemetry = self._configuration_telemetry(
            observability_manager,
        )

        if config.enable_observability and config.enable_telemetry_logging:
            try:
                if not config.telemetry_logger_name.strip():
                    raise ValueError("telemetry_logger_name cannot be empty.")
                observability_manager.add_sink(
                    TelemetryLogger(logger_name=config.telemetry_logger_name)
                )
            except Exception as error:
                configuration_telemetry.emit_configuration_failure(
                    component="telemetry_logging",
                    invalid_setting_names=("telemetry_logger_name",),
                    required=False,
                    error=error,
                    details={"integration_enabled": True},
                )

        try:
            validate_required_workflow_configuration(config)
        except WorkflowBootstrapConfigurationError as error:
            configuration_telemetry.emit_configuration_failure(
                component="workflow_runtime",
                invalid_setting_names=error.invalid_setting_names,
                required=True,
                error=error,
                details={"configuration_source": "workflow_bootstrap"},
            )
            raise

        if not config.enable_observability:
            if config.enable_opentelemetry:
                configuration_telemetry.emit_configuration_failure(
                    component="opentelemetry",
                    invalid_setting_names=("enable_observability",),
                    required=False,
                    error=ValueError("OpenTelemetry requires observability."),
                    details={"integration_enabled": True},
                )
            if config.enable_prometheus_metrics:
                configuration_telemetry.emit_configuration_failure(
                    component="prometheus",
                    invalid_setting_names=("enable_observability",),
                    required=False,
                    error=ValueError("Prometheus requires observability."),
                    details={"integration_enabled": True},
                )
            return observability_manager, prometheus_metrics_exporter

        if config.enable_opentelemetry:
            try:
                opentelemetry_config = (
                    overrides.opentelemetry_config or OpenTelemetryConfig.from_env()
                )
                self._validate_opentelemetry_config(opentelemetry_config)
                observability_manager.add_sink(
                    OpenTelemetrySink(
                        config=opentelemetry_config,
                    )
                )
            except Exception as error:
                configuration_telemetry.emit_configuration_failure(
                    component="opentelemetry",
                    invalid_setting_names=configuration_setting_names(
                        error,
                        fallback=("OpenTelemetry configuration",),
                    ),
                    required=False,
                    error=error,
                    details={"integration_enabled": True},
                )

        if config.enable_prometheus_metrics:
            try:
                prometheus_metrics_exporter = (
                    prometheus_metrics_exporter
                    or PrometheusMetricsExporter(
                        metrics_store=observability_manager.metrics_store,
                        config=PrometheusMetricsConfig(
                            host=config.prometheus_metrics_host,
                            port=config.prometheus_metrics_port,
                            path=config.prometheus_metrics_path,
                        ),
                    )
                )
                prometheus_metrics_exporter.start()
            except Exception as error:
                prometheus_metrics_exporter = None
                configuration_telemetry.emit_configuration_failure(
                    component="prometheus",
                    invalid_setting_names=(
                        "prometheus_metrics_host",
                        "prometheus_metrics_port",
                        "prometheus_metrics_path",
                    ),
                    required=False,
                    error=error,
                    details={"integration_enabled": True},
                )

        return observability_manager, prometheus_metrics_exporter

    def _assemble_runtime_lifecycle_manager(
        self,
        *,
        enabled: bool,
        supplied: RuntimeLifecycleManager | None,
        observability_manager: ObservabilityManager | None,
    ) -> RuntimeLifecycleManager:
        if supplied is not None:
            return supplied

        if enabled and observability_manager is not None:
            failure_telemetry = RuntimeLifecycleFailureTelemetry(observability_manager)
            return RuntimeLifecycleManager(
                failure_handler=failure_telemetry.emit_hook_failure,
            )

        return RuntimeLifecycleManager()

    def _assemble_runtime_telemetry(
        self,
        config: WorkflowBootstrapConfig,
        supplied: RuntimeTelemetry | None,
        observability_manager: ObservabilityManager | None,
    ) -> RuntimeTelemetry | None:
        telemetry = supplied
        if telemetry is None and config.enable_telemetry:
            telemetry = RuntimeTelemetry()

        if telemetry is not None and config.enable_jsonl_telemetry:
            try:
                if not config.telemetry_jsonl_path.strip():
                    raise ValueError("telemetry_jsonl_path cannot be empty.")
                telemetry.add_sink(
                    JsonlRuntimeTelemetrySink(file_path=config.telemetry_jsonl_path)
                )
            except Exception as error:
                if observability_manager is not None:
                    self._configuration_telemetry(
                        observability_manager
                    ).emit_configuration_failure(
                        component="jsonl_telemetry",
                        invalid_setting_names=("telemetry_jsonl_path",),
                        required=False,
                        error=error,
                        details={"integration_enabled": True},
                    )

        if (
            telemetry is not None
            and observability_manager is not None
            and config.enable_observability
            and config.enable_core_telemetry_sink
        ):
            telemetry.add_sink(CoreTelemetryRuntimeSink(sink=observability_manager))

        return telemetry

    @staticmethod
    def _configuration_telemetry(
        observability_manager: ObservabilityManager,
    ) -> BootstrapConfigurationTelemetry:
        return BootstrapConfigurationTelemetry(observability_manager)

    @staticmethod
    def _validate_opentelemetry_config(
        config: OpenTelemetryConfig,
    ) -> None:
        invalid_setting_names = tuple(
            setting_name
            for setting_name, value in (
                ("POLARIS_OTEL_SERVICE_NAME", config.service_name),
                ("POLARIS_OTEL_SERVICE_VERSION", config.service_version),
                ("POLARIS_OTEL_ENVIRONMENT", config.environment),
                ("POLARIS_OTEL_OTLP_ENDPOINT", config.otlp_endpoint),
            )
            if not value.strip()
        )
        if invalid_setting_names:
            raise ValueError(
                f"Invalid OpenTelemetry settings: {', '.join(invalid_setting_names)}."
            )

    def _assemble_policy_engine(
        self,
        enabled: bool,
        supplied: PolicyEngine | None,
        observability_manager: ObservabilityManager | None,
    ) -> PolicyEngine | None:
        policy_engine = supplied
        if policy_engine is None and enabled:
            policy_engine = PolicyEngine(
                telemetry_emitter=(
                    PolicyTelemetryEmitter(
                        observability_manager=observability_manager,
                    )
                    if observability_manager is not None
                    else None
                ),
            )
        elif (
            policy_engine is not None
            and policy_engine.telemetry_emitter is None
            and observability_manager is not None
        ):
            policy_engine.telemetry_emitter = PolicyTelemetryEmitter(
                observability_manager=observability_manager,
            )
        return policy_engine

    def _assemble_governance_engine(
        self,
        enabled: bool,
        supplied: GovernanceEngine | None,
        observability_manager: ObservabilityManager | None,
    ) -> GovernanceEngine | None:
        governance_engine = supplied
        if governance_engine is None and enabled:
            governance_engine = GovernanceEngine(
                telemetry_emitter=(
                    GovernanceTelemetryEmitter(
                        observability_manager=observability_manager,
                    )
                    if observability_manager is not None
                    else None
                ),
            )
        elif (
            governance_engine is not None
            and governance_engine.telemetry_emitter is None
            and observability_manager is not None
        ):
            governance_engine.telemetry_emitter = GovernanceTelemetryEmitter(
                observability_manager=observability_manager,
            )
        return governance_engine

    def _build_runtime_persistence_subscriber(
        self,
        config: WorkflowBootstrapConfig,
    ) -> RuntimePersistenceEventSubscriber | None:
        if not config.enable_postgres_runtime_persistence:
            return None

        from core.database.postgres import AsyncSessionLocal

        return RuntimePersistenceEventSubscriber(
            session_factory=AsyncSessionLocal,
            config=RuntimePersistenceEventSubscriberConfig(
                fail_fast=config.postgres_runtime_persistence_fail_fast,
            ),
        )
