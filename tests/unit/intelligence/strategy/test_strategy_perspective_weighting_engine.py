from __future__ import annotations

import pytest

from core.runtime.state.runtime_context import RuntimeContext
from domain.workflow_outputs import (
    STRATEGY_PERSPECTIVE_WEIGHTS_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)
from intelligence.strategy.hypothesis.context import StrategyEvidenceContext
from intelligence.strategy.hypothesis.normalization import (
    normalize_strategy_evidence_context,
)
from intelligence.strategy.weighting.strategy_perspective_weighting_engine import (
    StrategyPerspectiveWeightingEngine,
    StrategyPerspectiveWeights,
    calculate_strategy_perspective_weights,
)


@pytest.mark.asyncio
async def test_strategy_perspective_weighting_engine_uses_shared_evidence_context() -> (
    None
):
    evidence_context = _evidence_context(direction=0.55, trend_strength=0.72)
    engine = StrategyPerspectiveWeightingEngine()

    output = await engine._execute(_runtime_context(evidence_context))

    features = output.outputs["features"]
    perspective_weights = output.outputs["strategy_perspective_weights"]
    assert output.outputs["directional_score"] == 0.0
    assert output.output_contract == STRATEGY_PERSPECTIVE_WEIGHTS_OUTPUT_CONTRACT
    assert output.output_schema_version == WORKFLOW_OUTPUT_SCHEMA_VERSION_V1
    assert output.execution_metadata["evidence_fingerprint"] == (
        evidence_context.evidence_fingerprint()
    )
    assert isinstance(features, dict)
    assert isinstance(perspective_weights, dict)
    assert features["evidence_fingerprint"] == evidence_context.evidence_fingerprint()
    assert "graph_votes" not in features
    assert features["bull_weight"] > features["bear_weight"]
    assert features["weights_sum"] == pytest.approx(1.0)
    assert perspective_weights["bull_weight"] == features["bull_weight"]
    assert perspective_weights["bear_weight"] == features["bear_weight"]
    assert perspective_weights["sideways_weight"] == features["sideways_weight"]


@pytest.mark.asyncio
async def test_strategy_perspective_weighting_engine_rejects_missing_builder() -> None:
    engine = StrategyPerspectiveWeightingEngine()
    context = RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
        node_outputs={"sentiment_agent": {}, "technical_agent": {}},
    )

    with pytest.raises(ValueError, match="strategy_evidence_builder"):
        await engine._execute(context)


def test_strategy_perspective_weights_are_deterministic_and_normalized() -> None:
    evidence_context = _evidence_context(direction=-0.48, trend_strength=0.68)
    replay_context = StrategyEvidenceContext.from_dict(evidence_context.to_dict())

    first = calculate_strategy_perspective_weights(evidence_context)
    second = calculate_strategy_perspective_weights(replay_context)

    assert first.to_dict() == second.to_dict()
    assert first.bull_weight + first.bear_weight + first.sideways_weight == (
        pytest.approx(1.0)
    )
    assert first.bear_weight > first.bull_weight


def test_strategy_perspective_weights_from_dict_round_trips_boundary_payload() -> None:
    weights = StrategyPerspectiveWeights.from_dict(
        {
            "bull_weight": 0.50,
            "bear_weight": 0.25,
            "sideways_weight": 0.25,
            "confidence": 0.77,
            "evidence_fingerprint": "fingerprint-1",
            "features": {"source": "test"},
        }
    )

    assert weights.to_dict() == {
        "bull_weight": 0.50,
        "bear_weight": 0.25,
        "sideways_weight": 0.25,
        "confidence": 0.77,
        "evidence_fingerprint": "fingerprint-1",
        "features": {"source": "test"},
    }


@pytest.mark.asyncio
async def test_strategy_perspective_weights_are_independent_of_hypothesis_outputs() -> (
    None
):
    evidence_context = _evidence_context(direction=0.10, trend_strength=0.18)
    engine = StrategyPerspectiveWeightingEngine()

    baseline = await engine._execute(_runtime_context(evidence_context))
    with_hypotheses = await engine._execute(
        _runtime_context(
            evidence_context,
            extra_node_outputs={
                "bull_agent": {"outputs": {"directional_score": 0.95}},
                "bear_agent": {"outputs": {"directional_score": -0.95}},
                "sideways_agent": {"outputs": {"directional_score": 0.0}},
            },
        )
    )

    assert (
        baseline.outputs["strategy_perspective_weights"]
        == with_hypotheses.outputs["strategy_perspective_weights"]
    )


def test_strategy_perspective_weights_can_prefer_sideways_without_directional_bias() -> (  # noqa: E501 - descriptive pytest node id
    None
):
    evidence_context = _evidence_context(
        direction=0.02,
        trend_strength=0.08,
        volatility_score=0.12,
        risk_pressure=0.10,
    )

    perspective_weights = calculate_strategy_perspective_weights(evidence_context)

    assert perspective_weights.sideways_weight > perspective_weights.bull_weight
    assert perspective_weights.sideways_weight > perspective_weights.bear_weight


def _runtime_context(
    evidence_context: StrategyEvidenceContext,
    *,
    extra_node_outputs: dict[str, object] | None = None,
) -> RuntimeContext:
    node_outputs: dict[str, object] = {
        "strategy_evidence_builder": {
            "outputs": {
                "strategy_evidence_context": evidence_context.to_dict(),
                "evidence_fingerprint": evidence_context.evidence_fingerprint(),
            }
        }
    }
    if extra_node_outputs:
        node_outputs.update(extra_node_outputs)
    return RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
        node_outputs=node_outputs,
    )


def _evidence_context(
    *,
    direction: float,
    trend_strength: float,
    volatility_score: float = 0.30,
    risk_pressure: float = 0.20,
) -> StrategyEvidenceContext:
    return normalize_strategy_evidence_context(
        {
            "sentiment_agent": {
                "outputs": {
                    "directional_score": direction,
                    "confidence": 0.70,
                    "features": {
                        "momentum": direction,
                        "stability": 0.65,
                        "divergence": {"avg_divergence": 0.05},
                    },
                }
            },
            "technical_agent": {
                "outputs": {
                    "directional_score": direction,
                    "confidence": 0.72,
                    "features": {
                        "regime": {"regime": _technical_regime(direction)},
                        "trend": {"trend_strength": trend_strength},
                        "volatility": {
                            "volatility_score": volatility_score,
                            "volatility_regime": "normal",
                        },
                        "breadth_state": {
                            "has_breadth_data": True,
                            "breadth_regime": _breadth_regime(direction),
                            "risk_regime": "stable",
                            "breadth_score": direction,
                            "breadth_risk_score": risk_pressure,
                            "participation_score": direction,
                            "leadership_score": direction,
                        },
                    },
                }
            },
            "fundamental_agent": {
                "outputs": {"directional_score": direction * 0.8, "confidence": 0.60}
            },
            "news_agent": {
                "outputs": {"directional_score": direction * 0.5, "confidence": 0.55}
            },
            "risk_aggregator_agent": {
                "outputs": {
                    "confidence": 0.65,
                    "features": {
                        "risk_pressure": risk_pressure,
                        "composite_risk": risk_pressure,
                    },
                }
            },
            "market_events": {
                "outputs": {
                    "confidence": 0.60,
                    "features": {
                        "event_pressure": direction * 0.25,
                        "event_bias": "bullish" if direction > 0 else "bearish",
                        "event_volatility": volatility_score,
                    },
                }
            },
        },
        symbol="SPY",
        as_of="2026-07-10T14:30:00Z",
    )


def _technical_regime(direction: float) -> str:
    if direction > 0.25:
        return "bullish"
    if direction < -0.25:
        return "bearish"
    return "sideways"


def _breadth_regime(value: float) -> str:
    if value >= 0.25:
        return "strong_breadth"
    if value <= -0.25:
        return "weak_breadth"
    return "neutral_breadth"
