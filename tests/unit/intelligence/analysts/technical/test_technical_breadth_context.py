from __future__ import annotations

from intelligence.analysts.technical.technical_breadth_context import (
    TechnicalBreadthContext,
)
from intelligence.analysts.technical.technical_breadth_context import (
    extract_technical_breadth_context,
)
from intelligence.analysts.technical.technical_breadth_context import (
    extract_technical_breadth_context_from_features,
)


def test_extracts_typed_breadth_context_from_node_output() -> None:
    context = extract_technical_breadth_context(
        {
            "outputs": {
                "features": {
                    "breadth_state": {
                        "has_breadth_data": True,
                        "breadth_regime": "weak_breadth",
                        "risk_regime": "elevated",
                        "breadth_score": -0.52,
                        "breadth_risk_score": 0.76,
                        "participation_score": -0.41,
                        "leadership_score": -0.38,
                        "mcclellan_score": -0.45,
                        "divergence_score": -0.60,
                        "price_ad_divergence": True,
                        "breadth_percent": 0.37,
                        "pct_above_50dma": 0.42,
                        "pct_above_200dma": 0.48,
                        "new_high_low_diff": -36,
                        "mcclellan_oscillator": -32.5,
                    }
                }
            }
        }
    )

    assert context == TechnicalBreadthContext(
        has_breadth_data=True,
        breadth_regime="weak_breadth",
        risk_regime="elevated",
        breadth_score=-0.52,
        breadth_risk_score=0.76,
        participation_score=-0.41,
        leadership_score=-0.38,
        mcclellan_score=-0.45,
        divergence_score=-0.60,
        price_ad_divergence=True,
        breadth_percent=0.37,
        pct_above_50dma=0.42,
        pct_above_200dma=0.48,
        new_high_low_diff=-36.0,
        mcclellan_oscillator=-32.5,
    )
    assert context.is_weak is True
    assert context.is_strong is False
    assert context.risk_pressure > context.breadth_risk_score
    assert "price_ad_divergence" in context.risk_flags()
    assert "weak_market_participation" in context.risk_flags()


def test_extracts_from_features_and_falls_back_to_market_context() -> None:
    context = extract_technical_breadth_context_from_features(
        {
            "breadth": {
                "has_breadth_data": True,
                "breadth_regime": "strong_breadth",
                "breadth_score": "0.64",
                "breadth_risk_score": "0.24",
                "participation_score": "0.36",
                "leadership_score": "0.22",
                "mcclellan_score": "0.18",
            },
            "market_context": {
                "price_ad_divergence": "false",
                "breadth_percent": "0.62",
                "pct_above_50dma": "0.71",
                "pct_above_200dma": "0.68",
                "new_high_low_diff": "26",
                "mcclellan_oscillator": "28.5",
            },
        }
    )

    assert context.has_breadth_data is True
    assert context.breadth_regime == "strong_breadth"
    assert context.is_strong is True
    assert context.price_ad_divergence is False
    assert context.breadth_percent == 0.62
    assert context.new_high_low_diff == 26.0
    assert context.confirmation_score > 0.0
    assert context.risk_flags() == ()


def test_missing_breadth_is_neutral_and_unavailable() -> None:
    context = extract_technical_breadth_context(
        {
            "outputs": {
                "features": {
                    "market_context": {
                        "has_breadth": False,
                    }
                }
            }
        }
    )

    assert context == TechnicalBreadthContext.unavailable()
    assert context.is_weak is False
    assert context.is_strong is False
    assert context.confirmation_score == 0.0
    assert context.risk_pressure == 0.0
    assert context.risk_flags() == ()
    assert context.to_dict()["has_breadth_data"] is False
