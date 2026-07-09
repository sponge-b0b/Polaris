from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.sentiment import SentimentPersistenceBundle
from core.storage.persistence.sentiment import SentimentPersistenceRepository
from core.storage.persistence.sentiment import SentimentPersistenceResult
from core.storage.persistence.sentiment import SentimentSnapshotRecord
from core.storage.persistence.sentiment import SentimentSourceRecord
from core.storage.persistence.query import PersistenceListResult

from application.persistence.query_result_helpers import build_common_query
from application.persistence.query_result_helpers import build_list_result


@dataclass(
    frozen=True,
    slots=True,
)
class SentimentSnapshotPersistenceFilters:
    """
    Typed application-layer filters for curated sentiment snapshot retrieval.
    """

    source: str | None = None
    symbol: str | None = None
    universe: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
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
            "symbol",
            _clean_optional_symbol(
                self.symbol,
            ),
        )
        object.__setattr__(
            self,
            "universe",
            clean_optional_identifier(
                self.universe,
                "universe",
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
class SentimentSourcePersistenceFilters:
    """
    Typed application-layer filters for curated sentiment source retrieval.
    """

    sentiment_snapshot_id: str | None = None
    source: str | None = None
    source_type: str | None = None
    symbol: str | None = None
    universe: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "sentiment_snapshot_id",
            clean_optional_identifier(
                self.sentiment_snapshot_id,
                "sentiment_snapshot_id",
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
            "source_type",
            clean_optional_identifier(
                self.source_type,
                "source_type",
            ),
        )
        object.__setattr__(
            self,
            "symbol",
            _clean_optional_symbol(
                self.symbol,
            ),
        )
        object.__setattr__(
            self,
            "universe",
            clean_optional_identifier(
                self.universe,
                "universe",
            ),
        )
        _require_ordered_time_window(
            self.start,
            self.end,
        )


class SentimentPersistenceService:
    """
    Application service for curated sentiment persistence.

    This service coordinates typed sentiment persistence through the repository
    protocol only. It intentionally accepts curated typed records, not raw
    provider payloads, and does not auto-capture workflow node output.
    """

    def __init__(
        self,
        repository: SentimentPersistenceRepository,
    ) -> None:
        self._repository = repository

    async def persist_bundle(
        self,
        bundle: SentimentPersistenceBundle,
    ) -> SentimentPersistenceResult:
        return await self._repository.persist_sentiment_bundle(
            bundle,
        )

    async def persist_records(
        self,
        *,
        snapshots: Sequence[SentimentSnapshotRecord] = (),
        sources: Sequence[SentimentSourceRecord] = (),
    ) -> SentimentPersistenceResult:
        return await self.persist_bundle(
            SentimentPersistenceBundle(
                snapshots=tuple(
                    snapshots,
                ),
                sources=tuple(
                    sources,
                ),
            )
        )

    async def list_snapshots(
        self,
        filters: SentimentSnapshotPersistenceFilters | None = None,
    ) -> Sequence[SentimentSnapshotRecord]:
        result = await self.list_snapshots_result(
            filters,
        )
        return result.records

    async def list_snapshots_result(
        self,
        filters: SentimentSnapshotPersistenceFilters | None = None,
    ) -> PersistenceListResult[SentimentSnapshotRecord]:
        active_filters = filters or SentimentSnapshotPersistenceFilters()
        records = await self._repository.list_snapshots(
            source=active_filters.source,
            symbol=active_filters.symbol,
            universe=active_filters.universe,
            start=active_filters.start,
            end=active_filters.end,
        )
        query = build_common_query(
            record_type="sentiment_snapshot",
            source=active_filters.source,
            symbol=active_filters.symbol,
            start=active_filters.start,
            end=active_filters.end,
            metadata={
                "universe": active_filters.universe,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_sources(
        self,
        filters: SentimentSourcePersistenceFilters | None = None,
    ) -> Sequence[SentimentSourceRecord]:
        result = await self.list_sources_result(
            filters,
        )
        return result.records

    async def list_sources_result(
        self,
        filters: SentimentSourcePersistenceFilters | None = None,
    ) -> PersistenceListResult[SentimentSourceRecord]:
        active_filters = filters or SentimentSourcePersistenceFilters()
        records = await self._repository.list_sources(
            sentiment_snapshot_id=active_filters.sentiment_snapshot_id,
            source=active_filters.source,
            source_type=active_filters.source_type,
            symbol=active_filters.symbol,
            universe=active_filters.universe,
            start=active_filters.start,
            end=active_filters.end,
        )
        query = build_common_query(
            record_type="sentiment_source",
            source=active_filters.source,
            symbol=active_filters.symbol,
            start=active_filters.start,
            end=active_filters.end,
            metadata={
                "sentiment_snapshot_id": active_filters.sentiment_snapshot_id,
                "source_type": active_filters.source_type,
                "universe": active_filters.universe,
            },
        )
        return build_list_result(
            records,
            query=query,
        )


def _clean_optional_symbol(
    symbol: str | None,
) -> str | None:
    clean_symbol = clean_optional_identifier(
        symbol,
        "symbol",
    )
    if clean_symbol is None:
        return None

    return clean_symbol.upper()


def _require_ordered_time_window(
    start: datetime | None,
    end: datetime | None,
) -> None:
    if start is not None and end is not None and start > end:
        raise ValueError("start must be less than or equal to end.")
