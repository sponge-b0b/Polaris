from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}

DEFAULT_OTEL_SERVICE_NAME = "polaris-runtime"
DEFAULT_OTEL_SERVICE_VERSION = "1.0.0"
DEFAULT_OTEL_ENVIRONMENT = "development"
DEFAULT_OTEL_ENDPOINT = "http://localhost:4317"
DEFAULT_OTEL_ENABLE_TRACING = True
DEFAULT_OTEL_ENABLE_METRICS = True
DEFAULT_OTEL_ENABLE_CONSOLE_EXPORT = False
DEFAULT_OTEL_INSECURE = True


@dataclass(frozen=True, slots=True)
class OpenTelemetryConfig:
    """
    OpenTelemetry integration configuration.

    This config intentionally stays lightweight and vendor-neutral.
    """

    service_name: str = DEFAULT_OTEL_SERVICE_NAME

    service_version: str = DEFAULT_OTEL_SERVICE_VERSION

    environment: str = DEFAULT_OTEL_ENVIRONMENT

    otlp_endpoint: str = DEFAULT_OTEL_ENDPOINT

    enable_tracing: bool = DEFAULT_OTEL_ENABLE_TRACING

    enable_metrics: bool = DEFAULT_OTEL_ENABLE_METRICS

    enable_console_export: bool = DEFAULT_OTEL_ENABLE_CONSOLE_EXPORT

    insecure: bool = DEFAULT_OTEL_INSECURE

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> OpenTelemetryConfig:
        values = os.environ if environ is None else environ

        return cls(
            service_name=_read_text(
                values,
                "POLARIS_OTEL_SERVICE_NAME",
                "OTEL_SERVICE_NAME",
                default=DEFAULT_OTEL_SERVICE_NAME,
            ),
            service_version=_read_text(
                values,
                "POLARIS_OTEL_SERVICE_VERSION",
                "OTEL_SERVICE_VERSION",
                default=DEFAULT_OTEL_SERVICE_VERSION,
            ),
            environment=_read_text(
                values,
                "POLARIS_OTEL_ENVIRONMENT",
                "OTEL_ENVIRONMENT",
                default=DEFAULT_OTEL_ENVIRONMENT,
            ),
            otlp_endpoint=_read_text(
                values,
                "POLARIS_OTEL_OTLP_ENDPOINT",
                "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
                "OTEL_EXPORTER_OTLP_ENDPOINT",
                default=DEFAULT_OTEL_ENDPOINT,
            ),
            insecure=_read_bool(
                values,
                "POLARIS_OTEL_INSECURE",
                "OTEL_EXPORTER_OTLP_INSECURE",
                default=DEFAULT_OTEL_INSECURE,
            ),
            enable_tracing=_read_bool(
                values,
                "POLARIS_OTEL_ENABLE_TRACING",
                default=DEFAULT_OTEL_ENABLE_TRACING,
            ),
            enable_metrics=_read_bool(
                values,
                "POLARIS_OTEL_ENABLE_METRICS",
                default=DEFAULT_OTEL_ENABLE_METRICS,
            ),
            enable_console_export=_read_bool(
                values,
                "POLARIS_OTEL_ENABLE_CONSOLE_EXPORT",
                default=DEFAULT_OTEL_ENABLE_CONSOLE_EXPORT,
            ),
        )

    @classmethod
    def for_local_compose(
        cls,
        app_inside_docker: bool = False,
    ) -> OpenTelemetryConfig:
        return cls(
            otlp_endpoint=(
                "http://jaeger:4317" if app_inside_docker else "http://localhost:4317"
            ),
        )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "service_name": self.service_name,
            "service_version": self.service_version,
            "environment": self.environment,
            "otlp_endpoint": self.otlp_endpoint,
            "enable_tracing": self.enable_tracing,
            "enable_metrics": self.enable_metrics,
            "enable_console_export": self.enable_console_export,
            "insecure": self.insecure,
        }


def _read_text(
    values: Mapping[str, str],
    *names: str,
    default: str,
) -> str:
    for name in names:
        value = values.get(name)
        if value is not None and value.strip():
            return value.strip()

    return default


def _read_bool(
    values: Mapping[str, str],
    *names: str,
    default: bool,
) -> bool:
    for name in names:
        value = values.get(name)
        if value is None or not value.strip():
            continue

        normalized = value.strip().lower()
        if normalized in _TRUE_VALUES:
            return True
        if normalized in _FALSE_VALUES:
            return False

        raise ValueError(f"Invalid boolean OpenTelemetry environment value: {name}")

    return default
