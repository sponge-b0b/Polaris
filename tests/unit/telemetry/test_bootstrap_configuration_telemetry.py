from __future__ import annotations

import logging

import pytest

from core.telemetry.context import telemetry_context_scope
from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.emitters.bootstrap_configuration_telemetry import (
    BootstrapConfigurationTelemetry,
)
from core.telemetry.emitters.bootstrap_configuration_telemetry import (
    emergency_log_configuration_failure,
)
from core.telemetry.events.telemetry_event import TelemetryEventLevel
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink


def test_configuration_failure_uses_active_trace_context_and_sanitizes_details() -> (
    None
):
    sink = InMemoryTelemetrySink()
    manager = ObservabilityManager()
    manager.add_sink(sink)
    telemetry = BootstrapConfigurationTelemetry(manager)
    context = TelemetryContext(
        workflow_id="morning_report",
        execution_id="execution-123",
        correlation_id="correlation-123",
        trace_id="trace-123",
        span_id="span-123",
    )

    database_url = "".join(
        (
            "postgresql+asyncpg://polaris:",
            "password",
            "@localhost:5432/polaris",
        )
    )

    with telemetry_context_scope(context):
        event = telemetry.emit_configuration_failure(
            component="opentelemetry",
            invalid_setting_names=("POLARIS_OTEL_OTLP_ENDPOINT",),
            required=False,
            error=ValueError("invalid endpoint"),
            details={
                "api_key": "secret-value",
                "database_url": database_url,
                "endpoint": "http://localhost:4317/v1/traces",
            },
        )

    assert sink.events == [event]
    assert event.level is TelemetryEventLevel.WARNING
    assert event.workflow_id == "morning_report"
    assert event.execution_id == "execution-123"
    assert event.correlation_id == "correlation-123"
    assert event.trace_id == "trace-123"
    assert event.span_id == "span-123"
    assert event.payload["startup_action"] == "continued_degraded"
    assert event.payload["details"] == {
        "api_key": "[REDACTED]",
        "database_url": "[REDACTED_URL]",
        "endpoint": "[REDACTED_URL]",
    }


def test_required_configuration_failure_is_error_and_records_metrics() -> None:
    sink = InMemoryTelemetrySink()
    manager = ObservabilityManager()
    manager.add_sink(sink)

    event = BootstrapConfigurationTelemetry(manager).emit_configuration_failure(
        component="workflow_runtime",
        invalid_setting_names=("checkpoint_dir",),
        required=True,
        error=ValueError("invalid checkpoint directory"),
    )

    assert sink.events == [event]
    assert event.level is TelemetryEventLevel.ERROR
    assert event.payload["startup_action"] == "failed"
    assert event.success is False
    assert event.error_count == 1
    assert manager.metrics_store.to_dict()["counters"]


def test_emergency_configuration_log_is_single_critical_record_without_secrets(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger_name = "core.telemetry.emitters.bootstrap_configuration_telemetry"

    database_url = "".join(
        (
            "postgresql+asyncpg://polaris:",
            "password",
            "@localhost:5432/polaris",
        )
    )

    error_message = f"failed to connect to {database_url} with token=secret-token"

    try:
        raise ValueError(error_message)
    except ValueError as error:
        with caplog.at_level(logging.CRITICAL, logger=logger_name):
            emergency_log_configuration_failure(
                component="database",
                invalid_setting_names=("POLARIS_DATABASE_URL",),
                error=error,
                details={
                    "database_url": database_url,
                    "token": "secret-token",
                },
            )

    records = [record for record in caplog.records if record.name == logger_name]
    assert len(records) == 1
    assert records[0].levelno == logging.CRITICAL
    assert records[0].exc_info is not None
    assert "password" not in caplog.text
    assert "secret-token" not in caplog.text
    assert "postgresql+asyncpg://" not in caplog.text
    assert "[REDACTED_URL]" in caplog.text
