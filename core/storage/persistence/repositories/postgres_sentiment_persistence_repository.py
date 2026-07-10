from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.sentiment import SentimentSnapshotModel
from core.database.models.sentiment import SentimentSourceModel
from core.storage.persistence.sentiment import SentimentPersistenceBundle
from core.storage.persistence.sentiment import SentimentPersistenceResult
from core.storage.persistence.sentiment import SentimentSnapshotRecord
from core.storage.persistence.sentiment import SentimentSourceRecord
from core.storage.persistence.sentiment.sentiment_persistence_repository import (
    SentimentPersistenceRepository,
)
from core.storage.persistence.serializers.sentiment_persistence_serializer import (
    SentimentPersistenceSerializer,
)


class PostgresSentimentPersistenceRepository(SentimentPersistenceRepository):
    """
    PostgreSQL adapter for curated sentiment persistence.

    Sentiment snapshots and source contribution records are append-only inserts
    so point-in-time sentiment state and attribution remain immutable for audit,
    replay, report generation, and future curated RAG source creation.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def persist_sentiment_bundle(
        self,
        bundle: SentimentPersistenceBundle,
    ) -> SentimentPersistenceResult:
        try:
            for snapshot_record in bundle.snapshots:
                await self._session.execute(
                    _insert_snapshot_statement(
                        snapshot_record,
                    )
                )
            for source_record in bundle.sources:
                await self._session.execute(
                    _insert_source_statement(
                        source_record,
                    )
                )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return SentimentPersistenceResult.failed(
                str(exc),
            )

        return SentimentPersistenceResult.succeeded(
            primary_record_id=_bundle_primary_record_id(bundle),
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
        stmt = select(SentimentSnapshotModel)
        if source is not None:
            stmt = stmt.where(
                SentimentSnapshotModel.source == source,
            )
        if symbol is not None:
            stmt = stmt.where(
                SentimentSnapshotModel.symbol == symbol.upper(),
            )
        if universe is not None:
            stmt = stmt.where(
                SentimentSnapshotModel.universe == universe,
            )
        if start is not None:
            stmt = stmt.where(
                SentimentSnapshotModel.timestamp >= start,
            )
        if end is not None:
            stmt = stmt.where(
                SentimentSnapshotModel.timestamp <= end,
            )
        stmt = stmt.order_by(
            SentimentSnapshotModel.timestamp,
            SentimentSnapshotModel.sentiment_snapshot_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            SentimentPersistenceSerializer.snapshot_from_model(
                model,
            )
            for model in result.scalars().all()
        )

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
        stmt = select(SentimentSourceModel)
        if sentiment_snapshot_id is not None:
            stmt = stmt.where(
                SentimentSourceModel.sentiment_snapshot_id == sentiment_snapshot_id,
            )
        if source is not None:
            stmt = stmt.where(
                SentimentSourceModel.source == source,
            )
        if source_type is not None:
            stmt = stmt.where(
                SentimentSourceModel.source_type == source_type,
            )
        if symbol is not None:
            stmt = stmt.where(
                SentimentSourceModel.symbol == symbol.upper(),
            )
        if universe is not None:
            stmt = stmt.where(
                SentimentSourceModel.universe == universe,
            )
        if start is not None:
            stmt = stmt.where(
                SentimentSourceModel.timestamp >= start,
            )
        if end is not None:
            stmt = stmt.where(
                SentimentSourceModel.timestamp <= end,
            )
        stmt = stmt.order_by(
            SentimentSourceModel.timestamp,
            SentimentSourceModel.sentiment_source_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            SentimentPersistenceSerializer.source_from_model(
                model,
            )
            for model in result.scalars().all()
        )


def _insert_snapshot_statement(
    record: SentimentSnapshotRecord,
) -> Any:
    return insert(SentimentSnapshotModel).values(
        **SentimentPersistenceSerializer.snapshot_values(record)
    )


def _insert_source_statement(
    record: SentimentSourceRecord,
) -> Any:
    return insert(SentimentSourceModel).values(
        **SentimentPersistenceSerializer.source_values(record)
    )


def _bundle_primary_record_id(
    bundle: SentimentPersistenceBundle,
) -> str:
    for records in (
        bundle.snapshots,
        bundle.sources,
    ):
        if records:
            return _record_id(records[0])

    return "empty-sentiment-persistence-bundle"


def _record_id(
    record: SentimentSnapshotRecord | SentimentSourceRecord,
) -> str:
    if isinstance(record, SentimentSnapshotRecord):
        return record.sentiment_snapshot_id

    return record.sentiment_source_id
