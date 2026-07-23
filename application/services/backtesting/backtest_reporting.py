from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal

from application.services.backtesting.backtest_request import BacktestScenario
from application.services.backtesting.backtest_result import (
    BacktestMetrics,
    BacktestOutcomeVerification,
    BacktestStepResult,
)

type BacktestVerificationResults = tuple[BacktestOutcomeVerification, ...]


def build_backtest_artifacts(
    *,
    backtest_run_id: str,
    scenario: BacktestScenario,
    success: bool,
    status: str,
    started_at: datetime,
    completed_at: datetime,
    steps: tuple[BacktestStepResult, ...],
    metrics: BacktestMetrics,
    verifications: BacktestVerificationResults = (),
) -> Mapping[str, str]:
    return {
        "console": render_backtest_console_summary(
            backtest_run_id=backtest_run_id,
            scenario=scenario,
            success=success,
            status=status,
            steps=steps,
            metrics=metrics,
            verifications=verifications,
        ),
        "markdown": render_backtest_markdown_report(
            backtest_run_id=backtest_run_id,
            scenario=scenario,
            success=success,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            steps=steps,
            metrics=metrics,
            verifications=verifications,
        ),
        "json": render_backtest_json_artifact(
            backtest_run_id=backtest_run_id,
            scenario=scenario,
            success=success,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            steps=steps,
            metrics=metrics,
            verifications=verifications,
        ),
    }


def render_backtest_console_summary(
    *,
    backtest_run_id: str,
    scenario: BacktestScenario,
    success: bool,
    status: str,
    steps: tuple[BacktestStepResult, ...],
    metrics: BacktestMetrics,
    verifications: BacktestVerificationResults = (),
) -> str:
    filled_count, rejected_count = _fill_status_counts(steps)
    return "\n".join(
        (
            f"Backtest: {scenario.name}",
            f"Run ID: {backtest_run_id}",
            f"Workflow: {scenario.workflow_name}",
            f"Status: {status}",
            f"Success: {success}",
            f"Steps: {len(steps)}",
            f"Verified Expectations: {_verification_summary(verifications)}",
            f"Filled / Rejected Fills: {filled_count} / {rejected_count}",
            f"Total Return: {_format_percent(metrics.total_return)}",
            f"Max Drawdown: {_format_percent(metrics.max_drawdown)}",
            f"Sharpe Ratio: {_format_decimal(metrics.sharpe_ratio)}",
        )
    )


def render_backtest_markdown_report(
    *,
    backtest_run_id: str,
    scenario: BacktestScenario,
    success: bool,
    status: str,
    started_at: datetime,
    completed_at: datetime,
    steps: tuple[BacktestStepResult, ...],
    metrics: BacktestMetrics,
    verifications: BacktestVerificationResults = (),
) -> str:
    filled_count, rejected_count = _fill_status_counts(steps)
    final_equity = (
        steps[-1].portfolio_snapshot.equity if steps else scenario.initial_cash
    )

    return "\n".join(
        (
            f"# Backtest Report — {scenario.name}",
            "",
            "## Run Summary",
            "",
            f"- Run ID: `{backtest_run_id}`",
            f"- Workflow: `{scenario.workflow_name}`",
            f"- Scenario: `{scenario.scenario_id}`",
            f"- Status: `{status}`",
            f"- Success: `{success}`",
            f"- Started: `{started_at.isoformat()}`",
            f"- Completed: `{completed_at.isoformat()}`",
            f"- Simulation Window: `{scenario.start_date.isoformat()}` → "
            f"`{scenario.end_date.isoformat()}`",
            f"- Symbols: `{', '.join(scenario.symbols)}`",
            "",
            "## Portfolio Summary",
            "",
            f"- Initial Cash: `{_format_currency(scenario.initial_cash)}`",
            f"- Final Equity: `{_format_currency(final_equity)}`",
            f"- Filled Fills: `{filled_count}`",
            f"- Rejected Fills: `{rejected_count}`",
            "",
            "## Metrics",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| Total Return | {_format_percent(metrics.total_return)} |",
            f"| Annualized Return | {_format_percent(metrics.annualized_return)} |",
            f"| Volatility | {_format_percent(metrics.volatility)} |",
            f"| Max Drawdown | {_format_percent(metrics.max_drawdown)} |",
            f"| Sharpe Ratio | {_format_decimal(metrics.sharpe_ratio)} |",
            f"| Sortino Ratio | {_format_decimal(metrics.sortino_ratio)} |",
            f"| Win Rate | {_format_percent(metrics.win_rate)} |",
            f"| Profit Factor | {_format_decimal(metrics.profit_factor)} |",
            f"| Exposure | {_format_percent(metrics.exposure)} |",
            f"| Turnover | {_format_percent(metrics.turnover)} |",
            f"| Benchmark Relative Return | "
            f"{_format_percent(metrics.benchmark_relative_return)} |",
            "",
            "## Deterministic Verification",
            "",
            "| Target | Expectation | Expected | Actual | Result |",
            "| --- | --- | --- | --- | --- |",
            *_verification_rows(verifications),
            "",
            "## Equity Curve",
            "",
            "| Timestamp | Equity | Cash | Market Value |",
            "| --- | ---: | ---: | ---: |",
            *_equity_rows(
                steps,
            ),
            "",
            "## Simulated Fills",
            "",
            "| Timestamp | Symbol | Side | Quantity | Price | Status | Reason | "
            "Realized PnL |",
            "| --- | --- | --- | ---: | ---: | --- | --- | ---: |",
            *_fill_rows(
                steps,
            ),
        )
    )


def render_backtest_json_artifact(
    *,
    backtest_run_id: str,
    scenario: BacktestScenario,
    success: bool,
    status: str,
    started_at: datetime,
    completed_at: datetime,
    steps: tuple[BacktestStepResult, ...],
    metrics: BacktestMetrics,
    verifications: BacktestVerificationResults = (),
) -> str:
    return json.dumps(
        {
            "backtest_run_id": backtest_run_id,
            "scenario": scenario.to_dict(),
            "success": success,
            "status": status,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "steps": [step.to_dict() for step in steps],
            "metrics": metrics.to_dict(),
            "verifications": [verification.to_dict() for verification in verifications],
        },
        default=str,
        indent=2,
        sort_keys=True,
    )


def _equity_rows(
    steps: tuple[BacktestStepResult, ...],
) -> tuple[str, ...]:
    return tuple(
        f"| {step.timestamp.isoformat()} | "
        f"{_format_currency(step.portfolio_snapshot.equity)} | "
        f"{_format_currency(step.portfolio_snapshot.cash)} | "
        f"{_format_currency(step.portfolio_snapshot.market_value)} |"
        for step in steps
    )


def _fill_rows(
    steps: tuple[BacktestStepResult, ...],
) -> tuple[str, ...]:
    row_template = (
        "| {timestamp} | {symbol} | {side} | {quantity} | {price} | "
        "{status} | {reason} | {realized_pnl} |"
    )
    rows: list[str] = []
    for step in steps:
        for fill in step.simulated_fills:
            rows.append(
                row_template.format(
                    timestamp=fill.timestamp.isoformat(),
                    symbol=fill.symbol,
                    side=fill.side,
                    quantity=_format_decimal(fill.quantity),
                    price=_format_currency(fill.price),
                    status=fill.status,
                    reason=fill.reason or "",
                    realized_pnl=_format_currency(fill.realized_pnl),
                )
            )
    if not rows:
        return ("| — | — | — | — | — | — | No simulated fills | — |",)
    return tuple(rows)


def _fill_count(
    *,
    steps: tuple[BacktestStepResult, ...],
    status: str,
) -> int:
    return sum(
        1 for step in steps for fill in step.simulated_fills if fill.status == status
    )


def _fill_status_counts(
    steps: tuple[BacktestStepResult, ...],
) -> tuple[int, int]:
    return (
        _fill_count(steps=steps, status="filled"),
        _fill_count(steps=steps, status="rejected"),
    )


def _verification_summary(
    verifications: BacktestVerificationResults,
) -> str:
    passed = sum(verification.passed for verification in verifications)
    return f"{passed} / {len(verifications)}"


def _verification_rows(
    verifications: BacktestVerificationResults,
) -> tuple[str, ...]:
    if not verifications:
        return ("| — | — | — | — | No expectations declared |",)
    return tuple(
        "| {target} | {expectation} | {expected} | {actual} | {result} |".format(
            target=verification.target,
            expectation=verification.expectation_type,
            expected=verification.expected,
            actual=verification.actual,
            result="PASS" if verification.passed else "FAIL",
        )
        for verification in verifications
    )


def _format_currency(
    value: Decimal,
) -> str:
    return f"${value.quantize(Decimal('0.01'))}"


def _format_percent(
    value: Decimal,
) -> str:
    return f"{(value * Decimal('100')).quantize(Decimal('0.01'))}%"


def _format_decimal(
    value: Decimal,
) -> str:
    return str(
        value.quantize(
            Decimal("0.0001"),
        )
    )
