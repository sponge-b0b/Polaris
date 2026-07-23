from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from core.storage.persistence.strategy.strategy_persistence_models import (
    StrategyHypothesisEvaluationRecord,
    StrategyHypothesisPersistenceResult,
    StrategyHypothesisRecord,
    StrategyPersistenceBundle,
    StrategyPersistenceResult,
    StrategySynthesisDecisionRecord,
)


class StrategyPersistenceRepository(Protocol):
    """Async repository contract for durable curated strategy persistence."""

    async def persist_strategy_bundle(
        self,
        bundle: StrategyPersistenceBundle,
    ) -> StrategyPersistenceResult: ...

    async def persist_hypotheses(
        self,
        hypotheses: Sequence[StrategyHypothesisRecord],
    ) -> StrategyHypothesisPersistenceResult: ...

    async def get_hypothesis(
        self,
        hypothesis_id: str,
    ) -> StrategyHypothesisRecord | None: ...

    async def get_decision(
        self,
        decision_id: str,
    ) -> StrategySynthesisDecisionRecord | None: ...

    async def get_decision_bundle(
        self,
        decision_id: str,
    ) -> StrategyPersistenceBundle | None: ...

    async def list_hypotheses(
        self,
        *,
        symbol: str | None = None,
        perspective: str | None = None,
        execution_id: str | None = None,
        evidence_fingerprint: str | None = None,
    ) -> Sequence[StrategyHypothesisRecord]: ...

    async def list_decisions(
        self,
        *,
        symbol: str | None = None,
        selection_status: str | None = None,
        execution_id: str | None = None,
        evidence_fingerprint: str | None = None,
    ) -> Sequence[StrategySynthesisDecisionRecord]: ...

    async def list_evaluations(
        self,
        *,
        decision_id: str | None = None,
        hypothesis_id: str | None = None,
        symbol: str | None = None,
        perspective: str | None = None,
        execution_id: str | None = None,
    ) -> Sequence[StrategyHypothesisEvaluationRecord]: ...
