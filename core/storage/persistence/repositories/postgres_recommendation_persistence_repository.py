from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.recommendations import (
    RecommendationModel,
    RecommendationOutcomeModel,
    RecommendationRationaleModel,
    TradeSetupModel,
    WatchlistItemModel,
)
from core.storage.persistence.recommendations import (
    RecommendationOutcomeRecord,
    RecommendationPersistenceBundle,
    RecommendationPersistenceResult,
    RecommendationRationaleRecord,
    RecommendationRecord,
    TradeSetupRecord,
    WatchlistItemRecord,
)
from core.storage.persistence.recommendations.recommendation_persistence_repository import (  # noqa: E501 - canonical module path
    RecommendationPersistenceRepository,
)
from core.storage.persistence.serializers.recommendation_persistence_serializer import (
    RecommendationPersistenceSerializer,
)


class PostgresRecommendationPersistenceRepository(
    RecommendationPersistenceRepository,
):
    """
    PostgreSQL adapter for durable curated recommendation persistence.

    The parent recommendation is idempotently upserted. Child rationale,
    outcome, trade setup, and watchlist rows are also upserted by their stable
    child identifiers without deleting sibling rows, keeping rationales and
    outcomes append-friendly for audit/history use cases.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def persist_recommendation_bundle(
        self,
        bundle: RecommendationPersistenceBundle,
    ) -> RecommendationPersistenceResult:
        try:
            await self._session.execute(
                _upsert_recommendation_statement(
                    bundle.recommendation,
                )
            )
            for rationale in bundle.rationales:
                await self._session.execute(
                    _upsert_rationale_statement(
                        rationale,
                    )
                )
            for outcome in bundle.outcomes:
                await self._session.execute(
                    _upsert_outcome_statement(
                        outcome,
                    )
                )
            for setup in bundle.trade_setups:
                await self._session.execute(
                    _upsert_trade_setup_statement(
                        setup,
                    )
                )
            for item in bundle.watchlist_items:
                await self._session.execute(
                    _upsert_watchlist_item_statement(
                        item,
                    )
                )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return RecommendationPersistenceResult.failed(
                str(exc),
            )

        return RecommendationPersistenceResult.succeeded(
            recommendation_id=bundle.recommendation.recommendation_id,
            records_persisted=1
            + len(bundle.rationales)
            + len(bundle.outcomes)
            + len(bundle.trade_setups)
            + len(bundle.watchlist_items),
        )

    async def get_recommendation(
        self,
        recommendation_id: str,
    ) -> RecommendationRecord | None:
        stmt = select(RecommendationModel).where(
            RecommendationModel.recommendation_id == recommendation_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return RecommendationPersistenceSerializer.recommendation_from_model(
            model,
        )

    async def list_recommendations(
        self,
        *,
        symbol: str | None = None,
        status: str | None = None,
        execution_id: str | None = None,
    ) -> Sequence[RecommendationRecord]:
        stmt = select(RecommendationModel)
        if symbol is not None:
            stmt = stmt.where(
                RecommendationModel.symbol == symbol.upper(),
            )
        if status is not None:
            stmt = stmt.where(
                RecommendationModel.status == status,
            )
        if execution_id is not None:
            stmt = stmt.where(
                RecommendationModel.execution_id == execution_id,
            )
        stmt = stmt.order_by(
            RecommendationModel.created_at.desc(),
            RecommendationModel.recommendation_id,
        )

        result = await self._session.execute(stmt)

        return tuple(
            RecommendationPersistenceSerializer.recommendation_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_rationales(
        self,
        recommendation_id: str,
    ) -> Sequence[RecommendationRationaleRecord]:
        stmt = (
            select(RecommendationRationaleModel)
            .where(
                RecommendationRationaleModel.recommendation_id == recommendation_id,
            )
            .order_by(
                RecommendationRationaleModel.created_at,
                RecommendationRationaleModel.rationale_id,
            )
        )
        result = await self._session.execute(stmt)

        return tuple(
            RecommendationPersistenceSerializer.rationale_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_outcomes(
        self,
        recommendation_id: str,
    ) -> Sequence[RecommendationOutcomeRecord]:
        stmt = (
            select(RecommendationOutcomeModel)
            .where(
                RecommendationOutcomeModel.recommendation_id == recommendation_id,
            )
            .order_by(
                RecommendationOutcomeModel.evaluated_at,
                RecommendationOutcomeModel.outcome_id,
            )
        )
        result = await self._session.execute(stmt)

        return tuple(
            RecommendationPersistenceSerializer.outcome_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_trade_setups(
        self,
        *,
        recommendation_id: str | None = None,
        symbol: str | None = None,
    ) -> Sequence[TradeSetupRecord]:
        stmt = select(TradeSetupModel)
        if recommendation_id is not None:
            stmt = stmt.where(
                TradeSetupModel.recommendation_id == recommendation_id,
            )
        if symbol is not None:
            stmt = stmt.where(
                TradeSetupModel.symbol == symbol.upper(),
            )
        stmt = stmt.order_by(
            TradeSetupModel.created_at.desc(),
            TradeSetupModel.setup_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            RecommendationPersistenceSerializer.trade_setup_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_watchlist_items(
        self,
        *,
        recommendation_id: str | None = None,
        symbol: str | None = None,
        status: str | None = None,
    ) -> Sequence[WatchlistItemRecord]:
        stmt = select(WatchlistItemModel)
        if recommendation_id is not None:
            stmt = stmt.where(
                WatchlistItemModel.recommendation_id == recommendation_id,
            )
        if symbol is not None:
            stmt = stmt.where(
                WatchlistItemModel.symbol == symbol.upper(),
            )
        if status is not None:
            stmt = stmt.where(
                WatchlistItemModel.status == status,
            )
        stmt = stmt.order_by(
            WatchlistItemModel.priority,
            WatchlistItemModel.created_at.desc(),
            WatchlistItemModel.watchlist_item_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            RecommendationPersistenceSerializer.watchlist_item_from_model(
                model,
            )
            for model in result.scalars().all()
        )


def _upsert_recommendation_statement(
    record: RecommendationRecord,
) -> Any:
    values = RecommendationPersistenceSerializer.recommendation_values(record)
    stmt = insert(RecommendationModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=["recommendation_id"],
        set_={
            "symbol": excluded.symbol,
            "bias": excluded.bias,
            "confidence": excluded.confidence,
            "setup_quality": excluded.setup_quality,
            "risk_score": excluded.risk_score,
            "risk_level": excluded.risk_level,
            "time_horizon": excluded.time_horizon,
            "status": excluded.status,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "created_at": excluded.created_at,
            "entry_context": excluded.entry_context,
            "stop_context": excluded.stop_context,
            "target_context": excluded.target_context,
            "supporting_signals": excluded.supporting_signals,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _upsert_rationale_statement(
    record: RecommendationRationaleRecord,
) -> Any:
    values = RecommendationPersistenceSerializer.rationale_values(record)
    stmt = insert(RecommendationRationaleModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=["rationale_id"],
        set_={
            "recommendation_id": excluded.recommendation_id,
            "rationale_type": excluded.rationale_type,
            "rationale_text": excluded.rationale_text,
            "confidence": excluded.confidence,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "created_at": excluded.created_at,
            "supporting_signals": excluded.supporting_signals,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _upsert_outcome_statement(
    record: RecommendationOutcomeRecord,
) -> Any:
    values = RecommendationPersistenceSerializer.outcome_values(record)
    stmt = insert(RecommendationOutcomeModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=["outcome_id"],
        set_={
            "recommendation_id": excluded.recommendation_id,
            "evaluated_at": excluded.evaluated_at,
            "human_action": excluded.human_action,
            "outcome": excluded.outcome,
            "outcome_return": excluded.outcome_return,
            "outcome_notes": excluded.outcome_notes,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _upsert_trade_setup_statement(
    record: TradeSetupRecord,
) -> Any:
    values = RecommendationPersistenceSerializer.trade_setup_values(record)
    stmt = insert(TradeSetupModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=["setup_id"],
        set_={
            "recommendation_id": excluded.recommendation_id,
            "symbol": excluded.symbol,
            "setup_type": excluded.setup_type,
            "bias": excluded.bias,
            "setup_quality": excluded.setup_quality,
            "confidence": excluded.confidence,
            "risk_score": excluded.risk_score,
            "risk_reward_ratio": excluded.risk_reward_ratio,
            "time_horizon": excluded.time_horizon,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "created_at": excluded.created_at,
            "entry_context": excluded.entry_context,
            "stop_context": excluded.stop_context,
            "target_context": excluded.target_context,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _upsert_watchlist_item_statement(
    record: WatchlistItemRecord,
) -> Any:
    values = RecommendationPersistenceSerializer.watchlist_item_values(record)
    stmt = insert(WatchlistItemModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=["watchlist_item_id"],
        set_={
            "recommendation_id": excluded.recommendation_id,
            "symbol": excluded.symbol,
            "reason": excluded.reason,
            "priority": excluded.priority,
            "status": excluded.status,
            "bias": excluded.bias,
            "confidence": excluded.confidence,
            "setup_quality": excluded.setup_quality,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "created_at": excluded.created_at,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )
