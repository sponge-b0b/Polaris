from __future__ import annotations
from domain.workflow_outputs import STRATEGY_SIDEWAYS_HYPOTHESIS_OUTPUT_CONTRACT
from domain.workflow_outputs import WORKFLOW_OUTPUT_SCHEMA_VERSION_V1

import pytest

from core.runtime.state.runtime_context import RuntimeContext
from intelligence.strategy.hypothesis.context import StrategyEvidenceContext
from intelligence.strategy.hypothesis.normalization import (
    normalize_strategy_evidence_context,
)
from intelligence.strategy.sideways.sideways_agent import SidewaysAgent
from intelligence.strategy.sideways.sideways_hypothesis_policy import (
    build_sideways_hypothesis,
)


@pytest.mark.asyncio
async def test_sideways_agent_produces_complete_structured_hypothesis() -> None:
    evidence_context = _sideways_evidence_context()
    agent = SidewaysAgent()

    output = await agent._execute(_runtime_context(evidence_context))

    hypothesis = output.outputs["strategy_hypothesis"]
    assert isinstance(hypothesis, dict)
    assert hypothesis["perspective"] == "sideways"
    assert hypothesis["evidence_fingerprint"] == evidence_context.evidence_fingerprint()
    assert output.outputs["directional_score"] == 0.0
    assert hypothesis["directional_bias"] == 0.0
    assert (
        hypothesis["hypothesis_strength"]
        == output.outputs["features"]["sideways_score"]
    )
    assert hypothesis["confidence"] == output.outputs["confidence"]
    assert hypothesis["supporting_evidence"]
    assert hypothesis["key_assumptions"]
    assert hypothesis["invalidation_conditions"]
    assert output.output_contract == STRATEGY_SIDEWAYS_HYPOTHESIS_OUTPUT_CONTRACT
    assert output.output_schema_version == WORKFLOW_OUTPUT_SCHEMA_VERSION_V1
    assert output.execution_metadata["evidence_fingerprint"] == (
        evidence_context.evidence_fingerprint()
    )

    supporting_ids = {item["evidence_id"] for item in hypothesis["supporting_evidence"]}
    assert "sentiment.directional_score" in supporting_ids
    assert "technical.directional_score" in supporting_ids


@pytest.mark.asyncio
async def test_sideways_agent_requires_strategy_evidence_builder_output() -> None:
    agent = SidewaysAgent()
    context = RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
        node_outputs={"sentiment_agent": {}, "technical_agent": {}},
    )

    with pytest.raises(ValueError, match="strategy_evidence_builder"):
        await agent._execute(context)


def test_sideways_policy_is_deterministic_across_serialized_replay() -> None:
    evidence_context = _sideways_evidence_context()
    replay_context = StrategyEvidenceContext.from_dict(evidence_context.to_dict())

    first = build_sideways_hypothesis(evidence_context)
    second = build_sideways_hypothesis(replay_context)

    assert first.hypothesis.to_canonical_json() == second.hypothesis.to_canonical_json()
    assert first.to_runtime_outputs() == second.to_runtime_outputs()


def test_sideways_policy_invalidates_trend_breakout_and_volatility_expansion() -> None:
    evidence_context = _breakout_evidence_context()

    decision = build_sideways_hypothesis(evidence_context)
    hypothesis = decision.hypothesis

    invalidated_ids = {
        condition.condition_id
        for condition in hypothesis.invalidation_conditions
        if condition.is_invalidated()
    }
    contradicting_ids = {item.evidence_id for item in hypothesis.contradicting_evidence}
    assert "sideways.trend_breakout" in invalidated_ids
    assert "sideways.volatility_expansion" in invalidated_ids
    assert "sideways.sentiment_directional_breakout" in invalidated_ids
    assert "sideways.technical_directional_breakout" in invalidated_ids
    assert "technical.trend_strength" in contradicting_ids
    assert "technical.volatility_score" in contradicting_ids
    assert hypothesis.directional_bias == 0.0
    assert hypothesis.hypothesis_strength >= 0.0
    assert hypothesis.invalidated is True
    assert decision.features["invalidated"] is True


def test_sideways_policy_surfaces_missing_optional_inputs_as_data_quality_flags() -> (
    None
):
    evidence_context = _sideways_evidence_context(include_optional=False)

    decision = build_sideways_hypothesis(evidence_context)

    assert "fundamental_agent:missing" in decision.hypothesis.data_quality_flags
    assert "news_agent:missing" in decision.hypothesis.data_quality_flags
    assert "portfolio_state_builder:missing" in decision.hypothesis.data_quality_flags


def _runtime_context(evidence_context: StrategyEvidenceContext) -> RuntimeContext:
    return RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
        node_outputs={
            "strategy_evidence_builder": {
                "outputs": {
                    "strategy_evidence_context": evidence_context.to_dict(),
                    "evidence_fingerprint": evidence_context.evidence_fingerprint(),
                }
            }
        },
    )


def _sideways_evidence_context(
    *,
    include_optional: bool = True,
) -> StrategyEvidenceContext:
    node_outputs = _base_node_outputs(
        sentiment_score=0.03,
        technical_score=-0.02,
        momentum=0.04,
        divergence=0.08,
        technical_regime="sideways",
        trend_strength=0.22,
        volatility_score=0.20,
        breadth_score=0.04,
        breadth_risk_score=0.45,
        risk_pressure=0.30,
    )
    if include_optional:
        node_outputs.update(_optional_outputs(fundamental=0.01, news=-0.02))
    return normalize_strategy_evidence_context(
        node_outputs,
        symbol="SPY",
        as_of="2026-07-10T14:30:00Z",
    )


def _breakout_evidence_context() -> StrategyEvidenceContext:
    node_outputs = _base_node_outputs(
        sentiment_score=0.82,
        technical_score=0.86,
        momentum=0.80,
        divergence=0.02,
        technical_regime="bullish",
        trend_strength=0.88,
        volatility_score=0.82,
        breadth_score=0.58,
        breadth_risk_score=0.20,
        risk_pressure=0.20,
    )
    node_outputs.update(_optional_outputs(fundamental=0.45, news=0.40))
    return normalize_strategy_evidence_context(
        node_outputs,
        symbol="SPY",
        as_of="2026-07-10T14:30:00Z",
    )


def _base_node_outputs(
    *,
    sentiment_score: float,
    technical_score: float,
    momentum: float,
    divergence: float,
    technical_regime: str,
    trend_strength: float,
    volatility_score: float,
    breadth_score: float,
    breadth_risk_score: float,
    risk_pressure: float,
) -> dict[str, object]:
    return {
        "sentiment_agent": {
            "outputs": {
                "directional_score": sentiment_score,
                "confidence": 0.70,
                "features": {
                    "momentum": momentum,
                    "stability": 0.70,
                    "divergence": {"avg_divergence": divergence},
                },
            }
        },
        "technical_agent": {
            "outputs": {
                "directional_score": technical_score,
                "confidence": 0.72,
                "features": {
                    "regime": {"regime": technical_regime},
                    "trend": {"trend_strength": trend_strength},
                    "volatility": {
                        "volatility_score": volatility_score,
                        "volatility_regime": "normal",
                    },
                    "breadth_state": {
                        "has_breadth_data": True,
                        "breadth_regime": _breadth_regime(breadth_score),
                        "risk_regime": (
                            "elevated" if breadth_risk_score >= 0.65 else "stable"
                        ),
                        "breadth_score": breadth_score,
                        "breadth_risk_score": breadth_risk_score,
                        "participation_score": breadth_score,
                        "leadership_score": breadth_score,
                    },
                },
            }
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
    }


def _optional_outputs(*, fundamental: float, news: float) -> dict[str, object]:
    return {
        "fundamental_agent": {
            "outputs": {"directional_score": fundamental, "confidence": 0.58}
        },
        "news_agent": {"outputs": {"directional_score": news, "confidence": 0.55}},
        "portfolio_state_builder": {
            "outputs": {
                "confidence": 0.50,
                "features": {
                    "scale_factor": 0.55,
                    "status": "neutral",
                    "risk_features": {"portfolio_heat": 0.40},
                },
            }
        },
        "market_events": {
            "outputs": {
                "confidence": 0.60,
                "features": {
                    "event_pressure": 0.35,
                    "event_bias": "neutral",
                    "event_volatility": 0.30,
                },
            }
        },
    }


def _breadth_regime(value: float) -> str:
    if value >= 0.25:
        return "strong_breadth"
    if value <= -0.25:
        return "weak_breadth"
    return "neutral_breadth"
