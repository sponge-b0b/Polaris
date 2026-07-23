from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

import pytest

from application.rag.ingestion.curated_rag_models import CuratedRagSource
from application.rag.ingestion.rag_source_loaders import (
    CuratedRagSourceLoaderRegistry,
    StrategyRagSourceLoader,
)
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.rag import RagSourceEligibilityRecord
from core.storage.persistence.strategy import (
    StrategyHypothesisRecord,
    StrategyPersistenceBundle,
    StrategyPersistenceRepository,
    StrategySynthesisDecisionRecord,
)


@dataclass(slots=True)
class TrackingSourceLoader:
    source_tables: tuple[str, ...]
    calls: int = 0

    async def load(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> CuratedRagSource | None:
        self.calls += 1
        return None


class FakeStrategyRepository:
    def __init__(self) -> None:
        self.hypothesis = StrategyHypothesisRecord(
            hypothesis_id="strategy-hypothesis-1",
            symbol="SPY",
            perspective="bull",
            thesis="Bull hypothesis is supported by breadth.",
            directional_bias=0.6,
            hypothesis_strength=0.7,
            confidence=0.8,
            evidence_fingerprint="fingerprint-1",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            lineage=PersistenceLineage(execution_id="execution-1"),
        )
        decision = StrategySynthesisDecisionRecord(
            decision_id="strategy-decision-1",
            symbol="SPY",
            selection_status="selected",
            directional_score=0.6,
            confidence=0.8,
            regime="risk_on",
            uncertainty=0.2,
            thesis="Bull decision is supported by breadth.",
            evidence_fingerprint="fingerprint-1",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            lineage=PersistenceLineage(execution_id="execution-1"),
            selected_perspective="bull",
        )
        self.bundle = StrategyPersistenceBundle(
            decision=decision,
            hypotheses=(self.hypothesis,),
        )

    async def get_hypothesis(
        self,
        hypothesis_id: str,
    ) -> StrategyHypothesisRecord | None:
        if hypothesis_id == self.hypothesis.hypothesis_id:
            return self.hypothesis
        return None

    async def get_decision_bundle(
        self,
        decision_id: str,
    ) -> StrategyPersistenceBundle | None:
        if decision_id == self.bundle.decision.decision_id:
            return self.bundle
        return None


def test_registry_routes_source_to_registered_typed_loader() -> None:
    loader = TrackingSourceLoader(source_tables=("reports",))
    registry = CuratedRagSourceLoaderRegistry((loader,))

    result = asyncio.run(registry.load(_eligibility("reports")))

    assert result is None
    assert loader.calls == 1


def test_registry_returns_none_for_unregistered_source_table() -> None:
    loader = TrackingSourceLoader(source_tables=("reports",))
    registry = CuratedRagSourceLoaderRegistry((loader,))

    result = asyncio.run(registry.load(_eligibility("agent_signals")))

    assert result is None
    assert loader.calls == 0


def test_registry_rejects_duplicate_source_table_ownership() -> None:
    first = TrackingSourceLoader(source_tables=("reports",))
    second = TrackingSourceLoader(source_tables=("reports",))

    with pytest.raises(
        ValueError,
        match="Duplicate curated RAG source loader for 'reports'",
    ):
        CuratedRagSourceLoaderRegistry((first, second))


def test_strategy_loader_resolves_hypotheses_and_decision_bundles() -> None:
    repository = FakeStrategyRepository()
    loader = StrategyRagSourceLoader(cast(StrategyPersistenceRepository, repository))

    hypothesis = asyncio.run(
        loader.load(
            RagSourceEligibilityRecord(
                eligibility_id="eligibility-hypothesis",
                source_table="strategy_hypotheses",
                source_id="strategy-hypothesis-1",
                source_type="strategy_hypothesis",
                eligible=True,
                reason="test",
                quality_score=1.0,
                reviewed_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
    )
    decision_bundle = asyncio.run(
        loader.load(
            RagSourceEligibilityRecord(
                eligibility_id="eligibility-decision",
                source_table="strategy_synthesis_decisions",
                source_id="strategy-decision-1",
                source_type="strategy_synthesis_decision",
                eligible=True,
                reason="test",
                quality_score=1.0,
                reviewed_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
    )

    assert hypothesis == repository.hypothesis
    assert decision_bundle == repository.bundle


def _eligibility(source_table: str) -> RagSourceEligibilityRecord:
    return RagSourceEligibilityRecord(
        eligibility_id="eligibility-1",
        source_table=source_table,
        source_id="source-1",
        source_type="test",
        eligible=True,
        reason="test",
        quality_score=1.0,
        reviewed_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )
