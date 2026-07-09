from __future__ import annotations

from typing import cast

from sqlalchemy import Boolean
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from core.database.base import Base
from core.database.models.market import MarketBreadthSnapshotModel
from core.database.models.market import MarketContextSnapshotModel
from core.database.models.market import MarketEventSnapshotModel
from core.database.models.market import MarketIndicatorModel
from core.database.models.market import MarketOhlcvModel
from core.database.models.market import TechnicalAnalysisSnapshotModel


def test_market_models_are_imported_into_base_metadata() -> None:
    assert "market_ohlcv" in Base.metadata.tables
    assert "market_indicators" in Base.metadata.tables
    assert "market_context_snapshots" in Base.metadata.tables
    assert "technical_analysis_snapshots" in Base.metadata.tables
    assert "market_breadth_snapshots" in Base.metadata.tables
    assert "market_event_snapshots" in Base.metadata.tables


def test_market_ohlcv_model_persists_symbol_timestamp_source_facts() -> None:
    columns = MarketOhlcvModel.__table__.c
    primary_keys = _primary_key_names(MarketOhlcvModel.__table__)
    unique_constraints = _unique_constraint_names(MarketOhlcvModel.__table__)

    assert primary_keys == {"ohlcv_id"}
    assert columns.symbol.nullable is False
    assert columns.timestamp.nullable is False
    assert columns.source.nullable is False
    assert columns.open_price.nullable is False
    assert columns.high_price.nullable is False
    assert columns.low_price.nullable is False
    assert columns.close_price.nullable is False
    assert columns.adjusted_close.nullable is True
    assert columns.volume.nullable is False
    assert "uq_market_ohlcv_symbol_timestamp_source" in unique_constraints


def test_market_indicator_model_persists_indicator_values_and_parameters() -> None:
    columns = MarketIndicatorModel.__table__.c
    primary_keys = _primary_key_names(MarketIndicatorModel.__table__)
    unique_constraints = _unique_constraint_names(MarketIndicatorModel.__table__)

    assert primary_keys == {"indicator_id"}
    assert columns.symbol.nullable is False
    assert columns.timestamp.nullable is False
    assert columns.source.nullable is False
    assert columns.indicator_name.nullable is False
    assert columns.indicator_value.nullable is False
    assert columns.timeframe.nullable is True
    assert isinstance(columns.parameters.type, JSONB)
    assert (
        "uq_market_indicators_symbol_timestamp_source_name_timeframe"
        in unique_constraints
    )


def test_market_context_snapshot_model_persists_final_context_outputs() -> None:
    columns = MarketContextSnapshotModel.__table__.c
    primary_keys = _primary_key_names(MarketContextSnapshotModel.__table__)

    assert primary_keys == {"context_snapshot_id"}
    assert columns.timestamp.nullable is False
    assert columns.source.nullable is True
    assert columns.universe.nullable is True
    assert columns.market_regime.nullable is True
    assert columns.volatility_regime.nullable is True
    assert columns.breadth_regime.nullable is True
    for column_name in (
        "trend_score",
        "volatility_score",
        "breadth_score",
        "risk_score",
        "vix",
        "vix_20",
        "vix_50",
        "vix_percentile_252",
        "vix_trend_ratio",
        "vix_change_5d",
        "vix_change_20d",
        "vvix",
        "vvix_20",
        "vvix_50",
        "vvix_percentile_252",
        "vvix_trend_ratio",
        "vvix_change_5d",
        "vvix_change_20d",
        "market_cap_index",
        "market_cap_index_20",
        "market_cap_index_50",
        "market_cap_index_change_5d",
        "market_cap_index_change_20d",
        "breadth_percent",
        "ad_ratio",
        "ad_line",
        "ad_line_ema_10",
        "ad_line_ema_20",
        "ad_line_ema_50",
        "ad_line_slope_5",
        "ad_line_slope_20",
        "ad_line_trend_ratio",
        "ad_line_trend_score",
        "price_ad_divergence",
        "pct_above_50dma",
        "pct_above_200dma",
        "new_high_low_ratio",
        "net_breadth_ema_19",
        "net_breadth_ema_39",
        "mcclellan_oscillator",
        "mcclellan_summation_index",
    ):
        assert columns[column_name].nullable is True

    for column_name in (
        "advances_count",
        "declines_count",
        "unchanged_count",
        "active_count",
        "net_breadth",
        "new_highs",
        "new_lows",
        "new_high_low_diff",
    ):
        assert columns[column_name].nullable is True

    for column_name in (
        "has_vix",
        "has_vvix",
        "has_sp500",
        "has_ad_line",
        "has_breadth",
    ):
        assert columns[column_name].nullable is True
        assert isinstance(columns[column_name].type, Boolean)

    assert isinstance(columns.inputs_payload.type, JSONB)
    assert isinstance(columns.market_context_payload.type, JSONB)
    assert isinstance(columns.top_50_constituents_payload.type, JSONB)
    assert isinstance(columns.market_caps_payload.type, JSONB)
    assert "inputs" not in columns
    assert "outputs" not in columns


def test_technical_analysis_snapshot_model_persists_final_analysis_outputs() -> None:
    columns = TechnicalAnalysisSnapshotModel.__table__.c
    primary_keys = _primary_key_names(TechnicalAnalysisSnapshotModel.__table__)

    assert primary_keys == {"technical_snapshot_id"}
    assert columns.symbol.nullable is False
    assert columns.timestamp.nullable is False
    assert columns.source.nullable is True
    assert columns.technical_regime.nullable is True
    assert columns.trend_regime.nullable is True
    assert columns.volatility_regime.nullable is True
    assert columns.breadth_regime.nullable is True
    assert columns.technical_score.nullable is True
    assert columns.directional_technical_score.nullable is True
    assert columns.bull_score.nullable is True
    assert columns.bear_score.nullable is True
    assert columns.sideways_score.nullable is True
    assert columns.trend_score.nullable is True
    assert columns.trend_strength.nullable is True
    assert columns.trend_quality.nullable is True
    assert columns.volatility_score.nullable is True
    assert columns.breadth_score.nullable is True
    assert columns.risk_score.nullable is True
    assert columns.trend_risk_score.nullable is True
    assert columns.volatility_risk_score.nullable is True
    assert columns.breadth_risk_score.nullable is True
    assert columns.strategy_environment.nullable is True
    assert columns.confidence.nullable is True
    assert isinstance(columns.inputs_payload.type, JSONB)
    assert isinstance(columns.snapshot_payload.type, JSONB)
    assert isinstance(columns.market_context_payload.type, JSONB)
    assert isinstance(columns.micro_regime_payload.type, JSONB)
    assert isinstance(columns.trend_payload.type, JSONB)
    assert isinstance(columns.volatility_payload.type, JSONB)
    assert isinstance(columns.breadth_payload.type, JSONB)
    assert isinstance(columns.raw_regime_payload.type, JSONB)
    assert isinstance(columns.regime_payload.type, JSONB)
    assert "directional_score" not in columns
    assert "inputs" not in columns
    assert "indicator_outputs" not in columns
    assert "analysis_outputs" not in columns


def test_market_breadth_snapshot_model_persists_breadth_facts() -> None:
    columns = MarketBreadthSnapshotModel.__table__.c
    primary_keys = _primary_key_names(MarketBreadthSnapshotModel.__table__)

    assert primary_keys == {"breadth_snapshot_id"}
    assert columns.timestamp.nullable is False
    assert columns.universe.nullable is False
    assert columns.source.nullable is True
    for column_name in (
        "has_breadth_data",
        "advances_count",
        "declines_count",
        "unchanged_count",
        "new_highs",
        "new_lows",
        "ad_line",
        "ad_line_ema_10",
        "ad_line_ema_20",
        "ad_line_ema_50",
        "ad_line_slope_5",
        "ad_line_slope_20",
        "ad_line_trend_ratio",
        "ad_line_trend_score",
        "price_ad_divergence",
        "pct_above_50dma",
        "pct_above_200dma",
        "new_high_low_diff",
        "new_high_low_ratio",
        "net_breadth_ema_19",
        "net_breadth_ema_39",
        "mcclellan_oscillator",
        "mcclellan_summation_index",
        "breadth_score",
        "breadth_risk_score",
        "trend_score",
        "slope_score",
        "confirmation_score",
        "participation_score",
        "leadership_score",
        "mcclellan_score",
        "divergence_score",
        "breadth_regime",
        "risk_regime",
        "strategy_environment",
    ):
        assert columns[column_name].nullable is True

    assert isinstance(columns.has_breadth_data.type, Boolean)
    assert isinstance(columns.inputs_payload.type, JSONB)
    assert isinstance(columns.components_payload.type, JSONB)
    assert isinstance(columns.source_metrics_payload.type, JSONB)
    assert isinstance(columns.breadth_payload.type, JSONB)
    assert "advancing_count" not in columns
    assert "declining_count" not in columns
    assert "new_highs_count" not in columns
    assert "new_lows_count" not in columns
    assert "advance_decline_line" not in columns
    assert "percent_above_50dma" not in columns
    assert "percent_above_200dma" not in columns
    assert "inputs" not in columns
    assert "outputs" not in columns


def test_market_event_snapshot_model_persists_market_event_outputs() -> None:
    columns = MarketEventSnapshotModel.__table__.c
    primary_keys = _primary_key_names(MarketEventSnapshotModel.__table__)

    assert primary_keys == {"event_snapshot_id"}
    assert columns.symbol.nullable is False
    assert columns.timestamp.nullable is False
    assert columns.source.nullable is True
    assert columns.market_pressure_score.nullable is True
    assert columns.volatility_forecast.nullable is True
    assert isinstance(columns.volatility_forecast.type, String)
    assert columns.regime_bias.nullable is True
    assert columns.event_count.nullable is True
    assert columns.high_impact_count.nullable is True
    assert isinstance(columns.events_payload.type, JSONB)
    assert isinstance(columns.high_impact_events_payload.type, JSONB)
    assert isinstance(columns.risk_projection_payload.type, JSONB)
    assert "events" not in columns
    assert "high_impact_events" not in columns
    assert "risk_projection" not in columns


def test_market_models_use_jsonb_at_persistence_boundaries() -> None:
    assert isinstance(MarketOhlcvModel.__table__.c.metadata.type, JSONB)
    assert isinstance(MarketIndicatorModel.__table__.c.parameters.type, JSONB)
    assert isinstance(MarketIndicatorModel.__table__.c.metadata.type, JSONB)
    assert isinstance(MarketContextSnapshotModel.__table__.c.inputs_payload.type, JSONB)
    assert isinstance(
        MarketContextSnapshotModel.__table__.c.market_context_payload.type,
        JSONB,
    )
    assert isinstance(
        MarketContextSnapshotModel.__table__.c.top_50_constituents_payload.type,
        JSONB,
    )
    assert isinstance(
        MarketContextSnapshotModel.__table__.c.market_caps_payload.type, JSONB
    )
    assert isinstance(MarketContextSnapshotModel.__table__.c.metadata.type, JSONB)
    assert isinstance(
        TechnicalAnalysisSnapshotModel.__table__.c.inputs_payload.type, JSONB
    )
    assert isinstance(
        TechnicalAnalysisSnapshotModel.__table__.c.snapshot_payload.type, JSONB
    )
    assert isinstance(
        TechnicalAnalysisSnapshotModel.__table__.c.market_context_payload.type,
        JSONB,
    )
    assert isinstance(
        TechnicalAnalysisSnapshotModel.__table__.c.micro_regime_payload.type,
        JSONB,
    )
    assert isinstance(
        TechnicalAnalysisSnapshotModel.__table__.c.trend_payload.type, JSONB
    )
    assert isinstance(
        TechnicalAnalysisSnapshotModel.__table__.c.volatility_payload.type,
        JSONB,
    )
    assert isinstance(
        TechnicalAnalysisSnapshotModel.__table__.c.breadth_payload.type,
        JSONB,
    )
    assert isinstance(
        TechnicalAnalysisSnapshotModel.__table__.c.raw_regime_payload.type,
        JSONB,
    )
    assert isinstance(
        TechnicalAnalysisSnapshotModel.__table__.c.regime_payload.type, JSONB
    )
    assert isinstance(TechnicalAnalysisSnapshotModel.__table__.c.metadata.type, JSONB)
    assert isinstance(MarketBreadthSnapshotModel.__table__.c.inputs_payload.type, JSONB)
    assert isinstance(
        MarketBreadthSnapshotModel.__table__.c.components_payload.type, JSONB
    )
    assert isinstance(
        MarketBreadthSnapshotModel.__table__.c.source_metrics_payload.type,
        JSONB,
    )
    assert isinstance(
        MarketBreadthSnapshotModel.__table__.c.breadth_payload.type, JSONB
    )
    assert isinstance(MarketBreadthSnapshotModel.__table__.c.metadata.type, JSONB)
    assert isinstance(MarketEventSnapshotModel.__table__.c.events_payload.type, JSONB)
    assert isinstance(
        MarketEventSnapshotModel.__table__.c.high_impact_events_payload.type,
        JSONB,
    )
    assert isinstance(
        MarketEventSnapshotModel.__table__.c.risk_projection_payload.type, JSONB
    )
    assert isinstance(MarketEventSnapshotModel.__table__.c.metadata.type, JSONB)


def test_market_models_include_lineage_and_row_timestamps() -> None:
    for table in (
        MarketOhlcvModel.__table__,
        MarketIndicatorModel.__table__,
        MarketContextSnapshotModel.__table__,
        TechnicalAnalysisSnapshotModel.__table__,
        MarketBreadthSnapshotModel.__table__,
        MarketEventSnapshotModel.__table__,
    ):
        columns = table.c

        assert columns.workflow_name.nullable is True
        assert columns.execution_id.nullable is True
        assert columns.runtime_id.nullable is True
        assert columns.node_name.nullable is True
        assert columns.row_created_at.server_default is not None
        assert columns.row_updated_at.server_default is not None


def test_market_models_index_core_query_paths() -> None:
    ohlcv_indexes = _index_names(MarketOhlcvModel.__table__)
    indicator_indexes = _index_names(MarketIndicatorModel.__table__)
    context_indexes = _index_names(MarketContextSnapshotModel.__table__)
    technical_indexes = _index_names(TechnicalAnalysisSnapshotModel.__table__)
    breadth_indexes = _index_names(MarketBreadthSnapshotModel.__table__)
    event_indexes = _index_names(MarketEventSnapshotModel.__table__)

    assert "idx_market_ohlcv_symbol_timestamp" in ohlcv_indexes
    assert "idx_market_ohlcv_source_timestamp" in ohlcv_indexes
    assert "idx_market_ohlcv_workflow_execution" in ohlcv_indexes
    assert "idx_market_indicators_symbol_timestamp" in indicator_indexes
    assert "idx_market_indicators_source_timestamp" in indicator_indexes
    assert "idx_market_indicators_name_timestamp" in indicator_indexes
    assert "idx_market_indicators_workflow_execution" in indicator_indexes
    assert "idx_market_context_snapshots_timestamp_source" in context_indexes
    assert "idx_market_context_snapshots_universe_timestamp" in context_indexes
    assert "idx_market_context_snapshots_workflow_execution" in context_indexes
    assert "idx_technical_analysis_snapshots_symbol_timestamp" in technical_indexes
    assert "idx_technical_analysis_snapshots_source_timestamp" in technical_indexes
    assert "idx_technical_analysis_snapshots_regime_timestamp" in technical_indexes
    assert "idx_technical_analysis_snapshots_workflow_execution" in technical_indexes
    assert "idx_market_breadth_snapshots_universe_timestamp" in breadth_indexes
    assert "idx_market_breadth_snapshots_source_timestamp" in breadth_indexes
    assert "idx_market_breadth_snapshots_regime_timestamp" in breadth_indexes
    assert "idx_market_breadth_snapshots_workflow_execution" in breadth_indexes
    assert "idx_market_event_snapshots_symbol_timestamp" in event_indexes
    assert "idx_market_event_snapshots_source_timestamp" in event_indexes
    assert "idx_market_event_snapshots_regime_timestamp" in event_indexes
    assert "idx_market_event_snapshots_workflow_execution" in event_indexes


def _primary_key_names(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    return {column.name for column in sqlalchemy_table.primary_key}


def _unique_constraint_names(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    names: set[str] = set()
    for constraint in sqlalchemy_table.constraints:
        if not isinstance(constraint, UniqueConstraint):
            continue
        if isinstance(constraint.name, str):
            names.add(constraint.name)
    return names


def _index_names(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    return {index.name for index in sqlalchemy_table.indexes if index.name is not None}
