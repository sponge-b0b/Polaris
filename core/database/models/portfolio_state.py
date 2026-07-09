from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from core.database.base import Base


class PortfolioStateHistoryModel(Base):
    __tablename__ = "portfolio_state_history"

    snapshot_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    account_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    workflow_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    execution_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    schema_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
    )
    equity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    peak_equity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    portfolio_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    cash: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    buying_power: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    realized_pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    unrealized_pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    pnl_total: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    drawdown_absolute: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    drawdown_percent: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    capital_base: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    equity_retention_ratio: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    cash_ratio: Mapped[float] = mapped_column(
        "cash_pct",
        Float,
        nullable=False,
    )
    account_number: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    status: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    currency: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    regt_buying_power: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    daytrading_buying_power: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    non_marginable_buying_power: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    options_buying_power: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    multiplier: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    accrued_fees: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    pending_transfer_in: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    pending_transfer_out: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    options_approved_level: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    options_trading_level: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    account_health: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    risk_signals: Mapped[dict[str, Any] | None] = mapped_column(
        "risk_signals_payload",
        JSONB,
        nullable=True,
    )
    portfolio_state_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    equity_state_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    last_equity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    realized_pnl_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    unrealized_pnl_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    unrealized_intraday_pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    unrealized_intraday_pnl_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    pnl_total_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    long_market_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    short_market_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    gross_market_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    net_market_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    gross_exposure: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    net_exposure: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    long_exposure: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    short_exposure: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    leverage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    largest_position_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    concentration_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    diversification_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )
    beta_exposure: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    beta_risk: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    portfolio_heat: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    risk_intensity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    initial_margin: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    maintenance_margin: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    last_maintenance_margin: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    margin_utilization_ratio: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    initial_margin_ratio: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    daytrade_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    pattern_day_trader: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    trading_blocked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    transfers_blocked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    account_blocked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    trade_suspended_by_user: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    shorting_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    position_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    portfolio_regime: Mapped[str] = mapped_column(
        String,
        nullable=True,
    )
    directional_bias: Mapped[str] = mapped_column(
        String,
        nullable=True,
    )
    sector_exposure: Mapped[dict[str, float]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    asset_class_exposure: Mapped[dict[str, float]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    buying_power_ratio: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_portfolio_state_account_timestamp",
    PortfolioStateHistoryModel.account_id,
    PortfolioStateHistoryModel.timestamp,
)


class PortfolioStateLatestModel(Base):
    __tablename__ = "portfolio_state_latest"

    account_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    snapshot_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    workflow_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    execution_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    schema_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
    )
    equity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    peak_equity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    portfolio_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    cash: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    buying_power: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    realized_pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    unrealized_pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    pnl_total: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    drawdown_absolute: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    drawdown_percent: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    capital_base: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    equity_retention_ratio: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    cash_ratio: Mapped[float] = mapped_column(
        "cash_pct",
        Float,
        nullable=False,
    )
    account_number: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    status: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    currency: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    regt_buying_power: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    daytrading_buying_power: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    non_marginable_buying_power: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    options_buying_power: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    multiplier: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    accrued_fees: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    pending_transfer_in: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    pending_transfer_out: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    options_approved_level: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    options_trading_level: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    account_health: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    risk_signals: Mapped[dict[str, Any] | None] = mapped_column(
        "risk_signals_payload",
        JSONB,
        nullable=True,
    )
    portfolio_state_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    equity_state_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    last_equity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    realized_pnl_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    unrealized_pnl_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    unrealized_intraday_pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    unrealized_intraday_pnl_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    pnl_total_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    long_market_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    short_market_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    gross_market_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    net_market_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    gross_exposure: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    net_exposure: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    long_exposure: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    short_exposure: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    leverage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    largest_position_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    concentration_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    diversification_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )
    beta_exposure: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    beta_risk: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    portfolio_heat: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    risk_intensity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    initial_margin: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    maintenance_margin: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    last_maintenance_margin: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    margin_utilization_ratio: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    initial_margin_ratio: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    daytrade_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    pattern_day_trader: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    trading_blocked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    transfers_blocked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    account_blocked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    trade_suspended_by_user: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    shorting_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    position_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    portfolio_regime: Mapped[str] = mapped_column(
        String,
        nullable=True,
    )
    directional_bias: Mapped[str] = mapped_column(
        String,
        nullable=True,
    )
    sector_exposure: Mapped[dict[str, float]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    asset_class_exposure: Mapped[dict[str, float]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    buying_power_ratio: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
