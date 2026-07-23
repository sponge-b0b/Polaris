from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.news import NewsAnalysisSnapshotModel, NewsArticleModel
from core.storage.persistence.news import (
    NewsAnalysisSnapshotRecord,
    NewsArticleRecord,
    NewsPersistenceBundle,
    NewsPersistenceResult,
)
from core.storage.persistence.news.news_persistence_repository import (
    NewsPersistenceRepository,
)
from core.storage.persistence.serializers.news_persistence_serializer import (
    NewsPersistenceSerializer,
)


class PostgresNewsPersistenceRepository(NewsPersistenceRepository):
    """
    PostgreSQL adapter for curated news persistence.

    Article facts are upserted by the best available source identity key. News
    analysis snapshots are append-only inserts so report-time analysis remains
    immutable and complete, including full untruncated LLM responses.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def persist_news_bundle(
        self,
        bundle: NewsPersistenceBundle,
    ) -> NewsPersistenceResult:
        try:
            for article_record in bundle.articles:
                await self._session.execute(
                    _upsert_article_statement(
                        article_record,
                    )
                )
            for analysis_record in bundle.analysis_snapshots:
                await self._session.execute(
                    _insert_analysis_snapshot_statement(
                        analysis_record,
                    )
                )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return NewsPersistenceResult.failed(
                str(exc),
            )

        return NewsPersistenceResult.succeeded(
            primary_record_id=_bundle_primary_record_id(bundle),
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
        stmt = select(NewsArticleModel)
        if source is not None:
            stmt = stmt.where(
                NewsArticleModel.source == source,
            )
        if symbol is not None:
            stmt = stmt.where(
                NewsArticleModel.symbols.contains([symbol.upper()]),
            )
        if theme is not None:
            stmt = stmt.where(
                NewsArticleModel.themes.contains([theme]),
            )
        if start is not None:
            stmt = stmt.where(
                NewsArticleModel.published_timestamp >= start,
            )
        if end is not None:
            stmt = stmt.where(
                NewsArticleModel.published_timestamp <= end,
            )
        stmt = stmt.order_by(
            NewsArticleModel.published_timestamp,
            NewsArticleModel.source,
            NewsArticleModel.article_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            NewsPersistenceSerializer.article_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_analysis_snapshots(
        self,
        *,
        source: str | None = None,
        symbol: str | None = None,
        theme: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[NewsAnalysisSnapshotRecord]:
        stmt = select(NewsAnalysisSnapshotModel)
        if source is not None:
            stmt = stmt.where(
                NewsAnalysisSnapshotModel.source == source,
            )
        if symbol is not None:
            stmt = stmt.where(
                NewsAnalysisSnapshotModel.symbols.contains([symbol.upper()]),
            )
        if theme is not None:
            stmt = stmt.where(
                NewsAnalysisSnapshotModel.themes.contains([theme]),
            )
        if start is not None:
            stmt = stmt.where(
                NewsAnalysisSnapshotModel.timestamp >= start,
            )
        if end is not None:
            stmt = stmt.where(
                NewsAnalysisSnapshotModel.timestamp <= end,
            )
        stmt = stmt.order_by(
            NewsAnalysisSnapshotModel.timestamp,
            NewsAnalysisSnapshotModel.analysis_snapshot_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            NewsPersistenceSerializer.analysis_snapshot_from_model(
                model,
            )
            for model in result.scalars().all()
        )


def _upsert_article_statement(
    record: NewsArticleRecord,
) -> Any:
    values = NewsPersistenceSerializer.article_values(record)
    stmt = insert(NewsArticleModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=_article_conflict_index_elements(record),
        set_={
            "article_id": excluded.article_id,
            "external_id": excluded.external_id,
            "url": excluded.url,
            "title": excluded.title,
            "summary": excluded.summary,
            "published_at": excluded.published_at,
            "symbols": excluded.symbols,
            "themes": excluded.themes,
            "importance_score": excluded.importance_score,
            "headline_score": excluded.headline_score,
            "relevance_score": excluded.relevance_score,
            "sentiment_score": excluded.sentiment_score,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "normalized_article_payload": excluded.normalized_article_payload,
            "raw_payload": excluded.raw_payload,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _article_conflict_index_elements(
    record: NewsArticleRecord,
) -> list[str]:
    if record.external_id is not None:
        return [
            "source",
            "external_id",
        ]

    return [
        "source",
        "url",
    ]


def _insert_analysis_snapshot_statement(
    record: NewsAnalysisSnapshotRecord,
) -> Any:
    return insert(NewsAnalysisSnapshotModel).values(
        **NewsPersistenceSerializer.analysis_snapshot_values(record)
    )


def _bundle_primary_record_id(
    bundle: NewsPersistenceBundle,
) -> str:
    for records in (
        bundle.articles,
        bundle.analysis_snapshots,
    ):
        if records:
            return _record_id(records[0])

    return "empty-news-persistence-bundle"


def _record_id(
    record: NewsArticleRecord | NewsAnalysisSnapshotRecord,
) -> str:
    if isinstance(record, NewsArticleRecord):
        return record.article_id

    return record.analysis_snapshot_id
