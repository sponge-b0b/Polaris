from __future__ import annotations

from dataclasses import FrozenInstanceError
from dataclasses import fields
from datetime import datetime
from datetime import timezone

import pytest

from domain.portfolio.models.portfolio_state import PortfolioState


def _minimal_state() -> PortfolioState:
    return PortfolioState(
        account_id="acct-1",
        timestamp=datetime(2026, 6, 6, tzinfo=timezone.utc),
        equity=100_000.0,
        peak_equity=105_000.0,
        portfolio_value=101_000.0,
        cash=10_000.0,
        buying_power=20_000.0,
    )


def test_portfolio_state_v2_defaults_are_canonical() -> None:
    state = _minimal_state()

    assert state.schema_version == 2
    assert state.last_equity == 0.0
    assert state.cash_ratio == 0.0
    assert state.buying_power_ratio == 0.0
    assert state.realized_pnl_pct == 0.0
    assert state.unrealized_pnl_pct == 0.0
    assert state.unrealized_intraday_pnl == 0.0
    assert state.unrealized_intraday_pnl_pct == 0.0
    assert state.pnl_total_pct == 0.0
    assert state.long_market_value == 0.0
    assert state.short_market_value == 0.0
    assert state.gross_market_value == 0.0
    assert state.net_market_value == 0.0
    assert state.gross_exposure == 0.0
    assert state.net_exposure == 0.0
    assert state.long_exposure == 0.0
    assert state.short_exposure == 0.0
    assert state.leverage == 0.0
    assert state.largest_position_pct == 0.0
    assert state.concentration_score == 0.0
    assert state.diversification_score == 1.0
    assert state.beta_exposure == 0.0
    assert state.beta_risk == 0.0
    assert state.portfolio_heat == 0.0
    assert state.risk_intensity == 0.0
    assert state.initial_margin == 0.0
    assert state.maintenance_margin == 0.0
    assert state.last_maintenance_margin == 0.0
    assert state.margin_utilization_ratio == 0.0
    assert state.initial_margin_ratio == 0.0
    assert state.daytrade_count == 0
    assert state.pattern_day_trader is False
    assert state.trading_blocked is False
    assert state.transfers_blocked is False
    assert state.account_blocked is False
    assert state.trade_suspended_by_user is False
    assert state.shorting_enabled is False
    assert state.position_count == 0
    assert state.portfolio_regime == "unknown"
    assert state.directional_bias == "neutral"
    assert state.account_health == "unknown"
    assert state.sector_exposure == {}
    assert state.asset_class_exposure == {}
    assert state.risk_signals == {}
    assert state.snapshot_id


def test_portfolio_state_exposes_expected_v2_field_contract() -> None:
    field_names = {field.name for field in fields(PortfolioState)}

    expected_fields = {
        "account_id",
        "timestamp",
        "equity",
        "peak_equity",
        "portfolio_value",
        "cash",
        "buying_power",
        "last_equity",
        "cash_ratio",
        "buying_power_ratio",
        "realized_pnl",
        "realized_pnl_pct",
        "unrealized_pnl",
        "unrealized_pnl_pct",
        "unrealized_intraday_pnl",
        "unrealized_intraday_pnl_pct",
        "pnl_total",
        "pnl_total_pct",
        "drawdown_absolute",
        "drawdown_percent",
        "capital_base",
        "equity_retention_ratio",
        "long_market_value",
        "short_market_value",
        "gross_market_value",
        "net_market_value",
        "gross_exposure",
        "net_exposure",
        "long_exposure",
        "short_exposure",
        "leverage",
        "largest_position_pct",
        "concentration_score",
        "diversification_score",
        "beta_exposure",
        "beta_risk",
        "portfolio_heat",
        "risk_intensity",
        "initial_margin",
        "maintenance_margin",
        "last_maintenance_margin",
        "margin_utilization_ratio",
        "initial_margin_ratio",
        "daytrade_count",
        "pattern_day_trader",
        "trading_blocked",
        "transfers_blocked",
        "account_blocked",
        "trade_suspended_by_user",
        "shorting_enabled",
        "position_count",
        "portfolio_regime",
        "directional_bias",
        "account_health",
        "sector_exposure",
        "asset_class_exposure",
        "risk_signals",
        "schema_version",
        "snapshot_id",
    }

    assert expected_fields <= field_names


def test_portfolio_state_is_immutable() -> None:
    state = _minimal_state()

    with pytest.raises(FrozenInstanceError):
        state.equity = 99_000.0  # type: ignore[misc]
