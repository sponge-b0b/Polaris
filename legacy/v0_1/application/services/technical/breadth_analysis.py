from __future__ import annotations

from typing import Any

from core.utils.utils import _clamp, _safe_float

STRENGTH_THRESHOLD = 0.50
WEAKNESS_THRESHOLD = -0.50


def stability_to_risk(
    stability_score: float,
) -> float:
    return _clamp(
        (1.0 - stability_score) / 2.0,
        0.0,
        1.0,
    )


def analyze(
    technical_result: dict[str, Any],
) -> dict[str, Any]:

    market_context = dict(
        technical_result.get(
            "market_context",
            {},
        )
    )

    if not market_context.get("has_breadth"):
        return _empty_result()

    ad_line = _safe_float(
        market_context.get("ad_line"),
    )

    ad_line_ema_20 = _safe_float(
        market_context.get("ad_line_ema_20"),
    )

    ad_line_ema_50 = _safe_float(
        market_context.get("ad_line_ema_50"),
    )

    ad_line_slope_5 = _safe_float(
        market_context.get("ad_line_slope_5"),
    )

    ad_line_slope_20 = _safe_float(
        market_context.get("ad_line_slope_20"),
    )

    ad_line_trend_ratio = _safe_float(
        market_context.get("ad_line_trend_ratio"),
    )

    ad_line_trend_score = _safe_float(
        market_context.get("ad_line_trend_score"),
    )

    ad_ratio = _safe_float(
        market_context.get("ad_ratio"),
    )

    breadth_percent = _safe_float(
        market_context.get("breadth_percent"),
    )

    pct_above_50dma = _safe_float(
        market_context.get("pct_above_50dma"),
    )

    pct_above_200dma = _safe_float(
        market_context.get("pct_above_200dma"),
    )

    new_highs = _safe_float(
        market_context.get("new_highs"),
    )

    new_lows = _safe_float(
        market_context.get("new_lows"),
    )

    new_high_low_diff = _safe_float(
        market_context.get("new_high_low_diff"),
    )

    new_high_low_ratio = _safe_float(
        market_context.get("new_high_low_ratio"),
    )

    price_ad_divergence = bool(
        market_context.get("price_ad_divergence"),
    )

    mcclellan_oscillator = _safe_float(
        market_context.get(
            "mcclellan_oscillator",
        )
    )

    mcclellan_summation_index = _safe_float(
        market_context.get(
            "mcclellan_summation_index",
        )
    )

    trend_score = _compute_trend_score(
        ad_line=ad_line,
        ad_line_ema_20=ad_line_ema_20,
        ad_line_ema_50=ad_line_ema_50,
        ad_line_trend_ratio=ad_line_trend_ratio,
    )

    slope_score = _compute_slope_score(
        ad_line_trend_score=ad_line_trend_score,
        ad_line_slope_5=ad_line_slope_5,
        ad_line_slope_20=ad_line_slope_20,
    )

    confirmation_score = _compute_confirmation_score(
        ad_line=ad_line,
        ad_line_ema_20=ad_line_ema_20,
        ad_line_ema_50=ad_line_ema_50,
        ad_line_slope_20=ad_line_slope_20,
    )

    participation_score = _compute_participation_score(
        breadth_percent=breadth_percent,
        ad_ratio=ad_ratio,
        pct_above_50dma=pct_above_50dma,
        pct_above_200dma=pct_above_200dma,
    )

    leadership_score = _compute_leadership_score(
        new_highs=new_highs,
        new_lows=new_lows,
        new_high_low_diff=new_high_low_diff,
        new_high_low_ratio=new_high_low_ratio,
    )

    mcclellan_score = _compute_mcclellan_score(
        mcclellan_oscillator=mcclellan_oscillator,
        mcclellan_summation_index=mcclellan_summation_index,
    )

    divergence_score = -0.60 if price_ad_divergence else 0.0

    breadth_score = _clamp(
        trend_score * 0.25
        + slope_score * 0.15
        + confirmation_score * 0.15
        + participation_score * 0.20
        + leadership_score * 0.10
        + mcclellan_score * 0.10
        + divergence_score * 0.05,
    )

    breadth_risk_score = stability_to_risk(
        breadth_score,
    )

    breadth_regime = _determine_breadth_regime(
        breadth_score,
    )

    risk_regime = _determine_risk_regime(
        breadth_risk_score,
    )

    strategy_environment = _determine_strategy_environment(
        breadth_score=breadth_score,
        breadth_regime=breadth_regime,
        price_ad_divergence=price_ad_divergence,
    )

    return {
        "has_breadth_data": True,
        "breadth_score": breadth_score,
        "breadth_risk_score": breadth_risk_score,
        "breadth_regime": breadth_regime,
        "risk_regime": risk_regime,
        "strategy_environment": strategy_environment,
        "trend_score": trend_score,
        "slope_score": slope_score,
        "confirmation_score": confirmation_score,
        "participation_score": participation_score,
        "leadership_score": leadership_score,
        "mcclellan_score": mcclellan_score,
        "divergence_score": divergence_score,
        "components": {
            "trend_score": trend_score,
            "slope_score": slope_score,
            "confirmation_score": confirmation_score,
            "participation_score": participation_score,
            "leadership_score": leadership_score,
            "mcclellan_score": mcclellan_score,
            "divergence_score": divergence_score,
        },
        "source_metrics": {
            "price_ad_divergence": price_ad_divergence,
            "breadth_percent": breadth_percent,
            "pct_above_50dma": pct_above_50dma,
            "pct_above_200dma": pct_above_200dma,
            "new_high_low_diff": new_high_low_diff,
            "mcclellan_oscillator": mcclellan_oscillator,
            "mcclellan_summation_index": mcclellan_summation_index,
        },
    }


def _compute_trend_score(
    ad_line: float,
    ad_line_ema_20: float,
    ad_line_ema_50: float,
    ad_line_trend_ratio: float,
) -> float:
    score = 0.0

    if ad_line_ema_20 > ad_line_ema_50:
        score += 0.50
    elif ad_line_ema_20 < ad_line_ema_50:
        score -= 0.50

    if ad_line > ad_line_ema_20:
        score += 0.25
    elif ad_line < ad_line_ema_20:
        score -= 0.25

    if ad_line_trend_ratio > 1.0:
        score += _clamp(
            ad_line_trend_ratio - 1.0,
            0.0,
            0.25,
        )
    elif 0.0 < ad_line_trend_ratio < 1.0:
        score -= _clamp(
            1.0 - ad_line_trend_ratio,
            0.0,
            0.25,
        )

    return _clamp(
        score,
    )


def _compute_slope_score(
    ad_line_trend_score: float,
    ad_line_slope_5: float,
    ad_line_slope_20: float,
) -> float:
    score = ad_line_trend_score * 0.60

    if ad_line_slope_5 > 0:
        score += 0.20
    elif ad_line_slope_5 < 0:
        score -= 0.20

    if ad_line_slope_20 > 0:
        score += 0.20
    elif ad_line_slope_20 < 0:
        score -= 0.20

    return _clamp(
        score,
    )


def _compute_confirmation_score(
    ad_line: float,
    ad_line_ema_20: float,
    ad_line_ema_50: float,
    ad_line_slope_20: float,
) -> float:
    above_short = ad_line > ad_line_ema_20
    above_long = ad_line > ad_line_ema_50
    rising = ad_line_slope_20 > 0

    if above_short and above_long and rising:
        return 1.0

    if not above_short and not above_long and not rising:
        return -1.0

    if rising and above_short:
        return 0.5

    if not rising and not above_short:
        return -0.5

    return 0.0


def _compute_participation_score(
    breadth_percent: float,
    ad_ratio: float,
    pct_above_50dma: float,
    pct_above_200dma: float,
) -> float:
    breadth_percent_score = _clamp(
        (breadth_percent - 0.50) / 0.50,
    )

    ad_ratio_score = _score_ad_ratio(
        ad_ratio,
    )

    above_50_score = _clamp(
        (pct_above_50dma - 0.50) / 0.50,
    )

    above_200_score = _clamp(
        (pct_above_200dma - 0.50) / 0.50,
    )

    return _clamp(
        breadth_percent_score * 0.25
        + ad_ratio_score * 0.25
        + above_50_score * 0.25
        + above_200_score * 0.25,
    )


def _score_ad_ratio(
    ad_ratio: float,
) -> float:
    if ad_ratio <= 0:
        return 0.0

    if ad_ratio >= 2.0:
        return 1.0

    if ad_ratio >= 1.2:
        return 0.5

    if ad_ratio >= 0.8:
        return 0.0

    if ad_ratio >= 0.5:
        return -0.5

    return -1.0


def _compute_leadership_score(
    new_highs: float,
    new_lows: float,
    new_high_low_diff: float,
    new_high_low_ratio: float,
) -> float:
    total = new_highs + new_lows

    if total > 0:
        high_low_balance_score = _clamp(
            (new_highs - new_lows) / total,
        )
    else:
        high_low_balance_score = 0.0

    ratio_score = 0.0

    if new_high_low_ratio >= 3.0:
        ratio_score = 1.0
    elif new_high_low_ratio >= 1.5:
        ratio_score = 0.5
    elif 0.0 < new_high_low_ratio < 0.33:
        ratio_score = -1.0
    elif 0.0 < new_high_low_ratio < 0.75:
        ratio_score = -0.5

    diff_score = _clamp(
        new_high_low_diff / 100.0,
    )

    return _clamp(
        high_low_balance_score * 0.50 + ratio_score * 0.25 + diff_score * 0.25,
    )


def _compute_mcclellan_score(
    mcclellan_oscillator: float,
    mcclellan_summation_index: float,
) -> float:
    oscillator_score = _clamp(
        mcclellan_oscillator / 250.0,
    )

    summation_score = _clamp(
        mcclellan_summation_index / 1000.0,
    )

    return _clamp(
        oscillator_score * 0.65 + summation_score * 0.35,
    )


def _determine_breadth_regime(
    breadth_score: float,
) -> str:
    if breadth_score >= 0.75:
        return "very_strong_breadth"

    if breadth_score >= STRENGTH_THRESHOLD:
        return "strong_breadth"

    if breadth_score <= -0.75:
        return "very_weak_breadth"

    if breadth_score <= WEAKNESS_THRESHOLD:
        return "weak_breadth"

    if breadth_score > 0:
        return "improving_breadth"

    if breadth_score < 0:
        return "deteriorating_breadth"

    return "neutral_breadth"


def _determine_risk_regime(
    breadth_risk_score: float,
) -> str:
    if breadth_risk_score >= 0.75:
        return "high"

    if breadth_risk_score >= 0.50:
        return "elevated"

    if breadth_risk_score >= 0.25:
        return "normal"

    return "stable"


def _determine_strategy_environment(
    breadth_score: float,
    breadth_regime: str,
    price_ad_divergence: bool,
) -> dict[str, float]:
    bull = 1.0
    bear = 1.0
    sideways = 1.0

    if breadth_regime in {
        "very_strong_breadth",
        "strong_breadth",
    }:
        bull *= 1.20
        bear *= 0.85
        sideways *= 0.90

    elif breadth_regime == "improving_breadth":
        bull *= 1.10
        bear *= 0.90
        sideways *= 0.95

    elif breadth_regime in {
        "very_weak_breadth",
        "weak_breadth",
    }:
        bull *= 0.75
        bear *= 1.10
        sideways *= 1.15

    elif breadth_regime == "deteriorating_breadth":
        bull *= 0.85
        bear *= 1.05
        sideways *= 1.10

    if breadth_score <= -0.75:
        bull *= 0.85
        bear *= 1.10
        sideways *= 1.10

    elif breadth_score >= 0.75:
        bull *= 1.10
        bear *= 0.90

    if price_ad_divergence:
        bull *= 0.85
        bear *= 1.05
        sideways *= 1.05

    return {
        "bull": bull,
        "bear": bear,
        "sideways": sideways,
    }


def _empty_result() -> dict[str, Any]:
    return {
        "has_breadth_data": False,
        "ad_line": 0.0,
        "ad_line_ema_10": 0.0,
        "ad_line_ema_20": 0.0,
        "ad_line_ema_50": 0.0,
        "ad_line_slope_5": 0.0,
        "ad_line_slope_20": 0.0,
        "ad_line_trend_ratio": 0.0,
        "ad_line_trend_score": 0.0,
        "ad_ratio": 0.0,
        "breadth_percent": 0.0,
        "net_breadth": 0.0,
        "pct_above_50dma": 0.0,
        "pct_above_200dma": 0.0,
        "new_highs": 0.0,
        "new_lows": 0.0,
        "new_high_low_diff": 0.0,
        "new_high_low_ratio": 0.0,
        "mcclellan_oscillator": 0.0,
        "mcclellan_summation_index": 0.0,
        "price_ad_divergence": False,
        "trend_score": 0.0,
        "slope_score": 0.0,
        "confirmation_score": 0.0,
        "participation_score": 0.0,
        "leadership_score": 0.0,
        "mcclellan_score": 0.0,
        "divergence_score": 0.0,
        "breadth_score": 0.0,
        "breadth_risk_score": 0.5,
        "breadth_regime": "unknown",
        "risk_regime": "unknown",
        "strategy_environment": {
            "bull": 1.0,
            "bear": 1.0,
            "sideways": 1.0,
        },
        "components": {
            "trend_score": 0.0,
            "slope_score": 0.0,
            "confirmation_score": 0.0,
            "participation_score": 0.0,
            "leadership_score": 0.0,
            "mcclellan_score": 0.0,
            "divergence_score": 0.0,
        },
    }
