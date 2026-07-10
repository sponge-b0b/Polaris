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

from core.database.models.agent_intelligence import AgentReasoningModel
from core.database.models.agent_intelligence import AgentRecommendationModel
from core.database.models.agent_intelligence import AgentRiskAssessmentModel
from core.storage.persistence.agent_intelligence.agent_intelligence_persistence_models import (
    AgentIntelligencePersistenceBundle,
)
from core.storage.persistence.agent_intelligence.agent_intelligence_persistence_models import (
    AgentIntelligencePersistenceResult,
)
from core.storage.persistence.agent_intelligence.agent_intelligence_persistence_models import (
    AgentReasoningRecord,
)
from core.storage.persistence.agent_intelligence.agent_intelligence_persistence_models import (
    AgentRecommendationRecord,
)
from core.storage.persistence.agent_intelligence.agent_intelligence_persistence_models import (
    AgentRiskAssessmentRecord,
)
from core.storage.persistence.agent_intelligence.agent_intelligence_persistence_repository import (
    AgentIntelligencePersistenceRepository,
)
from core.storage.persistence.serializers.agent_intelligence_persistence_serializer import (
    AgentIntelligencePersistenceSerializer,
)


class PostgresAgentIntelligencePersistenceRepository(
    AgentIntelligencePersistenceRepository,
):
    """
    PostgreSQL adapter for enriched agent intelligence persistence.

    The canonical ``agent_signals`` table remains the primary signal table. This
    adapter upserts reasoning, recommendations, and risk assessments by their
    own stable identifiers while linking every row back to ``agent_signals`` via
    ``agent_signal_id``.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def persist_intelligence_bundle(
        self,
        bundle: AgentIntelligencePersistenceBundle,
    ) -> AgentIntelligencePersistenceResult:
        try:
            for reasoning in bundle.reasoning:
                await self._session.execute(
                    _upsert_reasoning_statement(
                        reasoning,
                    )
                )
            for recommendation in bundle.recommendations:
                await self._session.execute(
                    _upsert_recommendation_statement(
                        recommendation,
                    )
                )
            for risk_assessment in bundle.risk_assessments:
                await self._session.execute(
                    _upsert_risk_assessment_statement(
                        risk_assessment,
                    )
                )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return AgentIntelligencePersistenceResult.failed(
                str(exc),
            )

        return AgentIntelligencePersistenceResult.succeeded(
            primary_record_id=_bundle_primary_record_id(bundle),
            records_persisted=(
                len(bundle.reasoning)
                + len(bundle.recommendations)
                + len(bundle.risk_assessments)
            ),
        )

    async def persist_reasoning(
        self,
        reasoning: AgentReasoningRecord,
    ) -> AgentIntelligencePersistenceResult:
        try:
            await self._session.execute(_upsert_reasoning_statement(reasoning))
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return AgentIntelligencePersistenceResult.failed(
                str(exc),
            )

        return AgentIntelligencePersistenceResult.succeeded(
            primary_record_id=reasoning.reasoning_id,
            records_persisted=1,
        )

    async def persist_recommendation(
        self,
        recommendation: AgentRecommendationRecord,
    ) -> AgentIntelligencePersistenceResult:
        try:
            await self._session.execute(
                _upsert_recommendation_statement(recommendation)
            )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return AgentIntelligencePersistenceResult.failed(
                str(exc),
            )

        return AgentIntelligencePersistenceResult.succeeded(
            primary_record_id=recommendation.agent_recommendation_id,
            records_persisted=1,
        )

    async def persist_risk_assessment(
        self,
        risk_assessment: AgentRiskAssessmentRecord,
    ) -> AgentIntelligencePersistenceResult:
        try:
            await self._session.execute(
                _upsert_risk_assessment_statement(risk_assessment)
            )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return AgentIntelligencePersistenceResult.failed(
                str(exc),
            )

        return AgentIntelligencePersistenceResult.succeeded(
            primary_record_id=risk_assessment.risk_assessment_id,
            records_persisted=1,
        )

    async def get_reasoning(
        self,
        reasoning_id: str,
    ) -> AgentReasoningRecord | None:
        stmt = select(AgentReasoningModel).where(
            AgentReasoningModel.reasoning_id == reasoning_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return AgentIntelligencePersistenceSerializer.reasoning_from_model(
            model,
        )

    async def get_recommendation(
        self,
        agent_recommendation_id: str,
    ) -> AgentRecommendationRecord | None:
        stmt = select(AgentRecommendationModel).where(
            AgentRecommendationModel.agent_recommendation_id == agent_recommendation_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return AgentIntelligencePersistenceSerializer.recommendation_from_model(
            model,
        )

    async def get_risk_assessment(
        self,
        risk_assessment_id: str,
    ) -> AgentRiskAssessmentRecord | None:
        stmt = select(AgentRiskAssessmentModel).where(
            AgentRiskAssessmentModel.risk_assessment_id == risk_assessment_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return AgentIntelligencePersistenceSerializer.risk_assessment_from_model(
            model,
        )

    async def list_reasoning(
        self,
        *,
        agent_signal_id: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        agent_name: str | None = None,
        agent_type: str | None = None,
        symbol: str | None = None,
        universe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[AgentReasoningRecord]:
        stmt = _apply_common_filters(
            select(AgentReasoningModel),
            AgentReasoningModel,
            agent_signal_id=agent_signal_id,
            workflow_name=workflow_name,
            execution_id=execution_id,
            agent_name=agent_name,
            agent_type=agent_type,
            symbol=symbol,
            universe=universe,
            start=start,
            end=end,
        ).order_by(
            AgentReasoningModel.timestamp,
            AgentReasoningModel.agent_name,
            AgentReasoningModel.reasoning_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            AgentIntelligencePersistenceSerializer.reasoning_from_model(model)
            for model in result.scalars().all()
        )

    async def list_recommendations(
        self,
        *,
        agent_signal_id: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        agent_name: str | None = None,
        agent_type: str | None = None,
        symbol: str | None = None,
        universe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[AgentRecommendationRecord]:
        stmt = _apply_common_filters(
            select(AgentRecommendationModel),
            AgentRecommendationModel,
            agent_signal_id=agent_signal_id,
            workflow_name=workflow_name,
            execution_id=execution_id,
            agent_name=agent_name,
            agent_type=agent_type,
            symbol=symbol,
            universe=universe,
            start=start,
            end=end,
        ).order_by(
            AgentRecommendationModel.timestamp,
            AgentRecommendationModel.agent_name,
            AgentRecommendationModel.agent_recommendation_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            AgentIntelligencePersistenceSerializer.recommendation_from_model(model)
            for model in result.scalars().all()
        )

    async def list_risk_assessments(
        self,
        *,
        agent_signal_id: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        agent_name: str | None = None,
        agent_type: str | None = None,
        symbol: str | None = None,
        universe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[AgentRiskAssessmentRecord]:
        stmt = _apply_common_filters(
            select(AgentRiskAssessmentModel),
            AgentRiskAssessmentModel,
            agent_signal_id=agent_signal_id,
            workflow_name=workflow_name,
            execution_id=execution_id,
            agent_name=agent_name,
            agent_type=agent_type,
            symbol=symbol,
            universe=universe,
            start=start,
            end=end,
        ).order_by(
            AgentRiskAssessmentModel.timestamp,
            AgentRiskAssessmentModel.agent_name,
            AgentRiskAssessmentModel.risk_assessment_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            AgentIntelligencePersistenceSerializer.risk_assessment_from_model(model)
            for model in result.scalars().all()
        )


def _upsert_reasoning_statement(
    reasoning: AgentReasoningRecord,
) -> Any:
    values = AgentIntelligencePersistenceSerializer.reasoning_values(
        reasoning,
    )
    stmt = insert(AgentReasoningModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=["reasoning_id"],
        set_={
            "agent_signal_id": excluded.agent_signal_id,
            "agent_name": excluded.agent_name,
            "agent_type": excluded.agent_type,
            "timestamp": excluded.timestamp,
            "reasoning_type": excluded.reasoning_type,
            "model_name": excluded.model_name,
            "prompt_version": excluded.prompt_version,
            "symbol": excluded.symbol,
            "universe": excluded.universe,
            "reasoning_text": excluded.reasoning_text,
            "full_llm_response": excluded.full_llm_response,
            "inputs_payload": excluded.inputs_payload,
            "outputs_payload": excluded.outputs_payload,
            "linked_records": excluded.linked_records,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _upsert_recommendation_statement(
    recommendation: AgentRecommendationRecord,
) -> Any:
    values = AgentIntelligencePersistenceSerializer.recommendation_values(
        recommendation,
    )
    stmt = insert(AgentRecommendationModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=["agent_recommendation_id"],
        set_={
            "agent_signal_id": excluded.agent_signal_id,
            "agent_name": excluded.agent_name,
            "agent_type": excluded.agent_type,
            "timestamp": excluded.timestamp,
            "recommendation_type": excluded.recommendation_type,
            "recommendation_text": excluded.recommendation_text,
            "symbol": excluded.symbol,
            "universe": excluded.universe,
            "bias": excluded.bias,
            "action": excluded.action,
            "confidence": excluded.confidence,
            "conviction": excluded.conviction,
            "time_horizon": excluded.time_horizon,
            "rationale_text": excluded.rationale_text,
            "full_llm_response": excluded.full_llm_response,
            "supporting_signals": excluded.supporting_signals,
            "inputs_payload": excluded.inputs_payload,
            "outputs_payload": excluded.outputs_payload,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _upsert_risk_assessment_statement(
    risk_assessment: AgentRiskAssessmentRecord,
) -> Any:
    values = AgentIntelligencePersistenceSerializer.risk_assessment_values(
        risk_assessment,
    )
    stmt = insert(AgentRiskAssessmentModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=["risk_assessment_id"],
        set_={
            "agent_signal_id": excluded.agent_signal_id,
            "agent_name": excluded.agent_name,
            "agent_type": excluded.agent_type,
            "timestamp": excluded.timestamp,
            "risk_type": excluded.risk_type,
            "assessment_text": excluded.assessment_text,
            "symbol": excluded.symbol,
            "universe": excluded.universe,
            "risk_level": excluded.risk_level,
            "risk_score": excluded.risk_score,
            "confidence": excluded.confidence,
            "mitigation": excluded.mitigation,
            "full_llm_response": excluded.full_llm_response,
            "inputs_payload": excluded.inputs_payload,
            "outputs_payload": excluded.outputs_payload,
            "supporting_signals": excluded.supporting_signals,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _apply_common_filters(
    stmt: Select[Any],
    model: type[AgentReasoningModel]
    | type[AgentRecommendationModel]
    | type[AgentRiskAssessmentModel],
    *,
    agent_signal_id: str | None,
    workflow_name: str | None,
    execution_id: str | None,
    agent_name: str | None,
    agent_type: str | None,
    symbol: str | None,
    universe: str | None,
    start: datetime | None,
    end: datetime | None,
) -> Select[Any]:
    if agent_signal_id is not None:
        stmt = stmt.where(
            model.agent_signal_id == agent_signal_id,
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
    bundle: AgentIntelligencePersistenceBundle,
) -> str:
    for records in (
        bundle.reasoning,
        bundle.recommendations,
        bundle.risk_assessments,
    ):
        if records:
            return _record_id(records[0])

    return "empty-agent-intelligence-persistence-bundle"


def _record_id(
    record: AgentReasoningRecord
    | AgentRecommendationRecord
    | AgentRiskAssessmentRecord,
) -> str:
    if isinstance(record, AgentReasoningRecord):
        return record.reasoning_id
    if isinstance(record, AgentRecommendationRecord):
        return record.agent_recommendation_id

    return record.risk_assessment_id
