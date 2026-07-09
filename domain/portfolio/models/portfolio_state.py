from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass(
    frozen=True,
    slots=True,
)
class PortfolioState:
    account_id: str
    timestamp: datetime

    equity: float
    peak_equity: float
    portfolio_value: float

    cash: float
    buying_power: float

    last_equity: float = 0.0
    cash_ratio: float = 0.0
    buying_power_ratio: float = 0.0

    realized_pnl: float = 0.0
    realized_pnl_pct: float = 0.0

    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0

    unrealized_intraday_pnl: float = 0.0
    unrealized_intraday_pnl_pct: float = 0.0

    pnl_total: float = 0.0
    pnl_total_pct: float = 0.0

    drawdown_absolute: float = 0.0
    drawdown_percent: float = 0.0

    capital_base: float = 0.0
    equity_retention_ratio: float = 0.0

    long_market_value: float = 0.0
    short_market_value: float = 0.0
    gross_market_value: float = 0.0
    net_market_value: float = 0.0

    gross_exposure: float = 0.0
    net_exposure: float = 0.0
    long_exposure: float = 0.0
    short_exposure: float = 0.0
    leverage: float = 0.0

    largest_position_pct: float = 0.0
    concentration_score: float = 0.0
    diversification_score: float = 1.0

    beta_exposure: float = 0.0
    beta_risk: float = 0.0
    portfolio_heat: float = 0.0
    risk_intensity: float = 0.0

    initial_margin: float = 0.0
    maintenance_margin: float = 0.0
    last_maintenance_margin: float = 0.0
    margin_utilization_ratio: float = 0.0
    initial_margin_ratio: float = 0.0

    daytrade_count: int = 0
    pattern_day_trader: bool = False
    trading_blocked: bool = False
    transfers_blocked: bool = False
    account_blocked: bool = False
    trade_suspended_by_user: bool = False
    shorting_enabled: bool = False

    position_count: int = 0
    portfolio_regime: str = "unknown"
    directional_bias: str = "neutral"
    account_health: str = "unknown"

    sector_exposure: dict[str, float] = field(default_factory=dict)
    asset_class_exposure: dict[str, float] = field(default_factory=dict)

    risk_signals: dict[str, Any] = field(default_factory=dict)

    schema_version: int = 2

    snapshot_id: str = field(
        default_factory=lambda: str(uuid4()),
    )
