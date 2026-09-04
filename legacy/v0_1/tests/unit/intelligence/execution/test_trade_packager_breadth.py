from __future__ import annotations

import pytest

from core.runtime.state.runtime_context import RuntimeContext
from domain.authority import RiskTier
from intelligence.execution.trade_packaging.trade_packager import TradePackager

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
async def test_trade_packager_dampens_long_intent_when_breadth_is_weak() -> None:
    packager = TradePackager()

    baseline = await packager._execute(
        _context(
            sentiment_score=0.45,
            technical_score=0.45,
            breadth_state=MISSING_BREADTH,
        )
    )
    weak = await packager._execute(
        _context(
            sentiment_score=0.45,
            technical_score=0.45,
            breadth_state=WEAK_BREADTH,
        )
    )

    assert baseline.outputs["regime"] == "long"
    assert weak.outputs["directional_score"] < baseline.outputs["directional_score"]
    assert (
        weak.outputs["features"]["position_sizing_hint"]
        < baseline.outputs["features"]["position_sizing_hint"]
    )
    assert weak.outputs["features"]["breadth_entry_bias_modifier"] < 0.0
    assert weak.outputs["features"]["breadth_position_size_multiplier"] < 1.0
    assert "weak_breadth_dampens_long_trade_intent" in weak.outputs["signals"]
    assert "long_breadth_confirmation_failure" in weak.outputs["risks"]
    assert (
        "wait_for_breadth_confirmation_before_long_exposure"
        in weak.outputs["recommendations"]
    )


@pytest.mark.asyncio
async def test_trade_packager_dampens_short_intent_when_breadth_is_strong() -> None:
    packager = TradePackager()

    baseline = await packager._execute(
        _context(
            sentiment_score=-0.45,
            technical_score=-0.45,
            breadth_state=MISSING_BREADTH,
        )
    )
    strong = await packager._execute(
        _context(
            sentiment_score=-0.45,
            technical_score=-0.45,
            breadth_state=STRONG_BREADTH,
        )
    )

    assert baseline.outputs["regime"] == "short"
    assert strong.outputs["directional_score"] > baseline.outputs["directional_score"]
    assert (
        strong.outputs["features"]["position_sizing_hint"]
        < baseline.outputs["features"]["position_sizing_hint"]
    )
    assert strong.outputs["features"]["breadth_entry_bias_modifier"] > 0.0
    assert strong.outputs["features"]["breadth_position_size_multiplier"] < 1.0
    assert "strong_breadth_dampens_short_trade_intent" in strong.outputs["signals"]
    assert "short_against_strong_breadth_risk" in strong.outputs["risks"]
    assert (
        "avoid_short_bias_against_strong_breadth" in strong.outputs["recommendations"]
    )


@pytest.mark.asyncio
async def test_trade_packager_missing_breadth_is_neutral() -> None:
    packager = TradePackager()

    output = await packager._execute(
        _context(
            sentiment_score=0.45,
            technical_score=0.45,
            breadth_state=MISSING_BREADTH,
        )
    )

    features = output.outputs["features"]

    assert features["breadth_context"]["has_breadth_data"] is False
    assert features["breadth_entry_bias_modifier"] == 0.0
    assert features["breadth_position_size_multiplier"] == 1.0
    assert features["breadth_risk_flags"] == []
    assert not any(
        signal.startswith("breadth:") for signal in output.outputs["signals"]
    )


@pytest.mark.asyncio
async def test_trade_packager_can_move_unconfirmed_long_intent_to_flat() -> None:
    packager = TradePackager()

    baseline = await packager._execute(
        _context(
            sentiment_score=0.35,
            technical_score=0.35,
            breadth_state=MISSING_BREADTH,
        )
    )
    weak = await packager._execute(
        _context(
            sentiment_score=0.35,
            technical_score=0.35,
            breadth_state=WEAK_BREADTH,
        )
    )

    assert baseline.outputs["regime"] == "long"
    assert weak.outputs["regime"] == "flat"
    assert weak.outputs["features"]["breadth_entry_bias_modifier"] < 0.0
    assert weak.outputs["features"]["breadth_position_size_multiplier"] <= 0.50
    assert "breadth_adjusted_trade_to_flat" in weak.outputs["signals"]
    assert "breadth_reduced_directional_intent" in weak.outputs["risks"]
    assert (
        "keep_trade_intent_on_watchlist_until_breadth_confirms"
        in weak.outputs["recommendations"]
    )


@pytest.mark.asyncio
async def test_trade_packager_classifies_capital_relevant_runtime_output() -> None:
    output = await TradePackager()._execute(
        _context(
            sentiment_score=0.45,
            technical_score=0.45,
            breadth_state=MISSING_BREADTH,
        )
    )

    authority_metadata = output.execution_metadata["risk_authority"]
    assert authority_metadata["risk_tier"] == RiskTier.VIGILANT.value
    assert authority_metadata["authority_effect"] == ("deterministic_platform_decision")
    assert authority_metadata["intended_sink"] == "durable_domain_record"
    assert authority_metadata["capital_relevant"] is True
    assert authority_metadata["durable_authority"] is True


def _context(
    *,
    sentiment_score: float,
    technical_score: float,
    breadth_state: dict[str, object],
) -> RuntimeContext:
    return RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
        node_outputs={
            "sentiment_agent": {
                "outputs": {
                    "directional_score": sentiment_score,
                    "confidence": 0.70,
                }
            },
            "technical_agent": {
                "outputs": {
                    "directional_score": technical_score,
                    "confidence": 0.70,
                    "regime": "neutral",
                    "features": {
                        "breadth_state": breadth_state,
                    },
                }
            },
            "risk_aggregator_agent": {
                "outputs": {
                    "directional_score": 0.0,
                    "features": {
                        "risk_pressure": 0.05,
                    },
                }
            },
        },
    )
