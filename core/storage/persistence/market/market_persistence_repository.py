from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from core.storage.persistence.market.market_persistence_models import (
    MarketBreadthSnapshotRecord,
    MarketContextSnapshotRecord,
    MarketEventSnapshotRecord,
    MarketIndicatorRecord,
    MarketOhlcvRecord,
    MarketPersistenceBundle,
    MarketPersistenceResult,
    TechnicalAnalysisSnapshotRecord,
)


class MarketPersistenceRepository(Protocol):
    """
    Async repository contract for durable curated market/technical records.

    OHLCV and indicator facts are upserted by natural market keys. Context,
    technical, and breadth snapshots are append-only records that preserve final
    curated inputs and outputs for audit, replay, and future RAG ingestion.
    """

    async def persist_market_bundle(
        self,
        bundle: MarketPersistenceBundle,
    ) -> MarketPersistenceResult: ...

    async def list_ohlcv(
        self,
        *,
        symbol: str,
        source: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MarketOhlcvRecord]: ...

    async def list_indicators(
        self,
        *,
        symbol: str,
        indicator_name: str | None = None,
        source: str | None = None,
        timeframe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MarketIndicatorRecord]: ...

    async def list_context_snapshots(
        self,
        *,
        universe: str | None = None,
        source: str | None = None,
        market_regime: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MarketContextSnapshotRecord]: ...

    async def list_technical_snapshots(
        self,
        *,
        symbol: str,
        source: str | None = None,
        technical_regime: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[TechnicalAnalysisSnapshotRecord]: ...

    async def list_breadth_snapshots(
        self,
        *,
        universe: str,
        source: str | None = None,
        breadth_regime: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MarketBreadthSnapshotRecord]: ...

    async def list_event_snapshots(
        self,
        *,
        symbol: str,
        source: str | None = None,
        regime_bias: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MarketEventSnapshotRecord]: ...
