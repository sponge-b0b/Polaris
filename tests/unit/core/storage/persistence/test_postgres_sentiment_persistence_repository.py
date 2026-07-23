from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.sentiment import SentimentSnapshotModel, SentimentSourceModel
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.repositories.postgres_sentiment_persistence_repository import (  # noqa: E501
    PostgresSentimentPersistenceRepository,
)
from core.storage.persistence.sentiment import (
    SentimentPersistenceBundle,
    SentimentSnapshotRecord,
    SentimentSourceRecord,
)
from core.storage.persistence.serializers.sentiment_persistence_serializer import (
    SentimentPersistenceSerializer,
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
async def test_persist_sentiment_bundle_inserts_append_only_records() -> None:
    session = FakeAsyncSession()
    repository = PostgresSentimentPersistenceRepository(
        cast(AsyncSession, session),
    )

    result = await repository.persist_sentiment_bundle(_bundle())

    compiled = [
        str(
            statement.compile(
                dialect=postgresql.dialect(),
            )
        )
        for statement in session.executed
    ]

    assert result.success is True
    assert result.primary_record_id == "sentiment-snapshot-1"
    assert result.records_persisted == 2
    assert session.commits == 1
    assert len(session.executed) == 2
    assert "sentiment_snapshots" in compiled[0]
    assert "ON CONFLICT" not in compiled[0]
    assert "sentiment_sources" in compiled[1]
    assert "ON CONFLICT" not in compiled[1]


@pytest.mark.asyncio
async def test_sentiment_idempotency_review_keeps_snapshots_and_sources_append_only() -> (  # noqa: E501
    None
):
    session = FakeAsyncSession()
    repository = PostgresSentimentPersistenceRepository(
        cast(AsyncSession, session),
    )

    result = await repository.persist_sentiment_bundle(_bundle())

    compiled = [
        str(
            statement.compile(
                dialect=postgresql.dialect(),
            )
        )
        for statement in session.executed
    ]

    assert result.success is True
    assert len(compiled) == 2
    assert "sentiment_snapshots" in compiled[0]
    assert "ON CONFLICT" not in compiled[0]
    assert "sentiment_sources" in compiled[1]
    assert "ON CONFLICT" not in compiled[1]
    assert all("DELETE" not in statement.upper() for statement in compiled)


@pytest.mark.asyncio
async def test_persist_sentiment_bundle_rolls_back_on_sqlalchemy_error() -> None:
    session = FakeAsyncSession(error=SQLAlchemyError("database unavailable"))
    repository = PostgresSentimentPersistenceRepository(
        cast(AsyncSession, session),
    )

    result = await repository.persist_sentiment_bundle(_bundle())

    assert result.success is False
    assert result.error is not None
    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_list_sentiment_snapshots_returns_typed_records() -> None:
    snapshot_model = SentimentSnapshotModel(
        **SentimentPersistenceSerializer.snapshot_values(_snapshot())
    )

    snapshots = await PostgresSentimentPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([snapshot_model])))
    ).list_snapshots(
        source="morning_report",
        symbol="spy",
        universe="us_equities",
        start=_timestamp(),
        end=_timestamp(),
    )

    assert snapshots[0].sentiment_snapshot_id == "sentiment-snapshot-1"
    assert snapshots[0].symbol == "SPY"
    assert snapshots[0].fusion_components == {"news": 0.4, "market": 0.6}
    assert snapshots[0].metadata == {"prompt_version": "v1"}


@pytest.mark.asyncio
async def test_list_sentiment_sources_returns_typed_records() -> None:
    source_model = SentimentSourceModel(
        **SentimentPersistenceSerializer.source_values(_source())
    )

    sources = await PostgresSentimentPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([source_model])))
    ).list_sources(
        sentiment_snapshot_id="sentiment-snapshot-1",
        source="reuters",
        source_type="news",
        symbol="spy",
        universe="us_equities",
        start=_timestamp(),
        end=_timestamp(),
    )

    assert sources[0].sentiment_source_id == "sentiment-source-1"
    assert sources[0].sentiment_snapshot_id == "sentiment-snapshot-1"
    assert sources[0].source == "reuters"
    assert sources[0].source_reference == "article-group-1"
    assert sources[0].metadata == {"curated": True}


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
        lineage=_lineage(),
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
        lineage=_lineage(),
    )


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="sentiment_node",
    )


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=UTC)
