from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from application.persistence.diagnostics import DiagnosticsPersistenceService
from interfaces.cli.app import create_app
from interfaces.cli.commands import inspect_command


def test_cli_help_lists_platform_commands() -> None:
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "--help",
        ],
    )

    assert result.exit_code == 0
    assert "morning-report" in result.output
    assert "workflow" in result.output
    assert "inspect" in result.output
    assert "rag" in result.output
    assert "observability" in result.output
    assert "eval" in result.output


def test_inspect_config_outputs_json() -> None:
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "inspect",
            "config",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(
        result.output,
    )
    assert data["macro_provider"]
    assert data["market_data_provider"]
    assert data["sentiment_provider"]


def test_inspect_config_applies_provider_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "PROVIDER_PROFILE",
        "backtest_synthetic",
    )
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "inspect",
            "config",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(
        result.output,
    )
    assert data["provider_profile"] == "backtest_synthetic"
    assert data["macro_provider"] == "backtest_macro_provider"
    assert data["market_data_provider"] == "backtest_data_provider"
    assert data["market_events_provider"] == "backtest_events_provider"
    assert data["news_provider"] == "backtest_news_provider"
    assert data["portfolio_provider"] == "backtest_portfolio_provider"
    assert data["sentiment_provider"] == "backtest_sentiment_provider"


def test_inspect_persistence_outputs_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle: list[str] = []

    class FakeDiagnosticsService:
        async def run_diagnostics(self) -> SimpleNamespace:
            return SimpleNamespace(
                as_dict=_persistence_health_values,
            )

    class FakeScope:
        def get(
            self,
            dependency_type: type[DiagnosticsPersistenceService],
        ) -> FakeDiagnosticsService:
            assert dependency_type is DiagnosticsPersistenceService
            lifecycle.append("service_resolved")
            return FakeDiagnosticsService()

    @asynccontextmanager
    async def fake_scope() -> AsyncIterator[FakeScope]:
        lifecycle.append("scope_entered")
        try:
            yield FakeScope()
        finally:
            lifecycle.append("scope_closed")

    monkeypatch.setattr(
        inspect_command,
        "cli_runtime_scope",
        fake_scope,
    )
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "inspect",
            "persistence",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(
        result.output,
    )
    assert data["status"] == "healthy"
    assert data["checks"][0]["check_name"] == "alembic_schema_drift"
    assert lifecycle == ["scope_entered", "service_resolved", "scope_closed"]


@pytest.mark.asyncio
async def test_inspect_persistence_closes_scope_when_diagnostics_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle: list[str] = []

    class FailingDiagnosticsService:
        async def run_diagnostics(self) -> SimpleNamespace:
            raise RuntimeError("diagnostics failed")

    class FakeScope:
        def get(
            self,
            dependency_type: type[DiagnosticsPersistenceService],
        ) -> FailingDiagnosticsService:
            assert dependency_type is DiagnosticsPersistenceService
            lifecycle.append("service_resolved")
            return FailingDiagnosticsService()

    @asynccontextmanager
    async def fake_scope() -> AsyncIterator[FakeScope]:
        lifecycle.append("scope_entered")
        try:
            yield FakeScope()
        finally:
            lifecycle.append("scope_closed")

    monkeypatch.setattr(
        inspect_command,
        "cli_runtime_scope",
        fake_scope,
    )

    with pytest.raises(RuntimeError, match="diagnostics failed"):
        await inspect_command._inspect_persistence_values()

    assert lifecycle == ["scope_entered", "service_resolved", "scope_closed"]


def test_inspect_persistence_outputs_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def inspect_values() -> dict[str, object]:
        return _persistence_health_values()

    monkeypatch.setattr(
        inspect_command,
        "_inspect_persistence_values",
        inspect_values,
    )
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "inspect",
            "persistence",
        ],
    )

    assert result.exit_code == 0
    assert "Persistence diagnostics:" in result.output
    assert "status: healthy" in result.output
    assert "alembic_schema_drift" in result.output


def _persistence_health_values() -> dict[str, object]:
    return {
        "status": "healthy",
        "healthy_check_count": 1,
        "degraded_check_count": 0,
        "unhealthy_check_count": 0,
        "unknown_check_count": 0,
        "checks": (
            {
                "category": "migration_state",
                "check_name": "alembic_schema_drift",
                "status": "healthy",
                "message": "Database schema matches SQLAlchemy metadata.",
                "metadata": {
                    "operation_count": 0,
                    "operations": (),
                },
            },
        ),
    }


def test_workflow_list_includes_morning_report() -> None:
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "workflow",
            "list",
        ],
    )

    assert result.exit_code == 0
    assert "morning_report" in result.output


def test_morning_report_command_uses_canonical_workflow_without_override() -> None:
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "morning-report",
            "--help",
        ],
    )

    assert result.exit_code == 0
    assert "--symbol" in result.output
    assert "--workflow" not in result.output


def test_morning_report_describes_real_workflow_definition(
    monkeypatch,
) -> None:
    for name, value in {
        "MACRO_PROVIDER": "backtest_macro_provider",
        "MARKET_DATA_PROVIDER": "backtest_data_provider",
        "MARKET_EVENTS_PROVIDER": "backtest_events_provider",
        "NEWS_PROVIDER": "backtest_news_provider",
        "PORTFOLIO_PROVIDER": "backtest_portfolio_provider",
        "SENTIMENT_PROVIDER": "backtest_sentiment_provider",
    }.items():
        monkeypatch.setenv(
            name,
            value,
        )

    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "workflow",
            "describe",
            "morning_report",
        ],
    )

    assert result.exit_code == 0
    assert "portfolio_state_builder" in result.output
    assert "fundamental_agent" in result.output
    assert "execution_risk_guard" in result.output


def test_workflow_run_help_describes_default_control_and_file_formats() -> None:
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "workflow",
            "run",
            "--help",
        ],
    )

    assert result.exit_code == 0
    assert "Terminal output" in result.output
    assert "progress notifications" in result.output
    assert "interactive" in result.output
    assert "workflow control" in result.output
    assert "--format writes" in result.output
    assert "additional output" in result.output
    assert "html, json, markdown, or pdf" in result.output
    assert "--progress" not in result.output
    assert "--interactive-control" not in result.output
    assert "format: console" not in result.output.lower()


def test_morning_report_help_describes_default_control_and_file_formats() -> None:
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "morning-report",
            "--help",
        ],
    )

    assert result.exit_code == 0
    assert "Terminal output" in result.output
    assert "progress notifications" in result.output
    assert "interactive" in result.output
    assert "workflow control" in result.output
    assert "--format writes an" in result.output
    assert "additional report file" in result.output
    assert "html, json, markdown, or pdf" in result.output
    assert "--progress" not in result.output
    assert "--interactive-control" not in result.output
    assert "format: console" not in result.output.lower()


def test_cli_registers_completed_runs_alias() -> None:
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "completed-runs",
            "--help",
        ],
    )

    assert result.exit_code == 0
    assert "projection-status" in result.output
    assert "reconcile-projections" in result.output
