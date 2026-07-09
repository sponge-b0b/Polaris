from __future__ import annotations

import json
from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal

from application.services.backtesting import BacktestFill
from application.services.backtesting import BacktestPortfolioSnapshot
from application.services.backtesting import BacktestScenario
from application.services.backtesting import BacktestStepResult
from application.services.backtesting import build_backtest_artifacts
from application.services.backtesting import compute_backtest_metrics
from application.services.backtesting import render_backtest_markdown_report


def test_compute_backtest_metrics_from_deterministic_equity_curve_and_fills() -> None:
    scenario = _scenario(
        benchmark_return=Decimal("0.05"),
    )
    steps = (
        _step(
            day=1,
            equity=Decimal("1100"),
            cash=Decimal("500"),
            market_value=Decimal("600"),
            fills=(
                BacktestFill(
                    timestamp=_timestamp(1),
                    symbol="SPY",
                    side="buy",
                    quantity=Decimal("5"),
                    price=Decimal("100"),
                    status="filled",
                ),
            ),
        ),
        _step(
            day=2,
            equity=Decimal("1050"),
            cash=Decimal("1050"),
            market_value=Decimal("0"),
            fills=(
                BacktestFill(
                    timestamp=_timestamp(2),
                    symbol="SPY",
                    side="sell",
                    quantity=Decimal("5"),
                    price=Decimal("120"),
                    status="filled",
                    realized_pnl=Decimal("100"),
                ),
            ),
        ),
        _step(
            day=3,
            equity=Decimal("1200"),
            cash=Decimal("1200"),
            market_value=Decimal("0"),
        ),
    )

    metrics = compute_backtest_metrics(
        scenario=scenario,
        steps=steps,
    )

    assert metrics.total_return == Decimal("0.2")
    assert metrics.annualized_return == Decimal("16.8")
    assert metrics.max_drawdown == Decimal("50") / Decimal("1100")
    assert metrics.win_rate == Decimal("1")
    assert metrics.profit_factor == Decimal("100")
    assert metrics.benchmark_relative_return == Decimal("0.15")
    assert metrics.exposure > Decimal("0")
    assert metrics.turnover > Decimal("0")


def test_backtest_report_artifacts_include_console_markdown_and_json() -> None:
    scenario = _scenario()
    steps = (
        _step(
            day=1,
            equity=Decimal("1000"),
            cash=Decimal("500"),
            market_value=Decimal("500"),
        ),
    )
    metrics = compute_backtest_metrics(
        scenario=scenario,
        steps=steps,
    )

    artifacts = build_backtest_artifacts(
        backtest_run_id="backtest-report-check",
        scenario=scenario,
        success=True,
        status="succeeded",
        started_at=_timestamp(1),
        completed_at=_timestamp(1),
        steps=steps,
        metrics=metrics,
    )

    assert set(artifacts) == {"console", "markdown", "json"}
    assert "Backtest: Metrics check" in artifacts["console"]
    assert "# Backtest Report — Metrics check" in artifacts["markdown"]
    assert "## Metrics" in artifacts["markdown"]

    payload = json.loads(
        artifacts["json"],
    )
    assert payload["backtest_run_id"] == "backtest-report-check"
    assert payload["metrics"]["total_return"] == "0"


def test_markdown_report_includes_fill_rows() -> None:
    scenario = _scenario()
    steps = (
        _step(
            day=1,
            equity=Decimal("1000"),
            cash=Decimal("500"),
            market_value=Decimal("500"),
            fills=(
                BacktestFill(
                    timestamp=_timestamp(1),
                    symbol="SPY",
                    side="buy",
                    quantity=Decimal("5"),
                    price=Decimal("100"),
                    status="filled",
                ),
            ),
        ),
    )
    metrics = compute_backtest_metrics(
        scenario=scenario,
        steps=steps,
    )

    report = render_backtest_markdown_report(
        backtest_run_id="backtest-fill-report",
        scenario=scenario,
        success=True,
        status="succeeded",
        started_at=_timestamp(1),
        completed_at=_timestamp(1),
        steps=steps,
        metrics=metrics,
    )

    assert "## Simulated Fills" in report
    assert (
        "| 2026-01-01T00:00:00+00:00 | SPY | buy | 5.0000 | $100.00 | filled |"
        in report
    )


def _scenario(
    *,
    benchmark_return: Decimal = Decimal("0"),
) -> BacktestScenario:
    return BacktestScenario(
        scenario_id="metrics-check",
        name="Metrics check",
        workflow_name="morning_report",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
        symbols=("SPY",),
        benchmark_symbol="SPY",
        initial_cash=Decimal("1000"),
        parameters={
            "benchmark_return": str(benchmark_return),
        },
    )


def _step(
    *,
    day: int,
    equity: Decimal,
    cash: Decimal,
    market_value: Decimal,
    fills: tuple[BacktestFill, ...] = (),
) -> BacktestStepResult:
    timestamp = _timestamp(
        day,
    )
    return BacktestStepResult(
        timestamp=timestamp,
        workflow_run_id=f"workflow-{day}",
        success=True,
        node_outputs={},
        portfolio_snapshot=BacktestPortfolioSnapshot(
            timestamp=timestamp,
            cash=cash,
            equity=equity,
            market_value=market_value,
        ),
        simulated_fills=fills,
    )


def _timestamp(
    day: int,
) -> datetime:
    return datetime(
        2026,
        1,
        day,
        tzinfo=timezone.utc,
    )
