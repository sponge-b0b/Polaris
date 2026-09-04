from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal, InvalidOperation

from application.services.backtesting.backtest_request import BacktestScenario
from application.services.backtesting.backtest_result import (
    BacktestFill,
    BacktestMetrics,
    BacktestStepResult,
)

TRADING_DAYS_PER_YEAR = Decimal("252")


def compute_backtest_metrics(
    *,
    scenario: BacktestScenario,
    steps: tuple[BacktestStepResult, ...],
) -> BacktestMetrics:
    if not steps:
        return BacktestMetrics()

    initial_equity = _initial_equity(
        scenario,
    )
    if initial_equity <= Decimal("0"):
        return BacktestMetrics()

    equity_curve = (
        initial_equity,
        *(step.portfolio_snapshot.equity for step in steps),
    )
    returns = _period_returns(
        equity_curve,
    )
    final_equity = equity_curve[-1]
    total_return = (final_equity / initial_equity) - Decimal("1")
    annualized_return = _annualized_return(
        total_return=total_return,
        periods=len(steps),
    )
    volatility = _volatility(
        returns,
    )
    sharpe_ratio = _sharpe_ratio(
        returns=returns,
        volatility=volatility,
    )
    sortino_ratio = _sortino_ratio(
        returns,
    )
    realized_gains, realized_losses, profitable_trades, closed_trades = _realized_pnl(
        fill for step in steps for fill in step.simulated_fills
    )

    return BacktestMetrics(
        total_return=total_return,
        annualized_return=annualized_return,
        volatility=volatility,
        max_drawdown=_max_drawdown(
            equity_curve,
        ),
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        win_rate=_win_rate(
            profitable_trades=profitable_trades,
            closed_trades=closed_trades,
        ),
        profit_factor=_profit_factor(
            realized_gains=realized_gains,
            realized_losses=realized_losses,
        ),
        exposure=_average_exposure(
            steps,
        ),
        turnover=_turnover(
            steps=steps,
            average_equity=_average(
                equity_curve,
            ),
        ),
        benchmark_relative_return=total_return
        - _benchmark_return_from_parameters(
            scenario,
        ),
    )


def _initial_equity(
    scenario: BacktestScenario,
) -> Decimal:
    return scenario.initial_cash + sum(
        (
            position.quantity * position.average_price
            for position in scenario.initial_positions
        ),
        Decimal("0"),
    )


def _period_returns(
    equity_curve: tuple[Decimal, ...],
) -> tuple[Decimal, ...]:
    returns: list[Decimal] = []
    previous = equity_curve[0]
    for equity in equity_curve[1:]:
        if previous == Decimal("0"):
            returns.append(
                Decimal("0"),
            )
        else:
            returns.append(
                (equity / previous) - Decimal("1"),
            )
        previous = equity
    return tuple(returns)


def _annualized_return(
    *,
    total_return: Decimal,
    periods: int,
) -> Decimal:
    if periods <= 0:
        return Decimal("0")

    return total_return * TRADING_DAYS_PER_YEAR / Decimal(periods)


def _volatility(
    returns: tuple[Decimal, ...],
) -> Decimal:
    if len(returns) < 2:
        return Decimal("0")

    mean_return = _average(
        returns,
    )
    variance = sum(
        ((period_return - mean_return) ** 2 for period_return in returns),
        Decimal("0"),
    ) / Decimal(len(returns) - 1)
    return variance.sqrt() * TRADING_DAYS_PER_YEAR.sqrt()


def _sharpe_ratio(
    *,
    returns: tuple[Decimal, ...],
    volatility: Decimal,
) -> Decimal:
    if volatility == Decimal("0"):
        return Decimal("0")

    return (
        _average(
            returns,
        )
        * TRADING_DAYS_PER_YEAR
        / volatility
    )


def _sortino_ratio(
    returns: tuple[Decimal, ...],
) -> Decimal:
    downside_returns = tuple(
        period_return for period_return in returns if period_return < Decimal("0")
    )
    if not downside_returns:
        return Decimal("0")

    downside_deviation = _volatility(
        downside_returns,
    )
    if downside_deviation == Decimal("0"):
        return Decimal("0")

    return (
        _average(
            returns,
        )
        * TRADING_DAYS_PER_YEAR
        / downside_deviation
    )


def _max_drawdown(
    equity_curve: tuple[Decimal, ...],
) -> Decimal:
    peak = equity_curve[0]
    max_drawdown = Decimal("0")
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        if peak == Decimal("0"):
            continue
        drawdown = (peak - equity) / peak
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    return max_drawdown


def _realized_pnl(
    fills: Iterable[BacktestFill],
) -> tuple[Decimal, Decimal, int, int]:
    gains = Decimal("0")
    losses = Decimal("0")
    profitable_trades = 0
    closed_trades = 0

    for fill in fills:
        if fill.status != "filled" or fill.realized_pnl == Decimal("0"):
            continue
        closed_trades += 1
        if fill.realized_pnl > Decimal("0"):
            profitable_trades += 1
            gains += fill.realized_pnl
        else:
            losses += abs(fill.realized_pnl)

    return gains, losses, profitable_trades, closed_trades


def _win_rate(
    *,
    profitable_trades: int,
    closed_trades: int,
) -> Decimal:
    if closed_trades == 0:
        return Decimal("0")

    return Decimal(profitable_trades) / Decimal(closed_trades)


def _profit_factor(
    *,
    realized_gains: Decimal,
    realized_losses: Decimal,
) -> Decimal:
    if realized_losses == Decimal("0"):
        return realized_gains

    return realized_gains / realized_losses


def _average_exposure(
    steps: tuple[BacktestStepResult, ...],
) -> Decimal:
    exposures: list[Decimal] = []
    for step in steps:
        equity = step.portfolio_snapshot.equity
        if equity == Decimal("0"):
            exposures.append(
                Decimal("0"),
            )
        else:
            exposures.append(
                step.portfolio_snapshot.market_value / equity,
            )

    return _average(
        tuple(exposures),
    )


def _turnover(
    *,
    steps: tuple[BacktestStepResult, ...],
    average_equity: Decimal,
) -> Decimal:
    if average_equity == Decimal("0"):
        return Decimal("0")

    gross_notional = sum(
        (
            fill.quantity * fill.price
            for step in steps
            for fill in step.simulated_fills
            if fill.status == "filled"
        ),
        Decimal("0"),
    )
    return gross_notional / average_equity


def _benchmark_return_from_parameters(
    scenario: BacktestScenario,
) -> Decimal:
    value = scenario.parameters.get(
        "benchmark_return",
    )
    if value is None:
        return Decimal("0")

    try:
        return Decimal(
            str(value),
        )
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _average(
    values: tuple[Decimal, ...],
) -> Decimal:
    if not values:
        return Decimal("0")

    return sum(
        values,
        Decimal("0"),
    ) / Decimal(len(values))
