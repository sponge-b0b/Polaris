from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.market import (
    MarketBreadthSnapshotModel,
    MarketContextSnapshotModel,
    MarketEventSnapshotModel,
    MarketIndicatorModel,
    MarketOhlcvModel,
    TechnicalAnalysisSnapshotModel,
)
from core.storage.persistence.market import (
    MarketBreadthSnapshotRecord,
    MarketContextSnapshotRecord,
    MarketEventSnapshotRecord,
    MarketIndicatorRecord,
    MarketOhlcvRecord,
    MarketPersistenceBundle,
    MarketPersistenceResult,
    TechnicalAnalysisSnapshotRecord,
)
from core.storage.persistence.market.market_persistence_repository import (
    MarketPersistenceRepository,
)
from core.storage.persistence.serializers.market_persistence_serializer import (
    MarketPersistenceSerializer,
)


class PostgresMarketPersistenceRepository(MarketPersistenceRepository):
    """
    PostgreSQL adapter for curated market and technical persistence.

    OHLCV and indicator fact rows are idempotently upserted by their natural
    market keys. Market context, technical analysis, and breadth snapshots are
    append-only inserts so historical analysis observations remain immutable.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def persist_market_bundle(
        self,
        bundle: MarketPersistenceBundle,
    ) -> MarketPersistenceResult:
        try:
            for ohlcv_record in bundle.ohlcv:
                await self._session.execute(
                    _upsert_ohlcv_statement(
                        ohlcv_record,
                    )
                )
            for indicator_record in bundle.indicators:
                await self._session.execute(
                    _upsert_indicator_statement(
                        indicator_record,
                    )
                )
            for context_record in bundle.context_snapshots:
                await self._session.execute(
                    _insert_context_snapshot_statement(
                        context_record,
                    )
                )
            for technical_record in bundle.technical_snapshots:
                await self._session.execute(
                    _insert_technical_snapshot_statement(
                        technical_record,
                    )
                )
            for breadth_record in bundle.breadth_snapshots:
                await self._session.execute(
                    _insert_breadth_snapshot_statement(
                        breadth_record,
                    )
                )
            for event_record in bundle.event_snapshots:
                await self._session.execute(
                    _insert_event_snapshot_statement(
                        event_record,
                    )
                )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return MarketPersistenceResult.failed(
                str(exc),
            )

        return MarketPersistenceResult.succeeded(
            primary_record_id=_bundle_primary_record_id(bundle),
            records_persisted=(
                len(bundle.ohlcv)
                + len(bundle.indicators)
                + len(bundle.context_snapshots)
                + len(bundle.technical_snapshots)
                + len(bundle.breadth_snapshots)
                + len(bundle.event_snapshots)
            ),
        )

    async def list_ohlcv(
        self,
        *,
        symbol: str,
        source: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MarketOhlcvRecord]:
        stmt = select(MarketOhlcvModel).where(
            MarketOhlcvModel.symbol == symbol.upper(),
        )
        if source is not None:
            stmt = stmt.where(
                MarketOhlcvModel.source == source,
            )
        if start is not None:
            stmt = stmt.where(
                MarketOhlcvModel.timestamp >= start,
            )
        if end is not None:
            stmt = stmt.where(
                MarketOhlcvModel.timestamp <= end,
            )
        stmt = stmt.order_by(
            MarketOhlcvModel.timestamp,
            MarketOhlcvModel.source,
            MarketOhlcvModel.ohlcv_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            MarketPersistenceSerializer.ohlcv_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_indicators(
        self,
        *,
        symbol: str,
        indicator_name: str | None = None,
        source: str | None = None,
        timeframe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MarketIndicatorRecord]:
        stmt = select(MarketIndicatorModel).where(
            MarketIndicatorModel.symbol == symbol.upper(),
        )
        if indicator_name is not None:
            stmt = stmt.where(
                MarketIndicatorModel.indicator_name == indicator_name,
            )
        if source is not None:
            stmt = stmt.where(
                MarketIndicatorModel.source == source,
            )
        if timeframe is not None:
            stmt = stmt.where(
                MarketIndicatorModel.timeframe == timeframe,
            )
        if start is not None:
            stmt = stmt.where(
                MarketIndicatorModel.timestamp >= start,
            )
        if end is not None:
            stmt = stmt.where(
                MarketIndicatorModel.timestamp <= end,
            )
        stmt = stmt.order_by(
            MarketIndicatorModel.timestamp,
            MarketIndicatorModel.indicator_name,
            MarketIndicatorModel.timeframe,
            MarketIndicatorModel.indicator_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            MarketPersistenceSerializer.indicator_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_context_snapshots(
        self,
        *,
        universe: str | None = None,
        source: str | None = None,
        market_regime: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MarketContextSnapshotRecord]:
        stmt = select(MarketContextSnapshotModel)
        if universe is not None:
            stmt = stmt.where(
                MarketContextSnapshotModel.universe == universe,
            )
        if source is not None:
            stmt = stmt.where(
                MarketContextSnapshotModel.source == source,
            )
        if market_regime is not None:
            stmt = stmt.where(
                MarketContextSnapshotModel.market_regime == market_regime,
            )
        if start is not None:
            stmt = stmt.where(
                MarketContextSnapshotModel.timestamp >= start,
            )
        if end is not None:
            stmt = stmt.where(
                MarketContextSnapshotModel.timestamp <= end,
            )
        stmt = stmt.order_by(
            MarketContextSnapshotModel.timestamp,
            MarketContextSnapshotModel.context_snapshot_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            MarketPersistenceSerializer.context_snapshot_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_technical_snapshots(
        self,
        *,
        symbol: str,
        source: str | None = None,
        technical_regime: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[TechnicalAnalysisSnapshotRecord]:
        stmt = select(TechnicalAnalysisSnapshotModel).where(
            TechnicalAnalysisSnapshotModel.symbol == symbol.upper(),
        )
        if source is not None:
            stmt = stmt.where(
                TechnicalAnalysisSnapshotModel.source == source,
            )
        if technical_regime is not None:
            stmt = stmt.where(
                TechnicalAnalysisSnapshotModel.technical_regime == technical_regime,
            )
        if start is not None:
            stmt = stmt.where(
                TechnicalAnalysisSnapshotModel.timestamp >= start,
            )
        if end is not None:
            stmt = stmt.where(
                TechnicalAnalysisSnapshotModel.timestamp <= end,
            )
        stmt = stmt.order_by(
            TechnicalAnalysisSnapshotModel.timestamp,
            TechnicalAnalysisSnapshotModel.technical_snapshot_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            MarketPersistenceSerializer.technical_snapshot_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_breadth_snapshots(
        self,
        *,
        universe: str,
        source: str | None = None,
        breadth_regime: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MarketBreadthSnapshotRecord]:
        stmt = select(MarketBreadthSnapshotModel).where(
            MarketBreadthSnapshotModel.universe == universe,
        )
        if source is not None:
            stmt = stmt.where(
                MarketBreadthSnapshotModel.source == source,
            )
        if breadth_regime is not None:
            stmt = stmt.where(
                MarketBreadthSnapshotModel.breadth_regime == breadth_regime,
            )
        if start is not None:
            stmt = stmt.where(
                MarketBreadthSnapshotModel.timestamp >= start,
            )
        if end is not None:
            stmt = stmt.where(
                MarketBreadthSnapshotModel.timestamp <= end,
            )
        stmt = stmt.order_by(
            MarketBreadthSnapshotModel.timestamp,
            MarketBreadthSnapshotModel.breadth_snapshot_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            MarketPersistenceSerializer.breadth_snapshot_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_event_snapshots(
        self,
        *,
        symbol: str,
        source: str | None = None,
        regime_bias: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MarketEventSnapshotRecord]:
        stmt = select(MarketEventSnapshotModel).where(
            MarketEventSnapshotModel.symbol == symbol.upper(),
        )
        if source is not None:
            stmt = stmt.where(
                MarketEventSnapshotModel.source == source,
            )
        if regime_bias is not None:
            stmt = stmt.where(
                MarketEventSnapshotModel.regime_bias == regime_bias,
            )
        if start is not None:
            stmt = stmt.where(
                MarketEventSnapshotModel.timestamp >= start,
            )
        if end is not None:
            stmt = stmt.where(
                MarketEventSnapshotModel.timestamp <= end,
            )
        stmt = stmt.order_by(
            MarketEventSnapshotModel.timestamp,
            MarketEventSnapshotModel.event_snapshot_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            MarketPersistenceSerializer.event_snapshot_from_model(
                model,
            )
            for model in result.scalars().all()
        )


def _upsert_ohlcv_statement(
    record: MarketOhlcvRecord,
) -> Any:
    values = MarketPersistenceSerializer.ohlcv_values(record)
    stmt = insert(MarketOhlcvModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=["symbol", "timestamp", "source"],
        set_={
            "ohlcv_id": excluded.ohlcv_id,
            "open_price": excluded.open_price,
            "high_price": excluded.high_price,
            "low_price": excluded.low_price,
            "close_price": excluded.close_price,
            "adjusted_close": excluded.adjusted_close,
            "volume": excluded.volume,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _upsert_indicator_statement(
    record: MarketIndicatorRecord,
) -> Any:
    values = MarketPersistenceSerializer.indicator_values(record)
    stmt = insert(MarketIndicatorModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=[
            "symbol",
            "timestamp",
            "source",
            "indicator_name",
            "timeframe",
        ],
        set_={
            "indicator_id": excluded.indicator_id,
            "indicator_value": excluded.indicator_value,
            "parameters": excluded.parameters,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _insert_context_snapshot_statement(
    record: MarketContextSnapshotRecord,
) -> Any:
    return insert(MarketContextSnapshotModel).values(
        **MarketPersistenceSerializer.context_snapshot_values(record)
    )


def _insert_technical_snapshot_statement(
    record: TechnicalAnalysisSnapshotRecord,
) -> Any:
    return insert(TechnicalAnalysisSnapshotModel).values(
        **MarketPersistenceSerializer.technical_snapshot_values(record)
    )


def _insert_breadth_snapshot_statement(
    record: MarketBreadthSnapshotRecord,
) -> Any:
    return insert(MarketBreadthSnapshotModel).values(
        **MarketPersistenceSerializer.breadth_snapshot_values(record)
    )


def _insert_event_snapshot_statement(
    record: MarketEventSnapshotRecord,
) -> Any:
    return insert(MarketEventSnapshotModel).values(
        **MarketPersistenceSerializer.event_snapshot_values(record)
    )


def _bundle_primary_record_id(
    bundle: MarketPersistenceBundle,
) -> str:
    for records in (
        bundle.ohlcv,
        bundle.indicators,
        bundle.context_snapshots,
        bundle.technical_snapshots,
        bundle.breadth_snapshots,
        bundle.event_snapshots,
    ):
        if records:
            return _record_id(records[0])

    return "empty-market-persistence-bundle"


def _record_id(
    record: (
        MarketOhlcvRecord
        | MarketIndicatorRecord
        | MarketContextSnapshotRecord
        | TechnicalAnalysisSnapshotRecord
        | MarketBreadthSnapshotRecord
        | MarketEventSnapshotRecord
    ),
) -> str:
    if isinstance(record, MarketOhlcvRecord):
        return record.ohlcv_id
    if isinstance(record, MarketIndicatorRecord):
        return record.indicator_id
    if isinstance(record, MarketContextSnapshotRecord):
        return record.context_snapshot_id
    if isinstance(record, TechnicalAnalysisSnapshotRecord):
        return record.technical_snapshot_id
    if isinstance(record, MarketBreadthSnapshotRecord):
        return record.breadth_snapshot_id

    return record.event_snapshot_id
