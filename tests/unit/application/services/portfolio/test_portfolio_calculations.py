from __future__ import annotations

from typing import Any

import pytest

from application.services.portfolio.portfolio_analysis import (
    execute_portfolio_analysis,
)
from application.services.portfolio.portfolio_equity import (
    execute_equity_analysis,
)
from application.services.portfolio.portfolio_positions import (
    execute_positions_analysis,
)


def _equity_state(
    *,
    equity: float = 100000.0,
    cash: float = 60000.0,
    portfolio_value: float = 100000.0,
) -> dict[str, Any]:
    return execute_equity_analysis(
        raw_peak_equity=equity,
        raw_account={
            "id": "acct-123",
            "equity": equity,
            "portfolio_value": portfolio_value,
            "cash": cash,
            "buying_power": cash,
        },
    )


def test_portfolio_analysis_handles_no_position_portfolio() -> None:
    positions_state = execute_positions_analysis(
        [],
        symbol=None,
    )
    equity_state = _equity_state()

    analysis = execute_portfolio_analysis(
        positions_state=positions_state,
        equity_state=equity_state,
        portfolio_history={},
    )

    assert analysis["portfolio_regime"] == "flat"
    assert analysis["directional_bias"] == "neutral"
    assert analysis["position_count"] == 0
    assert analysis["gross_exposure"] == pytest.approx(0.0)
    assert analysis["net_exposure"] == pytest.approx(0.0)
    assert analysis["long_exposure"] == pytest.approx(0.0)
    assert analysis["short_exposure"] == pytest.approx(0.0)
    assert analysis["unrealized_pnl"] == pytest.approx(0.0)
    assert analysis["unrealized_pnl_pct"] == pytest.approx(0.0)
    assert analysis["unrealized_intraday_pnl"] == pytest.approx(0.0)
    assert analysis["unrealized_intraday_pnl_pct"] == pytest.approx(0.0)
    assert analysis["portfolio_history"]["has_history"] is False


def test_portfolio_analysis_preserves_long_only_precision() -> None:
    raw_positions = [
        {
            "symbol": "SPY",
            "quantity": 300.0,
            "avg_entry_price": 90.0,
            "current_price": 100.0,
            "market_value": 30000.0,
            "cost_basis": 27000.0,
            "unrealized_pl": 3000.0,
            "unrealized_plpc": 3000.0 / 27000.0,
            "unrealized_intraday_pl": 500.0,
            "unrealized_intraday_plpc": 500.0 / 27000.0,
            "side": "long",
            "sector": "technology",
            "asset_class": "equity",
            "beta": 1.2,
        }
    ]

    positions_state = execute_positions_analysis(
        raw_positions,
        symbol=None,
    )
    analysis = execute_portfolio_analysis(
        positions_state=positions_state,
        equity_state=_equity_state(),
        portfolio_history={
            "timestamp": ["2026-06-05T20:00:00Z"],
            "equity": [100000.0],
            "profit_loss": [5000.0],
            "profit_loss_pct": [0.05],
            "base_value": 95000.0,
            "timeframe": "1D",
            "cashflow": {},
        },
    )

    assert analysis["gross_exposure"] == pytest.approx(0.3)
    assert analysis["net_exposure"] == pytest.approx(0.3)
    assert analysis["long_exposure"] == pytest.approx(0.3)
    assert analysis["short_exposure"] == pytest.approx(0.0)
    assert analysis["directional_bias"] == "long"
    assert analysis["unrealized_pnl"] == pytest.approx(3000.0)
    assert analysis["unrealized_pnl_pct"] == pytest.approx(3000.0 / 27000.0)
    assert analysis["unrealized_intraday_pnl"] == pytest.approx(500.0)
    assert analysis["unrealized_intraday_pnl_pct"] == pytest.approx(
        500.0 / 27000.0,
    )
    assert analysis["realized_pnl"] == pytest.approx(2000.0)
    assert analysis["realized_pnl_pct"] == pytest.approx(2000.0 / 95000.0)
    assert analysis["sector_exposure"]["technology"] == pytest.approx(0.3)
    assert analysis["asset_class_exposure"]["equity"] == pytest.approx(0.3)
    assert analysis["beta_exposure"] == pytest.approx(0.36)


def test_portfolio_analysis_handles_mixed_long_short_pnl_percentages() -> None:
    raw_positions = [
        {
            "symbol": "SPY",
            "quantity": 100.0,
            "avg_entry_price": 90.0,
            "current_price": 100.0,
            "market_value": 10000.0,
            "cost_basis": 9000.0,
            "side": "long",
            "beta": 1.0,
        },
        {
            "symbol": "QQQ",
            "quantity": 50.0,
            "avg_entry_price": 200.0,
            "current_price": 180.0,
            "market_value": 9000.0,
            "cost_basis": 10000.0,
            "side": "short",
            "beta": 1.0,
        },
    ]

    positions_state = execute_positions_analysis(
        raw_positions,
        symbol=None,
    )

    assert positions_state["positions"][1]["unrealized_pnl"] == pytest.approx(
        1000.0,
    )
    assert positions_state["positions"][1]["signed_market_value"] == pytest.approx(
        -9000.0,
    )

    analysis = execute_portfolio_analysis(
        positions_state=positions_state,
        equity_state=_equity_state(),
        portfolio_history=None,
    )

    assert analysis["unrealized_pnl"] == pytest.approx(2000.0)
    assert analysis["unrealized_pnl_pct"] == pytest.approx(2000.0 / 19000.0)
    assert analysis["gross_exposure"] == pytest.approx(0.19)
    assert analysis["net_exposure"] == pytest.approx(0.01)
    assert analysis["long_exposure"] == pytest.approx(0.10)
    assert analysis["short_exposure"] == pytest.approx(0.09)
    assert analysis["directional_bias"] == "neutral"


def test_equity_analysis_preserves_margin_and_restriction_flags() -> None:
    equity_state = execute_equity_analysis(
        raw_peak_equity=120000.0,
        raw_account={
            "id": "acct-123",
            "equity": 100000.0,
            "portfolio_value": 100000.0,
            "cash": 5000.0,
            "buying_power": 8000.0,
            "long_market_value": 90000.0,
            "short_market_value": -30000.0,
            "initial_margin": 20000.0,
            "maintenance_margin": 80000.0,
            "last_maintenance_margin": 70000.0,
            "daytrade_count": 3,
            "pattern_day_trader": True,
            "trading_blocked": True,
            "transfers_blocked": True,
            "account_blocked": False,
            "trade_suspended_by_user": True,
            "shorting_enabled": False,
        },
    )

    assert equity_state["margin_utilization_ratio"] == pytest.approx(0.8)
    assert equity_state["initial_margin_ratio"] == pytest.approx(0.2)
    assert equity_state["last_maintenance_margin"] == pytest.approx(70000.0)
    assert equity_state["account_health"] == "restricted"
    assert equity_state["trading_blocked"] is True
    assert equity_state["transfers_blocked"] is True
    assert equity_state["account_blocked"] is False
    assert equity_state["trade_suspended_by_user"] is True
    assert equity_state["shorting_enabled"] is False
    assert equity_state["gross_market_value"] == pytest.approx(120000.0)
    assert equity_state["net_market_value"] == pytest.approx(60000.0)
    assert equity_state["gross_exposure_ratio"] == pytest.approx(1.2)
    assert equity_state["net_exposure_ratio"] == pytest.approx(0.6)
    assert equity_state["risk_signals"]["high_margin_utilization"] is True
    assert equity_state["risk_signals"]["critical_margin_utilization"] is True
    assert equity_state["risk_signals"]["daytrade_warning"] is True
    assert equity_state["risk_signals"]["shorting_disabled"] is True
