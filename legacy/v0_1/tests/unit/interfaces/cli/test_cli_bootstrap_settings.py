from __future__ import annotations

from pathlib import Path

import pytest

from interfaces.cli.bootstrap.container import _workflow_bootstrap_config
from interfaces.cli.bootstrap.settings import CliSettings


def test_cli_settings_default_external_observability_is_disabled() -> None:
    settings = CliSettings.from_env(
        environ={},
    )

    assert settings.enable_observability is False
    assert settings.enable_opentelemetry is False
    assert settings.enable_prometheus_metrics is False
    assert settings.prometheus_metrics_host == "0.0.0.0"
    assert settings.prometheus_metrics_port == 9464
    assert settings.prometheus_metrics_path == "/metrics"


def test_cli_settings_reads_external_observability_environment() -> None:
    settings = CliSettings.from_env(
        plugin_dirs=(Path("plugins"),),
        autoload_plugins=True,
        environ={
            "POLARIS_ENABLE_OBSERVABILITY": "true",
            "POLARIS_ENABLE_OPENTELEMETRY": "yes",
            "POLARIS_ENABLE_PROMETHEUS_METRICS": "1",
            "POLARIS_PROMETHEUS_METRICS_HOST": "127.0.0.1",
            "POLARIS_PROMETHEUS_METRICS_PORT": "9555",
            "POLARIS_PROMETHEUS_METRICS_PATH": "/custom-metrics",
        },
    )

    assert settings.plugin_dirs == ("plugins",)
    assert settings.autoload_plugins is True
    assert settings.enable_observability is True
    assert settings.enable_opentelemetry is True
    assert settings.enable_prometheus_metrics is True
    assert settings.prometheus_metrics_host == "127.0.0.1"
    assert settings.prometheus_metrics_port == 9555
    assert settings.prometheus_metrics_path == "/custom-metrics"


def test_cli_workflow_bootstrap_config_uses_external_observability_settings() -> None:
    settings = CliSettings.from_env(
        environ={
            "POLARIS_ENABLE_OBSERVABILITY": "true",
            "POLARIS_ENABLE_OPENTELEMETRY": "true",
            "POLARIS_ENABLE_PROMETHEUS_METRICS": "true",
            "POLARIS_PROMETHEUS_METRICS_PORT": "9555",
        },
    )

    config = _workflow_bootstrap_config(
        settings,
    )

    assert config.enable_observability is True
    assert config.enable_opentelemetry is True
    assert config.enable_prometheus_metrics is True
    assert config.prometheus_metrics_port == 9555


def test_cli_settings_rejects_invalid_boolean_environment() -> None:
    with pytest.raises(
        ValueError,
        match="POLARIS_ENABLE_OBSERVABILITY",
    ):
        CliSettings.from_env(
            environ={
                "POLARIS_ENABLE_OBSERVABILITY": "maybe",
            },
        )


def test_cli_settings_rejects_invalid_integer_environment() -> None:
    with pytest.raises(
        ValueError,
        match="POLARIS_PROMETHEUS_METRICS_PORT",
    ):
        CliSettings.from_env(
            environ={
                "POLARIS_PROMETHEUS_METRICS_PORT": "not-an-int",
            },
        )


def test_cli_settings_reads_completed_run_retention_environment() -> None:
    settings = CliSettings.from_env(
        environ={
            "POLARIS_COMPLETED_RUN_RETENTION_MAX_AGE_DAYS": "30",
            "POLARIS_COMPLETED_RUN_RETENTION_MAX_COUNT": "100",
        },
    )

    assert settings.completed_run_retention_max_age_days == 30
    assert settings.completed_run_retention_max_count == 100

    config = _workflow_bootstrap_config(
        settings,
    )

    assert config.completed_run_retention_max_age_days == 30
    assert config.completed_run_retention_max_count == 100


def test_cli_settings_rejects_invalid_completed_run_retention_environment() -> None:
    with pytest.raises(
        ValueError,
        match="POLARIS_COMPLETED_RUN_RETENTION_MAX_COUNT",
    ):
        CliSettings.from_env(
            environ={
                "POLARIS_COMPLETED_RUN_RETENTION_MAX_COUNT": "-1",
            },
        )


@pytest.mark.asyncio
async def test_cli_runtime_scope_emergency_logs_invalid_environment(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from interfaces.cli.bootstrap.container import cli_runtime_scope

    logger_name = "core.telemetry.emitters.bootstrap_configuration_telemetry"
    monkeypatch.setenv("POLARIS_ENABLE_OBSERVABILITY", "invalid-boolean")

    with caplog.at_level("CRITICAL", logger=logger_name):
        with pytest.raises(ValueError, match="POLARIS_ENABLE_OBSERVABILITY"):
            async with cli_runtime_scope():
                pytest.fail("invalid configuration must fail before opening a scope")

    records = [record for record in caplog.records if record.name == logger_name]
    assert len(records) == 1
    assert records[0].levelname == "CRITICAL"
    assert "POLARIS_ENABLE_OBSERVABILITY" in caplog.text
    assert "invalid-boolean" not in caplog.text
