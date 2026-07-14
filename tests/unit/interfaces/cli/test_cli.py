from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from interfaces.cli.app import create_app


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
