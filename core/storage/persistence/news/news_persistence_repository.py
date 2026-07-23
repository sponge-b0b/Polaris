from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from core.storage.persistence.news.news_persistence_models import (
    NewsAnalysisSnapshotRecord,
    NewsArticleRecord,
    NewsPersistenceBundle,
    NewsPersistenceResult,
)


class NewsPersistenceRepository(Protocol):
    """
    Async repository contract for durable curated news records.

    News article facts are idempotently upserted by source identity keys.
    News analysis snapshots are append-only records that preserve full LLM
    responses and curated inputs/outputs for audit, replay, and future RAG
    ingestion.
    """

    async def persist_news_bundle(
        self,
        bundle: NewsPersistenceBundle,
    ) -> NewsPersistenceResult: ...

    async def list_articles(
        self,
        *,
        source: str | None = None,
        symbol: str | None = None,
        theme: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[NewsArticleRecord]: ...

    async def list_analysis_snapshots(
        self,
        *,
        source: str | None = None,
        symbol: str | None = None,
        theme: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[NewsAnalysisSnapshotRecord]: ...
