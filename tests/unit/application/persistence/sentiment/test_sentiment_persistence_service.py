from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from datetime import timezone

import pytest

from application.persistence.sentiment import SentimentPersistenceService
from application.persistence.sentiment import SentimentSnapshotPersistenceFilters
from application.persistence.sentiment import SentimentSourcePersistenceFilters
from core.storage.persistence.sentiment import SentimentPersistenceBundle
from core.storage.persistence.sentiment import SentimentPersistenceResult
from core.storage.persistence.sentiment import SentimentSnapshotRecord
from core.storage.persistence.sentiment import SentimentSourceRecord


class FakeSentimentRepository:
    def __init__(
        self,
        *,
        snapshots: Sequence[SentimentSnapshotRecord] = (),
        sources: Sequence[SentimentSourceRecord] = (),
    ) -> None:
        self.bundle: SentimentPersistenceBundle | None = None
        self.snapshots = tuple(snapshots)
        self.sources = tuple(sources)
        self.snapshot_filters: dict[str, str | datetime | None] | None = None
        self.source_filters: dict[str, str | datetime | None] | None = None

    async def persist_sentiment_bundle(
        self,
        bundle: SentimentPersistenceBundle,
    ) -> SentimentPersistenceResult:
        self.bundle = bundle
        return SentimentPersistenceResult.succeeded(
            primary_record_id=_primary_record_id(bundle),
            records_persisted=(len(bundle.snapshots) + len(bundle.sources)),
        )

    async def list_snapshots(
        self,
        *,
        source: str | None = None,
        symbol: str | None = None,
        universe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[SentimentSnapshotRecord]:
        self.snapshot_filters = {
            "source": source,
            "symbol": symbol,
            "universe": universe,
            "start": start,
            "end": end,
        }
        return self.snapshots

    async def list_sources(
        self,
        *,
        sentiment_snapshot_id: str | None = None,
        source: str | None = None,
        source_type: str | None = None,
        symbol: str | None = None,
        universe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[SentimentSourceRecord]:
        self.source_filters = {
            "sentiment_snapshot_id": sentiment_snapshot_id,
            "source": source,
            "source_type": source_type,
            "symbol": symbol,
            "universe": universe,
            "start": start,
            "end": end,
        }
        return self.sources


@pytest.mark.asyncio
async def test_sentiment_persistence_service_persists_existing_bundle() -> None:
    repository = FakeSentimentRepository()
    service = SentimentPersistenceService(repository)
    bundle = _bundle()

    result = await service.persist_bundle(bundle)

    assert result.success is True
    assert result.records_persisted == 2
    assert repository.bundle == bundle


@pytest.mark.asyncio
async def test_sentiment_persistence_service_builds_typed_bundle() -> None:
    repository = FakeSentimentRepository()
    service = SentimentPersistenceService(repository)

    result = await service.persist_records(
        snapshots=(_snapshot(),),
        sources=(_source(),),
    )

    assert result.success is True
    assert repository.bundle is not None
    assert repository.bundle.snapshots[0].source == "morning_report"
    assert repository.bundle.snapshots[0].fusion_components == {
        "news": 0.4,
        "market": 0.6,
    }
    assert repository.bundle.sources[0].source == "reuters"
    assert repository.bundle.sources[0].source_reference == "article-group-1"


@pytest.mark.asyncio
async def test_sentiment_persistence_service_uses_typed_filters() -> None:
    repository = FakeSentimentRepository(
        snapshots=(_snapshot(),),
        sources=(_source(),),
    )
    service = SentimentPersistenceService(repository)
    start = _timestamp()
    end = datetime(2026, 5, 31, 15, 0, tzinfo=timezone.utc)

    snapshots = await service.list_snapshots(
        SentimentSnapshotPersistenceFilters(
            source=" morning_report ",
            symbol=" spy ",
            universe=" us_equities ",
            start=start,
            end=end,
        )
    )
    sources = await service.list_sources(
        SentimentSourcePersistenceFilters(
            sentiment_snapshot_id=" sentiment-snapshot-1 ",
            source=" reuters ",
            source_type=" news ",
            symbol=" qqq ",
            universe=" us_equities ",
            start=start,
            end=end,
        )
    )

    assert len(snapshots) == 1
    assert len(sources) == 1
    assert repository.snapshot_filters == {
        "source": "morning_report",
        "symbol": "SPY",
        "universe": "us_equities",
        "start": start,
        "end": end,
    }
    assert repository.source_filters == {
        "sentiment_snapshot_id": "sentiment-snapshot-1",
        "source": "reuters",
        "source_type": "news",
        "symbol": "QQQ",
        "universe": "us_equities",
        "start": start,
        "end": end,
    }


@pytest.mark.asyncio
async def test_sentiment_persistence_service_uses_default_filters() -> None:
    repository = FakeSentimentRepository(
        snapshots=(_snapshot(),),
        sources=(_source(),),
    )
    service = SentimentPersistenceService(repository)

    snapshots = await service.list_snapshots()
    sources = await service.list_sources()

    assert len(snapshots) == 1
    assert len(sources) == 1
    assert repository.snapshot_filters == {
        "source": None,
        "symbol": None,
        "universe": None,
        "start": None,
        "end": None,
    }
    assert repository.source_filters == {
        "sentiment_snapshot_id": None,
        "source": None,
        "source_type": None,
        "symbol": None,
        "universe": None,
        "start": None,
        "end": None,
    }


@pytest.mark.parametrize(
    "filters",
    [
        SentimentSnapshotPersistenceFilters,
        SentimentSourcePersistenceFilters,
    ],
)
def test_sentiment_time_window_filters_require_ordered_bounds(
    filters: type[
        SentimentSnapshotPersistenceFilters | SentimentSourcePersistenceFilters
    ],
) -> None:
    start = datetime(2026, 5, 31, 15, 0, tzinfo=timezone.utc)
    end = _timestamp()

    with pytest.raises(ValueError, match="start must be less than or equal to end"):
        filters(
            start=start,
            end=end,
        )


def _bundle() -> SentimentPersistenceBundle:
    return SentimentPersistenceBundle(
        snapshots=(_snapshot(),),
        sources=(_source(),),
    )


def _snapshot() -> SentimentSnapshotRecord:
    return SentimentSnapshotRecord(
        sentiment_snapshot_id="sentiment-snapshot-1",
        timestamp=_timestamp(),
        source="morning_report",
        symbol="spy",
        universe="us_equities",
        market_regime="risk_on",
        fear_greed_score=0.72,
        news_sentiment_score=0.4,
        market_sentiment_score=0.6,
        social_sentiment_score=0.1,
        composite_sentiment=0.5,
        confidence=0.86,
        fusion_components={"news": 0.4, "market": 0.6},
        providers_payload={"article_count": 25},
        sentiment_payload={"summary": "Constructive sentiment."},
        metadata={"prompt_version": "v1"},
    )


def _source() -> SentimentSourceRecord:
    return SentimentSourceRecord(
        sentiment_source_id="sentiment-source-1",
        sentiment_snapshot_id="sentiment-snapshot-1",
        timestamp=_timestamp(),
        source="reuters",
        source_type="news",
        symbol="spy",
        universe="us_equities",
        sentiment_score=0.35,
        confidence=0.8,
        weight=0.5,
        sample_size=14,
        source_reference="article-group-1",
        summary="News tone improved.",
        metadata={"curated": True},
    )


def _primary_record_id(
    bundle: SentimentPersistenceBundle,
) -> str:
    if bundle.snapshots:
        return bundle.snapshots[0].sentiment_snapshot_id
    if bundle.sources:
        return bundle.sources[0].sentiment_source_id
    return "empty-sentiment-persistence-bundle"


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=timezone.utc)
