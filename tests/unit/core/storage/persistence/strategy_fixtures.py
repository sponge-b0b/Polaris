from __future__ import annotations

from datetime import datetime
from datetime import timezone

from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.strategy import StrategyHypothesisEvaluationRecord
from core.storage.persistence.strategy import StrategyHypothesisRecord
from core.storage.persistence.strategy import StrategySynthesisDecisionRecord


def strategy_hypothesis(*, symbol: str = "spy") -> StrategyHypothesisRecord:
    return StrategyHypothesisRecord(
        hypothesis_id="hypothesis-1",
        symbol=symbol,
        perspective="bull",
        thesis="Bull case remains valid while breadth confirms leadership.",
        directional_bias=0.612345678901,
        hypothesis_strength=0.812345678901,
        confidence=0.732345678901,
        evidence_fingerprint="fingerprint-1",
        created_at=timestamp(),
        lineage=lineage(),
        horizon="swing",
        as_of=timestamp(),
        invalidated=False,
        supporting_evidence=(
            {
                "evidence_id": "e1",
                "source": "technical",
                "name": "trend",
                "observed_value": 0.712345678901,
            },
        ),
        contradicting_evidence=(
            {
                "evidence_id": "e2",
                "source": "risk",
                "name": "volatility",
                "observed_value": 0.421234567891,
            },
        ),
        key_assumptions=(
            {
                "assumption_id": "a1",
                "description": "Breadth remains supportive.",
            },
        ),
        invalidation_conditions=(
            {
                "condition_id": "i1",
                "operator": "lt",
                "threshold": 0.0,
                "observed_value": 0.2,
            },
        ),
        risks=("Volatility expansion",),
        recommendations=("Wait for confirmation",),
        data_quality_flags=("market_events_degraded",),
        metadata={"source_node_output_id": "node-output-1"},
    )


def strategy_synthesis_decision() -> StrategySynthesisDecisionRecord:
    return StrategySynthesisDecisionRecord(
        decision_id="decision-1",
        symbol="spy",
        selected_perspective="bull",
        selection_status="selected",
        directional_score=0.584567890123,
        confidence=0.764567890123,
        regime="risk_on",
        uncertainty=0.235432109877,
        thesis="Bullish synthesis selected with explicit invalidation criteria.",
        evidence_fingerprint="fingerprint-1",
        created_at=timestamp(),
        lineage=lineage(),
        horizon="swing",
        as_of=timestamp(),
        signals=("breadth_supportive", "trend_positive"),
        risks=("volatility_expansion",),
        recommendations=("increase_watchlist_priority",),
        degraded_reasons=("market_events_partial",),
        metadata={"decision_source": "strategy_synthesis"},
    )


def strategy_evaluation() -> StrategyHypothesisEvaluationRecord:
    return StrategyHypothesisEvaluationRecord(
        evaluation_id="decision-1:evaluation:bull",
        decision_id="decision-1",
        hypothesis_id="hypothesis-1",
        symbol="spy",
        perspective="bull",
        perspective_weight=0.42,
        contradiction_burden=0.128765432109,
        assumption_support=0.777654321098,
        invalidated=False,
        candidate_score=0.695678901234,
        synthesis_weight=0.684567890123,
        rank=1,
        selection_status="selected",
        evidence_fingerprint="fingerprint-1",
        created_at=timestamp(),
        lineage=lineage(),
        horizon="swing",
        as_of=timestamp(),
        degraded_reasons=("market_events_partial",),
        metadata={"selection_reason": "highest_synthesis_weight"},
    )


def lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="strategy_synthesis_agent",
    )


def timestamp() -> datetime:
    return datetime(2026, 5, 31, 13, 0, tzinfo=timezone.utc)
