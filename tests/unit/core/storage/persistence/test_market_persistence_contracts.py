from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.market import (
    MarketBreadthSnapshotRecord,
    MarketContextSnapshotRecord,
    MarketEventSnapshotRecord,
    MarketIndicatorRecord,
    MarketOhlcvRecord,
    MarketPersistenceBundle,
    MarketPersistenceResult,
    TechnicalAnalysisSnapshotRecord,
    new_market_breadth_snapshot_id,
    new_market_context_snapshot_id,
    new_market_event_snapshot_id,
    new_market_indicator_id,
    new_market_ohlcv_id,
    new_technical_analysis_snapshot_id,
)


def test_market_ohlcv_record_is_typed_normalized_and_immutable() -> None:
    record = MarketOhlcvRecord(
        ohlcv_id="ohlcv-1",
        symbol=" spy ",
        timestamp=_timestamp(),
        source=" polygon ",
        open_price=530.0,
        high_price=535.0,
        low_price=529.0,
        close_price=534.0,
        adjusted_close=533.9,
        volume=10_000_000.0,
        lineage=_lineage(),
        metadata={"currency": "USD"},
    )

    assert record.symbol == "SPY"
    assert record.source == "polygon"
    assert record.high_price == 535.0
    assert record.low_price == 529.0
    assert record.lineage.execution_id == "exec-1"

    with pytest.raises(FrozenInstanceError):
        record.symbol = "QQQ"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"ohlcv_id": " "}, "ohlcv_id"),
        ({"symbol": ""}, "symbol"),
        ({"source": " "}, "source"),
        ({"open_price": -1.0}, "open_price"),
        ({"high_price": -1.0}, "high_price"),
        ({"low_price": -1.0}, "low_price"),
        ({"close_price": -1.0}, "close_price"),
        ({"volume": -1.0}, "volume"),
        ({"adjusted_close": -1.0}, "adjusted_close"),
    ],
)
def test_market_ohlcv_record_validates_required_fields_and_prices(
    kwargs: dict[str, object],
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "ohlcv_id": "ohlcv-1",
        "symbol": "SPY",
        "timestamp": _timestamp(),
        "source": "polygon",
        "open_price": 530.0,
        "high_price": 535.0,
        "low_price": 529.0,
        "close_price": 534.0,
        "volume": 10_000_000.0,
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        MarketOhlcvRecord(**values)  # type: ignore[arg-type]


def test_market_ohlcv_record_validates_high_low_order() -> None:
    with pytest.raises(ValueError, match="high_price"):
        MarketOhlcvRecord(
            ohlcv_id="ohlcv-1",
            symbol="SPY",
            timestamp=_timestamp(),
            source="polygon",
            open_price=530.0,
            high_price=528.0,
            low_price=529.0,
            close_price=534.0,
            volume=10_000_000.0,
        )


def test_market_indicator_record_preserves_parameters_and_allows_negative_values() -> (
    None
):
    record = MarketIndicatorRecord(
        indicator_id="indicator-1",
        symbol=" spy ",
        timestamp=_timestamp(),
        source=" polygon ",
        indicator_name=" MACD ",
        indicator_value=-1.25,
        timeframe=" daily ",
        parameters={"fast": 12, "slow": 26},
    )

    assert record.symbol == "SPY"
    assert record.source == "polygon"
    assert record.indicator_name == "MACD"
    assert record.indicator_value == -1.25
    assert record.timeframe == "daily"
    assert record.parameters == {"fast": 12, "slow": 26}


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"indicator_id": " "}, "indicator_id"),
        ({"symbol": ""}, "symbol"),
        ({"source": " "}, "source"),
        ({"indicator_name": " "}, "indicator_name"),
    ],
)
def test_market_indicator_record_validates_identifiers(
    kwargs: dict[str, object],
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "indicator_id": "indicator-1",
        "symbol": "SPY",
        "timestamp": _timestamp(),
        "source": "polygon",
        "indicator_name": "RSI",
        "indicator_value": 55.0,
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        MarketIndicatorRecord(**values)  # type: ignore[arg-type]


def test_market_context_snapshot_captures_final_scores_regimes_and_io() -> None:
    record = MarketContextSnapshotRecord(
        context_snapshot_id="context-1",
        timestamp=_timestamp(),
        source=" morning_report ",
        universe=" SP500 ",
        market_regime=" bullish ",
        volatility_regime=" normal ",
        breadth_regime=" constructive ",
        trend_score=0.45,
        volatility_score=0.2,
        breadth_score=0.3,
        risk_score=0.25,
        vix=14.2,
        vvix=80.0,
        inputs_payload={"symbols": ["SPY", "QQQ"]},
        market_context_payload={"summary": "Constructive tape."},
        lineage=_lineage(),
    )

    assert record.source == "morning_report"
    assert record.universe == "SP500"
    assert record.market_regime == "bullish"
    assert record.volatility_regime == "normal"
    assert record.breadth_regime == "constructive"
    assert record.inputs_payload == {"symbols": ["SPY", "QQQ"]}
    assert record.market_context_payload == {"summary": "Constructive tape."}


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"context_snapshot_id": " "}, "context_snapshot_id"),
        ({"trend_score": 1.1}, "trend_score"),
        ({"volatility_score": -1.1}, "volatility_score"),
        ({"breadth_score": 1.1}, "breadth_score"),
        ({"risk_score": 1.1}, "risk_score"),
        ({"vix": -1.0}, "vix"),
        ({"vvix": -1.0}, "vvix"),
    ],
)
def test_market_context_snapshot_validates_score_ranges(
    kwargs: dict[str, object],
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "context_snapshot_id": "context-1",
        "timestamp": _timestamp(),
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        MarketContextSnapshotRecord(**values)  # type: ignore[arg-type]


def test_technical_analysis_snapshot_captures_final_regime_payload() -> None:
    record = TechnicalAnalysisSnapshotRecord(
        technical_snapshot_id="technical-1",
        symbol=" spy ",
        timestamp=_timestamp(),
        source=" morning_report ",
        technical_regime=" bullish ",
        trend_regime=" uptrend ",
        volatility_regime=" normal ",
        breadth_regime=" constructive ",
        directional_technical_score=0.6,
        trend_score=0.7,
        volatility_score=0.2,
        breadth_score=0.4,
        risk_score=0.2,
        confidence=0.82,
        inputs_payload={"close": 534.0},
        snapshot_payload={"rsi": 58.0},
        regime_payload={"calibrated_signal": "bullish"},
    )

    assert record.symbol == "SPY"
    assert record.source == "morning_report"
    assert record.technical_regime == "bullish"
    assert record.trend_regime == "uptrend"
    assert record.snapshot_payload == {"rsi": 58.0}
    assert record.regime_payload == {"calibrated_signal": "bullish"}


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"technical_snapshot_id": " "}, "technical_snapshot_id"),
        ({"symbol": ""}, "symbol"),
        ({"directional_technical_score": 1.1}, "directional_technical_score"),
        ({"trend_score": -1.1}, "trend_score"),
        ({"volatility_score": 1.1}, "volatility_score"),
        ({"breadth_score": -1.1}, "breadth_score"),
        ({"risk_score": 1.1}, "risk_score"),
        ({"confidence": -0.1}, "confidence"),
    ],
)
def test_technical_analysis_snapshot_validates_identifiers_and_scores(
    kwargs: dict[str, object],
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "technical_snapshot_id": "technical-1",
        "symbol": "SPY",
        "timestamp": _timestamp(),
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        TechnicalAnalysisSnapshotRecord(**values)  # type: ignore[arg-type]


def test_market_breadth_snapshot_captures_counts_ratios_and_outputs() -> None:
    record = MarketBreadthSnapshotRecord(
        breadth_snapshot_id="breadth-1",
        timestamp=_timestamp(),
        universe=" SP500 ",
        source=" morning_report ",
        advances_count=320,
        declines_count=170,
        unchanged_count=10,
        new_highs=45,
        new_lows=5,
        ad_line=12_345.0,
        pct_above_50dma=0.62,
        pct_above_200dma=0.58,
        breadth_score=0.35,
        breadth_risk_score=0.25,
        breadth_regime=" constructive ",
        inputs_payload={"members": 500},
        breadth_payload={"confirmation": "positive"},
    )

    assert record.universe == "SP500"
    assert record.source == "morning_report"
    assert record.breadth_regime == "constructive"
    assert record.pct_above_50dma == 0.62
    assert record.breadth_payload == {"confirmation": "positive"}


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"breadth_snapshot_id": " "}, "breadth_snapshot_id"),
        ({"universe": ""}, "universe"),
        ({"advances_count": -1}, "advances_count"),
        ({"declines_count": -1}, "declines_count"),
        ({"unchanged_count": -1}, "unchanged_count"),
        ({"new_highs": -1}, "new_highs"),
        ({"new_lows": -1}, "new_lows"),
        ({"pct_above_50dma": 1.1}, "pct_above_50dma"),
        ({"pct_above_200dma": -0.1}, "pct_above_200dma"),
        ({"breadth_score": 1.1}, "breadth_score"),
        ({"breadth_risk_score": -0.1}, "breadth_risk_score"),
    ],
)
def test_market_breadth_snapshot_validates_identifiers_counts_and_scores(
    kwargs: dict[str, object],
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "breadth_snapshot_id": "breadth-1",
        "timestamp": _timestamp(),
        "universe": "SP500",
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        MarketBreadthSnapshotRecord(**values)  # type: ignore[arg-type]


def test_market_event_snapshot_captures_event_outputs() -> None:
    record = MarketEventSnapshotRecord(
        event_snapshot_id="event-1",
        symbol=" spy ",
        timestamp=_timestamp(),
        source=" market-events-service ",
        market_pressure_score=0.45,
        volatility_forecast=" high ",
        regime_bias=" risk_off ",
        event_count=3,
        high_impact_count=1,
        events_payload={"events": ["cpi"]},
        high_impact_events_payload={"events": ["fomc"]},
        risk_projection_payload={"expected_volatility": "high"},
    )

    assert record.symbol == "SPY"
    assert record.source == "market-events-service"
    assert record.volatility_forecast == "high"
    assert record.regime_bias == "risk_off"
    assert record.events_payload == {"events": ["cpi"]}


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"event_snapshot_id": " "}, "event_snapshot_id"),
        ({"symbol": ""}, "symbol"),
        ({"market_pressure_score": 1.1}, "market_pressure_score"),
        ({"event_count": -1}, "event_count"),
        ({"high_impact_count": -1}, "high_impact_count"),
    ],
)
def test_market_event_snapshot_validates_identifiers_counts_and_scores(
    kwargs: dict[str, object],
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "event_snapshot_id": "event-1",
        "symbol": "SPY",
        "timestamp": _timestamp(),
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        MarketEventSnapshotRecord(**values)  # type: ignore[arg-type]


def test_market_bundle_groups_atomic_persistence_payload() -> None:
    bundle = MarketPersistenceBundle(
        ohlcv=(_ohlcv(),),
        indicators=(_indicator(),),
        context_snapshots=(_context_snapshot(),),
        technical_snapshots=(_technical_snapshot(),),
        breadth_snapshots=(_breadth_snapshot(),),
        event_snapshots=(_event_snapshot(),),
    )

    assert len(bundle.ohlcv) == 1
    assert len(bundle.indicators) == 1
    assert len(bundle.context_snapshots) == 1
    assert len(bundle.technical_snapshots) == 1
    assert len(bundle.breadth_snapshots) == 1
    assert len(bundle.event_snapshots) == 1


def test_market_persistence_result_validates_state() -> None:
    success = MarketPersistenceResult.succeeded(
        primary_record_id="market-record-1",
        records_persisted=5,
    )
    failure = MarketPersistenceResult.failed(
        "database unavailable",
    )

    assert success.success is True
    assert success.records_persisted == 5
    assert success.primary_record_id == "market-record-1"
    assert failure.success is False
    assert failure.error == "database unavailable"

    with pytest.raises(ValueError, match="records_persisted"):
        MarketPersistenceResult(
            success=True,
            primary_record_id="market-record-1",
            records_persisted=-1,
        )

    with pytest.raises(ValueError, match="successful"):
        MarketPersistenceResult(
            success=True,
            primary_record_id="market-record-1",
            error="unexpected",
        )

    with pytest.raises(ValueError, match="primary_record_id"):
        MarketPersistenceResult(
            success=True,
        )

    with pytest.raises(ValueError, match="error"):
        MarketPersistenceResult.failed(
            " ",
        )


def test_market_id_helpers_are_stable_with_lineage_and_source_keys() -> None:
    assert (
        new_market_ohlcv_id(
            symbol=" spy ",
            timestamp=_timestamp(),
            source=" polygon ",
        )
        == "market_ohlcv:2026-05-31T14:00:00+00:00:SPY:polygon"
    )
    assert (
        new_market_indicator_id(
            symbol=" spy ",
            timestamp=_timestamp(),
            indicator_name=" RSI ",
            source=" polygon ",
            timeframe=" daily ",
        )
        == "market_indicator:2026-05-31T14:00:00+00:00:SPY:RSI:polygon:daily"
    )
    assert (
        new_market_context_snapshot_id(
            timestamp=_timestamp(),
            execution_id=" exec-1 ",
            context_key=" primary ",
        )
        == "market_context_snapshot:exec-1:2026-05-31T14:00:00+00:00:primary"
    )
    assert (
        new_technical_analysis_snapshot_id(
            symbol=" spy ",
            timestamp=_timestamp(),
            execution_id=" exec-1 ",
            snapshot_key=" primary ",
        )
        == "technical_analysis_snapshot:exec-1:2026-05-31T14:00:00+00:00:SPY:primary"
    )
    assert (
        new_market_breadth_snapshot_id(
            universe=" SP500 ",
            timestamp=_timestamp(),
            execution_id=" exec-1 ",
            snapshot_key=" primary ",
        )
        == "market_breadth_snapshot:exec-1:2026-05-31T14:00:00+00:00:SP500:primary"
    )
    assert (
        new_market_event_snapshot_id(
            symbol=" spy ",
            timestamp=_timestamp(),
            execution_id=" exec-1 ",
            snapshot_key=" primary ",
        )
        == "market_event_snapshot:exec-1:2026-05-31T14:00:00+00:00:SPY:primary"
    )


def test_market_fact_id_helpers_are_deterministic_by_source_keys() -> None:
    ohlcv_id = new_market_ohlcv_id(
        symbol=" spy ",
        timestamp=_timestamp(),
        source=" polygon ",
    )
    repeat_ohlcv_id = new_market_ohlcv_id(
        symbol="SPY",
        timestamp=_timestamp(),
        source="polygon",
    )
    alternate_source_ohlcv_id = new_market_ohlcv_id(
        symbol="SPY",
        timestamp=_timestamp(),
        source="fmp",
    )
    indicator_id = new_market_indicator_id(
        symbol=" spy ",
        timestamp=_timestamp(),
        indicator_name=" RSI ",
        source=" polygon ",
        timeframe=" daily ",
    )
    repeat_indicator_id = new_market_indicator_id(
        symbol="SPY",
        timestamp=_timestamp(),
        indicator_name="RSI",
        source="polygon",
        timeframe="daily",
    )

    assert ohlcv_id == repeat_ohlcv_id
    assert ohlcv_id != alternate_source_ohlcv_id
    assert indicator_id == repeat_indicator_id
    assert ":polygon" in ohlcv_id
    assert ":polygon:daily" in indicator_id


def _ohlcv() -> MarketOhlcvRecord:
    return MarketOhlcvRecord(
        ohlcv_id="ohlcv-1",
        symbol="SPY",
        timestamp=_timestamp(),
        source="polygon",
        open_price=530.0,
        high_price=535.0,
        low_price=529.0,
        close_price=534.0,
        volume=10_000_000.0,
    )


def _indicator() -> MarketIndicatorRecord:
    return MarketIndicatorRecord(
        indicator_id="indicator-1",
        symbol="SPY",
        timestamp=_timestamp(),
        source="polygon",
        indicator_name="RSI",
        indicator_value=58.0,
    )


def _context_snapshot() -> MarketContextSnapshotRecord:
    return MarketContextSnapshotRecord(
        context_snapshot_id="context-1",
        timestamp=_timestamp(),
        market_regime="bullish",
        trend_score=0.5,
    )


def _technical_snapshot() -> TechnicalAnalysisSnapshotRecord:
    return TechnicalAnalysisSnapshotRecord(
        technical_snapshot_id="technical-1",
        symbol="SPY",
        timestamp=_timestamp(),
        technical_regime="bullish",
        confidence=0.8,
    )


def _breadth_snapshot() -> MarketBreadthSnapshotRecord:
    return MarketBreadthSnapshotRecord(
        breadth_snapshot_id="breadth-1",
        timestamp=_timestamp(),
        universe="SP500",
        breadth_score=0.3,
    )


def _event_snapshot() -> MarketEventSnapshotRecord:
    return MarketEventSnapshotRecord(
        event_snapshot_id="event-1",
        symbol="SPY",
        timestamp=_timestamp(),
        market_pressure_score=0.4,
        volatility_forecast="medium",
    )


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="technical_analysis",
    )


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=UTC)
