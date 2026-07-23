from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from application.persistence.query_result_helpers import (
    build_common_query,
    build_list_result,
)
from core.storage.persistence.lineage import (
    clean_optional_identifier,
    require_non_empty_identifier,
)
from core.storage.persistence.market import (
    MarketBreadthSnapshotRecord,
    MarketContextSnapshotRecord,
    MarketEventSnapshotRecord,
    MarketIndicatorRecord,
    MarketOhlcvRecord,
    MarketPersistenceBundle,
    MarketPersistenceRepository,
    MarketPersistenceResult,
    TechnicalAnalysisSnapshotRecord,
)
from core.storage.persistence.query import PersistenceListResult


@dataclass(
    frozen=True,
    slots=True,
)
class MarketOhlcvPersistenceFilters:
    """
    Typed application-layer filters for curated OHLCV retrieval.
    """

    symbol: str
    source: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "symbol",
            _clean_symbol(
                self.symbol,
            ),
        )
        object.__setattr__(
            self,
            "source",
            clean_optional_identifier(
                self.source,
                "source",
            ),
        )
        _require_ordered_time_window(
            self.start,
            self.end,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class MarketIndicatorPersistenceFilters:
    """
    Typed application-layer filters for curated technical indicator retrieval.
    """

    symbol: str
    indicator_name: str | None = None
    source: str | None = None
    timeframe: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "symbol",
            _clean_symbol(
                self.symbol,
            ),
        )
        object.__setattr__(
            self,
            "indicator_name",
            clean_optional_identifier(
                self.indicator_name,
                "indicator_name",
            ),
        )
        object.__setattr__(
            self,
            "source",
            clean_optional_identifier(
                self.source,
                "source",
            ),
        )
        object.__setattr__(
            self,
            "timeframe",
            clean_optional_identifier(
                self.timeframe,
                "timeframe",
            ),
        )
        _require_ordered_time_window(
            self.start,
            self.end,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class MarketContextSnapshotPersistenceFilters:
    """
    Typed application-layer filters for market context snapshot retrieval.
    """

    universe: str | None = None
    source: str | None = None
    market_regime: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "universe",
            clean_optional_identifier(
                self.universe,
                "universe",
            ),
        )
        object.__setattr__(
            self,
            "source",
            clean_optional_identifier(
                self.source,
                "source",
            ),
        )
        object.__setattr__(
            self,
            "market_regime",
            clean_optional_identifier(
                self.market_regime,
                "market_regime",
            ),
        )
        _require_ordered_time_window(
            self.start,
            self.end,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class TechnicalAnalysisSnapshotPersistenceFilters:
    """
    Typed application-layer filters for technical analysis snapshot retrieval.
    """

    symbol: str
    source: str | None = None
    technical_regime: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "symbol",
            _clean_symbol(
                self.symbol,
            ),
        )
        object.__setattr__(
            self,
            "source",
            clean_optional_identifier(
                self.source,
                "source",
            ),
        )
        object.__setattr__(
            self,
            "technical_regime",
            clean_optional_identifier(
                self.technical_regime,
                "technical_regime",
            ),
        )
        _require_ordered_time_window(
            self.start,
            self.end,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class MarketBreadthSnapshotPersistenceFilters:
    """
    Typed application-layer filters for market breadth snapshot retrieval.
    """

    universe: str
    source: str | None = None
    breadth_regime: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "universe",
            require_non_empty_identifier(
                self.universe,
                "universe",
            ),
        )
        object.__setattr__(
            self,
            "source",
            clean_optional_identifier(
                self.source,
                "source",
            ),
        )
        object.__setattr__(
            self,
            "breadth_regime",
            clean_optional_identifier(
                self.breadth_regime,
                "breadth_regime",
            ),
        )
        _require_ordered_time_window(
            self.start,
            self.end,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class MarketEventSnapshotPersistenceFilters:
    """
    Typed application-layer filters for market event snapshot retrieval.
    """

    symbol: str
    source: str | None = None
    regime_bias: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "symbol",
            _clean_symbol(
                self.symbol,
            ),
        )
        object.__setattr__(
            self,
            "source",
            clean_optional_identifier(
                self.source,
                "source",
            ),
        )
        object.__setattr__(
            self,
            "regime_bias",
            clean_optional_identifier(
                self.regime_bias,
                "regime_bias",
            ),
        )
        _require_ordered_time_window(
            self.start,
            self.end,
        )


class MarketPersistenceService:
    """
    Application service for curated market and technical persistence.

    This service coordinates typed market persistence through the repository
    protocol only. It intentionally accepts curated typed records, not raw
    provider payloads, and does not auto-capture workflow node output.
    """

    def __init__(
        self,
        repository: MarketPersistenceRepository,
    ) -> None:
        self._repository = repository

    async def persist_bundle(
        self,
        bundle: MarketPersistenceBundle,
    ) -> MarketPersistenceResult:
        return await self._repository.persist_market_bundle(
            bundle,
        )

    async def persist_records(
        self,
        *,
        ohlcv: Sequence[MarketOhlcvRecord] = (),
        indicators: Sequence[MarketIndicatorRecord] = (),
        context_snapshots: Sequence[MarketContextSnapshotRecord] = (),
        technical_snapshots: Sequence[TechnicalAnalysisSnapshotRecord] = (),
        breadth_snapshots: Sequence[MarketBreadthSnapshotRecord] = (),
        event_snapshots: Sequence[MarketEventSnapshotRecord] = (),
    ) -> MarketPersistenceResult:
        return await self.persist_bundle(
            MarketPersistenceBundle(
                ohlcv=tuple(
                    ohlcv,
                ),
                indicators=tuple(
                    indicators,
                ),
                context_snapshots=tuple(
                    context_snapshots,
                ),
                technical_snapshots=tuple(
                    technical_snapshots,
                ),
                breadth_snapshots=tuple(
                    breadth_snapshots,
                ),
                event_snapshots=tuple(
                    event_snapshots,
                ),
            )
        )

    async def list_ohlcv(
        self,
        filters: MarketOhlcvPersistenceFilters,
    ) -> Sequence[MarketOhlcvRecord]:
        result = await self.list_ohlcv_result(
            filters,
        )
        return result.records

    async def list_ohlcv_result(
        self,
        filters: MarketOhlcvPersistenceFilters,
    ) -> PersistenceListResult[MarketOhlcvRecord]:
        records = await self._repository.list_ohlcv(
            symbol=filters.symbol,
            source=filters.source,
            start=filters.start,
            end=filters.end,
        )
        query = build_common_query(
            record_type="market_ohlcv",
            source=filters.source,
            symbol=filters.symbol,
            start=filters.start,
            end=filters.end,
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_indicators(
        self,
        filters: MarketIndicatorPersistenceFilters,
    ) -> Sequence[MarketIndicatorRecord]:
        result = await self.list_indicators_result(
            filters,
        )
        return result.records

    async def list_indicators_result(
        self,
        filters: MarketIndicatorPersistenceFilters,
    ) -> PersistenceListResult[MarketIndicatorRecord]:
        records = await self._repository.list_indicators(
            symbol=filters.symbol,
            indicator_name=filters.indicator_name,
            source=filters.source,
            timeframe=filters.timeframe,
            start=filters.start,
            end=filters.end,
        )
        query = build_common_query(
            record_type="market_indicator",
            source=filters.source,
            symbol=filters.symbol,
            start=filters.start,
            end=filters.end,
            metadata={
                "indicator_name": filters.indicator_name,
                "timeframe": filters.timeframe,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_context_snapshots(
        self,
        filters: MarketContextSnapshotPersistenceFilters | None = None,
    ) -> Sequence[MarketContextSnapshotRecord]:
        result = await self.list_context_snapshots_result(
            filters,
        )
        return result.records

    async def list_context_snapshots_result(
        self,
        filters: MarketContextSnapshotPersistenceFilters | None = None,
    ) -> PersistenceListResult[MarketContextSnapshotRecord]:
        active_filters = filters or MarketContextSnapshotPersistenceFilters()
        records = await self._repository.list_context_snapshots(
            universe=active_filters.universe,
            source=active_filters.source,
            market_regime=active_filters.market_regime,
            start=active_filters.start,
            end=active_filters.end,
        )
        query = build_common_query(
            record_type="market_context_snapshot",
            source=active_filters.source,
            start=active_filters.start,
            end=active_filters.end,
            metadata={
                "universe": active_filters.universe,
                "market_regime": active_filters.market_regime,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_technical_snapshots(
        self,
        filters: TechnicalAnalysisSnapshotPersistenceFilters,
    ) -> Sequence[TechnicalAnalysisSnapshotRecord]:
        result = await self.list_technical_snapshots_result(
            filters,
        )
        return result.records

    async def list_technical_snapshots_result(
        self,
        filters: TechnicalAnalysisSnapshotPersistenceFilters,
    ) -> PersistenceListResult[TechnicalAnalysisSnapshotRecord]:
        records = await self._repository.list_technical_snapshots(
            symbol=filters.symbol,
            source=filters.source,
            technical_regime=filters.technical_regime,
            start=filters.start,
            end=filters.end,
        )
        query = build_common_query(
            record_type="technical_analysis_snapshot",
            source=filters.source,
            symbol=filters.symbol,
            start=filters.start,
            end=filters.end,
            metadata={
                "technical_regime": filters.technical_regime,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_breadth_snapshots(
        self,
        filters: MarketBreadthSnapshotPersistenceFilters,
    ) -> Sequence[MarketBreadthSnapshotRecord]:
        result = await self.list_breadth_snapshots_result(
            filters,
        )
        return result.records

    async def list_breadth_snapshots_result(
        self,
        filters: MarketBreadthSnapshotPersistenceFilters,
    ) -> PersistenceListResult[MarketBreadthSnapshotRecord]:
        records = await self._repository.list_breadth_snapshots(
            universe=filters.universe,
            source=filters.source,
            breadth_regime=filters.breadth_regime,
            start=filters.start,
            end=filters.end,
        )
        query = build_common_query(
            record_type="market_breadth_snapshot",
            source=filters.source,
            start=filters.start,
            end=filters.end,
            metadata={
                "universe": filters.universe,
                "breadth_regime": filters.breadth_regime,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_event_snapshots(
        self,
        filters: MarketEventSnapshotPersistenceFilters,
    ) -> Sequence[MarketEventSnapshotRecord]:
        result = await self.list_event_snapshots_result(
            filters,
        )
        return result.records

    async def list_event_snapshots_result(
        self,
        filters: MarketEventSnapshotPersistenceFilters,
    ) -> PersistenceListResult[MarketEventSnapshotRecord]:
        records = await self._repository.list_event_snapshots(
            symbol=filters.symbol,
            source=filters.source,
            regime_bias=filters.regime_bias,
            start=filters.start,
            end=filters.end,
        )
        query = build_common_query(
            record_type="market_event_snapshot",
            source=filters.source,
            symbol=filters.symbol,
            start=filters.start,
            end=filters.end,
            metadata={
                "regime_bias": filters.regime_bias,
            },
        )
        return build_list_result(
            records,
            query=query,
        )


def _clean_symbol(
    symbol: str,
) -> str:
    return require_non_empty_identifier(
        symbol,
        "symbol",
    ).upper()


def _require_ordered_time_window(
    start: datetime | None,
    end: datetime | None,
) -> None:
    if start is not None and end is not None and start > end:
        raise ValueError("start must be less than or equal to end.")
