from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from application.persistence.query_result_helpers import (
    build_common_query,
    build_list_result,
)
from core.storage.persistence.query import PersistenceListResult
from core.storage.persistence.strategy import (
    StrategyHypothesisEvaluationRecord,
    StrategyHypothesisPersistenceResult,
    StrategyHypothesisRecord,
    StrategyPersistenceBundle,
    StrategyPersistenceRepository,
    StrategyPersistenceResult,
    StrategySynthesisDecisionRecord,
)


@dataclass(frozen=True, slots=True)
class StrategyHypothesisPersistenceFilters:
    """Typed application-layer filters for strategy hypothesis retrieval."""

    symbol: str | None = None
    perspective: str | None = None
    execution_id: str | None = None
    evidence_fingerprint: str | None = None


@dataclass(frozen=True, slots=True)
class StrategySynthesisDecisionPersistenceFilters:
    """Typed application-layer filters for strategy synthesis decisions."""

    symbol: str | None = None
    selection_status: str | None = None
    execution_id: str | None = None
    evidence_fingerprint: str | None = None


@dataclass(frozen=True, slots=True)
class StrategyHypothesisEvaluationPersistenceFilters:
    """Typed application-layer filters for strategy evaluation lineage."""

    decision_id: str | None = None
    hypothesis_id: str | None = None
    symbol: str | None = None
    perspective: str | None = None
    execution_id: str | None = None


class StrategyPersistenceService:
    """
    Application service for curated strategy persistence.

    Runtime nodes and analytical services do not write strategy records directly.
    Projection/coordinator code may call this service once it has identified an
    eligible workflow output and converted it into typed strategy records.
    """

    def __init__(self, repository: StrategyPersistenceRepository) -> None:
        self._repository = repository

    async def persist_bundle(
        self,
        bundle: StrategyPersistenceBundle,
    ) -> StrategyPersistenceResult:
        return await self._repository.persist_strategy_bundle(bundle)

    async def persist_hypotheses(
        self,
        hypotheses: Sequence[StrategyHypothesisRecord],
    ) -> StrategyHypothesisPersistenceResult:
        return await self._repository.persist_hypotheses(tuple(hypotheses))

    async def persist(
        self,
        decision: StrategySynthesisDecisionRecord,
        *,
        hypotheses: Sequence[StrategyHypothesisRecord] = (),
        evaluations: Sequence[StrategyHypothesisEvaluationRecord] = (),
    ) -> StrategyPersistenceResult:
        return await self.persist_bundle(
            StrategyPersistenceBundle(
                decision=decision,
                hypotheses=tuple(hypotheses),
                evaluations=tuple(evaluations),
            )
        )

    async def get_hypothesis(
        self,
        hypothesis_id: str,
    ) -> StrategyHypothesisRecord | None:
        return await self._repository.get_hypothesis(hypothesis_id)

    async def get_decision(
        self,
        decision_id: str,
    ) -> StrategySynthesisDecisionRecord | None:
        return await self._repository.get_decision(decision_id)

    async def get_decision_bundle(
        self,
        decision_id: str,
    ) -> StrategyPersistenceBundle | None:
        return await self._repository.get_decision_bundle(decision_id)

    async def list_hypotheses(
        self,
        filters: StrategyHypothesisPersistenceFilters | None = None,
    ) -> Sequence[StrategyHypothesisRecord]:
        result = await self.list_hypotheses_result(filters)
        return result.records

    async def list_hypotheses_result(
        self,
        filters: StrategyHypothesisPersistenceFilters | None = None,
    ) -> PersistenceListResult[StrategyHypothesisRecord]:
        active_filters = filters or StrategyHypothesisPersistenceFilters()
        records = await self._repository.list_hypotheses(
            symbol=active_filters.symbol,
            perspective=active_filters.perspective,
            execution_id=active_filters.execution_id,
            evidence_fingerprint=active_filters.evidence_fingerprint,
        )
        query = build_common_query(
            record_type="strategy_hypothesis",
            symbol=active_filters.symbol,
            execution_id=active_filters.execution_id,
            metadata={
                "perspective": active_filters.perspective,
                "evidence_fingerprint": active_filters.evidence_fingerprint,
            },
        )
        return build_list_result(records, query=query)

    async def list_decisions(
        self,
        filters: StrategySynthesisDecisionPersistenceFilters | None = None,
    ) -> Sequence[StrategySynthesisDecisionRecord]:
        result = await self.list_decisions_result(filters)
        return result.records

    async def list_decisions_result(
        self,
        filters: StrategySynthesisDecisionPersistenceFilters | None = None,
    ) -> PersistenceListResult[StrategySynthesisDecisionRecord]:
        active_filters = filters or StrategySynthesisDecisionPersistenceFilters()
        records = await self._repository.list_decisions(
            symbol=active_filters.symbol,
            selection_status=active_filters.selection_status,
            execution_id=active_filters.execution_id,
            evidence_fingerprint=active_filters.evidence_fingerprint,
        )
        query = build_common_query(
            record_type="strategy_synthesis_decision",
            symbol=active_filters.symbol,
            execution_id=active_filters.execution_id,
            metadata={
                "selection_status": active_filters.selection_status,
                "evidence_fingerprint": active_filters.evidence_fingerprint,
            },
        )
        return build_list_result(records, query=query)

    async def list_evaluations(
        self,
        filters: StrategyHypothesisEvaluationPersistenceFilters | None = None,
    ) -> Sequence[StrategyHypothesisEvaluationRecord]:
        result = await self.list_evaluations_result(filters)
        return result.records

    async def list_evaluations_result(
        self,
        filters: StrategyHypothesisEvaluationPersistenceFilters | None = None,
    ) -> PersistenceListResult[StrategyHypothesisEvaluationRecord]:
        active_filters = filters or StrategyHypothesisEvaluationPersistenceFilters()
        records = await self._repository.list_evaluations(
            decision_id=active_filters.decision_id,
            hypothesis_id=active_filters.hypothesis_id,
            symbol=active_filters.symbol,
            perspective=active_filters.perspective,
            execution_id=active_filters.execution_id,
        )
        query = build_common_query(
            record_type="strategy_hypothesis_evaluation",
            symbol=active_filters.symbol,
            execution_id=active_filters.execution_id,
            metadata={
                "decision_id": active_filters.decision_id,
                "hypothesis_id": active_filters.hypothesis_id,
                "perspective": active_filters.perspective,
            },
        )
        return build_list_result(records, query=query)
