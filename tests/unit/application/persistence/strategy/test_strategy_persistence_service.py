from __future__ import annotations

import os
from collections.abc import Sequence
from typing import cast

import pytest

os.environ.setdefault(
    "POLARIS_DATABASE_URL", "postgresql+asyncpg://localhost/polaris_test"
)

from application.persistence.strategy import (
    StrategyHypothesisEvaluationPersistenceFilters,
    StrategyHypothesisPersistenceFilters,
    StrategyPersistenceService,
    StrategySynthesisDecisionPersistenceFilters,
)
from core.storage.persistence.strategy import (
    StrategyHypothesisEvaluationRecord,
    StrategyHypothesisRecord,
    StrategyPersistenceBundle,
    StrategyPersistenceRepository,
    StrategyPersistenceResult,
    StrategySynthesisDecisionRecord,
)
from tests.unit.core.storage.persistence.strategy_fixtures import (
    strategy_evaluation,
    strategy_hypothesis,
    strategy_synthesis_decision,
)


class FakeStrategyRepository:
    def __init__(
        self,
        *,
        hypothesis: StrategyHypothesisRecord | None = None,
        decision: StrategySynthesisDecisionRecord | None = None,
        evaluations: Sequence[StrategyHypothesisEvaluationRecord] = (),
    ) -> None:
        self.bundle: StrategyPersistenceBundle | None = None
        self.hypothesis = hypothesis
        self.decision = decision
        self.evaluations = tuple(evaluations)
        self.hypothesis_filters: dict[str, str | None] | None = None
        self.decision_filters: dict[str, str | None] | None = None
        self.evaluation_filters: dict[str, str | None] | None = None

    async def persist_strategy_bundle(
        self,
        bundle: StrategyPersistenceBundle,
    ) -> StrategyPersistenceResult:
        self.bundle = bundle
        return StrategyPersistenceResult.succeeded(
            decision_id=bundle.decision.decision_id,
            records_persisted=1 + len(bundle.hypotheses) + len(bundle.evaluations),
        )

    async def get_hypothesis(
        self,
        hypothesis_id: str,
    ) -> StrategyHypothesisRecord | None:
        if self.hypothesis is None:
            return None
        if self.hypothesis.hypothesis_id != hypothesis_id:
            return None
        return self.hypothesis

    async def get_decision(
        self,
        decision_id: str,
    ) -> StrategySynthesisDecisionRecord | None:
        if self.decision is None:
            return None
        if self.decision.decision_id != decision_id:
            return None
        return self.decision

    async def get_decision_bundle(
        self,
        decision_id: str,
    ) -> StrategyPersistenceBundle | None:
        if self.decision is None or self.decision.decision_id != decision_id:
            return None
        return StrategyPersistenceBundle(
            decision=self.decision,
            hypotheses=(self.hypothesis,) if self.hypothesis is not None else (),
            evaluations=self.evaluations,
        )

    async def list_hypotheses(
        self,
        *,
        symbol: str | None = None,
        perspective: str | None = None,
        execution_id: str | None = None,
        evidence_fingerprint: str | None = None,
    ) -> Sequence[StrategyHypothesisRecord]:
        self.hypothesis_filters = {
            "symbol": symbol,
            "perspective": perspective,
            "execution_id": execution_id,
            "evidence_fingerprint": evidence_fingerprint,
        }
        if self.hypothesis is None:
            return ()
        return (self.hypothesis,)

    async def list_decisions(
        self,
        *,
        symbol: str | None = None,
        selection_status: str | None = None,
        execution_id: str | None = None,
        evidence_fingerprint: str | None = None,
    ) -> Sequence[StrategySynthesisDecisionRecord]:
        self.decision_filters = {
            "symbol": symbol,
            "selection_status": selection_status,
            "execution_id": execution_id,
            "evidence_fingerprint": evidence_fingerprint,
        }
        if self.decision is None:
            return ()
        return (self.decision,)

    async def list_evaluations(
        self,
        *,
        decision_id: str | None = None,
        hypothesis_id: str | None = None,
        symbol: str | None = None,
        perspective: str | None = None,
        execution_id: str | None = None,
    ) -> Sequence[StrategyHypothesisEvaluationRecord]:
        self.evaluation_filters = {
            "decision_id": decision_id,
            "hypothesis_id": hypothesis_id,
            "symbol": symbol,
            "perspective": perspective,
            "execution_id": execution_id,
        }
        return self.evaluations


@pytest.mark.asyncio
async def test_strategy_persistence_service_persists_typed_bundle() -> None:
    repository = FakeStrategyRepository()
    service = StrategyPersistenceService(
        cast(StrategyPersistenceRepository, repository)
    )

    result = await service.persist(
        strategy_synthesis_decision(),
        hypotheses=(strategy_hypothesis(),),
        evaluations=(strategy_evaluation(),),
    )

    assert result.success is True
    assert result.records_persisted == 3
    assert repository.bundle is not None
    assert repository.bundle.decision.decision_id == "decision-1"
    assert (
        repository.bundle.hypotheses[0].supporting_evidence[0]["source"] == "technical"
    )
    assert repository.bundle.evaluations[0].synthesis_weight == 0.684567890123


@pytest.mark.asyncio
async def test_strategy_persistence_service_persists_existing_bundle() -> None:
    repository = FakeStrategyRepository()
    service = StrategyPersistenceService(
        cast(StrategyPersistenceRepository, repository)
    )
    bundle = StrategyPersistenceBundle(
        decision=strategy_synthesis_decision(),
        hypotheses=(strategy_hypothesis(),),
    )

    result = await service.persist_bundle(bundle)

    assert result.success is True
    assert result.records_persisted == 2
    assert repository.bundle == bundle


@pytest.mark.asyncio
async def test_strategy_persistence_service_lists_hypotheses_with_typed_filters() -> (
    None
):
    repository = FakeStrategyRepository(hypothesis=strategy_hypothesis())
    service = StrategyPersistenceService(
        cast(StrategyPersistenceRepository, repository)
    )

    result = await service.list_hypotheses_result(
        StrategyHypothesisPersistenceFilters(
            symbol="spy",
            perspective="bull",
            execution_id="exec-1",
            evidence_fingerprint="fingerprint-1",
        )
    )

    assert len(result.records) == 1
    assert result.records[0].symbol == "SPY"
    assert result.query.metadata["record_type"] == "strategy_hypothesis"
    assert repository.hypothesis_filters == {
        "symbol": "spy",
        "perspective": "bull",
        "execution_id": "exec-1",
        "evidence_fingerprint": "fingerprint-1",
    }


@pytest.mark.asyncio
async def test_strategy_persistence_service_lists_decisions_with_typed_filters() -> (
    None
):
    repository = FakeStrategyRepository(decision=strategy_synthesis_decision())
    service = StrategyPersistenceService(
        cast(StrategyPersistenceRepository, repository)
    )

    result = await service.list_decisions_result(
        StrategySynthesisDecisionPersistenceFilters(
            symbol="spy",
            selection_status="selected",
            execution_id="exec-1",
            evidence_fingerprint="fingerprint-1",
        )
    )

    assert len(result.records) == 1
    assert result.records[0].selection_status == "selected"
    assert result.query.metadata["record_type"] == "strategy_synthesis_decision"
    assert repository.decision_filters == {
        "symbol": "spy",
        "selection_status": "selected",
        "execution_id": "exec-1",
        "evidence_fingerprint": "fingerprint-1",
    }


@pytest.mark.asyncio
async def test_strategy_persistence_service_lists_evaluation_lineage() -> None:
    repository = FakeStrategyRepository(evaluations=(strategy_evaluation(),))
    service = StrategyPersistenceService(
        cast(StrategyPersistenceRepository, repository)
    )

    result = await service.list_evaluations_result(
        StrategyHypothesisEvaluationPersistenceFilters(
            decision_id="decision-1",
            hypothesis_id="hypothesis-1",
            symbol="spy",
            perspective="bull",
            execution_id="exec-1",
        )
    )

    assert len(result.records) == 1
    assert result.records[0].evaluation_id == "decision-1:evaluation:bull"
    assert result.query.metadata["record_type"] == "strategy_hypothesis_evaluation"
    assert repository.evaluation_filters == {
        "decision_id": "decision-1",
        "hypothesis_id": "hypothesis-1",
        "symbol": "spy",
        "perspective": "bull",
        "execution_id": "exec-1",
    }
