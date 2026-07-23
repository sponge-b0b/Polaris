from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.macro import (
    EconomicCalendarEventModel,
    MacroObservationModel,
    MacroRegimeSnapshotModel,
)
from core.storage.persistence.macro import (
    EconomicCalendarEventRecord,
    MacroObservationRecord,
    MacroPersistenceBundle,
    MacroPersistenceResult,
    MacroRegimeSnapshotRecord,
)
from core.storage.persistence.macro.macro_persistence_repository import (
    MacroPersistenceRepository,
)
from core.storage.persistence.serializers.macro_persistence_serializer import (
    MacroPersistenceSerializer,
)


class PostgresMacroPersistenceRepository(MacroPersistenceRepository):
    """
    PostgreSQL adapter for curated macro persistence.

    Macro observations and calendar event fact rows are idempotently upserted by
    their natural source keys. Macro regime snapshots are append-only inserts so
    historical macro analysis observations remain immutable.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def persist_macro_bundle(
        self,
        bundle: MacroPersistenceBundle,
    ) -> MacroPersistenceResult:
        try:
            for observation_record in bundle.observations:
                await self._session.execute(
                    _upsert_observation_statement(
                        observation_record,
                    )
                )
            for regime_record in bundle.regime_snapshots:
                await self._session.execute(
                    _insert_regime_snapshot_statement(
                        regime_record,
                    )
                )
            for calendar_record in bundle.calendar_events:
                await self._session.execute(
                    _upsert_calendar_event_statement(
                        calendar_record,
                    )
                )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return MacroPersistenceResult.failed(
                str(exc),
            )

        return MacroPersistenceResult.succeeded(
            primary_record_id=_bundle_primary_record_id(bundle),
            records_persisted=(
                len(bundle.observations)
                + len(bundle.regime_snapshots)
                + len(bundle.calendar_events)
            ),
        )

    async def list_observations(
        self,
        *,
        indicator_name: str | None = None,
        indicator_category: str | None = None,
        source: str | None = None,
        region: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MacroObservationRecord]:
        stmt = select(MacroObservationModel)
        if indicator_name is not None:
            stmt = stmt.where(
                MacroObservationModel.indicator_name == indicator_name,
            )
        if indicator_category is not None:
            stmt = stmt.where(
                MacroObservationModel.indicator_category == indicator_category,
            )
        if source is not None:
            stmt = stmt.where(
                MacroObservationModel.source == source,
            )
        if region is not None:
            stmt = stmt.where(
                MacroObservationModel.region == region,
            )
        if start is not None:
            stmt = stmt.where(
                MacroObservationModel.observation_timestamp >= start,
            )
        if end is not None:
            stmt = stmt.where(
                MacroObservationModel.observation_timestamp <= end,
            )
        stmt = stmt.order_by(
            MacroObservationModel.observation_timestamp,
            MacroObservationModel.indicator_name,
            MacroObservationModel.source,
            MacroObservationModel.observation_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            MacroPersistenceSerializer.observation_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_regime_snapshots(
        self,
        *,
        region: str | None = None,
        source: str | None = None,
        macro_regime: str | None = None,
        economic_regime: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MacroRegimeSnapshotRecord]:
        stmt = select(MacroRegimeSnapshotModel)
        if region is not None:
            stmt = stmt.where(
                MacroRegimeSnapshotModel.region == region,
            )
        if source is not None:
            stmt = stmt.where(
                MacroRegimeSnapshotModel.source == source,
            )
        if macro_regime is not None:
            stmt = stmt.where(
                MacroRegimeSnapshotModel.macro_regime == macro_regime,
            )
        if economic_regime is not None:
            stmt = stmt.where(
                MacroRegimeSnapshotModel.economic_regime == economic_regime,
            )
        if start is not None:
            stmt = stmt.where(
                MacroRegimeSnapshotModel.timestamp >= start,
            )
        if end is not None:
            stmt = stmt.where(
                MacroRegimeSnapshotModel.timestamp <= end,
            )
        stmt = stmt.order_by(
            MacroRegimeSnapshotModel.timestamp,
            MacroRegimeSnapshotModel.regime_snapshot_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            MacroPersistenceSerializer.regime_snapshot_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_calendar_events(
        self,
        *,
        event_name: str | None = None,
        event_type: str | None = None,
        source: str | None = None,
        region: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[EconomicCalendarEventRecord]:
        stmt = select(EconomicCalendarEventModel)
        if event_name is not None:
            stmt = stmt.where(
                EconomicCalendarEventModel.event_name == event_name,
            )
        if event_type is not None:
            stmt = stmt.where(
                EconomicCalendarEventModel.event_type == event_type,
            )
        if source is not None:
            stmt = stmt.where(
                EconomicCalendarEventModel.source == source,
            )
        if region is not None:
            stmt = stmt.where(
                EconomicCalendarEventModel.region == region,
            )
        if start is not None:
            stmt = stmt.where(
                EconomicCalendarEventModel.event_timestamp >= start,
            )
        if end is not None:
            stmt = stmt.where(
                EconomicCalendarEventModel.event_timestamp <= end,
            )
        stmt = stmt.order_by(
            EconomicCalendarEventModel.event_timestamp,
            EconomicCalendarEventModel.event_name,
            EconomicCalendarEventModel.event_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            MacroPersistenceSerializer.calendar_event_from_model(
                model,
            )
            for model in result.scalars().all()
        )


def _upsert_observation_statement(
    record: MacroObservationRecord,
) -> Any:
    values = MacroPersistenceSerializer.observation_values(record)
    stmt = insert(MacroObservationModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=[
            "indicator_name",
            "observation_timestamp",
            "source",
            "region",
        ],
        set_={
            "observation_id": excluded.observation_id,
            "value": excluded.value,
            "indicator_category": excluded.indicator_category,
            "unit": excluded.unit,
            "frequency": excluded.frequency,
            "release_timestamp": excluded.release_timestamp,
            "vintage_timestamp": excluded.vintage_timestamp,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _insert_regime_snapshot_statement(
    record: MacroRegimeSnapshotRecord,
) -> Any:
    return insert(MacroRegimeSnapshotModel).values(
        **MacroPersistenceSerializer.regime_snapshot_values(record)
    )


def _upsert_calendar_event_statement(
    record: EconomicCalendarEventRecord,
) -> Any:
    values = MacroPersistenceSerializer.calendar_event_values(record)
    stmt = insert(EconomicCalendarEventModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=[
            "event_name",
            "event_timestamp",
            "source",
            "region",
        ],
        set_={
            "event_id": excluded.event_id,
            "event_type": excluded.event_type,
            "importance_score": excluded.importance_score,
            "actual_value": excluded.actual_value,
            "forecast_value": excluded.forecast_value,
            "previous_value": excluded.previous_value,
            "surprise_score": excluded.surprise_score,
            "unit": excluded.unit,
            "currency": excluded.currency,
            "release_status": excluded.release_status,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _bundle_primary_record_id(
    bundle: MacroPersistenceBundle,
) -> str:
    for records in (
        bundle.observations,
        bundle.regime_snapshots,
        bundle.calendar_events,
    ):
        if records:
            return _record_id(records[0])

    return "empty-macro-persistence-bundle"


def _record_id(
    record: MacroObservationRecord
    | MacroRegimeSnapshotRecord
    | EconomicCalendarEventRecord,
) -> str:
    if isinstance(record, MacroObservationRecord):
        return record.observation_id
    if isinstance(record, MacroRegimeSnapshotRecord):
        return record.regime_snapshot_id

    return record.event_id
