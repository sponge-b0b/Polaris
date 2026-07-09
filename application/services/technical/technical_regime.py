from __future__ import annotations

from typing import Any, Dict
from core.utils.utils import _clamp, _safe_float


def build(
    technical: Dict[str, Any],
) -> Dict[str, Any]:
    trend = dict(technical.get("trend", {}))
    volatility = dict(technical.get("volatility", {}))
    breadth = dict(technical.get("breadth", {}))

    trend_score = _safe_float(trend.get("trend_score"))
    trend_strength = _safe_float(trend.get("trend_strength"))
    trend_confidence = _safe_float(trend.get("confidence"))

    volatility_score = _safe_float(volatility.get("volatility_score"))
    volatility_risk_score = _safe_float(
        volatility.get("volatility_risk_score"),
        default=0.5,
    )

    breadth_score = _safe_float(breadth.get("breadth_score"))
    breadth_risk_score = _safe_float(
        breadth.get("breadth_risk_score"),
        default=0.5,
    )

    participation_score = _safe_float(
        breadth.get("participation_score"),
    )
    leadership_score = _safe_float(
        breadth.get("leadership_score"),
    )
    mcclellan_score = _safe_float(
        breadth.get("mcclellan_score"),
    )
    divergence_score = _safe_float(
        breadth.get("divergence_score"),
    )
    price_ad_divergence = bool(
        breadth.get("price_ad_divergence"),
    )

    breadth_confirmation_score = _expanded_breadth_confirmation_score(
        breadth_score=breadth_score,
        participation_score=participation_score,
        leadership_score=leadership_score,
        mcclellan_score=mcclellan_score,
        divergence_score=divergence_score,
    )

    trend_force = trend_score * 0.50
    breadth_force = breadth_confirmation_score * 0.25

    volatility_modifier = _volatility_modifier(
        volatility_score=volatility_score,
        volatility_risk_score=volatility_risk_score,
    )

    breadth_modifier = _breadth_modifier(
        breadth_score=breadth_score,
        breadth_risk_score=breadth_risk_score,
        participation_score=participation_score,
        leadership_score=leadership_score,
        mcclellan_score=mcclellan_score,
        price_ad_divergence=price_ad_divergence,
    )

    directional_technical_score = _clamp(
        (trend_force + breadth_force) * volatility_modifier * breadth_modifier,
    )

    regime = _classify_regime(
        directional_technical_score,
    )

    bull_score = _bull_score(
        directional_technical_score=directional_technical_score,
        volatility_risk_score=volatility_risk_score,
        breadth_score=breadth_score,
        participation_score=participation_score,
        leadership_score=leadership_score,
        mcclellan_score=mcclellan_score,
        price_ad_divergence=price_ad_divergence,
    )

    bear_score = _bear_score(
        directional_technical_score=directional_technical_score,
        volatility_risk_score=volatility_risk_score,
        breadth_score=breadth_score,
        divergence_score=divergence_score,
        price_ad_divergence=price_ad_divergence,
    )

    sideways_score = _sideways_score(
        directional_technical_score=directional_technical_score,
        volatility_risk_score=volatility_risk_score,
        breadth_risk_score=breadth_risk_score,
        participation_score=participation_score,
        price_ad_divergence=price_ad_divergence,
    )

    confidence = _confidence(
        trend_confidence=trend_confidence,
        trend_strength=trend_strength,
        volatility_risk_score=volatility_risk_score,
        breadth_risk_score=breadth_risk_score,
        directional_technical_score=directional_technical_score,
        participation_score=participation_score,
        leadership_score=leadership_score,
        mcclellan_score=mcclellan_score,
        price_ad_divergence=price_ad_divergence,
    )

    components = {
        "trend_score": trend_score,
        "trend_strength": trend_strength,
        "trend_confidence": trend_confidence,
        "volatility_score": volatility_score,
        "volatility_risk_score": volatility_risk_score,
        "breadth_score": breadth_score,
        "breadth_risk_score": breadth_risk_score,
        "participation_score": participation_score,
        "leadership_score": leadership_score,
        "mcclellan_score": mcclellan_score,
        "divergence_score": divergence_score,
        "breadth_confirmation_score": breadth_confirmation_score,
        "volatility_modifier": volatility_modifier,
        "breadth_modifier": breadth_modifier,
    }

    return {
        "directional_technical_score": directional_technical_score,
        "regime": regime,
        "confidence": confidence,
        "bull_score": bull_score,
        "bear_score": bear_score,
        "sideways_score": sideways_score,
        "components": components,
        "inputs": {
            "trend_regime": trend.get("trend_regime"),
            "volatility_regime": volatility.get("volatility_regime"),
            "breadth_regime": breadth.get("breadth_regime"),
            "trend_quality": trend.get("trend_quality"),
            "stability_state": volatility.get("stability_state"),
            "risk_regime": breadth.get("risk_regime"),
            "price_ad_divergence": price_ad_divergence,
            "pct_above_50dma": breadth.get("pct_above_50dma"),
            "pct_above_200dma": breadth.get("pct_above_200dma"),
            "new_highs": breadth.get("new_highs"),
            "new_lows": breadth.get("new_lows"),
            "mcclellan_oscillator": breadth.get(
                "mcclellan_oscillator",
            ),
            "mcclellan_summation_index": breadth.get(
                "mcclellan_summation_index",
            ),
        },
    }


def _expanded_breadth_confirmation_score(
    breadth_score: float,
    participation_score: float,
    leadership_score: float,
    mcclellan_score: float,
    divergence_score: float,
) -> float:
    return _clamp(
        breadth_score * 0.45
        + participation_score * 0.25
        + leadership_score * 0.15
        + mcclellan_score * 0.15
        + divergence_score * 0.10,
    )


def _volatility_modifier(
    volatility_score: float,
    volatility_risk_score: float,
) -> float:
    modifier = 1.0 - (volatility_risk_score * 0.35)

    if volatility_score > 0.50:
        modifier += 0.05

    return _clamp(
        modifier,
        0.50,
        1.10,
    )


def _breadth_modifier(
    breadth_score: float,
    breadth_risk_score: float,
    participation_score: float,
    leadership_score: float,
    mcclellan_score: float,
    price_ad_divergence: bool,
) -> float:
    modifier = 1.0

    positive_confirmation = _clamp(
        max(0.0, breadth_score) * 0.10
        + max(0.0, participation_score) * 0.08
        + max(0.0, leadership_score) * 0.04
        + max(0.0, mcclellan_score) * 0.04,
        0.0,
        0.20,
    )

    negative_confirmation = _clamp(
        max(0.0, -breadth_score) * 0.12
        + max(0.0, -participation_score) * 0.08
        + max(0.0, -leadership_score) * 0.04
        + max(0.0, -mcclellan_score) * 0.04,
        0.0,
        0.25,
    )

    modifier += positive_confirmation
    modifier -= negative_confirmation
    modifier -= breadth_risk_score * 0.05

    if price_ad_divergence:
        modifier -= 0.10

    return _clamp(
        modifier,
        0.60,
        1.20,
    )


def _bull_score(
    directional_technical_score: float,
    volatility_risk_score: float,
    breadth_score: float,
    participation_score: float,
    leadership_score: float,
    mcclellan_score: float,
    price_ad_divergence: bool,
) -> float:
    score = 0.5 + (directional_technical_score * 0.5)

    score += max(0.0, breadth_score) * 0.10
    score += max(0.0, participation_score) * 0.08
    score += max(0.0, leadership_score) * 0.04
    score += max(0.0, mcclellan_score) * 0.04

    score -= volatility_risk_score * 0.15

    if price_ad_divergence:
        score -= 0.10

    return _clamp(score, 0.0, 1.0)


def _bear_score(
    directional_technical_score: float,
    volatility_risk_score: float,
    breadth_score: float,
    divergence_score: float,
    price_ad_divergence: bool,
) -> float:
    score = 0.5 - (directional_technical_score * 0.5)

    score += max(0.0, -breadth_score) * 0.15
    score += max(0.0, -divergence_score) * 0.08
    score += volatility_risk_score * 0.05

    if price_ad_divergence:
        score += 0.08

    return _clamp(score, 0.0, 1.0)


def _sideways_score(
    directional_technical_score: float,
    volatility_risk_score: float,
    breadth_risk_score: float,
    participation_score: float,
    price_ad_divergence: bool,
) -> float:
    trend_neutrality = 1.0 - abs(directional_technical_score)

    moderate_volatility_bonus = 1.0 - abs(
        volatility_risk_score - 0.50,
    )

    participation_mixed_bonus = 1.0 - abs(
        participation_score,
    )

    score = (
        trend_neutrality * 0.45
        + moderate_volatility_bonus * 0.25
        + breadth_risk_score * 0.15
        + participation_mixed_bonus * 0.15
    )

    if price_ad_divergence:
        score += 0.05

    return _clamp(score, 0.0, 1.0)


def _confidence(
    trend_confidence: float,
    trend_strength: float,
    volatility_risk_score: float,
    breadth_risk_score: float,
    directional_technical_score: float,
    participation_score: float,
    leadership_score: float,
    mcclellan_score: float,
    price_ad_divergence: bool,
) -> float:
    breadth_confirmation = (
        abs(participation_score) * 0.40
        + abs(leadership_score) * 0.25
        + abs(mcclellan_score) * 0.25
        + abs(directional_technical_score) * 0.10
    )

    base = (
        trend_confidence * 0.40
        + trend_strength * 0.20
        + abs(directional_technical_score) * 0.20
        + breadth_confirmation * 0.10
        + (1.0 - volatility_risk_score) * 0.05
        + (1.0 - breadth_risk_score) * 0.05
    )

    if volatility_risk_score >= 0.75:
        base *= 0.85

    if breadth_risk_score >= 0.75:
        base *= 0.90

    if price_ad_divergence:
        base *= 0.90

    return _clamp(base, 0.0, 1.0)


def _classify_regime(score: float) -> str:
    if score >= 0.60:
        return "strong_bullish"

    if score >= 0.20:
        return "bullish"

    if score <= -0.60:
        return "strong_bearish"

    if score <= -0.20:
        return "bearish"

    return "neutral"
