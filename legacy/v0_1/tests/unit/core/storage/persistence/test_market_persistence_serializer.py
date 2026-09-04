from __future__ import annotations

from datetime import UTC, datetime

from core.database.models.market import (
    MarketBreadthSnapshotModel,
    MarketContextSnapshotModel,
    MarketEventSnapshotModel,
    MarketIndicatorModel,
    MarketOhlcvModel,
    TechnicalAnalysisSnapshotModel,
)
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.market import (
    MarketBreadthSnapshotRecord,
    MarketContextSnapshotRecord,
    MarketEventSnapshotRecord,
    MarketIndicatorRecord,
    MarketOhlcvRecord,
    TechnicalAnalysisSnapshotRecord,
)
from core.storage.persistence.serializers.market_persistence_serializer import (
    MarketPersistenceSerializer,
)


def test_market_serializer_flattens_ohlcv_record() -> None:
    record = _ohlcv()

    values = MarketPersistenceSerializer.ohlcv_values(record)

    assert values["ohlcv_id"] == "market_ohlcv:2026-05-31T13:00:00+00:00:SPY:fmp"
    assert values["symbol"] == "SPY"
    assert values["source"] == "fmp"
    assert values["workflow_name"] == "morning_report"
    assert values["execution_id"] == "exec-1"
    assert values["metadata_payload"] == {"source": "unit-test"}


def test_market_serializer_round_trips_fact_records() -> None:
    ohlcv_model = MarketOhlcvModel(**MarketPersistenceSerializer.ohlcv_values(_ohlcv()))
    indicator_model = MarketIndicatorModel(
        **MarketPersistenceSerializer.indicator_values(_indicator())
    )

    ohlcv = MarketPersistenceSerializer.ohlcv_from_model(
        ohlcv_model,
    )
    indicator = MarketPersistenceSerializer.indicator_from_model(
        indicator_model,
    )

    assert ohlcv.symbol == "SPY"
    assert ohlcv.close_price == 532.0
    assert ohlcv.lineage.node_name == "technical_analysis"
    assert ohlcv.metadata == {"source": "unit-test"}
    assert indicator.indicator_id == "indicator-1"
    assert indicator.indicator_name == "rsi_14"
    assert indicator.parameters == {"period": 14}


def test_market_serializer_round_trips_snapshot_records() -> None:
    context_model = MarketContextSnapshotModel(
        **MarketPersistenceSerializer.context_snapshot_values(_context())
    )
    technical_model = TechnicalAnalysisSnapshotModel(
        **MarketPersistenceSerializer.technical_snapshot_values(_technical())
    )
    breadth_model = MarketBreadthSnapshotModel(
        **MarketPersistenceSerializer.breadth_snapshot_values(_breadth())
    )
    event_model = MarketEventSnapshotModel(
        **MarketPersistenceSerializer.event_snapshot_values(_event())
    )

    context = MarketPersistenceSerializer.context_snapshot_from_model(
        context_model,
    )
    technical = MarketPersistenceSerializer.technical_snapshot_from_model(
        technical_model,
    )
    breadth = MarketPersistenceSerializer.breadth_snapshot_from_model(
        breadth_model,
    )
    event = MarketPersistenceSerializer.event_snapshot_from_model(
        event_model,
    )

    assert context.context_snapshot_id == "context-1"
    assert context.market_regime == "bullish"
    assert context.market_context_payload == {"summary": "risk-on"}
    assert technical.technical_snapshot_id == "technical-1"
    assert technical.symbol == "SPY"
    assert technical.regime_payload == {"signal": "uptrend"}
    assert breadth.breadth_snapshot_id == "breadth-1"
    assert breadth.universe == "sp500"
    assert breadth.breadth_payload == {"summary": "constructive"}
    assert event.event_snapshot_id == "event-1"
    assert event.volatility_forecast == "high"
    assert event.risk_projection_payload == {"expected_volatility": "high"}


def _ohlcv() -> MarketOhlcvRecord:
    return MarketOhlcvRecord(
        ohlcv_id="market_ohlcv:2026-05-31T13:00:00+00:00:SPY:fmp",
        symbol="spy",
        timestamp=_timestamp(),
        source="fmp",
        open_price=530.0,
        high_price=535.0,
        low_price=529.0,
        close_price=532.0,
        adjusted_close=532.0,
        volume=1_000_000.0,
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _indicator() -> MarketIndicatorRecord:
    return MarketIndicatorRecord(
        indicator_id="indicator-1",
        symbol="spy",
        timestamp=_timestamp(),
        source="technical-service",
        indicator_name="rsi_14",
        indicator_value=61.5,
        timeframe="1d",
        parameters={"period": 14},
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _context() -> MarketContextSnapshotRecord:
    return MarketContextSnapshotRecord(
        context_snapshot_id="context-1",
        timestamp=_timestamp(),
        source="market-context-service",
        universe="sp500",
        market_regime="bullish",
        volatility_regime="normal",
        breadth_regime="constructive",
        trend_score=0.6,
        volatility_score=0.3,
        breadth_score=0.4,
        risk_score=0.25,
        vix=14.5,
        vvix=82.0,
        inputs_payload={"vix": 14.5},
        market_context_payload={"summary": "risk-on"},
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _technical() -> TechnicalAnalysisSnapshotRecord:
    return TechnicalAnalysisSnapshotRecord(
        technical_snapshot_id="technical-1",
        symbol="spy",
        timestamp=_timestamp(),
        source="technical-service",
        technical_regime="bullish",
        trend_regime="uptrend",
        volatility_regime="normal",
        breadth_regime="constructive",
        directional_technical_score=0.7,
        trend_score=0.65,
        volatility_score=0.25,
        breadth_score=0.45,
        risk_score=0.2,
        confidence=0.82,
        inputs_payload={"prices": 252},
        snapshot_payload={"rsi_14": 61.5},
        regime_payload={"signal": "uptrend"},
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _breadth() -> MarketBreadthSnapshotRecord:
    return MarketBreadthSnapshotRecord(
        breadth_snapshot_id="breadth-1",
        timestamp=_timestamp(),
        universe="sp500",
        source="breadth-service",
        advances_count=320,
        declines_count=170,
        unchanged_count=10,
        new_highs=30,
        new_lows=8,
        ad_line=1250.0,
        pct_above_50dma=0.62,
        pct_above_200dma=0.58,
        breadth_score=0.5,
        breadth_risk_score=0.2,
        breadth_regime="constructive",
        inputs_payload={"advancers": 320},
        breadth_payload={"summary": "constructive"},
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _event() -> MarketEventSnapshotRecord:
    return MarketEventSnapshotRecord(
        event_snapshot_id="event-1",
        symbol="spy",
        timestamp=_timestamp(),
        source="market-events-service",
        market_pressure_score=0.45,
        volatility_forecast="high",
        regime_bias="risk_off",
        event_count=3,
        high_impact_count=1,
        events_payload={"events": ["cpi"]},
        high_impact_events_payload={"events": ["fomc"]},
        risk_projection_payload={"expected_volatility": "high"},
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="technical_analysis",
    )


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 13, 0, tzinfo=UTC)
