from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from typer.testing import CliRunner

from application.services.backtesting import (
    BacktestApplicationService,
    BacktestResult,
    BacktestScenario,
)
from application.services.base import ServiceRunner
from interfaces.cli.app import create_app
from interfaces.cli.services.backtest_command_service import (
    BacktestCommandService,
    BacktestRunCommandRequest,
)


class FakeWorkflowFacade:
    def __init__(
        self,
    ) -> None:
        self.calls: list[dict[str, Any]] = []

    async def run_workflow(
        self,
        workflow_name: str,
        execution_id: str | None = None,
        mode: str = "live",
        workflow_inputs: Mapping[str, Any] | None = None,
        simulation_time: datetime | None = None,
        archive_on_completion: bool = True,
        checkpoint_on_completion: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        if workflow_inputs is None or simulation_time is None:
            raise AssertionError("workflow_inputs and simulation_time are required")

        self.calls.append(
            {
                "workflow_name": workflow_name,
                "execution_id": execution_id,
                "mode": mode,
                "workflow_inputs": workflow_inputs,
                "simulation_time": simulation_time,
                "archive_on_completion": archive_on_completion,
                "checkpoint_on_completion": checkpoint_on_completion,
                "metadata": metadata,
            }
        )
        return SimpleNamespace(
            success=True,
            execution_id=f"workflow-{len(self.calls)}",
            execution_result=SimpleNamespace(
                final_context=SimpleNamespace(
                    node_outputs={
                        "deterministic_node": {
                            "success": True,
                            "step_index": workflow_inputs["backtest"]["step_index"],
                        }
                    }
                )
            ),
        )


@pytest.mark.asyncio
async def test_backtest_command_service_runs_scenario_through_workflow_facade(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    scenario_file = tmp_path / "scenario.json"
    scenario_file.write_text(
        json.dumps(
            {
                "scenario_id": "cli-runtime-check",
                "name": "CLI runtime check",
                "workflow_name": "morning_report",
                "start_date": "2026-01-01",
                "end_date": "2026-01-02",
                "symbols": ["SPY"],
                "benchmark_symbol": "SPY",
                "initial_cash": "100000",
                "provider_profile": "backtest_synthetic",
            }
        ),
        encoding="utf-8",
    )
    facade = FakeWorkflowFacade()

    class DirectServiceRunner:
        async def run(self, service: Any, request: Any) -> Any:
            return await service.run(request)

    class FakeScope:
        def get(self, dependency_type: type[Any]) -> Any:
            if dependency_type is BacktestApplicationService:
                return BacktestApplicationService(facade)
            if dependency_type is ServiceRunner:
                return DirectServiceRunner()
            raise AssertionError(f"Unexpected dependency: {dependency_type}")

    @asynccontextmanager
    async def fake_cli_runtime_scope(
        **kwargs: object,
    ) -> AsyncIterator[FakeScope]:
        assert kwargs["provider_profile"] == "backtest_synthetic"
        yield FakeScope()

    monkeypatch.setattr(
        "interfaces.cli.services.backtest_command_service.cli_runtime_scope",
        fake_cli_runtime_scope,
    )

    result = await BacktestCommandService().run_backtest(
        BacktestRunCommandRequest(
            scenario_path=scenario_file,
            persist_results=False,
            checkpoint_workflow_runs=False,
        )
    )

    assert result.success is True
    assert result.status == "succeeded"
    assert len(result.steps) == 2
    assert len(facade.calls) == 2
    assert facade.calls[0]["mode"] == "backtest"
    assert facade.calls[0]["archive_on_completion"] is False
    assert facade.calls[0]["checkpoint_on_completion"] is False


def test_backtest_help_lists_runtime_native_commands() -> None:
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "backtest",
            "--help",
        ],
    )

    assert result.exit_code == 0
    assert "run" in result.output
    assert "list" in result.output
    assert "show" in result.output
    assert "report" in result.output


def test_backtest_run_cli_renders_console_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    scenario_file = tmp_path / "scenario.json"
    scenario_file.write_text(
        "{}",
        encoding="utf-8",
    )
    scenario = BacktestScenario(
        scenario_id="fake-cli-result",
        name="Fake CLI result",
        workflow_name="morning_report",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
        symbols=("SPY",),
        benchmark_symbol="SPY",
        initial_cash=Decimal("100000"),
    )
    backtest_result = BacktestResult(
        backtest_run_id="backtest-fake",
        scenario=scenario,
        success=True,
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        completed_at=datetime(2026, 1, 1, tzinfo=UTC),
        status="succeeded",
        artifacts={
            "console": "Backtest: Fake CLI result\nStatus: succeeded",
        },
    )

    class FakeBacktestCommandService:
        async def run_backtest(
            self,
            request: BacktestRunCommandRequest,
        ) -> BacktestResult:
            assert request.scenario_path == scenario_file
            assert request.persist_results is False
            return backtest_result

    monkeypatch.setattr(
        "interfaces.cli.commands.backtest_command.BacktestCommandService",
        FakeBacktestCommandService,
    )

    runner = CliRunner()
    result = runner.invoke(
        create_app(),
        [
            "backtest",
            "run",
            "--scenario",
            str(scenario_file),
            "--no-persist-results",
        ],
    )

    assert result.exit_code == 0
    assert "Backtest: Fake CLI result" in result.output
    assert "Status: succeeded" in result.output


def test_backtesting_package_excludes_legacy_parallel_runtime_paths() -> None:
    repository_root = Path(__file__).resolve().parents[4]

    legacy_paths = (
        repository_root / "backtesting" / "runtime",
        repository_root / "backtesting" / "cli",
        repository_root / "backtesting" / "execution",
        repository_root / "backtesting" / "replay",
        repository_root / "backtesting" / "metrics",
        repository_root / "backtesting" / "analytics",
        repository_root / "backtesting" / "portfolio",
        repository_root / "backtesting" / "scenarios",
        repository_root / "backtesting" / "configs",
    )

    assert [path for path in legacy_paths if path.exists()] == []
