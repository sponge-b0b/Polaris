from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Select
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.attribution import AttributionRecordModel
from core.database.models.attribution import RecommendationAttributionModel
from core.database.models.attribution import SignalAttributionModel
from core.storage.persistence.attribution import AttributionPersistenceBundle
from core.storage.persistence.attribution import AttributionPersistenceRepository
from core.storage.persistence.attribution import AttributionPersistenceResult
from core.storage.persistence.attribution import AttributionRecord
from core.storage.persistence.attribution import RecommendationAttributionRecord
from core.storage.persistence.attribution import SignalAttributionRecord
from core.storage.persistence.serializers.attribution_persistence_serializer import (
    AttributionPersistenceSerializer,
)


class PostgresAttributionPersistenceRepository(
    AttributionPersistenceRepository,
):
    """
    PostgreSQL adapter for durable attribution persistence.

    The adapter upserts each attribution row by its stable identifier and never
    deletes sibling attribution rows for the same target, signal, or
    recommendation, keeping attribution persistence append-friendly.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def persist_attribution_bundle(
        self,
        bundle: AttributionPersistenceBundle,
    ) -> AttributionPersistenceResult:
        try:
            for attribution in bundle.attribution_records:
                await self._session.execute(_upsert_attribution_statement(attribution))
            for signal_attribution in bundle.signal_attributions:
                await self._session.execute(
                    _upsert_signal_attribution_statement(signal_attribution)
                )
            for recommendation_attribution in bundle.recommendation_attributions:
                await self._session.execute(
                    _upsert_recommendation_attribution_statement(
                        recommendation_attribution,
                    )
                )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return AttributionPersistenceResult.failed(
                str(exc),
            )

        return AttributionPersistenceResult.succeeded(
            primary_record_id=_bundle_primary_record_id(bundle),
            records_persisted=(
                len(bundle.attribution_records)
                + len(bundle.signal_attributions)
                + len(bundle.recommendation_attributions)
            ),
        )

    async def persist_attribution(
        self,
        attribution: AttributionRecord,
    ) -> AttributionPersistenceResult:
        try:
            await self._session.execute(_upsert_attribution_statement(attribution))
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return AttributionPersistenceResult.failed(
                str(exc),
            )

        return AttributionPersistenceResult.succeeded(
            primary_record_id=attribution.attribution_id,
            records_persisted=1,
        )

    async def persist_signal_attribution(
        self,
        attribution: SignalAttributionRecord,
    ) -> AttributionPersistenceResult:
        try:
            await self._session.execute(
                _upsert_signal_attribution_statement(attribution)
            )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return AttributionPersistenceResult.failed(
                str(exc),
            )

        return AttributionPersistenceResult.succeeded(
            primary_record_id=attribution.signal_attribution_id,
            records_persisted=1,
        )

    async def persist_recommendation_attribution(
        self,
        attribution: RecommendationAttributionRecord,
    ) -> AttributionPersistenceResult:
        try:
            await self._session.execute(
                _upsert_recommendation_attribution_statement(attribution)
            )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return AttributionPersistenceResult.failed(
                str(exc),
            )

        return AttributionPersistenceResult.succeeded(
            primary_record_id=attribution.recommendation_attribution_id,
            records_persisted=1,
        )

    async def get_attribution(
        self,
        attribution_id: str,
    ) -> AttributionRecord | None:
        stmt = select(AttributionRecordModel).where(
            AttributionRecordModel.attribution_id == attribution_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return AttributionPersistenceSerializer.attribution_from_model(model)

    async def get_signal_attribution(
        self,
        signal_attribution_id: str,
    ) -> SignalAttributionRecord | None:
        stmt = select(SignalAttributionModel).where(
            SignalAttributionModel.signal_attribution_id == signal_attribution_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return AttributionPersistenceSerializer.signal_attribution_from_model(model)

    async def get_recommendation_attribution(
        self,
        recommendation_attribution_id: str,
    ) -> RecommendationAttributionRecord | None:
        stmt = select(RecommendationAttributionModel).where(
            RecommendationAttributionModel.recommendation_attribution_id
            == recommendation_attribution_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return AttributionPersistenceSerializer.recommendation_attribution_from_model(
            model,
        )

    async def list_attributions(
        self,
        *,
        target_record_type: str | None = None,
        target_record_id: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        agent_name: str | None = None,
        agent_type: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[AttributionRecord]:
        stmt = _apply_attribution_filters(
            select(AttributionRecordModel),
            target_record_type=target_record_type,
            target_record_id=target_record_id,
            workflow_name=workflow_name,
            execution_id=execution_id,
            agent_name=agent_name,
            agent_type=agent_type,
            start=start,
            end=end,
        ).order_by(
            AttributionRecordModel.timestamp,
            AttributionRecordModel.target_record_type,
            AttributionRecordModel.target_record_id,
            AttributionRecordModel.attribution_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            AttributionPersistenceSerializer.attribution_from_model(model)
            for model in result.scalars().all()
        )

    async def list_signal_attributions(
        self,
        *,
        signal_id: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        agent_name: str | None = None,
        agent_type: str | None = None,
        symbol: str | None = None,
        universe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[SignalAttributionRecord]:
        stmt = _apply_scoped_filters(
            select(SignalAttributionModel),
            SignalAttributionModel,
            signal_id=signal_id,
            workflow_name=workflow_name,
            execution_id=execution_id,
            agent_name=agent_name,
            agent_type=agent_type,
            symbol=symbol,
            universe=universe,
            start=start,
            end=end,
        ).order_by(
            SignalAttributionModel.timestamp,
            SignalAttributionModel.signal_id,
            SignalAttributionModel.signal_attribution_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            AttributionPersistenceSerializer.signal_attribution_from_model(model)
            for model in result.scalars().all()
        )

    async def list_recommendation_attributions(
        self,
        *,
        recommendation_id: str | None = None,
        signal_id: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        agent_name: str | None = None,
        agent_type: str | None = None,
        symbol: str | None = None,
        universe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[RecommendationAttributionRecord]:
        stmt = _apply_scoped_filters(
            select(RecommendationAttributionModel),
            RecommendationAttributionModel,
            signal_id=signal_id,
            workflow_name=workflow_name,
            execution_id=execution_id,
            agent_name=agent_name,
            agent_type=agent_type,
            symbol=symbol,
            universe=universe,
            start=start,
            end=end,
        )
        if recommendation_id is not None:
            stmt = stmt.where(
                RecommendationAttributionModel.recommendation_id == recommendation_id,
            )
        stmt = stmt.order_by(
            RecommendationAttributionModel.timestamp,
            RecommendationAttributionModel.recommendation_id,
            RecommendationAttributionModel.recommendation_attribution_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            AttributionPersistenceSerializer.recommendation_attribution_from_model(
                model,
            )
            for model in result.scalars().all()
        )


def _upsert_attribution_statement(
    attribution: AttributionRecord,
) -> Any:
    values = AttributionPersistenceSerializer.attribution_values(
        attribution,
    )
    stmt = insert(AttributionRecordModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=["attribution_id"],
        set_={
            "target_record_type": excluded.target_record_type,
            "target_record_id": excluded.target_record_id,
            "attribution_type": excluded.attribution_type,
            "contribution_type": excluded.contribution_type,
            "contribution_score": excluded.contribution_score,
            "confidence": excluded.confidence,
            "explanation": excluded.explanation,
            "timestamp": excluded.timestamp,
            "agent_name": excluded.agent_name,
            "agent_type": excluded.agent_type,
            "source_records": excluded.source_records,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _upsert_signal_attribution_statement(
    attribution: SignalAttributionRecord,
) -> Any:
    values = AttributionPersistenceSerializer.signal_attribution_values(
        attribution,
    )
    stmt = insert(SignalAttributionModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=["signal_attribution_id"],
        set_={
            "signal_id": excluded.signal_id,
            "attribution_type": excluded.attribution_type,
            "contribution_type": excluded.contribution_type,
            "contribution_score": excluded.contribution_score,
            "confidence": excluded.confidence,
            "explanation": excluded.explanation,
            "timestamp": excluded.timestamp,
            "signal_type": excluded.signal_type,
            "agent_name": excluded.agent_name,
            "agent_type": excluded.agent_type,
            "symbol": excluded.symbol,
            "universe": excluded.universe,
            "source_records": excluded.source_records,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _upsert_recommendation_attribution_statement(
    attribution: RecommendationAttributionRecord,
) -> Any:
    values = AttributionPersistenceSerializer.recommendation_attribution_values(
        attribution,
    )
    stmt = insert(RecommendationAttributionModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=["recommendation_attribution_id"],
        set_={
            "recommendation_id": excluded.recommendation_id,
            "signal_id": excluded.signal_id,
            "attribution_type": excluded.attribution_type,
            "contribution_type": excluded.contribution_type,
            "contribution_score": excluded.contribution_score,
            "confidence": excluded.confidence,
            "explanation": excluded.explanation,
            "timestamp": excluded.timestamp,
            "agent_name": excluded.agent_name,
            "agent_type": excluded.agent_type,
            "symbol": excluded.symbol,
            "universe": excluded.universe,
            "source_records": excluded.source_records,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _apply_attribution_filters(
    stmt: Select[Any],
    *,
    target_record_type: str | None,
    target_record_id: str | None,
    workflow_name: str | None,
    execution_id: str | None,
    agent_name: str | None,
    agent_type: str | None,
    start: datetime | None,
    end: datetime | None,
) -> Select[Any]:
    if target_record_type is not None:
        stmt = stmt.where(
            AttributionRecordModel.target_record_type == target_record_type,
        )
    if target_record_id is not None:
        stmt = stmt.where(
            AttributionRecordModel.target_record_id == target_record_id,
        )
    if workflow_name is not None:
        stmt = stmt.where(
            AttributionRecordModel.workflow_name == workflow_name,
        )
    if execution_id is not None:
        stmt = stmt.where(
            AttributionRecordModel.execution_id == execution_id,
        )
    if agent_name is not None:
        stmt = stmt.where(
            AttributionRecordModel.agent_name == agent_name,
        )
    if agent_type is not None:
        stmt = stmt.where(
            AttributionRecordModel.agent_type == agent_type,
        )
    if start is not None:
        stmt = stmt.where(
            AttributionRecordModel.timestamp >= start,
        )
    if end is not None:
        stmt = stmt.where(
            AttributionRecordModel.timestamp <= end,
        )

    return stmt


def _apply_scoped_filters(
    stmt: Select[Any],
    model: type[SignalAttributionModel] | type[RecommendationAttributionModel],
    *,
    signal_id: str | None,
    workflow_name: str | None,
    execution_id: str | None,
    agent_name: str | None,
    agent_type: str | None,
    symbol: str | None,
    universe: str | None,
    start: datetime | None,
    end: datetime | None,
) -> Select[Any]:
    if signal_id is not None:
        stmt = stmt.where(
            model.signal_id == signal_id,
        )
    if workflow_name is not None:
        stmt = stmt.where(
            model.workflow_name == workflow_name,
        )
    if execution_id is not None:
        stmt = stmt.where(
            model.execution_id == execution_id,
        )
    if agent_name is not None:
        stmt = stmt.where(
            model.agent_name == agent_name,
        )
    if agent_type is not None:
        stmt = stmt.where(
            model.agent_type == agent_type,
        )
    if symbol is not None:
        stmt = stmt.where(
            model.symbol == symbol.upper(),
        )
    if universe is not None:
        stmt = stmt.where(
            model.universe == universe,
        )
    if start is not None:
        stmt = stmt.where(
            model.timestamp >= start,
        )
    if end is not None:
        stmt = stmt.where(
            model.timestamp <= end,
        )

    return stmt


def _bundle_primary_record_id(
    bundle: AttributionPersistenceBundle,
) -> str:
    for records in (
        bundle.attribution_records,
        bundle.signal_attributions,
        bundle.recommendation_attributions,
    ):
        if records:
            return _record_id(records[0])

    return "empty-attribution-persistence-bundle"


def _record_id(
    record: AttributionRecord
    | SignalAttributionRecord
    | RecommendationAttributionRecord,
) -> str:
    if isinstance(record, AttributionRecord):
        return record.attribution_id
    if isinstance(record, SignalAttributionRecord):
        return record.signal_attribution_id

    return record.recommendation_attribution_id
