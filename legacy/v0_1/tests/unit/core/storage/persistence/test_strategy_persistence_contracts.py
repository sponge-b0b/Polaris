from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.strategy import (
    StrategyPersistenceBundle,
    StrategyPersistenceResult,
    StrategySynthesisDecisionRecord,
    new_strategy_decision_id,
    new_strategy_evaluation_id,
    new_strategy_hypothesis_id,
)
from tests.unit.core.storage.persistence.strategy_fixtures import (
    strategy_evaluation,
    strategy_hypothesis,
    strategy_synthesis_decision,
)


def test_strategy_hypothesis_record_normalizes_identity_without_losing_precision() -> (
    None
):
    record = strategy_hypothesis(symbol="spy")

    assert record.symbol == "SPY"
    assert record.directional_bias == 0.612345678901
    assert record.hypothesis_strength == 0.812345678901
    assert record.confidence == 0.732345678901
    assert record.supporting_evidence[0]["observed_value"] == 0.712345678901
    assert record.lineage.execution_id == "exec-1"
    assert record.metadata["source_node_output_id"] == "node-output-1"


def test_strategy_records_are_immutable_typed_internal_contracts() -> None:
    record = strategy_synthesis_decision()

    with pytest.raises(FrozenInstanceError):
        record.symbol = "QQQ"  # type: ignore[misc]


def test_strategy_evaluation_record_preserves_decision_lineage_and_rank() -> None:
    record = strategy_evaluation()

    assert record.evaluation_id == "decision-1:evaluation:bull"
    assert record.decision_id == "decision-1"
    assert record.hypothesis_id == "hypothesis-1"
    assert record.rank == 1
    assert record.synthesis_weight == 0.684567890123
    assert record.degraded_reasons == ("market_events_partial",)


def test_strategy_persistence_bundle_groups_complete_lineage() -> None:
    hypothesis = strategy_hypothesis()
    decision = strategy_synthesis_decision()
    evaluation = strategy_evaluation()

    bundle = StrategyPersistenceBundle(
        decision=decision,
        hypotheses=(hypothesis,),
        evaluations=(evaluation,),
    )

    assert bundle.decision.decision_id == "decision-1"
    assert bundle.hypotheses[0].evidence_fingerprint == "fingerprint-1"
    assert bundle.evaluations[0].hypothesis_id == "hypothesis-1"


def test_strategy_persistence_result_requires_error_for_failed_result() -> None:
    result = StrategyPersistenceResult.succeeded(
        decision_id="decision-1",
        records_persisted=3,
    )

    assert result.success is True
    assert result.records_persisted == 3

    with pytest.raises(ValueError):
        StrategyPersistenceResult(success=False)


def test_strategy_id_helpers_create_stable_execution_scoped_ids() -> None:
    assert (
        new_strategy_hypothesis_id(
            symbol="spy",
            perspective="bull",
            evidence_fingerprint="fingerprint-1",
            execution_id="exec-1",
        )
        == "strategy_hypothesis:exec-1:SPY:bull:fingerprint-1"
    )
    assert (
        new_strategy_decision_id(
            symbol="spy",
            evidence_fingerprint="fingerprint-1",
            execution_id="exec-1",
            decision_key="primary",
        )
        == "strategy_decision:exec-1:SPY:primary:fingerprint-1"
    )
    assert (
        new_strategy_evaluation_id(
            decision_id="decision-1",
            perspective="bull",
        )
        == "decision-1:evaluation:bull"
    )


def test_strategy_record_score_validation() -> None:
    with pytest.raises(ValueError, match="directional_score"):
        StrategySynthesisDecisionRecord(
            decision_id="decision-1",
            symbol="spy",
            selection_status="selected",
            directional_score=1.5,
            confidence=0.75,
            regime="risk_on",
            uncertainty=0.25,
            thesis="Invalid score.",
            evidence_fingerprint="fingerprint-1",
            created_at=datetime(2026, 5, 31, 13, 0, tzinfo=UTC),
            lineage=PersistenceLineage(execution_id="exec-1"),
        )
