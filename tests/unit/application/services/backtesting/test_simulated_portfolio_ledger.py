from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal

from application.services.backtesting import BacktestInitialPosition
from application.services.backtesting import BacktestScenario
from application.services.backtesting.simulated_portfolio_ledger import (
    BacktestPortfolioLedger,
)


def test_ledger_fills_long_trade_from_trade_packager_and_execution_guard() -> None:
    scenario = _scenario(
        initial_cash=Decimal("1000"),
    )
    ledger = BacktestPortfolioLedger(
        scenario,
    )
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)

    snapshot, fills = ledger.apply_workflow_outputs(
        timestamp=timestamp,
        scenario=scenario,
        node_outputs=_node_outputs(
            price=Decimal("100"),
            direction="long",
            adjusted_position_size=Decimal("0.5"),
        ),
    )

    assert len(fills) == 1
    assert fills[0].status == "filled"
    assert fills[0].side == "buy"
    assert fills[0].quantity == Decimal("5.0")
    assert snapshot.cash == Decimal("500.0")
    assert snapshot.market_value == Decimal("500.0")
    assert snapshot.equity == Decimal("1000.0")
    position = snapshot.positions["SPY"]
    assert isinstance(position, dict)
    assert position["quantity"] == "5.0"
    assert position["side"] == "long"


def test_ledger_marks_existing_position_to_market_without_trade_intent() -> None:
    scenario = _scenario(
        initial_cash=Decimal("1000"),
        initial_positions=(
            BacktestInitialPosition(
                symbol="SPY",
                quantity=Decimal("2"),
                average_price=Decimal("100"),
            ),
        ),
    )
    ledger = BacktestPortfolioLedger(
        scenario,
    )
    timestamp = datetime(2026, 1, 2, tzinfo=timezone.utc)

    snapshot, fills = ledger.apply_workflow_outputs(
        timestamp=timestamp,
        scenario=scenario,
        node_outputs=_technical_only_outputs(
            price=Decimal("125"),
        ),
    )

    assert fills == ()
    assert snapshot.cash == Decimal("1000")
    assert snapshot.market_value == Decimal("250")
    assert snapshot.equity == Decimal("1250")
    position = snapshot.positions["SPY"]
    assert isinstance(position, dict)
    assert position["unrealized_pnl"] == "50"


def test_ledger_rejects_buy_when_cash_is_insufficient() -> None:
    scenario = _scenario(
        initial_cash=Decimal("1000"),
    )
    ledger = BacktestPortfolioLedger(
        scenario,
    )
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)

    snapshot, fills = ledger.apply_workflow_outputs(
        timestamp=timestamp,
        scenario=scenario,
        node_outputs=_node_outputs(
            price=Decimal("100"),
            direction="long",
            adjusted_position_size=Decimal("2.0"),
        ),
    )

    assert len(fills) == 1
    assert fills[0].status == "rejected"
    assert fills[0].reason == "insufficient_cash"
    assert snapshot.cash == Decimal("1000")
    assert snapshot.market_value == Decimal("0")
    assert snapshot.equity == Decimal("1000")


def test_ledger_uses_scenario_parameter_prices_for_deterministic_replay() -> None:
    scenario = _scenario(
        initial_cash=Decimal("1000"),
        parameters={
            "prices": {
                "SPY": {
                    "2026-01-01": "50",
                }
            }
        },
    )
    ledger = BacktestPortfolioLedger(
        scenario,
    )
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)

    snapshot, fills = ledger.apply_workflow_outputs(
        timestamp=timestamp,
        scenario=scenario,
        node_outputs=_node_outputs(
            price=Decimal("100"),
            direction="long",
            adjusted_position_size=Decimal("0.5"),
        ),
    )

    assert fills[0].price == Decimal("50")
    assert fills[0].quantity == Decimal("10.0")
    assert snapshot.cash == Decimal("500.0")


def _scenario(
    *,
    initial_cash: Decimal,
    initial_positions: tuple[BacktestInitialPosition, ...] = (),
    parameters: dict[str, object] | None = None,
) -> BacktestScenario:
    return BacktestScenario(
        scenario_id="ledger-check",
        name="Ledger check",
        workflow_name="morning_report",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
        symbols=("SPY",),
        benchmark_symbol="SPY",
        initial_cash=initial_cash,
        initial_positions=initial_positions,
        parameters=parameters or {},
    )


def _node_outputs(
    *,
    price: Decimal,
    direction: str,
    adjusted_position_size: Decimal,
) -> dict[str, object]:
    return {
        **_technical_only_outputs(
            price=price,
        ),
        "trade_packager": {
            "outputs": {
                "features": {
                    "trade_intent": {
                        "symbol": "SPY",
                        "direction": direction,
                        "position_sizing_hint": str(adjusted_position_size),
                    }
                }
            }
        },
        "execution_risk_guard": {
            "outputs": {
                "features": {
                    "execution_guard": {
                        "mode": "normal",
                        "adjusted_position_size": str(adjusted_position_size),
                    }
                }
            }
        },
    }


def _technical_only_outputs(
    *,
    price: Decimal,
) -> dict[str, object]:
    return {
        "technical_agent": {
            "outputs": {
                "features": {
                    "symbol": "SPY",
                    "snapshot": {
                        "close": str(price),
                    },
                }
            }
        }
    }
