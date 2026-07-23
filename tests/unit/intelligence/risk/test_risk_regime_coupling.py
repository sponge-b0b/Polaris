from __future__ import annotations

from intelligence.analysts.technical.technical_breadth_context import (
    TechnicalBreadthContext,
)
from intelligence.risk.regime import risk_regime_coupling

BASE_RISK = {
    "composite_risk": 0.40,
    "risk_pressure": 0.40,
    "stability_score": 0.60,
}

TECHNICAL_REGIME = {
    "regime": "neutral",
    "directional_technical_score": 0.10,
    "confidence": 0.50,
    "execution_readiness": 0.50,
    "signal_quality": 0.50,
}

VOLATILITY = {
    "volatility_score": 0.55,
}


def test_risk_regime_coupling_keeps_missing_breadth_neutral() -> None:
    baseline = risk_regime_coupling.apply(
        risk=BASE_RISK,
        technical_regime=TECHNICAL_REGIME,
        volatility=VOLATILITY,
    )
    unavailable = risk_regime_coupling.apply(
        risk=BASE_RISK,
        technical_regime=TECHNICAL_REGIME,
        volatility=VOLATILITY,
        breadth_context=TechnicalBreadthContext.unavailable(),
    )

    assert unavailable["adjusted_composite_risk"] == baseline["adjusted_composite_risk"]
    assert unavailable["adjusted_risk_pressure"] == baseline["adjusted_risk_pressure"]
    assert unavailable["modifiers"]["breadth_modifier"] == 1.0
    assert unavailable["modifiers"]["breadth_pressure_adjustment"] == 0.0
    assert unavailable["inputs"]["breadth_context"]["has_breadth_data"] is False


def test_risk_regime_coupling_increases_risk_for_weak_breadth() -> None:
    baseline = risk_regime_coupling.apply(
        risk=BASE_RISK,
        technical_regime=TECHNICAL_REGIME,
        volatility=VOLATILITY,
    )
    weak = risk_regime_coupling.apply(
        risk=BASE_RISK,
        technical_regime=TECHNICAL_REGIME,
        volatility=VOLATILITY,
        breadth_context=TechnicalBreadthContext(
            has_breadth_data=True,
            breadth_regime="weak_breadth",
            risk_regime="elevated",
            breadth_score=-0.52,
            breadth_risk_score=0.76,
            participation_score=-0.41,
            leadership_score=-0.38,
            mcclellan_score=-0.45,
            price_ad_divergence=True,
        ),
    )

    assert weak["adjusted_composite_risk"] > baseline["adjusted_composite_risk"]
    assert weak["adjusted_risk_pressure"] > baseline["adjusted_risk_pressure"]
    assert weak["adjusted_risk_score"] > baseline["adjusted_risk_score"]
    assert weak["modifiers"]["breadth_modifier"] > 1.0
    assert weak["modifiers"]["breadth_pressure_adjustment"] > 0.0
    assert weak["inputs"]["breadth_context"]["breadth_regime"] == "weak_breadth"


def test_risk_regime_coupling_reduces_risk_for_strong_breadth() -> None:
    baseline = risk_regime_coupling.apply(
        risk=BASE_RISK,
        technical_regime=TECHNICAL_REGIME,
        volatility=VOLATILITY,
    )
    strong = risk_regime_coupling.apply(
        risk=BASE_RISK,
        technical_regime=TECHNICAL_REGIME,
        volatility=VOLATILITY,
        breadth_context=TechnicalBreadthContext(
            has_breadth_data=True,
            breadth_regime="strong_breadth",
            risk_regime="stable",
            breadth_score=0.64,
            breadth_risk_score=0.24,
            participation_score=0.36,
            leadership_score=0.22,
            mcclellan_score=0.18,
            price_ad_divergence=False,
        ),
    )

    assert strong["adjusted_composite_risk"] < baseline["adjusted_composite_risk"]
    assert strong["adjusted_risk_pressure"] < baseline["adjusted_risk_pressure"]
    assert strong["adjusted_risk_score"] < baseline["adjusted_risk_score"]
    assert strong["modifiers"]["breadth_modifier"] < 1.0
    assert strong["modifiers"]["breadth_pressure_adjustment"] < 0.0
