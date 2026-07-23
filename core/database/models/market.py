from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base


class MarketOhlcvModel(Base):
    __tablename__ = "market_ohlcv"
    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "timestamp",
            "source",
            name="uq_market_ohlcv_symbol_timestamp_source",
        ),
    )

    ohlcv_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
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
    source: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    open_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    high_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    low_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    close_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    adjusted_close: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    volume: Mapped[float] = mapped_column(
        Float,
        nullable=False,
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
    "idx_market_ohlcv_symbol_timestamp",
    MarketOhlcvModel.symbol,
    MarketOhlcvModel.timestamp,
)
Index(
    "idx_market_ohlcv_source_timestamp",
    MarketOhlcvModel.source,
    MarketOhlcvModel.timestamp,
)
Index(
    "idx_market_ohlcv_workflow_execution",
    MarketOhlcvModel.workflow_name,
    MarketOhlcvModel.execution_id,
)


class MarketIndicatorModel(Base):
    __tablename__ = "market_indicators"
    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "timestamp",
            "source",
            "indicator_name",
            "timeframe",
            name="uq_market_indicators_symbol_timestamp_source_name_timeframe",
        ),
    )

    indicator_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
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
    source: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    indicator_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    indicator_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    timeframe: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(
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
    "idx_market_indicators_symbol_timestamp",
    MarketIndicatorModel.symbol,
    MarketIndicatorModel.timestamp,
)
Index(
    "idx_market_indicators_source_timestamp",
    MarketIndicatorModel.source,
    MarketIndicatorModel.timestamp,
)
Index(
    "idx_market_indicators_name_timestamp",
    MarketIndicatorModel.indicator_name,
    MarketIndicatorModel.timestamp,
)
Index(
    "idx_market_indicators_workflow_execution",
    MarketIndicatorModel.workflow_name,
    MarketIndicatorModel.execution_id,
)


class MarketContextSnapshotModel(Base):
    __tablename__ = "market_context_snapshots"

    context_snapshot_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    source: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    universe: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    market_regime: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    volatility_regime: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    breadth_regime: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    trend_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    volatility_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    breadth_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    vix: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    vix_20: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    vix_50: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    vix_percentile_252: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    vix_trend_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    vix_change_5d: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    vix_change_20d: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    vvix: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    vvix_20: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    vvix_50: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    vvix_percentile_252: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    vvix_trend_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    vvix_change_5d: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    vvix_change_20d: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    market_cap_index: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    market_cap_index_20: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    market_cap_index_50: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    market_cap_index_change_5d: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    market_cap_index_change_20d: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    advances_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    declines_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    unchanged_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    active_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    net_breadth: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    breadth_percent: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    ad_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    ad_line: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    ad_line_ema_10: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    ad_line_ema_20: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    ad_line_ema_50: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    ad_line_slope_5: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    ad_line_slope_20: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    ad_line_trend_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    ad_line_trend_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    price_ad_divergence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    pct_above_50dma: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    pct_above_200dma: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    new_highs: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    new_lows: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    new_high_low_diff: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    new_high_low_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    net_breadth_ema_19: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    net_breadth_ema_39: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    mcclellan_oscillator: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    mcclellan_summation_index: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    has_vix: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    has_vvix: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    has_sp500: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    has_ad_line: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    has_breadth: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    inputs_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    market_context_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    top_50_constituents_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    market_caps_payload: Mapped[dict[str, Any]] = mapped_column(
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
    "idx_market_context_snapshots_timestamp_source",
    MarketContextSnapshotModel.timestamp,
    MarketContextSnapshotModel.source,
)
Index(
    "idx_market_context_snapshots_universe_timestamp",
    MarketContextSnapshotModel.universe,
    MarketContextSnapshotModel.timestamp,
)
Index(
    "idx_market_context_snapshots_workflow_execution",
    MarketContextSnapshotModel.workflow_name,
    MarketContextSnapshotModel.execution_id,
)


class TechnicalAnalysisSnapshotModel(Base):
    __tablename__ = "technical_analysis_snapshots"

    technical_snapshot_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
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
    source: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    technical_regime: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    trend_regime: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    volatility_regime: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    breadth_regime: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    technical_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    directional_technical_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    bull_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    bear_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    sideways_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    trend_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    trend_strength: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    trend_quality: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    volatility_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    breadth_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    trend_risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    volatility_risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    breadth_risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    strategy_environment: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    inputs_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    snapshot_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    market_context_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    micro_regime_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    trend_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    volatility_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    breadth_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    raw_regime_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    regime_payload: Mapped[dict[str, Any]] = mapped_column(
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
    "idx_technical_analysis_snapshots_symbol_timestamp",
    TechnicalAnalysisSnapshotModel.symbol,
    TechnicalAnalysisSnapshotModel.timestamp,
)
Index(
    "idx_technical_analysis_snapshots_source_timestamp",
    TechnicalAnalysisSnapshotModel.source,
    TechnicalAnalysisSnapshotModel.timestamp,
)
Index(
    "idx_technical_analysis_snapshots_regime_timestamp",
    TechnicalAnalysisSnapshotModel.technical_regime,
    TechnicalAnalysisSnapshotModel.timestamp,
)
Index(
    "idx_technical_analysis_snapshots_workflow_execution",
    TechnicalAnalysisSnapshotModel.workflow_name,
    TechnicalAnalysisSnapshotModel.execution_id,
)


class MarketBreadthSnapshotModel(Base):
    __tablename__ = "market_breadth_snapshots"

    breadth_snapshot_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    universe: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    source: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    has_breadth_data: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    advances_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    declines_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    unchanged_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    new_highs: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    new_lows: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    ad_line: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    ad_line_ema_10: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    ad_line_ema_20: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    ad_line_ema_50: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    ad_line_slope_5: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    ad_line_slope_20: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    ad_line_trend_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    ad_line_trend_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    price_ad_divergence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    pct_above_50dma: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    pct_above_200dma: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    new_high_low_diff: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    new_high_low_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    net_breadth_ema_19: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    net_breadth_ema_39: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    mcclellan_oscillator: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    mcclellan_summation_index: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    breadth_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    breadth_risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    trend_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    slope_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    confirmation_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    participation_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    leadership_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    mcclellan_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    divergence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    breadth_regime: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    risk_regime: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    strategy_environment: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    inputs_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    components_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    source_metrics_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    breadth_payload: Mapped[dict[str, Any]] = mapped_column(
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
    "idx_market_breadth_snapshots_universe_timestamp",
    MarketBreadthSnapshotModel.universe,
    MarketBreadthSnapshotModel.timestamp,
)
Index(
    "idx_market_breadth_snapshots_source_timestamp",
    MarketBreadthSnapshotModel.source,
    MarketBreadthSnapshotModel.timestamp,
)
Index(
    "idx_market_breadth_snapshots_regime_timestamp",
    MarketBreadthSnapshotModel.breadth_regime,
    MarketBreadthSnapshotModel.timestamp,
)
Index(
    "idx_market_breadth_snapshots_workflow_execution",
    MarketBreadthSnapshotModel.workflow_name,
    MarketBreadthSnapshotModel.execution_id,
)


class MarketEventSnapshotModel(Base):
    __tablename__ = "market_event_snapshots"

    event_snapshot_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
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
    source: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    market_pressure_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    volatility_forecast: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    regime_bias: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    event_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    high_impact_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    events_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    high_impact_events_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    risk_projection_payload: Mapped[dict[str, Any]] = mapped_column(
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
    "idx_market_event_snapshots_symbol_timestamp",
    MarketEventSnapshotModel.symbol,
    MarketEventSnapshotModel.timestamp,
)
Index(
    "idx_market_event_snapshots_source_timestamp",
    MarketEventSnapshotModel.source,
    MarketEventSnapshotModel.timestamp,
)
Index(
    "idx_market_event_snapshots_regime_timestamp",
    MarketEventSnapshotModel.regime_bias,
    MarketEventSnapshotModel.timestamp,
)
Index(
    "idx_market_event_snapshots_workflow_execution",
    MarketEventSnapshotModel.workflow_name,
    MarketEventSnapshotModel.execution_id,
)
