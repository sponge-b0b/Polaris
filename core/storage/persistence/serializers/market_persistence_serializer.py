from __future__ import annotations

from typing import Any
from typing import cast

from core.database.models.market import MarketBreadthSnapshotModel
from core.database.models.market import MarketContextSnapshotModel
from core.database.models.market import MarketEventSnapshotModel
from core.database.models.market import MarketIndicatorModel
from core.database.models.market import MarketOhlcvModel
from core.database.models.market import TechnicalAnalysisSnapshotModel
from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.market import MarketBreadthSnapshotRecord
from core.storage.persistence.market import MarketContextSnapshotRecord
from core.storage.persistence.market import MarketEventSnapshotRecord
from core.storage.persistence.market import MarketIndicatorRecord
from core.storage.persistence.market import MarketOhlcvRecord
from core.storage.persistence.market import TechnicalAnalysisSnapshotRecord


class MarketPersistenceSerializer:
    """
    Serializer between typed market persistence records and SQLAlchemy models.

    Market/provider payloads should be normalized into typed records before this
    boundary. JSON dictionaries are introduced here only for PostgreSQL JSONB
    columns that preserve final curated inputs, outputs, parameters, and
    metadata for replay, audit, and future RAG source curation.
    """

    @staticmethod
    def ohlcv_values(
        record: MarketOhlcvRecord,
    ) -> dict[str, Any]:
        return {
            "ohlcv_id": record.ohlcv_id,
            "symbol": record.symbol,
            "timestamp": record.timestamp,
            "source": record.source,
            "open_price": record.open_price,
            "high_price": record.high_price,
            "low_price": record.low_price,
            "close_price": record.close_price,
            "adjusted_close": record.adjusted_close,
            "volume": record.volume,
            **_lineage_values(record.lineage),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def indicator_values(
        record: MarketIndicatorRecord,
    ) -> dict[str, Any]:
        return {
            "indicator_id": record.indicator_id,
            "symbol": record.symbol,
            "timestamp": record.timestamp,
            "source": record.source,
            "indicator_name": record.indicator_name,
            "indicator_value": record.indicator_value,
            "timeframe": record.timeframe,
            "parameters": dict(record.parameters),
            **_lineage_values(record.lineage),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def context_snapshot_values(
        record: MarketContextSnapshotRecord,
    ) -> dict[str, Any]:
        return {
            "context_snapshot_id": record.context_snapshot_id,
            "timestamp": record.timestamp,
            "source": record.source,
            "universe": record.universe,
            "market_regime": record.market_regime,
            "volatility_regime": record.volatility_regime,
            "breadth_regime": record.breadth_regime,
            "trend_score": record.trend_score,
            "volatility_score": record.volatility_score,
            "breadth_score": record.breadth_score,
            "risk_score": record.risk_score,
            "vix": record.vix,
            "vix_20": record.vix_20,
            "vix_50": record.vix_50,
            "vix_percentile_252": record.vix_percentile_252,
            "vix_trend_ratio": record.vix_trend_ratio,
            "vix_change_5d": record.vix_change_5d,
            "vix_change_20d": record.vix_change_20d,
            "vvix": record.vvix,
            "vvix_20": record.vvix_20,
            "vvix_50": record.vvix_50,
            "vvix_percentile_252": record.vvix_percentile_252,
            "vvix_trend_ratio": record.vvix_trend_ratio,
            "vvix_change_5d": record.vvix_change_5d,
            "vvix_change_20d": record.vvix_change_20d,
            "market_cap_index": record.market_cap_index,
            "market_cap_index_20": record.market_cap_index_20,
            "market_cap_index_50": record.market_cap_index_50,
            "market_cap_index_change_5d": record.market_cap_index_change_5d,
            "market_cap_index_change_20d": record.market_cap_index_change_20d,
            "advances_count": record.advances_count,
            "declines_count": record.declines_count,
            "unchanged_count": record.unchanged_count,
            "active_count": record.active_count,
            "net_breadth": record.net_breadth,
            "breadth_percent": record.breadth_percent,
            "ad_ratio": record.ad_ratio,
            "ad_line": record.ad_line,
            "ad_line_ema_10": record.ad_line_ema_10,
            "ad_line_ema_20": record.ad_line_ema_20,
            "ad_line_ema_50": record.ad_line_ema_50,
            "ad_line_slope_5": record.ad_line_slope_5,
            "ad_line_slope_20": record.ad_line_slope_20,
            "ad_line_trend_ratio": record.ad_line_trend_ratio,
            "ad_line_trend_score": record.ad_line_trend_score,
            "price_ad_divergence": record.price_ad_divergence,
            "pct_above_50dma": record.pct_above_50dma,
            "pct_above_200dma": record.pct_above_200dma,
            "new_highs": record.new_highs,
            "new_lows": record.new_lows,
            "new_high_low_diff": record.new_high_low_diff,
            "new_high_low_ratio": record.new_high_low_ratio,
            "net_breadth_ema_19": record.net_breadth_ema_19,
            "net_breadth_ema_39": record.net_breadth_ema_39,
            "mcclellan_oscillator": record.mcclellan_oscillator,
            "mcclellan_summation_index": record.mcclellan_summation_index,
            "has_vix": record.has_vix,
            "has_vvix": record.has_vvix,
            "has_sp500": record.has_sp500,
            "has_ad_line": record.has_ad_line,
            "has_breadth": record.has_breadth,
            "inputs_payload": dict(record.inputs_payload),
            "market_context_payload": dict(record.market_context_payload),
            "top_50_constituents_payload": dict(record.top_50_constituents_payload),
            "market_caps_payload": dict(record.market_caps_payload),
            **_lineage_values(record.lineage),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def technical_snapshot_values(
        record: TechnicalAnalysisSnapshotRecord,
    ) -> dict[str, Any]:
        return {
            "technical_snapshot_id": record.technical_snapshot_id,
            "symbol": record.symbol,
            "timestamp": record.timestamp,
            "source": record.source,
            "technical_regime": record.technical_regime,
            "trend_regime": record.trend_regime,
            "volatility_regime": record.volatility_regime,
            "breadth_regime": record.breadth_regime,
            "technical_score": record.technical_score,
            "directional_technical_score": record.directional_technical_score,
            "bull_score": record.bull_score,
            "bear_score": record.bear_score,
            "sideways_score": record.sideways_score,
            "trend_score": record.trend_score,
            "trend_strength": record.trend_strength,
            "trend_quality": record.trend_quality,
            "volatility_score": record.volatility_score,
            "breadth_score": record.breadth_score,
            "risk_score": record.risk_score,
            "trend_risk_score": record.trend_risk_score,
            "volatility_risk_score": record.volatility_risk_score,
            "breadth_risk_score": record.breadth_risk_score,
            "strategy_environment": record.strategy_environment,
            "confidence": record.confidence,
            "inputs_payload": dict(record.inputs_payload),
            "snapshot_payload": dict(record.snapshot_payload),
            "market_context_payload": dict(record.market_context_payload),
            "micro_regime_payload": dict(record.micro_regime_payload),
            "trend_payload": dict(record.trend_payload),
            "volatility_payload": dict(record.volatility_payload),
            "breadth_payload": dict(record.breadth_payload),
            "raw_regime_payload": dict(record.raw_regime_payload),
            "regime_payload": dict(record.regime_payload),
            **_lineage_values(record.lineage),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def breadth_snapshot_values(
        record: MarketBreadthSnapshotRecord,
    ) -> dict[str, Any]:
        return {
            "breadth_snapshot_id": record.breadth_snapshot_id,
            "timestamp": record.timestamp,
            "universe": record.universe,
            "source": record.source,
            "has_breadth_data": record.has_breadth_data,
            "advances_count": record.advances_count,
            "declines_count": record.declines_count,
            "unchanged_count": record.unchanged_count,
            "new_highs": record.new_highs,
            "new_lows": record.new_lows,
            "ad_line": record.ad_line,
            "ad_line_ema_10": record.ad_line_ema_10,
            "ad_line_ema_20": record.ad_line_ema_20,
            "ad_line_ema_50": record.ad_line_ema_50,
            "ad_line_slope_5": record.ad_line_slope_5,
            "ad_line_slope_20": record.ad_line_slope_20,
            "ad_line_trend_ratio": record.ad_line_trend_ratio,
            "ad_line_trend_score": record.ad_line_trend_score,
            "price_ad_divergence": record.price_ad_divergence,
            "pct_above_50dma": record.pct_above_50dma,
            "pct_above_200dma": record.pct_above_200dma,
            "new_high_low_diff": record.new_high_low_diff,
            "new_high_low_ratio": record.new_high_low_ratio,
            "net_breadth_ema_19": record.net_breadth_ema_19,
            "net_breadth_ema_39": record.net_breadth_ema_39,
            "mcclellan_oscillator": record.mcclellan_oscillator,
            "mcclellan_summation_index": record.mcclellan_summation_index,
            "breadth_score": record.breadth_score,
            "breadth_risk_score": record.breadth_risk_score,
            "trend_score": record.trend_score,
            "slope_score": record.slope_score,
            "confirmation_score": record.confirmation_score,
            "participation_score": record.participation_score,
            "leadership_score": record.leadership_score,
            "mcclellan_score": record.mcclellan_score,
            "divergence_score": record.divergence_score,
            "breadth_regime": record.breadth_regime,
            "risk_regime": record.risk_regime,
            "strategy_environment": record.strategy_environment,
            "inputs_payload": dict(record.inputs_payload),
            "components_payload": dict(record.components_payload),
            "source_metrics_payload": dict(record.source_metrics_payload),
            "breadth_payload": dict(record.breadth_payload),
            **_lineage_values(record.lineage),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def event_snapshot_values(
        record: MarketEventSnapshotRecord,
    ) -> dict[str, Any]:
        return {
            "event_snapshot_id": record.event_snapshot_id,
            "symbol": record.symbol,
            "timestamp": record.timestamp,
            "source": record.source,
            "market_pressure_score": record.market_pressure_score,
            "volatility_forecast": record.volatility_forecast,
            "regime_bias": record.regime_bias,
            "event_count": record.event_count,
            "high_impact_count": record.high_impact_count,
            "events_payload": dict(record.events_payload),
            "high_impact_events_payload": dict(record.high_impact_events_payload),
            "risk_projection_payload": dict(record.risk_projection_payload),
            **_lineage_values(record.lineage),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def ohlcv_from_model(
        model: MarketOhlcvModel,
    ) -> MarketOhlcvRecord:
        return MarketOhlcvRecord(
            ohlcv_id=model.ohlcv_id,
            symbol=model.symbol,
            timestamp=model.timestamp,
            source=model.source,
            open_price=model.open_price,
            high_price=model.high_price,
            low_price=model.low_price,
            close_price=model.close_price,
            adjusted_close=model.adjusted_close,
            volume=model.volume,
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def indicator_from_model(
        model: MarketIndicatorModel,
    ) -> MarketIndicatorRecord:
        return MarketIndicatorRecord(
            indicator_id=model.indicator_id,
            symbol=model.symbol,
            timestamp=model.timestamp,
            source=model.source,
            indicator_name=model.indicator_name,
            indicator_value=model.indicator_value,
            timeframe=model.timeframe,
            parameters=cast(JsonObject, model.parameters),
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def context_snapshot_from_model(
        model: MarketContextSnapshotModel,
    ) -> MarketContextSnapshotRecord:
        return MarketContextSnapshotRecord(
            context_snapshot_id=model.context_snapshot_id,
            timestamp=model.timestamp,
            source=model.source,
            universe=model.universe,
            market_regime=model.market_regime,
            volatility_regime=model.volatility_regime,
            breadth_regime=model.breadth_regime,
            trend_score=model.trend_score,
            volatility_score=model.volatility_score,
            breadth_score=model.breadth_score,
            risk_score=model.risk_score,
            vix=model.vix,
            vix_20=model.vix_20,
            vix_50=model.vix_50,
            vix_percentile_252=model.vix_percentile_252,
            vix_trend_ratio=model.vix_trend_ratio,
            vix_change_5d=model.vix_change_5d,
            vix_change_20d=model.vix_change_20d,
            vvix=model.vvix,
            vvix_20=model.vvix_20,
            vvix_50=model.vvix_50,
            vvix_percentile_252=model.vvix_percentile_252,
            vvix_trend_ratio=model.vvix_trend_ratio,
            vvix_change_5d=model.vvix_change_5d,
            vvix_change_20d=model.vvix_change_20d,
            market_cap_index=model.market_cap_index,
            market_cap_index_20=model.market_cap_index_20,
            market_cap_index_50=model.market_cap_index_50,
            market_cap_index_change_5d=model.market_cap_index_change_5d,
            market_cap_index_change_20d=model.market_cap_index_change_20d,
            advances_count=model.advances_count,
            declines_count=model.declines_count,
            unchanged_count=model.unchanged_count,
            active_count=model.active_count,
            net_breadth=model.net_breadth,
            breadth_percent=model.breadth_percent,
            ad_ratio=model.ad_ratio,
            ad_line=model.ad_line,
            ad_line_ema_10=model.ad_line_ema_10,
            ad_line_ema_20=model.ad_line_ema_20,
            ad_line_ema_50=model.ad_line_ema_50,
            ad_line_slope_5=model.ad_line_slope_5,
            ad_line_slope_20=model.ad_line_slope_20,
            ad_line_trend_ratio=model.ad_line_trend_ratio,
            ad_line_trend_score=model.ad_line_trend_score,
            price_ad_divergence=model.price_ad_divergence,
            pct_above_50dma=model.pct_above_50dma,
            pct_above_200dma=model.pct_above_200dma,
            new_highs=model.new_highs,
            new_lows=model.new_lows,
            new_high_low_diff=model.new_high_low_diff,
            new_high_low_ratio=model.new_high_low_ratio,
            net_breadth_ema_19=model.net_breadth_ema_19,
            net_breadth_ema_39=model.net_breadth_ema_39,
            mcclellan_oscillator=model.mcclellan_oscillator,
            mcclellan_summation_index=model.mcclellan_summation_index,
            has_vix=model.has_vix,
            has_vvix=model.has_vvix,
            has_sp500=model.has_sp500,
            has_ad_line=model.has_ad_line,
            has_breadth=model.has_breadth,
            inputs_payload=cast(JsonObject, model.inputs_payload),
            market_context_payload=cast(JsonObject, model.market_context_payload),
            top_50_constituents_payload=cast(
                JsonObject,
                model.top_50_constituents_payload,
            ),
            market_caps_payload=cast(JsonObject, model.market_caps_payload),
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def technical_snapshot_from_model(
        model: TechnicalAnalysisSnapshotModel,
    ) -> TechnicalAnalysisSnapshotRecord:
        return TechnicalAnalysisSnapshotRecord(
            technical_snapshot_id=model.technical_snapshot_id,
            symbol=model.symbol,
            timestamp=model.timestamp,
            source=model.source,
            technical_regime=model.technical_regime,
            trend_regime=model.trend_regime,
            volatility_regime=model.volatility_regime,
            breadth_regime=model.breadth_regime,
            technical_score=model.technical_score,
            directional_technical_score=model.directional_technical_score,
            bull_score=model.bull_score,
            bear_score=model.bear_score,
            sideways_score=model.sideways_score,
            trend_score=model.trend_score,
            trend_strength=model.trend_strength,
            trend_quality=model.trend_quality,
            volatility_score=model.volatility_score,
            breadth_score=model.breadth_score,
            risk_score=model.risk_score,
            trend_risk_score=model.trend_risk_score,
            volatility_risk_score=model.volatility_risk_score,
            breadth_risk_score=model.breadth_risk_score,
            strategy_environment=model.strategy_environment,
            confidence=model.confidence,
            inputs_payload=cast(JsonObject, model.inputs_payload),
            snapshot_payload=cast(JsonObject, model.snapshot_payload),
            market_context_payload=cast(JsonObject, model.market_context_payload),
            micro_regime_payload=cast(JsonObject, model.micro_regime_payload),
            trend_payload=cast(JsonObject, model.trend_payload),
            volatility_payload=cast(JsonObject, model.volatility_payload),
            breadth_payload=cast(JsonObject, model.breadth_payload),
            raw_regime_payload=cast(JsonObject, model.raw_regime_payload),
            regime_payload=cast(JsonObject, model.regime_payload),
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def breadth_snapshot_from_model(
        model: MarketBreadthSnapshotModel,
    ) -> MarketBreadthSnapshotRecord:
        return MarketBreadthSnapshotRecord(
            breadth_snapshot_id=model.breadth_snapshot_id,
            timestamp=model.timestamp,
            universe=model.universe,
            source=model.source,
            has_breadth_data=model.has_breadth_data,
            advances_count=model.advances_count,
            declines_count=model.declines_count,
            unchanged_count=model.unchanged_count,
            new_highs=model.new_highs,
            new_lows=model.new_lows,
            ad_line=model.ad_line,
            ad_line_ema_10=model.ad_line_ema_10,
            ad_line_ema_20=model.ad_line_ema_20,
            ad_line_ema_50=model.ad_line_ema_50,
            ad_line_slope_5=model.ad_line_slope_5,
            ad_line_slope_20=model.ad_line_slope_20,
            ad_line_trend_ratio=model.ad_line_trend_ratio,
            ad_line_trend_score=model.ad_line_trend_score,
            price_ad_divergence=model.price_ad_divergence,
            pct_above_50dma=model.pct_above_50dma,
            pct_above_200dma=model.pct_above_200dma,
            new_high_low_diff=model.new_high_low_diff,
            new_high_low_ratio=model.new_high_low_ratio,
            net_breadth_ema_19=model.net_breadth_ema_19,
            net_breadth_ema_39=model.net_breadth_ema_39,
            mcclellan_oscillator=model.mcclellan_oscillator,
            mcclellan_summation_index=model.mcclellan_summation_index,
            breadth_score=model.breadth_score,
            breadth_risk_score=model.breadth_risk_score,
            trend_score=model.trend_score,
            slope_score=model.slope_score,
            confirmation_score=model.confirmation_score,
            participation_score=model.participation_score,
            leadership_score=model.leadership_score,
            mcclellan_score=model.mcclellan_score,
            divergence_score=model.divergence_score,
            breadth_regime=model.breadth_regime,
            risk_regime=model.risk_regime,
            strategy_environment=model.strategy_environment,
            inputs_payload=cast(JsonObject, model.inputs_payload),
            components_payload=cast(JsonObject, model.components_payload),
            source_metrics_payload=cast(JsonObject, model.source_metrics_payload),
            breadth_payload=cast(JsonObject, model.breadth_payload),
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def event_snapshot_from_model(
        model: MarketEventSnapshotModel,
    ) -> MarketEventSnapshotRecord:
        return MarketEventSnapshotRecord(
            event_snapshot_id=model.event_snapshot_id,
            symbol=model.symbol,
            timestamp=model.timestamp,
            source=model.source,
            market_pressure_score=model.market_pressure_score,
            volatility_forecast=model.volatility_forecast,
            regime_bias=model.regime_bias,
            event_count=model.event_count,
            high_impact_count=model.high_impact_count,
            events_payload=cast(JsonObject, model.events_payload),
            high_impact_events_payload=cast(
                JsonObject,
                model.high_impact_events_payload,
            ),
            risk_projection_payload=cast(JsonObject, model.risk_projection_payload),
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )


def _lineage_values(
    lineage: PersistenceLineage,
) -> dict[str, str | None]:
    return {
        "workflow_name": lineage.workflow_name,
        "execution_id": lineage.execution_id,
        "runtime_id": lineage.runtime_id,
        "node_name": lineage.node_name,
    }


def _lineage_from_model(
    model: (
        MarketOhlcvModel
        | MarketIndicatorModel
        | MarketContextSnapshotModel
        | TechnicalAnalysisSnapshotModel
        | MarketBreadthSnapshotModel
        | MarketEventSnapshotModel
    ),
) -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name=model.workflow_name,
        execution_id=model.execution_id,
        runtime_id=model.runtime_id,
        node_name=model.node_name,
    )
