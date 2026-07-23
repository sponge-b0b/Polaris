from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.agent_signals import AgentSignalModel
from core.storage.persistence.agent_signals.agent_signal_persistence_models import (
    AgentSignalPersistenceResult,
    AgentSignalRecord,
)
from core.storage.persistence.agent_signals.agent_signal_persistence_repository import (
    AgentSignalPersistenceRepository,
)
from core.storage.persistence.serializers.agent_signal_persistence_serializer import (
    AgentSignalPersistenceSerializer,
)


class PostgresAgentSignalPersistenceRepository(AgentSignalPersistenceRepository):
    """
    PostgreSQL adapter for durable curated agent signal persistence.

    Signals are idempotent upserts by ``signal_id`` so workflow retries can
    preserve one canonical signal row per typed agent output.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def persist_signal(
        self,
        signal: AgentSignalRecord,
    ) -> AgentSignalPersistenceResult:
        try:
            await self._session.execute(
                _upsert_signal_statement(
                    signal,
                )
            )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return AgentSignalPersistenceResult.failed(
                str(exc),
            )

        return AgentSignalPersistenceResult.succeeded(
            signal_id=signal.signal_id,
            records_persisted=1,
        )

    async def get_signal(
        self,
        signal_id: str,
    ) -> AgentSignalRecord | None:
        stmt = select(AgentSignalModel).where(
            AgentSignalModel.signal_id == signal_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return AgentSignalPersistenceSerializer.signal_from_model(
            model,
        )

    async def list_signals_for_execution(
        self,
        *,
        workflow_name: str,
        execution_id: str,
    ) -> Sequence[AgentSignalRecord]:
        stmt = (
            select(AgentSignalModel)
            .where(
                AgentSignalModel.workflow_name == workflow_name,
                AgentSignalModel.execution_id == execution_id,
            )
            .order_by(
                AgentSignalModel.timestamp,
                AgentSignalModel.agent_name,
                AgentSignalModel.signal_id,
            )
        )
        result = await self._session.execute(stmt)

        return tuple(
            AgentSignalPersistenceSerializer.signal_from_model(
                model,
            )
            for model in result.scalars().all()
        )


def _upsert_signal_statement(
    signal: AgentSignalRecord,
) -> Any:
    values = AgentSignalPersistenceSerializer.signal_values(
        signal,
    )
    stmt = insert(AgentSignalModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=[
            "signal_id",
        ],
        set_={
            "agent_name": excluded.agent_name,
            "agent_type": excluded.agent_type,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "symbol": excluded.symbol,
            "universe": excluded.universe,
            "timestamp": excluded.timestamp,
            "directional_score": excluded.directional_score,
            "confidence": excluded.confidence,
            "regime": excluded.regime,
            "signals": excluded.signals,
            "risks": excluded.risks,
            "recommendations": excluded.recommendations,
            "features": excluded.features,
            "reasoning_text": excluded.reasoning_text,
            "llm_response": excluded.llm_response,
            "metadata": excluded.metadata,
            "updated_at": func.now(),
        },
    )
