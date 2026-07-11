from __future__ import annotations

import pytest

from intelligence.strategy.hypothesis import StrategyPerspective
from intelligence.strategy.synthesis import StrategyHypothesisEvaluation
from intelligence.strategy.synthesis import StrategySynthesisDecision
from intelligence.strategy.synthesis import StrategySynthesisDegradedReason
from intelligence.strategy.synthesis import StrategySynthesisSelectionStatus
from intelligence.strategy.synthesis import normalize_strategy_hypothesis_evaluations


def test_strategy_hypothesis_evaluations_normalize_to_synthesis_weights_and_selection() -> (
    None
):
    evaluations = normalize_strategy_hypothesis_evaluations(
        (
            _evaluation(StrategyPerspective.BULL, score=0.60),
            _evaluation(StrategyPerspective.BEAR, score=0.20),
            _evaluation(StrategyPerspective.SIDEWAYS, score=0.20),
        )
    )

    by_perspective = {item.perspective: item for item in evaluations}

    assert by_perspective[StrategyPerspective.BULL].selection_status is (
        StrategySynthesisSelectionStatus.SELECTED
    )
    assert by_perspective[StrategyPerspective.BULL].synthesis_weight == pytest.approx(
        0.60
    )
    assert by_perspective[StrategyPerspective.BEAR].synthesis_weight == pytest.approx(
        0.20
    )
    assert by_perspective[StrategyPerspective.SIDEWAYS].synthesis_weight == (
        pytest.approx(0.20)
    )
    assert sum(item.synthesis_weight for item in evaluations) == pytest.approx(1.0)
    assert by_perspective[StrategyPerspective.BULL].rank == 1
    assert by_perspective[StrategyPerspective.BEAR].rank == 2
    assert by_perspective[StrategyPerspective.SIDEWAYS].rank == 2


def test_strategy_synthesis_decision_marks_all_invalidated_as_degraded() -> None:
    decision = StrategySynthesisDecision.from_evaluations(
        evaluations=(
            _evaluation(StrategyPerspective.BULL, score=0.70, invalidated=True),
            _evaluation(StrategyPerspective.BEAR, score=0.20, invalidated=True),
            _evaluation(StrategyPerspective.SIDEWAYS, score=0.10, invalidated=True),
        ),
        directional_score=0.0,
        confidence=0.25,
        regime="neutral",
        uncertainty=1.0,
        thesis="No hypothesis is currently valid.",
    )

    assert decision.selected_perspective is None
    assert decision.selection_status is StrategySynthesisSelectionStatus.DEGRADED
    assert StrategySynthesisDegradedReason.ALL_HYPOTHESES_INVALIDATED in (
        decision.degraded_reasons
    )
    assert all(
        evaluation.selection_status is StrategySynthesisSelectionStatus.INVALIDATED
        for evaluation in decision.evaluations
    )
    assert sum(item.synthesis_weight for item in decision.evaluations) == 0.0


def test_strategy_synthesis_decision_models_tied_candidates_as_degraded() -> None:
    decision = StrategySynthesisDecision.from_evaluations(
        evaluations=(
            _evaluation(StrategyPerspective.BULL, score=0.50),
            _evaluation(StrategyPerspective.BEAR, score=0.50),
            _evaluation(StrategyPerspective.SIDEWAYS, score=0.10),
        ),
        directional_score=0.0,
        confidence=0.45,
        regime="neutral",
        uncertainty=0.70,
        thesis="Top candidates are tied.",
    )

    tied = tuple(
        evaluation
        for evaluation in decision.evaluations
        if evaluation.selection_status is StrategySynthesisSelectionStatus.TIED
    )

    assert decision.selected_perspective is None
    assert decision.selection_status is StrategySynthesisSelectionStatus.DEGRADED
    assert StrategySynthesisDegradedReason.TIED_CANDIDATES in decision.degraded_reasons
    assert {item.perspective for item in tied} == {
        StrategyPerspective.BULL,
        StrategyPerspective.BEAR,
    }


def test_strategy_synthesis_decision_serializes_and_replays_deterministically() -> None:
    decision = StrategySynthesisDecision.from_evaluations(
        evaluations=(
            _evaluation(StrategyPerspective.BULL, score=0.65),
            _evaluation(StrategyPerspective.BEAR, score=0.15),
            _evaluation(StrategyPerspective.SIDEWAYS, score=0.20),
        ),
        directional_score=0.42,
        confidence=0.74,
        regime="risk_on",
        uncertainty=0.26,
        thesis="Bull case has the strongest adjusted candidate score.",
        signals=("bull_selected",),
        risks=("watch_contradictions",),
        recommendations=("favor_quality_long_exposure",),
    )

    replayed = StrategySynthesisDecision.from_dict(decision.to_dict())

    assert replayed == decision
    assert replayed.selected_perspective is StrategyPerspective.BULL
    assert replayed.to_canonical_json() == decision.to_canonical_json()


def _evaluation(
    perspective: StrategyPerspective,
    *,
    score: float,
    invalidated: bool = False,
) -> StrategyHypothesisEvaluation:
    return StrategyHypothesisEvaluation(
        perspective=perspective,
        perspective_weight=score,
        contradiction_burden=0.10,
        assumption_support=0.85,
        invalidated=invalidated,
        candidate_score=score,
        synthesis_weight=0.0,
        rank=0,
        selection_status=StrategySynthesisSelectionStatus.CANDIDATE,
    )
