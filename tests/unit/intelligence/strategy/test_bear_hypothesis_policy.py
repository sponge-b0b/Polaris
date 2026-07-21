from __future__ import annotations

import pytest

from config.strategy_model_config import StrategyModelConfig
from core.runtime.state.runtime_context import RuntimeContext
from domain.workflow_outputs import (
    STRATEGY_BEAR_HYPOTHESIS_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)
from intelligence.strategy.bear.bear_agent import BearAgent
from intelligence.strategy.bear.bear_hypothesis_policy import build_bear_hypothesis
from intelligence.strategy.hypothesis.context import StrategyEvidenceContext
from intelligence.strategy.hypothesis.normalization import (
    normalize_strategy_evidence_context,
)


@pytest.mark.asyncio
async def test_bear_agent_produces_complete_structured_hypothesis() -> None:
    evidence_context = _bearish_evidence_context()
    agent = BearAgent(strategy_model_config=StrategyModelConfig())

    output = await agent._execute(_runtime_context(evidence_context))

    hypothesis = output.outputs["strategy_hypothesis"]
    assert isinstance(hypothesis, dict)
    assert hypothesis["perspective"] == "bear"
    assert hypothesis["evidence_fingerprint"] == evidence_context.evidence_fingerprint()
    assert hypothesis["directional_bias"] == output.outputs["directional_score"]
    assert hypothesis["hypothesis_strength"] == output.outputs["features"]["bear_score"]
    assert hypothesis["hypothesis_strength"] == abs(output.outputs["directional_score"])
    assert hypothesis["confidence"] == output.outputs["confidence"]
    assert hypothesis["supporting_evidence"]
    assert hypothesis["key_assumptions"]
    assert hypothesis["invalidation_conditions"]
    assert output.outputs["directional_score"] < 0.0
    assert output.output_contract == STRATEGY_BEAR_HYPOTHESIS_OUTPUT_CONTRACT
    assert output.output_schema_version == WORKFLOW_OUTPUT_SCHEMA_VERSION_V1
    assert output.execution_metadata["evidence_fingerprint"] == (
        evidence_context.evidence_fingerprint()
    )

    supporting_ids = {item["evidence_id"] for item in hypothesis["supporting_evidence"]}
    assert "sentiment.directional_score" in supporting_ids
    assert "technical.directional_score" in supporting_ids


@pytest.mark.asyncio
async def test_bear_agent_requires_strategy_evidence_builder_output() -> None:
    agent = BearAgent(strategy_model_config=StrategyModelConfig())
    context = RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
        node_outputs={"sentiment_agent": {}, "technical_agent": {}},
    )

    with pytest.raises(ValueError, match="strategy_evidence_builder"):
        await agent._execute(context)


def test_bear_policy_is_deterministic_across_serialized_replay() -> None:
    evidence_context = _bearish_evidence_context()
    replay_context = StrategyEvidenceContext.from_dict(evidence_context.to_dict())

    first = build_bear_hypothesis(evidence_context)
    second = build_bear_hypothesis(replay_context)

    assert first.hypothesis.to_canonical_json() == second.hypothesis.to_canonical_json()
    assert first.to_runtime_outputs() == second.to_runtime_outputs()


def test_bear_policy_marks_bullish_observations_as_contradicting_evidence() -> None:
    evidence_context = _bullish_reversal_evidence_context()

    decision = build_bear_hypothesis(evidence_context)
    hypothesis = decision.hypothesis

    contradicting_ids = {item.evidence_id for item in hypothesis.contradicting_evidence}
    invalidated_ids = {
        condition.condition_id
        for condition in hypothesis.invalidation_conditions
        if condition.is_invalidated()
    }
    assert "sentiment.directional_score" in contradicting_ids
    assert "technical.directional_score" in contradicting_ids
    assert "technical.breadth.confirmation_score" in contradicting_ids
    assert "bear.sentiment_reversal" in invalidated_ids
    assert "bear.technical_reversal" in invalidated_ids
    assert "bear.breadth_reacceleration" in invalidated_ids
    assert hypothesis.invalidated is True
    assert decision.features["invalidated"] is True


def test_bear_policy_surfaces_missing_optional_inputs_as_data_quality_flags() -> None:
    evidence_context = _bearish_evidence_context(include_optional=False)

    decision = build_bear_hypothesis(evidence_context)

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


def _bearish_evidence_context(
    *, include_optional: bool = True
) -> StrategyEvidenceContext:
    node_outputs = _base_node_outputs(
        sentiment_score=-0.62,
        technical_score=-0.68,
        momentum=-0.20,
        divergence=-0.08,
        technical_regime="bearish",
        volatility_score=0.72,
        breadth_score=-0.48,
        breadth_risk_score=0.78,
        risk_pressure=0.82,
    )
    if include_optional:
        node_outputs.update(_optional_outputs(fundamental=-0.42, news=-0.35))
    return normalize_strategy_evidence_context(
        node_outputs,
        symbol="SPY",
        as_of="2026-07-10T14:30:00Z",
    )


def _bullish_reversal_evidence_context() -> StrategyEvidenceContext:
    node_outputs = _base_node_outputs(
        sentiment_score=0.62,
        technical_score=0.68,
        momentum=0.20,
        divergence=0.08,
        technical_regime="bullish",
        volatility_score=0.28,
        breadth_score=0.58,
        breadth_risk_score=0.18,
        risk_pressure=0.10,
    )
    node_outputs.update(_optional_outputs(fundamental=0.42, news=0.35))
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
                    "stability": 0.45,
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
                    "trend": {"trend_strength": 0.45},
                    "volatility": {
                        "volatility_score": volatility_score,
                        "volatility_regime": "elevated",
                    },
                    "breadth_state": {
                        "has_breadth_data": True,
                        "breadth_regime": (
                            "strong_breadth" if breadth_score > 0 else "weak_breadth"
                        ),
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
                    "scale_factor": 0.45,
                    "status": "defensive",
                    "risk_features": {"portfolio_heat": 0.70},
                },
            }
        },
        "market_events": {
            "outputs": {
                "confidence": 0.60,
                "features": {
                    "event_pressure": 0.70,
                    "event_bias": "risk_off",
                    "event_volatility": 0.65,
                },
            }
        },
    }
