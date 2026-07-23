from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from application.persistence.audit.audit_emission import PersistenceAuditEmission
from application.persistence.news import (
    NewsAnalysisSnapshotPersistenceFilters,
    NewsArticlePersistenceFilters,
    NewsPersistenceService,
)
from core.storage.persistence.audit import PersistenceAuditEventResult
from core.storage.persistence.news import (
    NewsAnalysisSnapshotRecord,
    NewsArticleRecord,
    NewsPersistenceBundle,
    NewsPersistenceResult,
)


class FakeNewsRepository:
    def __init__(
        self,
        *,
        articles: Sequence[NewsArticleRecord] = (),
        analysis_snapshots: Sequence[NewsAnalysisSnapshotRecord] = (),
    ) -> None:
        self.bundle: NewsPersistenceBundle | None = None
        self.articles = tuple(articles)
        self.analysis_snapshots = tuple(analysis_snapshots)
        self.article_filters: dict[str, str | datetime | None] | None = None
        self.analysis_filters: dict[str, str | datetime | None] | None = None

    async def persist_news_bundle(
        self,
        bundle: NewsPersistenceBundle,
    ) -> NewsPersistenceResult:
        self.bundle = bundle
        return NewsPersistenceResult.succeeded(
            primary_record_id=_primary_record_id(bundle),
            records_persisted=(len(bundle.articles) + len(bundle.analysis_snapshots)),
        )

    async def list_articles(
        self,
        *,
        source: str | None = None,
        symbol: str | None = None,
        theme: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[NewsArticleRecord]:
        self.article_filters = {
            "source": source,
            "symbol": symbol,
            "theme": theme,
            "start": start,
            "end": end,
        }
        return self.articles

    async def list_analysis_snapshots(
        self,
        *,
        source: str | None = None,
        symbol: str | None = None,
        theme: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[NewsAnalysisSnapshotRecord]:
        self.analysis_filters = {
            "source": source,
            "symbol": symbol,
            "theme": theme,
            "start": start,
            "end": end,
        }
        return self.analysis_snapshots


class RecordingAuditEmitter:
    def __init__(
        self,
        *,
        fail: bool = False,
    ) -> None:
        self.fail = fail
        self.emissions: list[PersistenceAuditEmission] = []

    async def emit(
        self,
        emission: PersistenceAuditEmission,
    ) -> PersistenceAuditEventResult | None:
        if self.fail:
            raise RuntimeError("audit failure")
        self.emissions.append(
            emission,
        )
        return None

    async def emit_many(
        self,
        emissions: Sequence[PersistenceAuditEmission],
    ) -> Sequence[PersistenceAuditEventResult | None]:
        if self.fail:
            raise RuntimeError("audit failure")
        self.emissions.extend(
            emissions,
        )
        return tuple(None for _ in emissions)


@pytest.mark.asyncio
async def test_news_persistence_service_persists_existing_bundle() -> None:
    repository = FakeNewsRepository()
    service = NewsPersistenceService(repository)
    bundle = _bundle()

    result = await service.persist_bundle(bundle)

    assert result.success is True
    assert result.records_persisted == 2
    assert repository.bundle == bundle


@pytest.mark.asyncio
async def test_news_persistence_service_emits_non_fatal_audit_events() -> None:
    repository = FakeNewsRepository()
    audit_emitter = RecordingAuditEmitter()
    service = NewsPersistenceService(
        repository,
        audit_emitter,
    )

    result = await service.persist_bundle(
        _bundle(),
    )

    assert result.success is True
    assert [emission.entity_type for emission in audit_emitter.emissions] == [
        "news_article",
        "news_analysis_snapshot",
    ]
    assert [emission.entity_id for emission in audit_emitter.emissions] == [
        "article-1",
        "news-analysis-1",
    ]
    assert all(emission.action == "persist" for emission in audit_emitter.emissions)
    assert audit_emitter.emissions[0].metadata["source"] == "reuters"
    assert audit_emitter.emissions[1].metadata["source"] == "morning_report"


@pytest.mark.asyncio
async def test_news_persistence_service_does_not_fail_primary_write_when_audit_fails() -> (  # noqa: E501
    None
):
    repository = FakeNewsRepository()
    service = NewsPersistenceService(
        repository,
        RecordingAuditEmitter(
            fail=True,
        ),
    )

    result = await service.persist_bundle(
        _bundle(),
    )

    assert result.success is True
    assert result.records_persisted == 2
    assert repository.bundle == _bundle()


@pytest.mark.asyncio
async def test_news_persistence_service_builds_typed_bundle() -> None:
    repository = FakeNewsRepository()
    service = NewsPersistenceService(repository)

    result = await service.persist_records(
        articles=(_article(),),
        analysis_snapshots=(_analysis_snapshot(),),
    )

    assert result.success is True
    assert repository.bundle is not None
    assert repository.bundle.articles[0].source == "reuters"
    assert repository.bundle.analysis_snapshots[0].source == "morning_report"
    assert repository.bundle.analysis_snapshots[0].full_llm_response == _full_response()


@pytest.mark.asyncio
async def test_news_persistence_service_uses_typed_filters() -> None:
    repository = FakeNewsRepository(
        articles=(_article(),),
        analysis_snapshots=(_analysis_snapshot(),),
    )
    service = NewsPersistenceService(repository)
    start = _timestamp()
    end = datetime(2026, 5, 31, 15, 0, tzinfo=UTC)

    articles = await service.list_articles(
        NewsArticlePersistenceFilters(
            source=" reuters ",
            symbol=" spy ",
            theme=" macro ",
            start=start,
            end=end,
        )
    )
    analyses = await service.list_analysis_snapshots(
        NewsAnalysisSnapshotPersistenceFilters(
            source=" morning_report ",
            symbol=" qqq ",
            theme=" rates ",
            start=start,
            end=end,
        )
    )

    assert len(articles) == 1
    assert len(analyses) == 1
    assert repository.article_filters == {
        "source": "reuters",
        "symbol": "SPY",
        "theme": "macro",
        "start": start,
        "end": end,
    }
    assert repository.analysis_filters == {
        "source": "morning_report",
        "symbol": "QQQ",
        "theme": "rates",
        "start": start,
        "end": end,
    }


@pytest.mark.asyncio
async def test_news_persistence_service_returns_query_result_envelopes() -> None:
    repository = FakeNewsRepository(
        articles=(_article(),),
        analysis_snapshots=(_analysis_snapshot(),),
    )
    service = NewsPersistenceService(repository)
    start = _timestamp()
    end = datetime(2026, 5, 31, 15, 0, tzinfo=UTC)

    article_result = await service.list_articles_result(
        NewsArticlePersistenceFilters(
            source=" reuters ",
            symbol=" spy ",
            theme=" macro ",
            start=start,
            end=end,
        )
    )
    analysis_result = await service.list_analysis_snapshots_result(
        NewsAnalysisSnapshotPersistenceFilters(
            source=" morning_report ",
            symbol=" qqq ",
            theme=" rates ",
            start=start,
            end=end,
        )
    )

    assert article_result.records == (_article(),)
    assert article_result.returned_count == 1
    assert article_result.total_count == 1
    assert article_result.has_more is False
    assert article_result.query is not None
    assert article_result.query.symbols.symbol == "SPY"
    assert article_result.query.time_range.start == start
    assert article_result.query.time_range.end == end
    assert article_result.query.metadata == {
        "record_type": "news_article",
        "source": "reuters",
        "theme": "macro",
    }
    assert article_result.page_metadata()["query"] == article_result.query.as_dict()
    assert analysis_result.records == (_analysis_snapshot(),)
    assert analysis_result.query is not None
    assert analysis_result.query.symbols.symbol == "QQQ"
    assert analysis_result.query.metadata == {
        "record_type": "news_analysis_snapshot",
        "source": "morning_report",
        "theme": "rates",
    }
    assert repository.article_filters == {
        "source": "reuters",
        "symbol": "SPY",
        "theme": "macro",
        "start": start,
        "end": end,
    }
    assert repository.analysis_filters == {
        "source": "morning_report",
        "symbol": "QQQ",
        "theme": "rates",
        "start": start,
        "end": end,
    }


@pytest.mark.asyncio
async def test_news_persistence_service_uses_default_filters() -> None:
    repository = FakeNewsRepository(
        articles=(_article(),),
        analysis_snapshots=(_analysis_snapshot(),),
    )
    service = NewsPersistenceService(repository)

    articles = await service.list_articles()
    analyses = await service.list_analysis_snapshots()

    assert len(articles) == 1
    assert len(analyses) == 1
    assert repository.article_filters == {
        "source": None,
        "symbol": None,
        "theme": None,
        "start": None,
        "end": None,
    }
    assert repository.analysis_filters == {
        "source": None,
        "symbol": None,
        "theme": None,
        "start": None,
        "end": None,
    }


@pytest.mark.parametrize(
    "filters",
    [
        NewsArticlePersistenceFilters,
        NewsAnalysisSnapshotPersistenceFilters,
    ],
)
def test_news_time_window_filters_require_ordered_bounds(
    filters: type[
        NewsArticlePersistenceFilters | NewsAnalysisSnapshotPersistenceFilters
    ],
) -> None:
    start = datetime(2026, 5, 31, 15, 0, tzinfo=UTC)
    end = _timestamp()

    with pytest.raises(ValueError, match="start must be less than or equal to end"):
        filters(
            start=start,
            end=end,
        )


def _bundle() -> NewsPersistenceBundle:
    return NewsPersistenceBundle(
        articles=(_article(),),
        analysis_snapshots=(_analysis_snapshot(),),
    )


def _article() -> NewsArticleRecord:
    return NewsArticleRecord(
        article_id="article-1",
        source="reuters",
        external_id="article-123",
        title="Fed signals patience",
        published_timestamp=_timestamp(),
        url="https://example.com/fed-signals-patience",
        summary="Policy makers emphasized incoming data.",
        symbols=("SPY", "QQQ"),
        themes=("macro", "fed_policy"),
        importance_score=0.8,
        sentiment_score=0.25,
        metadata={"publisher": "Reuters"},
    )


def _analysis_snapshot() -> NewsAnalysisSnapshotRecord:
    return NewsAnalysisSnapshotRecord(
        analysis_snapshot_id="news-analysis-1",
        timestamp=_timestamp(),
        source="morning_report",
        article_ids=("article-1",),
        symbols=("SPY", "QQQ"),
        themes=("macro", "rates"),
        importance_score=0.85,
        sentiment_score=-0.2,
        impact_score=0.4,
        confidence=0.9,
        llm_summary="Markets are focused on policy path.",
        full_llm_response=_full_response(),
        analysis_model="gpt-test",
        inputs={"article_count": 1},
        outputs={"summary": "Policy uncertainty dominates."},
        metadata={"prompt_version": "v1"},
    )


def _full_response() -> str:
    return "\n".join(
        f"Paragraph {index}: full response content is retained." for index in range(120)
    )


def _primary_record_id(
    bundle: NewsPersistenceBundle,
) -> str:
    if bundle.articles:
        return bundle.articles[0].article_id
    if bundle.analysis_snapshots:
        return bundle.analysis_snapshots[0].analysis_snapshot_id
    return "empty-news-persistence-bundle"


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=UTC)
