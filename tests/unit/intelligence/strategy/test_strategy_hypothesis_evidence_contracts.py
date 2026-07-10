from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from typing import cast

from intelligence.strategy.hypothesis import StrategyAssumption
from intelligence.strategy.hypothesis import StrategyEvidenceItem
from intelligence.strategy.hypothesis import StrategyInvalidationCondition
from intelligence.strategy.hypothesis import StrategyInvalidationOperator
from intelligence.strategy.hypothesis import StrategyJsonScalar
from intelligence.strategy.hypothesis import StrategyPerspective
from intelligence.strategy.hypothesis import evaluate_invalidation_operator


def test_strategy_evidence_item_round_trips_deterministically() -> None:
    evidence = StrategyEvidenceItem(
        evidence_id="breadth.confirmation",
        source="technical_analysis",
        name="advance_decline_strength",
        observed_value=0.72,
        strength=0.81,
        reliability=0.77,
        supports=(StrategyPerspective.BULL,),
        contradicts=(StrategyPerspective.BEAR,),
        explanation="Breadth confirms the bullish case.",
    )

    assert StrategyEvidenceItem.from_dict(evidence.to_dict()) == evidence
    assert evidence.to_canonical_json() == (
        '{"contradicts":["bear"],"evidence_id":"breadth.confirmation",'
        '"explanation":"Breadth confirms the bullish case.","name":"advance_decline_strength",'
        '"observed_value":0.72,"reliability":0.77,"source":"technical_analysis",'
        '"strength":0.81,"supports":["bull"]}'
    )


def test_strategy_evidence_item_is_immutable_and_rejects_invalid_values() -> None:
    evidence = StrategyEvidenceItem(
        evidence_id="trend.score",
        source="technical_analysis",
        name="trend_score",
        observed_value=0.6,
        strength=0.5,
        reliability=0.5,
    )

    with pytest.raises(FrozenInstanceError):
        evidence.name = "mutated"  # type: ignore[misc]
    with pytest.raises(ValueError):
        StrategyEvidenceItem(
            evidence_id=" ",
            source="technical_analysis",
            name="trend_score",
            observed_value=0.6,
            strength=0.5,
            reliability=0.5,
        )
    with pytest.raises(ValueError):
        StrategyEvidenceItem(
            evidence_id="trend.score",
            source="technical_analysis",
            name="trend_score",
            observed_value=0.6,
            strength=1.1,
            reliability=0.5,
        )
    with pytest.raises(TypeError):
        StrategyEvidenceItem(
            evidence_id="trend.score",
            source="technical_analysis",
            name="trend_score",
            observed_value=cast(StrategyJsonScalar, {"not": "scalar"}),
            strength=0.5,
            reliability=0.5,
        )


def test_strategy_assumption_round_trips_deterministically() -> None:
    assumption = StrategyAssumption(
        assumption_id="risk.remains_contained",
        perspective=StrategyPerspective.BULL,
        description="Risk remains contained enough for upside participation.",
        confidence=0.64,
        evidence_ids=("risk.drawdown", "technical.breadth"),
    )

    assert StrategyAssumption.from_dict(assumption.to_dict()) == assumption
    assert assumption.to_canonical_json() == (
        '{"assumption_id":"risk.remains_contained","confidence":0.64,'
        '"description":"Risk remains contained enough for upside participation.",'
        '"evidence_ids":["risk.drawdown","technical.breadth"],"perspective":"bull"}'
    )


def test_strategy_assumption_rejects_invalid_perspective_and_confidence() -> None:
    with pytest.raises(ValueError, match="strategy perspective"):
        StrategyAssumption(
            assumption_id="invalid",
            perspective="neutral",  # type: ignore[arg-type]
            description="Invalid perspective.",
            confidence=0.5,
        )
    with pytest.raises(ValueError):
        StrategyAssumption(
            assumption_id="invalid",
            perspective=StrategyPerspective.BEAR,
            description="Invalid confidence.",
            confidence=1.5,
        )


@pytest.mark.parametrize(
    ("operator", "observed", "threshold", "expected"),
    (
        (StrategyInvalidationOperator.GREATER_THAN, 0.8, 0.7, True),
        (StrategyInvalidationOperator.GREATER_THAN_OR_EQUAL, 0.7, 0.7, True),
        (StrategyInvalidationOperator.LESS_THAN, 0.2, 0.3, True),
        (StrategyInvalidationOperator.LESS_THAN_OR_EQUAL, 0.3, 0.3, True),
        (StrategyInvalidationOperator.EQUAL, "risk_off", "risk_off", True),
        (StrategyInvalidationOperator.NOT_EQUAL, "risk_on", "risk_off", True),
        (StrategyInvalidationOperator.GREATER_THAN, 0.6, 0.7, False),
    ),
)
def test_invalidation_operator_evaluates_supported_comparisons(
    operator: StrategyInvalidationOperator,
    observed: float | str,
    threshold: float | str,
    expected: bool,
) -> None:
    assert (
        evaluate_invalidation_operator(
            observed_value=observed,
            operator=operator,
            threshold=threshold,
        )
        is expected
    )


def test_strategy_invalidation_condition_round_trips_and_evaluates() -> None:
    condition = StrategyInvalidationCondition(
        condition_id="risk.max_drawdown",
        perspective=StrategyPerspective.BULL,
        description="Bull case is invalidated if drawdown pressure is too high.",
        observed_value=0.18,
        operator=StrategyInvalidationOperator.GREATER_THAN_OR_EQUAL,
        threshold=0.15,
        evidence_id="risk.drawdown",
    )

    assert condition.is_invalidated() is True
    assert StrategyInvalidationCondition.from_dict(condition.to_dict()) == condition
    assert condition.to_canonical_json() == (
        '{"condition_id":"risk.max_drawdown","description":"Bull case is invalidated if drawdown pressure is too high.",'
        '"evidence_id":"risk.drawdown","invalidated":true,"observed_value":0.18,'
        '"operator":"gte","perspective":"bull","threshold":0.15}'
    )


def test_strategy_invalidation_condition_rejects_callback_like_or_nonscalar_thresholds() -> (
    None
):
    with pytest.raises(ValueError, match="invalidation operator"):
        StrategyInvalidationCondition(
            condition_id="invalid.operator",
            perspective=StrategyPerspective.BEAR,
            description="Invalid operator.",
            observed_value=0.2,
            operator="callback",  # type: ignore[arg-type]
            threshold=0.1,
        )
    with pytest.raises(TypeError):
        StrategyInvalidationCondition(
            condition_id="invalid.threshold",
            perspective=StrategyPerspective.BEAR,
            description="Invalid threshold.",
            observed_value=0.2,
            operator=StrategyInvalidationOperator.GREATER_THAN,
            threshold=cast(StrategyJsonScalar, {"not": "scalar"}),
        )
    with pytest.raises(TypeError):
        StrategyInvalidationCondition(
            condition_id="invalid.comparison",
            perspective=StrategyPerspective.BEAR,
            description="Invalid numeric comparison.",
            observed_value="risk_off",
            operator=StrategyInvalidationOperator.GREATER_THAN,
            threshold=0.1,
        )


def test_deserialization_rejects_missing_required_fields() -> None:
    with pytest.raises(KeyError, match="observed_value"):
        StrategyEvidenceItem.from_dict(
            {
                "evidence_id": "missing.value",
                "source": "technical_analysis",
                "name": "missing_value",
                "strength": 0.5,
                "reliability": 0.5,
                "supports": [],
                "contradicts": [],
            }
        )
