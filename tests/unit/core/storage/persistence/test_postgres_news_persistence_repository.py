from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.news import NewsAnalysisSnapshotModel
from core.database.models.news import NewsArticleModel
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.news import NewsAnalysisSnapshotRecord
from core.storage.persistence.news import NewsArticleRecord
from core.storage.persistence.news import NewsPersistenceBundle
from core.storage.persistence.repositories.postgres_news_persistence_repository import (
    PostgresNewsPersistenceRepository,
)
from core.storage.persistence.serializers.news_persistence_serializer import (
    NewsPersistenceSerializer,
)


class FakeScalarResult:
    def __init__(self, rows: Sequence[object]) -> None:
        self._rows = list(rows)

    def all(self) -> list[object]:
        return self._rows


class FakeExecuteResult:
    def __init__(self, rows: Sequence[object] | None = None) -> None:
        self._rows = list(rows or [])

    def scalars(self) -> FakeScalarResult:
        return FakeScalarResult(self._rows)


class FakeAsyncSession:
    def __init__(
        self,
        result: FakeExecuteResult | None = None,
        error: SQLAlchemyError | None = None,
    ) -> None:
        self.result = result or FakeExecuteResult()
        self.error = error
        self.executed: list[Any] = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, statement: Any) -> FakeExecuteResult:
        self.executed.append(statement)
        if self.error is not None:
            raise self.error
        return self.result

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_persist_news_bundle_upserts_articles_and_inserts_snapshots() -> None:
    session = FakeAsyncSession()
    repository = PostgresNewsPersistenceRepository(
        cast(AsyncSession, session),
    )

    result = await repository.persist_news_bundle(_bundle())

    compiled = [
        str(
            statement.compile(
                dialect=postgresql.dialect(),
            )
        )
        for statement in session.executed
    ]

    assert result.success is True
    assert result.primary_record_id == "article-1"
    assert result.records_persisted == 3
    assert session.commits == 1
    assert len(session.executed) == 3
    assert "news_articles" in compiled[0]
    assert "ON CONFLICT" in compiled[0]
    assert "source, external_id" in compiled[0]
    assert "news_articles" in compiled[1]
    assert "ON CONFLICT" in compiled[1]
    assert "source, url" in compiled[1]
    assert "news_analysis_snapshots" in compiled[2]
    assert "ON CONFLICT" not in compiled[2]


@pytest.mark.asyncio
async def test_news_idempotency_review_dedupes_articles_by_source_identity() -> None:
    session = FakeAsyncSession()
    repository = PostgresNewsPersistenceRepository(
        cast(AsyncSession, session),
    )

    result = await repository.persist_news_bundle(_bundle())

    compiled = [
        str(
            statement.compile(
                dialect=postgresql.dialect(),
            )
        )
        for statement in session.executed
    ]

    assert result.success is True
    assert len(compiled) == 3
    assert "news_articles" in compiled[0]
    assert "ON CONFLICT (source, external_id)" in compiled[0]
    assert "DO UPDATE" in compiled[0]
    assert "news_articles" in compiled[1]
    assert "ON CONFLICT (source, url)" in compiled[1]
    assert "DO UPDATE" in compiled[1]
    assert "news_analysis_snapshots" in compiled[2]
    assert "ON CONFLICT" not in compiled[2]
    assert all("DELETE" not in statement.upper() for statement in compiled)


@pytest.mark.asyncio
async def test_persist_news_bundle_rolls_back_on_sqlalchemy_error() -> None:
    session = FakeAsyncSession(error=SQLAlchemyError("database unavailable"))
    repository = PostgresNewsPersistenceRepository(
        cast(AsyncSession, session),
    )

    result = await repository.persist_news_bundle(_bundle())

    assert result.success is False
    assert result.error is not None
    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_list_news_articles_returns_typed_records() -> None:
    article_model = NewsArticleModel(
        **NewsPersistenceSerializer.article_values(_article())
    )

    articles = await PostgresNewsPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([article_model])))
    ).list_articles(
        source="reuters",
        symbol="spy",
        theme="macro",
        start=_timestamp(),
        end=_timestamp(),
    )

    assert articles[0].article_id == "article-1"
    assert articles[0].source == "reuters"
    assert articles[0].symbols == ("SPY", "QQQ")
    assert articles[0].headline_score == 0.7
    assert articles[0].relevance_score == 0.9
    assert articles[0].normalized_article_payload == {"id": "article-1"}
    assert articles[0].raw_payload == {"vendor_id": "article-123"}
    assert articles[0].metadata == {"publisher": "Reuters"}


@pytest.mark.asyncio
async def test_list_news_analysis_snapshots_returns_typed_records() -> None:
    snapshot_model = NewsAnalysisSnapshotModel(
        **NewsPersistenceSerializer.analysis_snapshot_values(_analysis_snapshot())
    )

    snapshots = await PostgresNewsPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([snapshot_model])))
    ).list_analysis_snapshots(
        source="morning_report",
        symbol="spy",
        theme="macro",
        start=_timestamp(),
        end=_timestamp(),
    )

    assert snapshots[0].analysis_snapshot_id == "news-analysis-1"
    assert snapshots[0].article_ids == ("article-1", "article-2")
    assert snapshots[0].outputs == {"summary": "Policy uncertainty dominates."}
    assert snapshots[0].full_llm_response == _analysis_snapshot().full_llm_response


def _bundle() -> NewsPersistenceBundle:
    return NewsPersistenceBundle(
        articles=(
            _article(),
            _url_only_article(),
        ),
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
        headline_score=0.7,
        relevance_score=0.9,
        sentiment_score=0.25,
        lineage=_lineage(),
        normalized_article_payload={"id": "article-1"},
        raw_payload={"vendor_id": "article-123"},
        metadata={"publisher": "Reuters"},
    )


def _url_only_article() -> NewsArticleRecord:
    return NewsArticleRecord(
        article_id="article-2",
        source="ap",
        title="Markets await inflation data",
        published_timestamp=_timestamp(),
        url="https://example.com/markets-await-inflation-data",
        summary="Investors are focused on CPI.",
        symbols=("SPY",),
        themes=("inflation",),
        importance_score=0.7,
        headline_score=0.6,
        relevance_score=0.8,
        sentiment_score=0.1,
        lineage=_lineage(),
        normalized_article_payload={"id": "article-2"},
        raw_payload={"vendor_id": "article-456"},
        metadata={"publisher": "AP"},
    )


def _analysis_snapshot() -> NewsAnalysisSnapshotRecord:
    full_response = "\n".join(
        f"Paragraph {index}: full response content is retained." for index in range(120)
    )
    return NewsAnalysisSnapshotRecord(
        analysis_snapshot_id="news-analysis-1",
        timestamp=_timestamp(),
        source="morning_report",
        article_ids=("article-1", "article-2"),
        symbols=("SPY", "QQQ"),
        themes=("macro", "rates"),
        importance_score=0.85,
        sentiment_score=-0.2,
        impact_score=0.4,
        confidence=0.9,
        llm_summary="Markets are focused on policy path.",
        full_llm_response=full_response,
        analysis_model="gpt-test",
        inputs={"article_count": 2},
        outputs={"summary": "Policy uncertainty dominates."},
        metadata={"prompt_version": "v1"},
        lineage=_lineage(),
    )


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="news_node",
    )


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=timezone.utc)
