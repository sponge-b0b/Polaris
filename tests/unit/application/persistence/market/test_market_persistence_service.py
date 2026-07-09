from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from datetime import timezone

import pytest

from application.persistence.market import MarketBreadthSnapshotPersistenceFilters
from application.persistence.market import MarketContextSnapshotPersistenceFilters
from application.persistence.market import MarketEventSnapshotPersistenceFilters
from application.persistence.market import MarketIndicatorPersistenceFilters
from application.persistence.market import MarketOhlcvPersistenceFilters
from application.persistence.market import MarketPersistenceService
from application.persistence.market import TechnicalAnalysisSnapshotPersistenceFilters
from core.storage.persistence.market import MarketBreadthSnapshotRecord
from core.storage.persistence.market import MarketContextSnapshotRecord
from core.storage.persistence.market import MarketEventSnapshotRecord
from core.storage.persistence.market import MarketIndicatorRecord
from core.storage.persistence.market import MarketOhlcvRecord
from core.storage.persistence.market import MarketPersistenceBundle
from core.storage.persistence.market import MarketPersistenceResult
from core.storage.persistence.market import TechnicalAnalysisSnapshotRecord


class FakeMarketRepository:
    def __init__(
        self,
        *,
        ohlcv: Sequence[MarketOhlcvRecord] = (),
        indicators: Sequence[MarketIndicatorRecord] = (),
        context_snapshots: Sequence[MarketContextSnapshotRecord] = (),
        technical_snapshots: Sequence[TechnicalAnalysisSnapshotRecord] = (),
        breadth_snapshots: Sequence[MarketBreadthSnapshotRecord] = (),
        event_snapshots: Sequence[MarketEventSnapshotRecord] = (),
    ) -> None:
        self.bundle: MarketPersistenceBundle | None = None
        self.ohlcv = tuple(ohlcv)
        self.indicators = tuple(indicators)
        self.context_snapshots = tuple(context_snapshots)
        self.technical_snapshots = tuple(technical_snapshots)
        self.breadth_snapshots = tuple(breadth_snapshots)
        self.event_snapshots = tuple(event_snapshots)
        self.ohlcv_filters: dict[str, str | datetime | None] | None = None
        self.indicator_filters: dict[str, str | datetime | None] | None = None
        self.context_filters: dict[str, str | datetime | None] | None = None
        self.technical_filters: dict[str, str | datetime | None] | None = None
        self.breadth_filters: dict[str, str | datetime | None] | None = None
        self.event_filters: dict[str, str | datetime | None] | None = None

    async def persist_market_bundle(
        self,
        bundle: MarketPersistenceBundle,
    ) -> MarketPersistenceResult:
        self.bundle = bundle
        return MarketPersistenceResult.succeeded(
            primary_record_id=_primary_record_id(bundle),
            records_persisted=(
                len(bundle.ohlcv)
                + len(bundle.indicators)
                + len(bundle.context_snapshots)
                + len(bundle.technical_snapshots)
                + len(bundle.breadth_snapshots)
                + len(bundle.event_snapshots)
            ),
        )

    async def list_ohlcv(
        self,
        *,
        symbol: str,
        source: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MarketOhlcvRecord]:
        self.ohlcv_filters = {
            "symbol": symbol,
            "source": source,
            "start": start,
            "end": end,
        }
        return self.ohlcv

    async def list_indicators(
        self,
        *,
        symbol: str,
        indicator_name: str | None = None,
        source: str | None = None,
        timeframe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MarketIndicatorRecord]:
        self.indicator_filters = {
            "symbol": symbol,
            "indicator_name": indicator_name,
            "source": source,
            "timeframe": timeframe,
            "start": start,
            "end": end,
        }
        return self.indicators

    async def list_context_snapshots(
        self,
        *,
        universe: str | None = None,
        source: str | None = None,
        market_regime: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MarketContextSnapshotRecord]:
        self.context_filters = {
            "universe": universe,
            "source": source,
            "market_regime": market_regime,
            "start": start,
            "end": end,
        }
        return self.context_snapshots

    async def list_technical_snapshots(
        self,
        *,
        symbol: str,
        source: str | None = None,
        technical_regime: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[TechnicalAnalysisSnapshotRecord]:
        self.technical_filters = {
            "symbol": symbol,
            "source": source,
            "technical_regime": technical_regime,
            "start": start,
            "end": end,
        }
        return self.technical_snapshots

    async def list_breadth_snapshots(
        self,
        *,
        universe: str,
        source: str | None = None,
        breadth_regime: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MarketBreadthSnapshotRecord]:
        self.breadth_filters = {
            "universe": universe,
            "source": source,
            "breadth_regime": breadth_regime,
            "start": start,
            "end": end,
        }
        return self.breadth_snapshots

    async def list_event_snapshots(
        self,
        *,
        symbol: str,
        source: str | None = None,
        regime_bias: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MarketEventSnapshotRecord]:
        self.event_filters = {
            "symbol": symbol,
            "source": source,
            "regime_bias": regime_bias,
            "start": start,
            "end": end,
        }
        return self.event_snapshots


@pytest.mark.asyncio
async def test_market_persistence_service_persists_existing_bundle() -> None:
    repository = FakeMarketRepository()
    service = MarketPersistenceService(repository)
    bundle = _bundle()

    result = await service.persist_bundle(bundle)

    assert result.success is True
    assert result.records_persisted == 6
    assert repository.bundle == bundle


@pytest.mark.asyncio
async def test_market_persistence_service_builds_typed_bundle() -> None:
    repository = FakeMarketRepository()
    service = MarketPersistenceService(repository)

    result = await service.persist_records(
        ohlcv=(_ohlcv(),),
        indicators=(_indicator(),),
        context_snapshots=(_context(),),
        technical_snapshots=(_technical(),),
        breadth_snapshots=(_breadth(),),
        event_snapshots=(_event(),),
    )

    assert result.success is True
    assert repository.bundle is not None
    assert repository.bundle.ohlcv[0].symbol == "SPY"
    assert repository.bundle.indicators[0].indicator_name == "rsi_14"
    assert repository.bundle.context_snapshots[0].market_regime == "bullish"
    assert repository.bundle.technical_snapshots[0].technical_regime == "bullish"
    assert repository.bundle.breadth_snapshots[0].breadth_regime == "constructive"
    assert repository.bundle.event_snapshots[0].regime_bias == "risk_off"


@pytest.mark.asyncio
async def test_market_persistence_service_uses_typed_filters() -> None:
    repository = FakeMarketRepository(
        ohlcv=(_ohlcv(),),
        indicators=(_indicator(),),
        context_snapshots=(_context(),),
        technical_snapshots=(_technical(),),
        breadth_snapshots=(_breadth(),),
        event_snapshots=(_event(),),
    )
    service = MarketPersistenceService(repository)
    start = _timestamp()
    end = datetime(2026, 5, 31, 15, 0, tzinfo=timezone.utc)

    ohlcv = await service.list_ohlcv(
        MarketOhlcvPersistenceFilters(
            symbol="spy",
            source="fmp",
            start=start,
            end=end,
        )
    )
    indicators = await service.list_indicators(
        MarketIndicatorPersistenceFilters(
            symbol="spy",
            indicator_name="rsi_14",
            source="technical-service",
            timeframe="1d",
            start=start,
            end=end,
        )
    )
    contexts = await service.list_context_snapshots(
        MarketContextSnapshotPersistenceFilters(
            universe="sp500",
            source="market-context-service",
            market_regime="bullish",
            start=start,
            end=end,
        )
    )
    technicals = await service.list_technical_snapshots(
        TechnicalAnalysisSnapshotPersistenceFilters(
            symbol="spy",
            source="technical-service",
            technical_regime="bullish",
            start=start,
            end=end,
        )
    )
    breadth = await service.list_breadth_snapshots(
        MarketBreadthSnapshotPersistenceFilters(
            universe="sp500",
            source="breadth-service",
            breadth_regime="constructive",
            start=start,
            end=end,
        )
    )
    events = await service.list_event_snapshots(
        MarketEventSnapshotPersistenceFilters(
            symbol="spy",
            source="market-events-service",
            regime_bias="risk_off",
            start=start,
            end=end,
        )
    )

    assert len(ohlcv) == 1
    assert len(indicators) == 1
    assert len(contexts) == 1
    assert len(technicals) == 1
    assert len(breadth) == 1
    assert len(events) == 1
    assert repository.ohlcv_filters == {
        "symbol": "SPY",
        "source": "fmp",
        "start": start,
        "end": end,
    }
    assert repository.indicator_filters == {
        "symbol": "SPY",
        "indicator_name": "rsi_14",
        "source": "technical-service",
        "timeframe": "1d",
        "start": start,
        "end": end,
    }
    assert repository.context_filters == {
        "universe": "sp500",
        "source": "market-context-service",
        "market_regime": "bullish",
        "start": start,
        "end": end,
    }
    assert repository.technical_filters == {
        "symbol": "SPY",
        "source": "technical-service",
        "technical_regime": "bullish",
        "start": start,
        "end": end,
    }
    assert repository.breadth_filters == {
        "universe": "sp500",
        "source": "breadth-service",
        "breadth_regime": "constructive",
        "start": start,
        "end": end,
    }
    assert repository.event_filters == {
        "symbol": "SPY",
        "source": "market-events-service",
        "regime_bias": "risk_off",
        "start": start,
        "end": end,
    }


@pytest.mark.asyncio
async def test_market_persistence_service_uses_default_context_filters() -> None:
    repository = FakeMarketRepository(context_snapshots=(_context(),))
    service = MarketPersistenceService(repository)

    contexts = await service.list_context_snapshots()

    assert len(contexts) == 1
    assert repository.context_filters == {
        "universe": None,
        "source": None,
        "market_regime": None,
        "start": None,
        "end": None,
    }


@pytest.mark.parametrize(
    "filters,args",
    [
        (
            MarketOhlcvPersistenceFilters,
            {
                "symbol": "SPY",
            },
        ),
        (
            MarketIndicatorPersistenceFilters,
            {
                "symbol": "SPY",
            },
        ),
        (
            MarketContextSnapshotPersistenceFilters,
            {},
        ),
        (
            TechnicalAnalysisSnapshotPersistenceFilters,
            {
                "symbol": "SPY",
            },
        ),
        (
            MarketBreadthSnapshotPersistenceFilters,
            {
                "universe": "sp500",
            },
        ),
        (
            MarketEventSnapshotPersistenceFilters,
            {
                "symbol": "SPY",
            },
        ),
    ],
)
def test_market_time_window_filters_require_ordered_bounds(
    filters: type[
        MarketOhlcvPersistenceFilters
        | MarketIndicatorPersistenceFilters
        | MarketContextSnapshotPersistenceFilters
        | TechnicalAnalysisSnapshotPersistenceFilters
        | MarketBreadthSnapshotPersistenceFilters
        | MarketEventSnapshotPersistenceFilters
    ],
    args: dict[str, str],
) -> None:
    start = datetime(2026, 5, 31, 15, 0, tzinfo=timezone.utc)
    end = _timestamp()

    with pytest.raises(ValueError, match="start must be less than or equal to end"):
        filters(
            **args,
            start=start,
            end=end,
        )


def _bundle() -> MarketPersistenceBundle:
    return MarketPersistenceBundle(
        ohlcv=(_ohlcv(),),
        indicators=(_indicator(),),
        context_snapshots=(_context(),),
        technical_snapshots=(_technical(),),
        breadth_snapshots=(_breadth(),),
        event_snapshots=(_event(),),
    )


def _ohlcv() -> MarketOhlcvRecord:
    return MarketOhlcvRecord(
        ohlcv_id="ohlcv-1",
        symbol="spy",
        timestamp=_timestamp(),
        source="fmp",
        open_price=530.0,
        high_price=535.0,
        low_price=529.0,
        close_price=532.0,
        adjusted_close=532.0,
        volume=1_000_000.0,
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
        inputs_payload={"vix": 14.5},
        market_context_payload={"summary": "risk-on"},
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
        pct_above_50dma=0.62,
        pct_above_200dma=0.58,
        breadth_score=0.5,
        breadth_risk_score=0.2,
        breadth_regime="constructive",
        inputs_payload={"advancers": 320},
        breadth_payload={"summary": "constructive"},
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
    )


def _primary_record_id(
    bundle: MarketPersistenceBundle,
) -> str:
    if bundle.ohlcv:
        return bundle.ohlcv[0].ohlcv_id
    if bundle.indicators:
        return bundle.indicators[0].indicator_id
    if bundle.context_snapshots:
        return bundle.context_snapshots[0].context_snapshot_id
    if bundle.technical_snapshots:
        return bundle.technical_snapshots[0].technical_snapshot_id
    if bundle.breadth_snapshots:
        return bundle.breadth_snapshots[0].breadth_snapshot_id
    if bundle.event_snapshots:
        return bundle.event_snapshots[0].event_snapshot_id
    return "empty-market-persistence-bundle"


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=timezone.utc)
