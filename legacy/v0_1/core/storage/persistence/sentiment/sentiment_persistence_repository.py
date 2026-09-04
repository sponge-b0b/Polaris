from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from core.storage.persistence.sentiment.sentiment_persistence_models import (
    SentimentPersistenceBundle,
    SentimentPersistenceResult,
    SentimentSnapshotRecord,
    SentimentSourceRecord,
)


class SentimentPersistenceRepository(Protocol):
    """
    Async repository contract for durable curated sentiment records.

    Sentiment snapshots and source contribution records are append-only. They
    preserve normalized sentiment outputs and source attribution for audit,
    replay, reporting, and future curated RAG ingestion without storing raw
    provider payloads as canonical records.
    """

    async def persist_sentiment_bundle(
        self,
        bundle: SentimentPersistenceBundle,
    ) -> SentimentPersistenceResult: ...

    async def list_snapshots(
        self,
        *,
        source: str | None = None,
        symbol: str | None = None,
        universe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[SentimentSnapshotRecord]: ...

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
    ) -> Sequence[SentimentSourceRecord]: ...
