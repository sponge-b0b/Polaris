from __future__ import annotations

import pytest

from application.services.technical import breadth_analysis
from application.services.technical import volatility_analysis


def test_volatility_breadth_confirmation_uses_raw_market_context() -> None:
    result = volatility_analysis.analyze(
        {
            "snapshot": {
                "close": 450.0,
                "atr_14": 4.5,
                "atr_50": 4.1,
                "atr_14_percent_of_price": 0.01,
                "atr_14_percentile_252": 50.0,
                "hv_20": 0.14,
                "hv_50": 0.13,
                "hv_100": 0.12,
            },
            "market_context": {
                "has_breadth": True,
                "breadth_percent": 0.38,
                "ad_ratio": 0.55,
                "pct_above_50dma": 0.40,
                "pct_above_200dma": 0.44,
                "new_high_low_diff": -42.0,
                "new_high_low_ratio": 0.25,
                "mcclellan_oscillator": -55.0,
                "mcclellan_summation_index": -420.0,
                "price_ad_divergence": True,
                "ad_line_trend_score": -0.30,
            },
        }
    )

    breadth_components = result["components"]["breadth"]
    assert result["breadth_confirmation_score"] < 0.0
    assert breadth_components["raw_participation_score"] < 0.0
    assert breadth_components["raw_leadership_score"] < 0.0
    assert breadth_components["raw_mcclellan_score"] < 0.0
    assert breadth_components["price_ad_divergence_pressure"] == -1.0
    assert "breadth_score" not in breadth_components


def test_volatility_missing_breadth_context_is_neutral() -> None:
    result = volatility_analysis.analyze(
        {
            "snapshot": {
                "close": 450.0,
            },
            "market_context": {
                "has_breadth": False,
            },
        }
    )

    assert result["breadth_confirmation_score"] == 0.0
    assert result["components"]["breadth"] == {
        "raw_participation_score": 0.0,
        "raw_leadership_score": 0.0,
        "raw_mcclellan_score": 0.0,
        "price_ad_divergence_pressure": 0.0,
        "ad_line_trend_score": 0.0,
    }


def test_breadth_leadership_severe_new_low_ratio_branch_is_reachable() -> None:
    severe_score = breadth_analysis._compute_leadership_score(
        new_highs=1.0,
        new_lows=5.0,
        new_high_low_diff=-4.0,
        new_high_low_ratio=0.20,
    )
    weak_score = breadth_analysis._compute_leadership_score(
        new_highs=2.0,
        new_lows=4.0,
        new_high_low_diff=-2.0,
        new_high_low_ratio=0.50,
    )

    assert severe_score < weak_score


def test_breadth_analysis_preserves_canonical_scores_and_full_precision() -> None:
    result = breadth_analysis.analyze(
        {
            "market_context": {
                "has_breadth": True,
                "ad_line": 200.0,
                "ad_line_ema_20": 180.0,
                "ad_line_ema_50": 150.0,
                "ad_line_slope_5": 2.0,
                "ad_line_slope_20": 1.0,
                "ad_line_trend_ratio": 1.2,
                "ad_line_trend_score": 0.8,
                "ad_ratio": 1.5,
                "breadth_percent": 0.7,
                "pct_above_50dma": 0.8,
                "pct_above_200dma": 0.7,
                "new_highs": 40.0,
                "new_lows": 10.0,
                "new_high_low_diff": 30.0,
                "new_high_low_ratio": 4.0,
                "price_ad_divergence": False,
                "mcclellan_oscillator": 100.0,
                "mcclellan_summation_index": 500.0,
            }
        }
    )

    assert result["has_breadth_data"] is True
    assert result["trend_score"] == pytest.approx(0.95)
    assert result["slope_score"] == pytest.approx(0.88)
    assert result["confirmation_score"] == 1.0
    assert result["participation_score"] == pytest.approx(0.475)
    assert result["leadership_score"] == pytest.approx(0.625)
    assert result["mcclellan_score"] == pytest.approx(0.435)
    assert result["breadth_score"] == pytest.approx(0.7205)
    assert result["breadth_risk_score"] == pytest.approx(0.13975)
    assert result["breadth_regime"] == "strong_breadth"
    assert result["risk_regime"] == "stable"
    assert result["strategy_environment"] == {
        "bull": 1.2,
        "bear": 0.85,
        "sideways": 0.9,
    }
