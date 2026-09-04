from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

yaml = importlib.import_module("yaml")

_REPOSITORY_ROOT = Path(__file__).parents[3]
_PROMETHEUS_CONFIG = _REPOSITORY_ROOT / "deployment/prometheus/prometheus.yml"
_PROMETHEUS_ALERTS = _REPOSITORY_ROOT / "deployment/prometheus/alerts.yml"
_GRAFANA_DASHBOARD = (
    _REPOSITORY_ROOT
    / "deployment/grafana/dashboards/polaris-core-telemetry-overview.json"
)
_DOCKER_COMPOSE = _REPOSITORY_ROOT / "docker-compose.yml"


def _yaml_mapping(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text())
    assert isinstance(document, dict)
    return document


def test_prometheus_loads_repository_owned_observability_alerts() -> None:
    config = _yaml_mapping(_PROMETHEUS_CONFIG)
    compose = _yaml_mapping(_DOCKER_COMPOSE)

    assert config["rule_files"] == ["/etc/prometheus/alerts.yml"]
    assert (
        "./deployment/prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro"
        in compose["services"]["prometheus"]["volumes"]
    )


def test_prometheus_alerts_cover_required_operational_failures() -> None:
    alerts = _yaml_mapping(_PROMETHEUS_ALERTS)
    rules = alerts["groups"][0]["rules"]
    expressions = {rule["alert"]: rule["expr"] for rule in rules}

    assert set(expressions) == {
        "PolarisApplicationServiceRetrySpike",
        "PolarisApplicationServiceDegraded",
        "PolarisIntegrationClientRetrySpike",
        "PolarisTelemetrySinkFailure",
        "PolarisConfigurationFailure",
        "PolarisCallbackFailure",
    }
    rendered_expressions = "\n".join(expressions.values())
    for metric_name in (
        "application_service_configuration_failures",
        "application_service_retries",
        "application_service_degraded",
        "integration_client_retries",
        "telemetry_sink_failures",
        "plugin_lifecycle_callback_failures",
        "runtime_lifecycle_callback_failures",
        "runtime_event_bus_subscriber_failures",
        "platform_bootstrap_configuration_failures",
    ):
        assert metric_name in rendered_expressions


def test_grafana_dashboard_uses_canonical_metric_families() -> None:
    dashboard = json.loads(_GRAFANA_DASHBOARD.read_text())
    panels = dashboard["panels"]
    expressions = "\n".join(
        target["expr"] for panel in panels for target in panel.get("targets", [])
    )

    assert len(panels) == 10
    for metric_name in (
        "workflow_executions_total",
        "runtime_nodes_total",
        "integration_provider_duration_seconds_bucket",
        "application_service_retries",
        "application_service_degraded",
        "application_service_configuration_failures",
        "integration_client_retries",
        "telemetry_sink_failures",
        "plugin_lifecycle_callback_failures",
        "runtime_lifecycle_callback_failures",
        "runtime_event_bus_subscriber_failures",
        "platform_bootstrap_configuration_failures",
    ):
        assert metric_name in expressions

    assert "runtime_node_executions_total" not in expressions
    assert "provider_call_duration_seconds_bucket" not in expressions
    assert "increase(provider_calls_total" not in expressions
