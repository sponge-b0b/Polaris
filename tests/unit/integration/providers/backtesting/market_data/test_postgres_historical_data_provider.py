from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any

import pytest

from integration.providers.backtesting.market_data.postgres_historical_data_provider import (
    MissingHistoricalMarketDataError,
)
from integration.providers.backtesting.market_data.postgres_historical_data_provider import (
    PostgresHistoricalDataProvider,
)
from integration.providers.backtesting.market_data.postgres_historical_data_provider import (
    PostgresHistoricalDataProviderConfig,
)
from core.storage.persistence.market import MarketBreadthSnapshotRecord
from core.storage.persistence.market import MarketContextSnapshotRecord
from core.storage.persistence.market import MarketEventSnapshotRecord
from core.storage.persistence.market import MarketIndicatorRecord
from core.storage.persistence.market import MarketOhlcvRecord
from core.storage.persistence.market import MarketPersistenceBundle
from core.storage.persistence.market import MarketPersistenceResult
from core.storage.persistence.market import TechnicalAnalysisSnapshotRecord


class FakeMarketPersistenceRepository:
    def __init__(
        self,
        *,
        ohlcv: Sequence[MarketOhlcvRecord] = (),
        context_snapshots: Sequence[MarketContextSnapshotRecord] = (),
    ) -> None:
        self.ohlcv = tuple(ohlcv)
        self.context_snapshots = tuple(context_snapshots)
        self.ohlcv_requests: list[dict[str, Any]] = []
        self.context_requests: list[dict[str, Any]] = []

    async def persist_market_bundle(
        self,
        bundle: MarketPersistenceBundle,
    ) -> MarketPersistenceResult:
        return MarketPersistenceResult.succeeded(
            primary_record_id="unused",
            records_persisted=0,
        )

    async def list_ohlcv(
        self,
        *,
        symbol: str,
        source: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MarketOhlcvRecord]:
        self.ohlcv_requests.append(
            {
                "symbol": symbol,
                "source": source,
                "start": start,
                "end": end,
            }
        )
        return tuple(record for record in self.ohlcv if record.symbol == symbol.upper())

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
        return ()

    async def list_context_snapshots(
        self,
        *,
        universe: str | None = None,
        source: str | None = None,
        market_regime: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MarketContextSnapshotRecord]:
        self.context_requests.append(
            {
                "universe": universe,
                "source": source,
                "market_regime": market_regime,
                "start": start,
                "end": end,
            }
        )
        return tuple(
            record for record in self.context_snapshots if record.universe == universe
        )

    async def list_technical_snapshots(
        self,
        *,
        symbol: str,
        source: str | None = None,
        technical_regime: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[TechnicalAnalysisSnapshotRecord]:
        return ()

    async def list_breadth_snapshots(
        self,
        *,
        universe: str,
        source: str | None = None,
        breadth_regime: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MarketBreadthSnapshotRecord]:
        return ()

    async def list_event_snapshots(
        self,
        *,
        symbol: str,
        source: str | None = None,
        regime_bias: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MarketEventSnapshotRecord]:
        return ()


class FakeRepositoryContext:
    def __init__(
        self,
        repository: FakeMarketPersistenceRepository,
    ) -> None:
        self._repository = repository

    async def __aenter__(
        self,
    ) -> FakeMarketPersistenceRepository:
        return self._repository

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        return None


def _provider(
    repository: FakeMarketPersistenceRepository,
    *,
    missing_data_policy: str = "fail_fast",
) -> PostgresHistoricalDataProvider:
    return PostgresHistoricalDataProvider(
        repository_factory=lambda: FakeRepositoryContext(repository),
        config=PostgresHistoricalDataProviderConfig(
            source="curated",
            missing_data_policy=missing_data_policy,
        ),
    )


def _ohlcv_record(
    index: int,
    *,
    symbol: str = "SPY",
) -> MarketOhlcvRecord:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index)
    return MarketOhlcvRecord(
        ohlcv_id=f"ohlcv-{symbol}-{index}",
        symbol=symbol,
        timestamp=timestamp,
        source="curated",
        open_price=100.0 + index,
        high_price=101.0 + index,
        low_price=99.0 + index,
        close_price=100.5 + index,
        volume=1_000_000.0 + index,
    )


def _context_record(
    index: int,
) -> MarketContextSnapshotRecord:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index)
    return MarketContextSnapshotRecord(
        context_snapshot_id=f"context-{index}",
        timestamp=timestamp,
        source="curated",
        universe="sp500",
        market_cap_index=5000.0 + index,
        advances_count=300 + index,
        declines_count=190 - index,
        unchanged_count=10,
        active_count=500,
        pct_above_50dma=0.6,
        pct_above_200dma=0.55,
        new_highs=40 + index,
        new_lows=15,
        net_breadth=110 + index,
        breadth_percent=0.62,
        ad_line=1000.0 + index,
        ad_ratio=1.55,
        top_50_constituents_payload={"symbols": ["AAPL", "MSFT"]},
        market_caps_payload={"AAPL": 3_000_000_000_000.0, "MSFT": 2_500_000_000_000.0},
    )


@pytest.mark.asyncio
async def test_get_symbol_data_reads_curated_ohlcv_and_returns_tail_frame() -> None:
    repository = FakeMarketPersistenceRepository(
        ohlcv=tuple(_ohlcv_record(index) for index in range(4)),
    )
    provider = _provider(repository)

    frame = await provider.get_symbol_data(
        symbol="SPY",
        days=2,
    )

    assert list(frame.columns) == ["open", "high", "low", "close", "volume"]
    assert len(frame) == 2
    assert frame.iloc[0]["close"] == 102.5
    assert repository.ohlcv_requests == [
        {
            "symbol": "SPY",
            "source": "curated",
            "start": None,
            "end": None,
        }
    ]


@pytest.mark.asyncio
async def test_get_symbol_data_fails_fast_when_curated_history_is_incomplete() -> None:
    repository = FakeMarketPersistenceRepository(
        ohlcv=(_ohlcv_record(0),),
    )
    provider = _provider(repository)

    with pytest.raises(
        MissingHistoricalMarketDataError,
        match="requested 3 OHLCV rows, found 1",
    ):
        await provider.get_symbol_data(
            symbol="SPY",
            days=3,
        )


@pytest.mark.asyncio
async def test_get_symbol_data_can_forward_fill_when_explicitly_configured() -> None:
    repository = FakeMarketPersistenceRepository(
        ohlcv=(_ohlcv_record(0), _ohlcv_record(3)),
    )
    provider = _provider(
        repository,
        missing_data_policy="forward_fill",
    )

    frame = await provider.get_symbol_data(
        symbol="SPY",
        days=4,
    )

    assert len(frame) == 4
    assert frame.iloc[1]["close"] == 100.5
    assert frame.iloc[-1]["close"] == 103.5


@pytest.mark.asyncio
async def test_get_sp500_data_reads_context_snapshots_for_breadth_payload() -> None:
    repository = FakeMarketPersistenceRepository(
        context_snapshots=(_context_record(0), _context_record(1)),
    )
    provider = _provider(repository)

    sp500_data = await provider.get_sp500_data(
        days=2,
    )

    assert list(sp500_data.analytics.columns) == [
        "market_cap_index",
        "advances_count",
        "declines_count",
        "unchanged_count",
        "active_count",
        "pct_above_50dma",
        "pct_above_200dma",
        "new_highs",
        "new_lows",
        "net_breadth",
        "breadth_percent",
        "ad_line",
        "ad_ratio",
    ]
    assert sp500_data.analytics.iloc[-1]["market_cap_index"] == 5001.0
    assert sp500_data.top_50_constituents == ["AAPL", "MSFT"]
    assert sp500_data.market_caps["AAPL"] == 3_000_000_000_000.0
    assert repository.context_requests == [
        {
            "universe": "sp500",
            "source": "curated",
            "market_regime": None,
            "start": None,
            "end": None,
        }
    ]
