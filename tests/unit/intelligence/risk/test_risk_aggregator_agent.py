from __future__ import annotations

import pytest

from core.runtime.state.runtime_context import RuntimeContext
from intelligence.risk.aggregation.risk_aggregator_agent import (
    RiskAggregatorAgent,
)


@pytest.mark.asyncio
async def test_risk_aggregator_agent_adds_weak_breadth_context() -> None:
    agent = RiskAggregatorAgent()

    baseline = await agent._execute(
        _context_with_breadth(
            breadth_state={
                "has_breadth_data": False,
            }
        )
    )
    output = await agent._execute(
        _context_with_breadth(
            breadth_state={
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
        )
    )

    baseline_features = baseline.outputs["features"]
    features = output.outputs["features"]

    assert features["breadth_context"]["breadth_regime"] == "weak_breadth"
    assert features["breadth_confirmation_score"] < 0.0
    assert features["breadth_risk_pressure"] > 0.5
    assert features["breadth_regime_modifier"] > 1.0
    assert "price_ad_divergence" in features["breadth_risk_flags"]
    assert features["breadth_pressure_adjustment"] > 0.0
    assert (
        features["adjusted_composite_risk"]
        > baseline_features["adjusted_composite_risk"]
    )
    assert (
        features["adjusted_risk_pressure"] > baseline_features["adjusted_risk_pressure"]
    )
    assert "breadth:weak_breadth" in output.outputs["signals"]
    assert "price_ad_divergence" in output.outputs["risks"]
    assert "weak_market_participation" in output.outputs["risks"]
    assert (
        "elevated_breadth_risk_increases_portfolio_risk"
        in output.outputs["recommendations"]
    )
    assert (
        "risk_regime_requires_breadth_divergence_review"
        in output.outputs["recommendations"]
    )


@pytest.mark.asyncio
async def test_risk_aggregator_agent_does_not_penalize_missing_breadth() -> None:
    agent = RiskAggregatorAgent()

    output = await agent._execute(
        _context_with_breadth(
            breadth_state={
                "has_breadth_data": False,
            }
        )
    )

    features = output.outputs["features"]
    assert features["breadth_context"]["has_breadth_data"] is False
    assert features["breadth_regime_modifier"] == 1.0
    assert features["breadth_pressure_adjustment"] == 0.0
    assert not any(
        signal.startswith("breadth:") for signal in output.outputs["signals"]
    )
    assert "price_ad_divergence" not in output.outputs["risks"]


@pytest.mark.asyncio
async def test_risk_aggregator_agent_credits_strong_breadth() -> None:
    agent = RiskAggregatorAgent()

    baseline = await agent._execute(
        _context_with_breadth(
            breadth_state={
                "has_breadth_data": False,
            }
        )
    )
    output = await agent._execute(
        _context_with_breadth(
            breadth_state={
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
        )
    )

    baseline_features = baseline.outputs["features"]
    features = output.outputs["features"]

    assert features["breadth_context"]["breadth_regime"] == "strong_breadth"
    assert features["breadth_confirmation_score"] > 0.0
    assert features["breadth_risk_pressure"] < 0.5
    assert features["breadth_regime_modifier"] < 1.0
    assert features["breadth_risk_flags"] == []
    assert features["breadth_pressure_adjustment"] < 0.0
    assert (
        features["adjusted_composite_risk"]
        < baseline_features["adjusted_composite_risk"]
    )
    assert (
        features["adjusted_risk_pressure"] < baseline_features["adjusted_risk_pressure"]
    )
    assert "breadth:strong_breadth" in output.outputs["signals"]
    assert "breadth_confirms_lower_risk_pressure" in output.outputs["recommendations"]


def _context_with_breadth(
    *,
    breadth_state: dict[str, object],
) -> RuntimeContext:
    return RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
        node_outputs={
            "risk_signal_builder": {
                "outputs": {
                    "features": {
                        "volatility_risk": 0.38,
                        "drawdown_risk": 0.30,
                        "exposure_risk": 0.24,
                        "composite_risk": 0.40,
                        "risk_pressure": 0.40,
                        "stability_score": 0.60,
                        "risk_regime": "neutral",
                        "risk_bias": "neutral",
                    },
                    "recommendations": [
                        "monitor_risk",
                    ],
                }
            },
            "technical_agent": {
                "outputs": {
                    "features": {
                        "regime": {
                            "regime": "neutral",
                            "directional_technical_score": 0.10,
                            "confidence": 0.50,
                            "execution_readiness": 0.50,
                            "signal_quality": 0.50,
                        },
                        "volatility": {
                            "volatility_score": 0.55,
                        },
                        "breadth_state": breadth_state,
                    }
                }
            },
        },
    )
