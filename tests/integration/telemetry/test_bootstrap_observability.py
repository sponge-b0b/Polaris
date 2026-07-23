from __future__ import annotations

from unittest.mock import patch

import pytest
from dishka import make_container

from core.bootstrap.workflow_providers import WorkflowInfrastructureProvider
from core.telemetry.events.telemetry_event import TelemetryEvent
from core.telemetry.integrations.opentelemetry import (
    OpenTelemetryConfig,
    OpenTelemetrySink,
)
from core.telemetry.logging import TelemetryLogger
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)
from core.telemetry.sinks.telemetry_sink import (
    InMemoryTelemetrySink,
)
from core.workflow.bootstrap import (
    workflow_runtime_assembler as workflow_runtime_assembler_module,
)
from core.workflow.bootstrap.workflow_bootstrap import (
    WorkflowBootstrapConfig,
    build_workflow_runtime,
    build_workflow_runtime_async,
)


class FakePrometheusMetricsExporter:
    def __init__(
        self,
        metrics_store: object,
        config: object | None = None,
    ) -> None:
        self.metrics_store = metrics_store
        self.config = config
        self.running = False
        self.server_address: tuple[str, int] | None = None
        self.start_calls = 0
        self.stop_calls = 0

    def start(
        self,
    ) -> None:
        self.start_calls += 1
        self.running = True
        self.server_address = (
            "127.0.0.1",
            0,
        )

    def stop(
        self,
    ) -> None:
        if not self.running:
            return

        self.stop_calls += 1
        self.running = False
        self.server_address = None


def install_fake_prometheus_exporter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        workflow_runtime_assembler_module,
        "PrometheusMetricsExporter",
        FakePrometheusMetricsExporter,
    )


def assert_fake_prometheus_exporter(
    exporter: object,
) -> FakePrometheusMetricsExporter:
    assert isinstance(
        exporter,
        FakePrometheusMetricsExporter,
    )
    return exporter


@pytest.mark.asyncio
async def test_bootstrap_observability_receives_runtime_telemetry() -> None:
    runtime = await build_workflow_runtime_async(
        config=WorkflowBootstrapConfig(
            enable_telemetry=True,
            enable_jsonl_telemetry=False,
            enable_observability=True,
            enable_core_telemetry_sink=True,
            autoload_plugins=True,
            plugin_dirs=("plugins/example_market_plugin",),
            autoload_plugins_recursive=False,
            autoload_plugin_overwrite=True,
            autoload_register_workflows=True,
        ),
    )

    assert runtime.observability_manager is not None

    sink = InMemoryTelemetrySink()

    runtime.observability_manager.add_sink(
        sink,
    )

    result = await runtime.facade.run_workflow(
        workflow_name="example_plugin_workflow",
        mode="simulation",
        archive_on_completion=False,
        checkpoint_on_completion=False,
    )

    assert result.success is True

    event_types = [event.event_type for event in sink.events]

    assert (
        event_types.count(
            "runtime.workflow.started",
        )
        == 1
    )
    assert (
        event_types.count(
            "runtime.workflow.completed",
        )
        == 1
    )
    assert (
        event_types.count(
            "runtime.wave.started",
        )
        == 1
    )
    assert (
        event_types.count(
            "runtime.wave.completed",
        )
        == 1
    )
    assert (
        event_types.count(
            "runtime.node.started",
        )
        == 1
    )
    assert (
        event_types.count(
            "runtime.node.completed",
        )
        == 1
    )
    assert "workflow_progress.workflow_started" in event_types
    assert "workflow_progress.workflow_running" in event_types
    assert "workflow_progress.workflow_completed" in event_types
    assert "workflow_progress.wave_started" in event_types
    assert "workflow_progress.wave_completed" in event_types
    assert "workflow_progress.node_started" in event_types
    assert "workflow_progress.node_running" in event_types
    assert "workflow_progress.node_completed" in event_types

    workflow_completed = [
        event
        for event in sink.events
        if event.event_type == "runtime.workflow.completed"
    ]

    assert workflow_completed

    assert workflow_completed[-1].success is True
    assert workflow_completed[-1].error_count == 0
    assert "runtime_event" not in workflow_completed[-1].payload
    assert workflow_completed[-1].workflow_id == "example_plugin_workflow"

    metrics = runtime.observability_manager.metrics_store.to_dict()

    assert metrics["counters"]
    assert any(key.startswith("telemetry.events.total") for key in metrics["counters"])


def opentelemetry_sinks(
    observability_manager: ObservabilityManager,
) -> list[OpenTelemetrySink]:
    return [
        sink
        for sink in observability_manager.collector.sinks
        if isinstance(
            sink,
            OpenTelemetrySink,
        )
    ]


def shutdown_opentelemetry_sinks(
    sinks: list[OpenTelemetrySink],
) -> None:
    for sink in sinks:
        sink.shutdown()


def telemetry_logger_sinks(
    observability_manager: ObservabilityManager,
) -> list[TelemetryLogger]:
    return [
        sink
        for sink in observability_manager.collector.sinks
        if isinstance(
            sink,
            TelemetryLogger,
        )
    ]


def test_workflow_bootstrap_wires_telemetry_logger_by_default() -> None:
    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            enable_jsonl_telemetry=False,
        ),
    )

    assert runtime.observability_manager is not None

    logger_sinks = telemetry_logger_sinks(
        runtime.observability_manager,
    )

    assert len(logger_sinks) == 1
    assert logger_sinks[0].logger_name == "polaris.telemetry"


def test_workflow_bootstrap_does_not_wire_telemetry_logger_when_disabled() -> None:
    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            enable_jsonl_telemetry=False,
            enable_telemetry_logging=False,
        ),
    )

    assert runtime.observability_manager is not None
    assert (
        telemetry_logger_sinks(
            runtime.observability_manager,
        )
        == []
    )


def test_workflow_bootstrap_uses_configured_telemetry_logger_name() -> None:
    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            enable_jsonl_telemetry=False,
            telemetry_logger_name="polaris.telemetry.custom",
        ),
    )

    assert runtime.observability_manager is not None

    logger_sinks = telemetry_logger_sinks(
        runtime.observability_manager,
    )

    assert len(logger_sinks) == 1
    assert logger_sinks[0].logger_name == "polaris.telemetry.custom"


def test_workflow_infrastructure_provider_wires_telemetry_logger_by_default() -> None:
    container = make_container(
        WorkflowInfrastructureProvider(
            config=WorkflowBootstrapConfig(
                enable_jsonl_telemetry=False,
            ),
        ),
    )

    observability_manager = container.get(
        ObservabilityManager,
    )

    logger_sinks = telemetry_logger_sinks(
        observability_manager,
    )

    assert len(logger_sinks) == 1
    assert logger_sinks[0].logger_name == "polaris.telemetry"


def test_workflow_infrastructure_provider_does_not_wire_telemetry_logger_when_disabled() -> (  # noqa: E501 - descriptive pytest node id
    None
):
    container = make_container(
        WorkflowInfrastructureProvider(
            config=WorkflowBootstrapConfig(
                enable_jsonl_telemetry=False,
                enable_telemetry_logging=False,
            ),
        ),
    )

    observability_manager = container.get(
        ObservabilityManager,
    )

    assert (
        telemetry_logger_sinks(
            observability_manager,
        )
        == []
    )


def test_workflow_bootstrap_does_not_wire_opentelemetry_by_default() -> None:
    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            enable_jsonl_telemetry=False,
        ),
    )

    assert runtime.observability_manager is not None
    assert opentelemetry_sinks(runtime.observability_manager) == []


def test_workflow_bootstrap_wires_opentelemetry_when_enabled() -> None:
    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            enable_jsonl_telemetry=False,
            enable_opentelemetry=True,
        ),
    )

    assert runtime.observability_manager is not None

    sinks = opentelemetry_sinks(runtime.observability_manager)

    try:
        assert len(sinks) == 1
    finally:
        shutdown_opentelemetry_sinks(sinks)


def test_workflow_infrastructure_provider_wires_opentelemetry_when_enabled() -> None:
    container = make_container(
        WorkflowInfrastructureProvider(
            config=WorkflowBootstrapConfig(
                enable_jsonl_telemetry=False,
                enable_opentelemetry=True,
            ),
        ),
    )

    observability_manager = container.get(
        ObservabilityManager,
    )
    sinks = opentelemetry_sinks(observability_manager)

    assert len(sinks) == 1
    assert sinks[0].to_dict()["shutdown"] is False

    container.close()

    assert sinks[0].to_dict()["shutdown"] is True


def test_workflow_bootstrap_does_not_start_prometheus_metrics_by_default() -> None:
    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            enable_jsonl_telemetry=False,
        ),
    )

    assert runtime.prometheus_metrics_exporter is None


def test_workflow_bootstrap_starts_prometheus_metrics_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_prometheus_exporter(
        monkeypatch,
    )

    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            enable_jsonl_telemetry=False,
            enable_prometheus_metrics=True,
            prometheus_metrics_host="127.0.0.1",
            prometheus_metrics_port=0,
        ),
    )

    exporter = assert_fake_prometheus_exporter(
        runtime.prometheus_metrics_exporter,
    )

    try:
        assert exporter.running is True
        assert exporter.server_address is not None
        assert exporter.start_calls == 1
    finally:
        exporter.stop()


def test_workflow_infrastructure_provider_starts_prometheus_metrics_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_prometheus_exporter(
        monkeypatch,
    )

    provider = WorkflowInfrastructureProvider(
        config=WorkflowBootstrapConfig(
            enable_jsonl_telemetry=False,
            enable_prometheus_metrics=True,
            prometheus_metrics_host="127.0.0.1",
            prometheus_metrics_port=0,
        ),
    )
    container = make_container(provider)
    observability_manager = container.get(
        ObservabilityManager,
    )
    exporter = assert_fake_prometheus_exporter(
        provider.prometheus_metrics_exporter,
    )

    assert exporter.running is True
    assert exporter.server_address is not None
    assert exporter.start_calls == 1

    with (
        patch.object(
            observability_manager,
            "force_flush",
            wraps=observability_manager.force_flush,
        ) as force_flush,
        patch.object(
            observability_manager,
            "shutdown",
            wraps=observability_manager.shutdown,
        ) as shutdown,
    ):
        container.close()

    assert exporter.running is False
    assert exporter.stop_calls == 1
    force_flush.assert_called_once_with()
    shutdown.assert_called_once_with()


def test_workflow_bootstrap_uses_env_backed_opentelemetry_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "POLARIS_OTEL_SERVICE_NAME",
        "polaris-env-service",
    )
    monkeypatch.setenv(
        "POLARIS_OTEL_SERVICE_VERSION",
        "9.9.9",
    )
    monkeypatch.setenv(
        "POLARIS_OTEL_ENVIRONMENT",
        "test",
    )
    monkeypatch.setenv(
        "POLARIS_OTEL_OTLP_ENDPOINT",
        "http://localhost:4317",
    )
    monkeypatch.setenv(
        "POLARIS_OTEL_INSECURE",
        "true",
    )

    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            enable_jsonl_telemetry=False,
            enable_opentelemetry=True,
        ),
    )

    assert runtime.observability_manager is not None

    sinks = opentelemetry_sinks(runtime.observability_manager)

    try:
        assert len(sinks) == 1
        assert sinks[0].config == OpenTelemetryConfig(
            service_name="polaris-env-service",
            service_version="9.9.9",
            environment="test",
            otlp_endpoint="http://localhost:4317",
            insecure=True,
        )
    finally:
        runtime.shutdown_telemetry()


def test_workflow_bootstrap_result_shutdowns_observability_components(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_prometheus_exporter(
        monkeypatch,
    )

    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            enable_jsonl_telemetry=False,
            enable_opentelemetry=True,
            enable_prometheus_metrics=True,
            prometheus_metrics_host="127.0.0.1",
            prometheus_metrics_port=0,
        ),
    )

    assert runtime.observability_manager is not None
    exporter = assert_fake_prometheus_exporter(
        runtime.prometheus_metrics_exporter,
    )
    sinks = opentelemetry_sinks(runtime.observability_manager)

    assert exporter.running is True
    assert exporter.start_calls == 1
    assert len(sinks) == 1

    runtime.shutdown_telemetry()
    runtime.shutdown_telemetry()

    assert exporter.running is False
    assert exporter.stop_calls == 1
    assert sinks[0].to_dict()["shutdown"] is True


class FailingPrometheusMetricsExporter(FakePrometheusMetricsExporter):
    def start(self) -> None:
        self.start_calls += 1
        raise OSError("metrics endpoint unavailable")


def configuration_failure_events(
    sink: InMemoryTelemetrySink,
) -> list[TelemetryEvent]:
    return [
        event
        for event in sink.events
        if event.event_type == "platform.bootstrap.configuration_failed"
    ]


def test_disabled_opentelemetry_does_not_parse_irrelevant_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POLARIS_OTEL_INSECURE", "invalid-boolean")

    provider = WorkflowInfrastructureProvider(
        config=WorkflowBootstrapConfig(
            enable_jsonl_telemetry=False,
            enable_opentelemetry=False,
        ),
    )
    container = make_container(provider)

    assert container.get(ObservabilityManager) is not None
    container.close()


def test_invalid_optional_opentelemetry_configuration_degrades_with_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POLARIS_OTEL_INSECURE", "invalid-boolean")
    sink = InMemoryTelemetrySink()
    manager = ObservabilityManager()
    manager.add_sink(sink)

    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            enable_jsonl_telemetry=False,
            enable_telemetry_logging=False,
            enable_opentelemetry=True,
        ),
        observability_manager=manager,
    )

    assert opentelemetry_sinks(manager) == []
    events = configuration_failure_events(sink)
    assert len(events) == 1
    assert events[0].level.value == "warning"
    assert events[0].payload["component"] == "opentelemetry"
    assert events[0].payload["startup_action"] == "continued_degraded"
    runtime.shutdown_telemetry()


def test_unavailable_optional_prometheus_exporter_degrades_with_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        workflow_runtime_assembler_module,
        "PrometheusMetricsExporter",
        FailingPrometheusMetricsExporter,
    )
    sink = InMemoryTelemetrySink()
    manager = ObservabilityManager()
    manager.add_sink(sink)

    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            enable_jsonl_telemetry=False,
            enable_telemetry_logging=False,
            enable_prometheus_metrics=True,
        ),
        observability_manager=manager,
    )

    assert runtime.prometheus_metrics_exporter is None
    events = configuration_failure_events(sink)
    assert len(events) == 1
    assert events[0].level.value == "warning"
    assert events[0].payload["component"] == "prometheus"
    assert events[0].payload["startup_action"] == "continued_degraded"


def test_invalid_optional_jsonl_path_degrades_with_warning() -> None:
    sink = InMemoryTelemetrySink()
    manager = ObservabilityManager()
    manager.add_sink(sink)

    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            telemetry_jsonl_path="   ",
            enable_telemetry_logging=False,
        ),
        observability_manager=manager,
    )

    assert runtime.telemetry is not None
    events = configuration_failure_events(sink)
    assert len(events) == 1
    assert events[0].level.value == "warning"
    assert events[0].payload["component"] == "jsonl_telemetry"


def test_invalid_required_workflow_configuration_fails_with_error_event() -> None:
    sink = InMemoryTelemetrySink()
    manager = ObservabilityManager()
    manager.add_sink(sink)

    with pytest.raises(ValueError, match="checkpoint_dir"):
        build_workflow_runtime(
            config=WorkflowBootstrapConfig(
                checkpoint_dir="   ",
                enable_jsonl_telemetry=False,
                enable_telemetry_logging=False,
            ),
            observability_manager=manager,
        )

    events = configuration_failure_events(sink)
    assert len(events) == 1
    assert events[0].level.value == "error"
    assert events[0].payload["component"] == "workflow_runtime"
    assert events[0].payload["invalid_setting_names"] == ["checkpoint_dir"]
    assert events[0].payload["startup_action"] == "failed"


def test_required_runtime_persistence_failure_emits_error_and_fails_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sink = InMemoryTelemetrySink()
    manager = ObservabilityManager()
    manager.add_sink(sink)

    def fail_persistence_build(*_: object) -> None:
        raise RuntimeError("runtime persistence unavailable")

    monkeypatch.setattr(
        workflow_runtime_assembler_module.WorkflowRuntimeAssembler,
        "_build_runtime_persistence_subscriber",
        fail_persistence_build,
    )

    with pytest.raises(RuntimeError, match="runtime persistence unavailable"):
        build_workflow_runtime(
            config=WorkflowBootstrapConfig(
                enable_jsonl_telemetry=False,
                enable_telemetry_logging=False,
                enable_postgres_runtime_persistence=True,
            ),
            observability_manager=manager,
        )

    events = configuration_failure_events(sink)
    assert len(events) == 1
    assert events[0].level.value == "error"
    assert events[0].payload["component"] == "postgres_runtime_persistence"
    assert events[0].payload["startup_action"] == "failed"


def test_observability_construction_failure_uses_emergency_critical_log(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger_name = "core.telemetry.emitters.bootstrap_configuration_telemetry"

    class FailingObservabilityManager:
        def __init__(self, **_: object) -> None:
            raise RuntimeError("observability construction failed")

    monkeypatch.setattr(
        workflow_runtime_assembler_module,
        "ObservabilityManager",
        FailingObservabilityManager,
    )

    with caplog.at_level("CRITICAL", logger=logger_name):
        with pytest.raises(RuntimeError, match="observability construction failed"):
            build_workflow_runtime(
                config=WorkflowBootstrapConfig(
                    enable_jsonl_telemetry=False,
                ),
            )

    records = [record for record in caplog.records if record.name == logger_name]
    assert len(records) == 1
    assert records[0].levelname == "CRITICAL"
    assert records[0].exc_info is not None
