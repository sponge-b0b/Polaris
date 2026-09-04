from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.strategy import (
    StrategyHypothesisEvaluationModel,
    StrategyHypothesisModel,
    StrategySynthesisDecisionModel,
)
from core.storage.persistence.serializers.strategy_persistence_serializer import (
    StrategyPersistenceSerializer,
)
from core.storage.persistence.strategy import (
    StrategyHypothesisEvaluationRecord,
    StrategyHypothesisPersistenceResult,
    StrategyHypothesisRecord,
    StrategyPersistenceBundle,
    StrategyPersistenceRepository,
    StrategyPersistenceResult,
    StrategySynthesisDecisionRecord,
)


class PostgresStrategyPersistenceRepository(StrategyPersistenceRepository):
    """PostgreSQL adapter for durable curated strategy persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def persist_strategy_bundle(
        self,
        bundle: StrategyPersistenceBundle,
    ) -> StrategyPersistenceResult:
        try:
            for hypothesis in bundle.hypotheses:
                await self._session.execute(_upsert_hypothesis_statement(hypothesis))
            await self._session.execute(_upsert_decision_statement(bundle.decision))
            for evaluation in bundle.evaluations:
                await self._session.execute(_upsert_evaluation_statement(evaluation))
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            return StrategyPersistenceResult.failed(str(exc))

        return StrategyPersistenceResult.succeeded(
            decision_id=bundle.decision.decision_id,
            records_persisted=1 + len(bundle.hypotheses) + len(bundle.evaluations),
        )

    async def persist_hypotheses(
        self,
        hypotheses: Sequence[StrategyHypothesisRecord],
    ) -> StrategyHypothesisPersistenceResult:
        records = tuple(hypotheses)
        if not records:
            return StrategyHypothesisPersistenceResult.failed(
                "No strategy hypotheses supplied for persistence."
            )
        try:
            for hypothesis in records:
                await self._session.execute(_upsert_hypothesis_statement(hypothesis))
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            return StrategyHypothesisPersistenceResult.failed(str(exc))

        return StrategyHypothesisPersistenceResult.succeeded(
            hypothesis_ids=tuple(record.hypothesis_id for record in records),
            records_persisted=len(records),
        )

    async def get_hypothesis(
        self,
        hypothesis_id: str,
    ) -> StrategyHypothesisRecord | None:
        stmt = select(StrategyHypothesisModel).where(
            StrategyHypothesisModel.hypothesis_id == hypothesis_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return StrategyPersistenceSerializer.hypothesis_from_model(model)

    async def get_decision(
        self,
        decision_id: str,
    ) -> StrategySynthesisDecisionRecord | None:
        stmt = select(StrategySynthesisDecisionModel).where(
            StrategySynthesisDecisionModel.decision_id == decision_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return StrategyPersistenceSerializer.decision_from_model(model)

    async def get_decision_bundle(
        self,
        decision_id: str,
    ) -> StrategyPersistenceBundle | None:
        decision = await self.get_decision(decision_id)
        if decision is None:
            return None
        evaluations = await self.list_evaluations(decision_id=decision_id)
        hypothesis_ids = tuple(
            evaluation.hypothesis_id
            for evaluation in evaluations
            if evaluation.hypothesis_id is not None
        )
        hypotheses: list[StrategyHypothesisRecord] = []
        for hypothesis_id in hypothesis_ids:
            hypothesis = await self.get_hypothesis(hypothesis_id)
            if hypothesis is not None:
                hypotheses.append(hypothesis)
        return StrategyPersistenceBundle(
            decision=decision,
            hypotheses=tuple(hypotheses),
            evaluations=tuple(evaluations),
        )

    async def list_hypotheses(
        self,
        *,
        symbol: str | None = None,
        perspective: str | None = None,
        execution_id: str | None = None,
        evidence_fingerprint: str | None = None,
    ) -> Sequence[StrategyHypothesisRecord]:
        stmt = select(StrategyHypothesisModel)
        if symbol is not None:
            stmt = stmt.where(StrategyHypothesisModel.symbol == symbol.upper())
        if perspective is not None:
            stmt = stmt.where(StrategyHypothesisModel.perspective == perspective)
        if execution_id is not None:
            stmt = stmt.where(StrategyHypothesisModel.execution_id == execution_id)
        if evidence_fingerprint is not None:
            stmt = stmt.where(
                StrategyHypothesisModel.evidence_fingerprint == evidence_fingerprint,
            )
        stmt = stmt.order_by(
            StrategyHypothesisModel.created_at.desc(),
            StrategyHypothesisModel.hypothesis_id,
        )
        result = await self._session.execute(stmt)
        return tuple(
            StrategyPersistenceSerializer.hypothesis_from_model(model)
            for model in result.scalars().all()
        )

    async def list_decisions(
        self,
        *,
        symbol: str | None = None,
        selection_status: str | None = None,
        execution_id: str | None = None,
        evidence_fingerprint: str | None = None,
    ) -> Sequence[StrategySynthesisDecisionRecord]:
        stmt = select(StrategySynthesisDecisionModel)
        if symbol is not None:
            stmt = stmt.where(StrategySynthesisDecisionModel.symbol == symbol.upper())
        if selection_status is not None:
            stmt = stmt.where(
                StrategySynthesisDecisionModel.selection_status == selection_status,
            )
        if execution_id is not None:
            stmt = stmt.where(
                StrategySynthesisDecisionModel.execution_id == execution_id,
            )
        if evidence_fingerprint is not None:
            stmt = stmt.where(
                StrategySynthesisDecisionModel.evidence_fingerprint
                == evidence_fingerprint,
            )
        stmt = stmt.order_by(
            StrategySynthesisDecisionModel.created_at.desc(),
            StrategySynthesisDecisionModel.decision_id,
        )
        result = await self._session.execute(stmt)
        return tuple(
            StrategyPersistenceSerializer.decision_from_model(model)
            for model in result.scalars().all()
        )

    async def list_evaluations(
        self,
        *,
        decision_id: str | None = None,
        hypothesis_id: str | None = None,
        symbol: str | None = None,
        perspective: str | None = None,
        execution_id: str | None = None,
    ) -> Sequence[StrategyHypothesisEvaluationRecord]:
        stmt = select(StrategyHypothesisEvaluationModel)
        if decision_id is not None:
            stmt = stmt.where(
                StrategyHypothesisEvaluationModel.decision_id == decision_id
            )
        if hypothesis_id is not None:
            stmt = stmt.where(
                StrategyHypothesisEvaluationModel.hypothesis_id == hypothesis_id,
            )
        if symbol is not None:
            stmt = stmt.where(
                StrategyHypothesisEvaluationModel.symbol == symbol.upper()
            )
        if perspective is not None:
            stmt = stmt.where(
                StrategyHypothesisEvaluationModel.perspective == perspective
            )
        if execution_id is not None:
            stmt = stmt.where(
                StrategyHypothesisEvaluationModel.execution_id == execution_id,
            )
        stmt = stmt.order_by(
            StrategyHypothesisEvaluationModel.rank,
            StrategyHypothesisEvaluationModel.evaluation_id,
        )
        result = await self._session.execute(stmt)
        return tuple(
            StrategyPersistenceSerializer.evaluation_from_model(model)
            for model in result.scalars().all()
        )


def _upsert_hypothesis_statement(record: StrategyHypothesisRecord) -> Any:
    values = StrategyPersistenceSerializer.hypothesis_values(record)
    stmt = insert(StrategyHypothesisModel).values(**values)
    excluded = stmt.excluded
    return stmt.on_conflict_do_update(
        index_elements=["hypothesis_id"],
        set_={
            "symbol": excluded.symbol,
            "perspective": excluded.perspective,
            "thesis": excluded.thesis,
            "directional_bias": excluded.directional_bias,
            "hypothesis_strength": excluded.hypothesis_strength,
            "confidence": excluded.confidence,
            "evidence_fingerprint": excluded.evidence_fingerprint,
            "invalidated": excluded.invalidated,
            "horizon": excluded.horizon,
            "as_of": excluded.as_of,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "created_at": excluded.created_at,
            "supporting_evidence": excluded.supporting_evidence,
            "contradicting_evidence": excluded.contradicting_evidence,
            "key_assumptions": excluded.key_assumptions,
            "invalidation_conditions": excluded.invalidation_conditions,
            "risks": excluded.risks,
            "recommendations": excluded.recommendations,
            "data_quality_flags": excluded.data_quality_flags,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _upsert_decision_statement(record: StrategySynthesisDecisionRecord) -> Any:
    values = StrategyPersistenceSerializer.decision_values(record)
    stmt = insert(StrategySynthesisDecisionModel).values(**values)
    excluded = stmt.excluded
    return stmt.on_conflict_do_update(
        index_elements=["decision_id"],
        set_={
            "symbol": excluded.symbol,
            "selected_perspective": excluded.selected_perspective,
            "selection_status": excluded.selection_status,
            "directional_score": excluded.directional_score,
            "confidence": excluded.confidence,
            "regime": excluded.regime,
            "uncertainty": excluded.uncertainty,
            "thesis": excluded.thesis,
            "evidence_fingerprint": excluded.evidence_fingerprint,
            "horizon": excluded.horizon,
            "as_of": excluded.as_of,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "created_at": excluded.created_at,
            "signals": excluded.signals,
            "risks": excluded.risks,
            "recommendations": excluded.recommendations,
            "degraded_reasons": excluded.degraded_reasons,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _upsert_evaluation_statement(record: StrategyHypothesisEvaluationRecord) -> Any:
    values = StrategyPersistenceSerializer.evaluation_values(record)
    stmt = insert(StrategyHypothesisEvaluationModel).values(**values)
    excluded = stmt.excluded
    return stmt.on_conflict_do_update(
        index_elements=["evaluation_id"],
        set_={
            "decision_id": excluded.decision_id,
            "hypothesis_id": excluded.hypothesis_id,
            "symbol": excluded.symbol,
            "perspective": excluded.perspective,
            "perspective_weight": excluded.perspective_weight,
            "contradiction_burden": excluded.contradiction_burden,
            "assumption_support": excluded.assumption_support,
            "invalidated": excluded.invalidated,
            "candidate_score": excluded.candidate_score,
            "synthesis_weight": excluded.synthesis_weight,
            "rank": excluded.rank,
            "selection_status": excluded.selection_status,
            "evidence_fingerprint": excluded.evidence_fingerprint,
            "horizon": excluded.horizon,
            "as_of": excluded.as_of,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "created_at": excluded.created_at,
            "degraded_reasons": excluded.degraded_reasons,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )
