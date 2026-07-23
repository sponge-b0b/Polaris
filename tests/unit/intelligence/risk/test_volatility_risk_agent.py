from __future__ import annotations

import pytest

from core.runtime.state.runtime_context import RuntimeContext
from domain.workflow_outputs import (
    RISK_VOLATILITY_SIGNAL_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)
from intelligence.risk.volatility.volatility_risk_agent import VolatilityRiskAgent
from intelligence.risk.volatility.volatility_risk_policy import (
    convert_volatility_score_to_risk,
)


def test_volatility_score_stable_reduces_market_volatility_risk() -> None:
    assert convert_volatility_score_to_risk(1.0) == 0.0


def test_volatility_score_dangerous_increases_market_volatility_risk() -> None:
    assert convert_volatility_score_to_risk(-1.0) == 1.0


def test_volatility_score_neutral_maps_to_mid_risk() -> None:
    assert convert_volatility_score_to_risk(0.0) == 0.5


@pytest.mark.asyncio
async def test_volatility_risk_agent_adds_weak_breadth_pressure() -> None:
    agent = VolatilityRiskAgent()

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

    features = output.outputs["features"]
    assert features["breadth_context"]["breadth_regime"] == "weak_breadth"
    assert features["breadth_confirmation_score"] < 0.0
    assert features["breadth_risk_pressure"] > 0.5
    assert features["breadth_risk_modifier"] > 0.0
    assert "price_ad_divergence" in features["breadth_risk_flags"]
    assert features["composite_risk"] > features["base_composite_risk"]
    assert "breadth:weak_breadth" in output.outputs["signals"]
    assert "price_ad_divergence" in output.outputs["risks"]
    assert "weak_market_participation" in output.outputs["risks"]
    assert (
        "deteriorating_breadth_increases_volatility_risk"
        in output.outputs["recommendations"]
    )
    assert (
        "validate_volatility_signal_with_breadth_confirmation"
        in output.outputs["recommendations"]
    )

    # Golden characterization: preserve the established risk calculation while
    # policy calculations move out of the runtime node.
    assert features["market_volatility_risk"] == pytest.approx(0.27299999999999996)
    assert features["base_composite_risk"] == pytest.approx(0.2897833333333333)
    assert features["composite_risk"] == pytest.approx(0.38978333333333326)
    assert features["stability_score"] == pytest.approx(0.6102166666666667)
    assert output.output_contract == RISK_VOLATILITY_SIGNAL_OUTPUT_CONTRACT
    assert output.output_schema_version == WORKFLOW_OUTPUT_SCHEMA_VERSION_V1
    assert features["composite_risk"] != round(
        features["composite_risk"],
        4,
    )


@pytest.mark.asyncio
async def test_volatility_risk_agent_does_not_penalize_missing_breadth() -> None:
    agent = VolatilityRiskAgent()

    output = await agent._execute(
        _context_with_breadth(
            breadth_state={
                "has_breadth_data": False,
            }
        )
    )

    features = output.outputs["features"]
    assert features["breadth_context"]["has_breadth_data"] is False
    assert features["breadth_risk_modifier"] == 0.0
    assert features["composite_risk"] == features["base_composite_risk"]
    assert not any(
        signal.startswith("breadth:") for signal in output.outputs["signals"]
    )
    assert "price_ad_divergence" not in output.outputs["risks"]


@pytest.mark.asyncio
async def test_volatility_risk_agent_credits_strong_breadth() -> None:
    agent = VolatilityRiskAgent()

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

    features = output.outputs["features"]
    assert features["breadth_context"]["breadth_regime"] == "strong_breadth"
    assert features["breadth_confirmation_score"] > 0.0
    assert features["breadth_risk_pressure"] < 0.5
    assert features["breadth_risk_modifier"] < 0.0
    assert features["breadth_risk_flags"] == []
    assert features["composite_risk"] < features["base_composite_risk"]
    assert "breadth:strong_breadth" in output.outputs["signals"]
    assert (
        "breadth_confirms_lower_volatility_pressure"
        in output.outputs["recommendations"]
    )


def _context_with_breadth(
    *,
    breadth_state: dict[str, object],
) -> RuntimeContext:
    return RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
        node_outputs={
            "portfolio_state_builder": {
                "outputs": {
                    "features": {
                        "portfolio_state": {
                            "gross_exposure": 0.85,
                            "leverage": 1.0,
                            "concentration_score": 0.25,
                            "largest_position_pct": 0.12,
                            "cash_pct": 0.20,
                        }
                    }
                }
            },
            "technical_agent": {
                "outputs": {
                    "features": {
                        "snapshot": {
                            "atr_14": 4.5,
                        },
                        "volatility": {
                            "atr_percent": 0.02,
                            "historical_volatility": 0.18,
                            "volatility_score": 0.25,
                            "volatility_regime": "normal",
                            "stability_state": "normal",
                        },
                        "breadth_state": breadth_state,
                    }
                }
            },
        },
    )
