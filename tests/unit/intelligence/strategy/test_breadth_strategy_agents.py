from __future__ import annotations

import pytest

from config.strategy_model_config import StrategyModelConfig
from core.runtime.state.runtime_context import RuntimeContext
from intelligence.strategy.bear.bear_agent import BearAgent
from intelligence.strategy.bull.bull_agent import BullAgent
from intelligence.strategy.hypothesis.normalization import (
    normalize_strategy_evidence_context,
)
from intelligence.strategy.sideways.sideways_agent import SidewaysAgent

WEAK_BREADTH: dict[str, object] = {
    "has_breadth_data": True,
    "breadth_regime": "weak_breadth",
    "risk_regime": "elevated",
    "breadth_score": -0.52,
    "breadth_risk_score": 0.76,
    "participation_score": -0.41,
    "leadership_score": -0.38,
    "mcclellan_score": -0.45,
    "price_ad_divergence": True,
}

STRONG_BREADTH: dict[str, object] = {
    "has_breadth_data": True,
    "breadth_regime": "strong_breadth",
    "risk_regime": "stable",
    "breadth_score": 0.64,
    "breadth_risk_score": 0.24,
    "participation_score": 0.36,
    "leadership_score": 0.22,
    "mcclellan_score": 0.18,
    "price_ad_divergence": False,
}

MISSING_BREADTH: dict[str, object] = {
    "has_breadth_data": False,
}


@pytest.mark.asyncio
async def test_bull_agent_penalizes_weak_breadth_and_credits_strong_breadth() -> None:
    agent = BullAgent(strategy_model_config=StrategyModelConfig())

    baseline = await agent._execute(
        _context(
            sentiment_score=0.40,
            technical_score=0.40,
            breadth_state=MISSING_BREADTH,
        )
    )
    weak = await agent._execute(
        _context(
            sentiment_score=0.40,
            technical_score=0.40,
            breadth_state=WEAK_BREADTH,
        )
    )
    strong = await agent._execute(
        _context(
            sentiment_score=0.40,
            technical_score=0.40,
            breadth_state=STRONG_BREADTH,
        )
    )

    assert (
        weak.outputs["features"]["bull_score"]
        < baseline.outputs["features"]["bull_score"]
    )
    assert weak.outputs["features"]["breadth_score_modifier"] < 0.0
    assert weak.outputs["confidence"] < baseline.outputs["confidence"]
    assert "breadth_not_confirming_bullish_setup" in weak.outputs["risks"]
    assert "wait_for_breadth_confirmation" in weak.outputs["recommendations"]

    assert (
        strong.outputs["features"]["bull_score"]
        > baseline.outputs["features"]["bull_score"]
    )
    assert strong.outputs["features"]["breadth_score_modifier"] > 0.0
    assert "bullish_breadth_confirmation" in strong.outputs["signals"]
    assert "breadth_confirms_bullish_setup" in strong.outputs["recommendations"]


@pytest.mark.asyncio
async def test_bear_agent_credits_weak_breadth_and_penalizes_strong_breadth() -> None:
    agent = BearAgent(strategy_model_config=StrategyModelConfig())

    baseline = await agent._execute(
        _context(
            sentiment_score=-0.40,
            technical_score=-0.40,
            breadth_state=MISSING_BREADTH,
        )
    )
    weak = await agent._execute(
        _context(
            sentiment_score=-0.40,
            technical_score=-0.40,
            breadth_state=WEAK_BREADTH,
        )
    )
    strong = await agent._execute(
        _context(
            sentiment_score=-0.40,
            technical_score=-0.40,
            breadth_state=STRONG_BREADTH,
        )
    )

    assert (
        weak.outputs["features"]["bear_score"]
        > baseline.outputs["features"]["bear_score"]
    )
    assert weak.outputs["features"]["breadth_score_modifier"] > 0.0
    assert "bearish_breadth_confirmation" in weak.outputs["signals"]
    assert "breadth_confirms_defensive_bias" in weak.outputs["recommendations"]

    assert (
        strong.outputs["features"]["bear_score"]
        < baseline.outputs["features"]["bear_score"]
    )
    assert strong.outputs["features"]["breadth_score_modifier"] < 0.0
    assert "strong_breadth_countertrend_risk" in strong.outputs["risks"]
    assert (
        "reduce_bearish_conviction_until_breadth_weakens"
        in strong.outputs["recommendations"]
    )


@pytest.mark.asyncio
async def test_sideways_agent_credits_weak_or_divergent_breadth() -> None:
    agent = SidewaysAgent(strategy_model_config=StrategyModelConfig())

    baseline = await agent._execute(
        _context(
            sentiment_score=0.10,
            technical_score=0.10,
            breadth_state=MISSING_BREADTH,
        )
    )
    weak = await agent._execute(
        _context(
            sentiment_score=0.10,
            technical_score=0.10,
            breadth_state=WEAK_BREADTH,
        )
    )
    strong = await agent._execute(
        _context(
            sentiment_score=0.10,
            technical_score=0.10,
            breadth_state=STRONG_BREADTH,
        )
    )

    assert (
        weak.outputs["features"]["sideways_score"]
        > baseline.outputs["features"]["sideways_score"]
    )
    assert weak.outputs["features"]["breadth_score_modifier"] > 0.0
    assert "narrow_or_weak_breadth_supports_sideways_case" in weak.outputs["signals"]
    assert "breadth_uncertainty_risk" in weak.outputs["risks"]
    assert "wait_for_breadth_resolution" in weak.outputs["recommendations"]

    assert (
        strong.outputs["features"]["sideways_score"]
        < baseline.outputs["features"]["sideways_score"]
    )
    assert strong.outputs["features"]["breadth_score_modifier"] < 0.0
    assert (
        "avoid_fading_strong_breadth_without_price_confirmation"
        in strong.outputs["recommendations"]
    )


@pytest.mark.asyncio
async def test_strategy_agents_keep_missing_breadth_neutral() -> None:
    agents = (
        BullAgent(strategy_model_config=StrategyModelConfig()),
        BearAgent(strategy_model_config=StrategyModelConfig()),
        SidewaysAgent(strategy_model_config=StrategyModelConfig()),
    )

    for agent in agents:
        output = await agent._execute(
            _context(
                sentiment_score=0.10,
                technical_score=0.10,
                breadth_state=MISSING_BREADTH,
            )
        )

        features = output.outputs["features"]
        assert features["breadth_context"]["has_breadth_data"] is False
        assert features["breadth_score_modifier"] == 0.0
        assert features["breadth_confidence_modifier"] == 0.0
        assert features["breadth_risk_flags"] == []
        assert not any(
            signal.startswith("breadth:") for signal in output.outputs["signals"]
        )


def _context(
    *,
    sentiment_score: float,
    technical_score: float,
    breadth_state: dict[str, object],
) -> RuntimeContext:
    node_outputs: dict[str, object] = {
        "sentiment_agent": {
            "outputs": {
                "directional_score": sentiment_score,
                "confidence": 0.60,
                "features": {
                    "momentum": 0.10 if sentiment_score >= 0 else -0.10,
                    "stability": 0.50,
                    "divergence": {
                        "avg_divergence": 0.0,
                    },
                },
            }
        },
        "technical_agent": {
            "outputs": {
                "directional_score": technical_score,
                "confidence": 0.60,
                "features": {
                    "regime": {
                        "regime": "neutral",
                    },
                    "trend": {
                        "trend_strength": 0.40,
                    },
                    "volatility": {
                        "volatility_score": 0.30,
                        "volatility_regime": "normal",
                    },
                    "breadth_state": breadth_state,
                },
            }
        },
    }
    evidence_context = normalize_strategy_evidence_context(node_outputs)
    node_outputs["strategy_evidence_builder"] = {
        "outputs": {
            "strategy_evidence_context": evidence_context.to_dict(),
            "evidence_fingerprint": evidence_context.evidence_fingerprint(),
        }
    }
    return RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
        node_outputs=node_outputs,
    )
