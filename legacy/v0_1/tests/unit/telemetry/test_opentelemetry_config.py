from __future__ import annotations

import pytest

from core.telemetry.integrations.opentelemetry import OpenTelemetryConfig


def test_opentelemetry_config_defaults() -> None:
    config = OpenTelemetryConfig()

    assert config.service_name == "polaris-runtime"
    assert config.service_version == "1.0.0"
    assert config.environment == "development"
    assert config.otlp_endpoint == "http://localhost:4317"
    assert config.insecure is True


def test_opentelemetry_config_from_env_prefers_polaris_values() -> None:
    config = OpenTelemetryConfig.from_env(
        {
            "POLARIS_OTEL_SERVICE_NAME": "polaris-test",
            "OTEL_SERVICE_NAME": "otel-test",
            "POLARIS_OTEL_SERVICE_VERSION": "2.0.0",
            "POLARIS_OTEL_ENVIRONMENT": "test",
            "POLARIS_OTEL_OTLP_ENDPOINT": "http://jaeger:4317",
            "POLARIS_OTEL_INSECURE": "false",
            "POLARIS_OTEL_ENABLE_TRACING": "yes",
            "POLARIS_OTEL_ENABLE_METRICS": "no",
            "POLARIS_OTEL_ENABLE_CONSOLE_EXPORT": "on",
        }
    )

    assert config.service_name == "polaris-test"
    assert config.service_version == "2.0.0"
    assert config.environment == "test"
    assert config.otlp_endpoint == "http://jaeger:4317"
    assert config.insecure is False
    assert config.enable_tracing is True
    assert config.enable_metrics is False
    assert config.enable_console_export is True


def test_opentelemetry_config_from_env_uses_standard_otel_fallbacks() -> None:
    config = OpenTelemetryConfig.from_env(
        {
            "OTEL_SERVICE_NAME": "standard-service",
            "OTEL_SERVICE_VERSION": "3.0.0",
            "OTEL_ENVIRONMENT": "staging",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
            "OTEL_EXPORTER_OTLP_INSECURE": "true",
        }
    )

    assert config.service_name == "standard-service"
    assert config.service_version == "3.0.0"
    assert config.environment == "staging"
    assert config.otlp_endpoint == "http://localhost:4317"
    assert config.insecure is True


def test_opentelemetry_config_from_env_prefers_trace_endpoint() -> None:
    config = OpenTelemetryConfig.from_env(
        {
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4317",
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": "http://traces:4317",
        }
    )

    assert config.otlp_endpoint == "http://traces:4317"


def test_opentelemetry_config_from_env_rejects_invalid_bool() -> None:
    with pytest.raises(ValueError, match="POLARIS_OTEL_INSECURE"):
        OpenTelemetryConfig.from_env(
            {
                "POLARIS_OTEL_INSECURE": "maybe",
            }
        )


def test_opentelemetry_config_local_compose_endpoints() -> None:
    host_config = OpenTelemetryConfig.for_local_compose()
    docker_config = OpenTelemetryConfig.for_local_compose(
        app_inside_docker=True,
    )

    assert host_config.otlp_endpoint == "http://localhost:4317"
    assert docker_config.otlp_endpoint == "http://jaeger:4317"
