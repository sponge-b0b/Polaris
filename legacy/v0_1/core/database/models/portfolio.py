from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base


class PortfolioPositionHistoryModel(Base):
    __tablename__ = "portfolio_positions_history"

    position_history_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    account_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "portfolio_state_history.snapshot_id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    quantity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    side: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    qty_available: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    entry_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    current_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    lastday_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    change_today: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    market_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    signed_market_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    cost_basis: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    unrealized_pnl: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    unrealized_pnl_pct: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    unrealized_intraday_pnl: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    unrealized_intraday_pnl_pct: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    asset_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    exchange: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    asset_class: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    asset_marginable: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    weight: Mapped[float | None] = mapped_column(
        "exposure_weight",
        Float,
        nullable=True,
    )
    sector: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    theme: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    beta: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    swap_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    avg_entry_swap_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    risk_weight: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
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
    runtime_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    node_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    position_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    position_risk_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    row_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    row_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_portfolio_positions_history_account_timestamp",
    PortfolioPositionHistoryModel.account_id,
    PortfolioPositionHistoryModel.timestamp,
)
Index(
    "idx_portfolio_positions_history_symbol_timestamp",
    PortfolioPositionHistoryModel.symbol,
    PortfolioPositionHistoryModel.timestamp,
)
Index(
    "idx_portfolio_positions_history_workflow_execution",
    PortfolioPositionHistoryModel.workflow_name,
    PortfolioPositionHistoryModel.execution_id,
)
Index(
    "idx_portfolio_positions_history_account_symbol",
    PortfolioPositionHistoryModel.account_id,
    PortfolioPositionHistoryModel.symbol,
)


class PortfolioPositionLatestModel(Base):
    __tablename__ = "portfolio_positions_latest"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "symbol",
            name="uq_portfolio_positions_latest_account_symbol",
        ),
    )

    position_latest_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    account_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "portfolio_state_history.snapshot_id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    quantity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    side: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    qty_available: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    entry_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    current_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    lastday_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    change_today: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    market_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    signed_market_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    cost_basis: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    unrealized_pnl: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    unrealized_pnl_pct: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    unrealized_intraday_pnl: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    unrealized_intraday_pnl_pct: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    asset_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    exchange: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    asset_class: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    asset_marginable: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    weight: Mapped[float | None] = mapped_column(
        "exposure_weight",
        Float,
        nullable=True,
    )
    sector: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    theme: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    beta: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    swap_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    avg_entry_swap_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    risk_weight: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
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
    runtime_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    node_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    position_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    position_risk_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    row_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    row_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_portfolio_positions_latest_account_symbol",
    PortfolioPositionLatestModel.account_id,
    PortfolioPositionLatestModel.symbol,
)
Index(
    "idx_portfolio_positions_latest_symbol_timestamp",
    PortfolioPositionLatestModel.symbol,
    PortfolioPositionLatestModel.timestamp,
)
Index(
    "idx_portfolio_positions_latest_workflow_execution",
    PortfolioPositionLatestModel.workflow_name,
    PortfolioPositionLatestModel.execution_id,
)


class PortfolioExposureSnapshotModel(Base):
    __tablename__ = "portfolio_exposure_snapshots"

    exposure_snapshot_id: Mapped[str] = mapped_column(
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
    snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "portfolio_state_history.snapshot_id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    exposure_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    exposure_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    exposure_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    weight: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    beta: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    risk_weight: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
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
    runtime_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    node_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    row_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    row_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_portfolio_exposure_snapshots_account_timestamp",
    PortfolioExposureSnapshotModel.account_id,
    PortfolioExposureSnapshotModel.timestamp,
)
Index(
    "idx_portfolio_exposure_snapshots_type_name",
    PortfolioExposureSnapshotModel.exposure_type,
    PortfolioExposureSnapshotModel.exposure_name,
)
Index(
    "idx_portfolio_exposure_snapshots_workflow_execution",
    PortfolioExposureSnapshotModel.workflow_name,
    PortfolioExposureSnapshotModel.execution_id,
)


class PortfolioRiskSnapshotModel(Base):
    __tablename__ = "portfolio_risk_snapshots"

    risk_snapshot_id: Mapped[str] = mapped_column(
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
    snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "portfolio_state_history.snapshot_id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    portfolio_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    cash: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    account_health: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    risk_level: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    drawdown_risk: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    volatility_risk: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    concentration_risk: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    liquidity_risk: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    beta: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    cash_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    equity_retention_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    risk_signals: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
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
    runtime_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    node_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    row_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    row_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_portfolio_risk_snapshots_account_timestamp",
    PortfolioRiskSnapshotModel.account_id,
    PortfolioRiskSnapshotModel.timestamp,
)
Index(
    "idx_portfolio_risk_snapshots_risk_level_timestamp",
    PortfolioRiskSnapshotModel.risk_level,
    PortfolioRiskSnapshotModel.timestamp,
)
Index(
    "idx_portfolio_risk_snapshots_workflow_execution",
    PortfolioRiskSnapshotModel.workflow_name,
    PortfolioRiskSnapshotModel.execution_id,
)


class PortfolioAllocationSnapshotModel(Base):
    __tablename__ = "portfolio_allocation_snapshots"

    allocation_snapshot_id: Mapped[str] = mapped_column(
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
    snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "portfolio_state_history.snapshot_id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    allocation_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    allocation_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    current_weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    target_weight: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    drift: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    market_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
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
    runtime_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    node_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    row_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    row_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_portfolio_allocation_snapshots_account_timestamp",
    PortfolioAllocationSnapshotModel.account_id,
    PortfolioAllocationSnapshotModel.timestamp,
)
Index(
    "idx_portfolio_allocation_snapshots_type_name",
    PortfolioAllocationSnapshotModel.allocation_type,
    PortfolioAllocationSnapshotModel.allocation_name,
)
Index(
    "idx_portfolio_allocation_snapshots_workflow_execution",
    PortfolioAllocationSnapshotModel.workflow_name,
    PortfolioAllocationSnapshotModel.execution_id,
)


class PortfolioEquityHistoryPointModel(Base):
    __tablename__ = "portfolio_equity_history_points"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "source",
            "timeframe",
            "observed_at",
            name="uq_portfolio_equity_history_natural_key",
        ),
    )

    portfolio_equity_history_point_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    account_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String, nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    equity: Mapped[float] = mapped_column(Float, nullable=False)
    profit_loss: Mapped[float] = mapped_column(Float, nullable=False)
    profit_loss_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    base_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    cashflow_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    workflow_name: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    execution_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    runtime_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    node_name: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    row_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    row_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_portfolio_equity_history_account_observed_at",
    PortfolioEquityHistoryPointModel.account_id,
    PortfolioEquityHistoryPointModel.observed_at,
)
Index(
    "idx_portfolio_equity_history_workflow_execution",
    PortfolioEquityHistoryPointModel.workflow_name,
    PortfolioEquityHistoryPointModel.execution_id,
)
