from __future__ import annotations

from typing import Any, Dict
from core.utils.utils import _clamp, _safe_float


def calibrate(
    regime_output: Dict[str, Any],
    trend: Dict[str, Any],
    volatility: Dict[str, Any],
    breadth: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    breadth = breadth or {}

    score = _safe_float(regime_output.get("directional_technical_score"))
    confidence = _safe_float(regime_output.get("confidence"))

    trend_strength = _safe_float(trend.get("trend_strength"))
    trend_score = _safe_float(
        trend.get("trend_score"),
        default=_safe_float(trend.get("directional_bias_score")),
    )

    structure = str(trend.get("structure", ""))
    ema_alignment = str(trend.get("ema_alignment", ""))
    momentum_confirmation = str(trend.get("momentum_confirmation", ""))

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

    participation_score = _safe_float(breadth.get("participation_score"))
    leadership_score = _safe_float(breadth.get("leadership_score"))
    mcclellan_score = _safe_float(breadth.get("mcclellan_score"))
    divergence_score = _safe_float(breadth.get("divergence_score"))
    price_ad_divergence = bool(breadth.get("price_ad_divergence"))

    breadth_confirmation = _breadth_confirmation(
        breadth_score=breadth_score,
        participation_score=participation_score,
        leadership_score=leadership_score,
        mcclellan_score=mcclellan_score,
        divergence_score=divergence_score,
    )

    trend_confirmation = _trend_confirmation_boost(
        ema_alignment=ema_alignment,
        structure=structure,
        trend_strength=trend_strength,
        momentum_confirmation=momentum_confirmation,
        trend_score=trend_score,
    )

    structure_multiplier = _structure_multiplier(
        structure=structure,
        trend_strength=trend_strength,
    )

    volatility_adjustment = _volatility_adjustment(
        volatility_risk_score=volatility_risk_score,
        trend_strength=trend_strength,
    )

    breadth_adjustment = _breadth_adjustment(
        breadth_score=breadth_score,
        breadth_risk_score=breadth_risk_score,
        participation_score=participation_score,
        leadership_score=leadership_score,
        mcclellan_score=mcclellan_score,
        price_ad_divergence=price_ad_divergence,
    )

    calibrated_score = score
    calibrated_score *= structure_multiplier
    calibrated_score *= volatility_adjustment
    calibrated_score *= breadth_adjustment
    calibrated_score += trend_confirmation
    calibrated_score += breadth_confirmation * 0.05
    calibrated_score = _clamp(calibrated_score)

    calibrated_confidence = _calibrate_confidence(
        confidence=confidence,
        trend_strength=trend_strength,
        trend_confirmation=trend_confirmation,
        volatility_risk_score=volatility_risk_score,
        breadth_risk_score=breadth_risk_score,
        participation_score=participation_score,
        leadership_score=leadership_score,
        mcclellan_score=mcclellan_score,
        price_ad_divergence=price_ad_divergence,
        ema_alignment=ema_alignment,
        structure=structure,
    )

    regime_output["directional_technical_score"] = calibrated_score
    regime_output["regime"] = _classify_regime(calibrated_score)
    regime_output["confidence"] = calibrated_confidence

    regime_output["calibration"] = {
        "trend_confirmation": trend_confirmation,
        "breadth_confirmation": breadth_confirmation,
        "structure_multiplier": structure_multiplier,
        "volatility_adjustment": volatility_adjustment,
        "breadth_adjustment": breadth_adjustment,
        "volatility_score": volatility_score,
        "volatility_risk_score": volatility_risk_score,
        "breadth_score": breadth_score,
        "breadth_risk_score": breadth_risk_score,
        "participation_score": participation_score,
        "leadership_score": leadership_score,
        "mcclellan_score": mcclellan_score,
        "divergence_score": divergence_score,
        "price_ad_divergence": price_ad_divergence,
        "confidence_floor_applied": _confidence_floor_applies(
            trend_strength=trend_strength,
            ema_alignment=ema_alignment,
            structure=structure,
        ),
    }

    return regime_output


def _breadth_confirmation(
    breadth_score: float,
    participation_score: float,
    leadership_score: float,
    mcclellan_score: float,
    divergence_score: float,
) -> float:
    return _clamp(
        breadth_score * 0.40
        + participation_score * 0.25
        + leadership_score * 0.15
        + mcclellan_score * 0.15
        + divergence_score * 0.05,
    )


def _trend_confirmation_boost(
    ema_alignment: str,
    structure: str,
    trend_strength: float,
    momentum_confirmation: str,
    trend_score: float,
) -> float:
    boost = 0.0

    if ema_alignment == "fully_bullish":
        boost += 0.04
    elif ema_alignment == "fully_bearish":
        boost -= 0.04

    if structure == "higher_highs_higher_lows":
        boost += 0.04
    elif structure == "lower_highs_lower_lows":
        boost -= 0.04

    if momentum_confirmation == "bullish_confirmation":
        boost += 0.03
    elif momentum_confirmation == "bearish_confirmation":
        boost -= 0.03

    boost += trend_score * trend_strength * 0.03

    return _clamp(boost, -0.15, 0.15)


def _structure_multiplier(structure: str, trend_strength: float) -> float:
    if trend_strength > 0.75:
        if structure in {
            "higher_highs_higher_lows",
            "lower_highs_lower_lows",
        }:
            return 1.05

    if trend_strength < 0.40:
        return 0.95

    return 1.0


def _volatility_adjustment(
    volatility_risk_score: float,
    trend_strength: float,
) -> float:
    if trend_strength > 0.75:
        return _clamp(
            1.0 - (volatility_risk_score * 0.10),
            0.85,
            1.0,
        )

    return _clamp(
        1.0 - (volatility_risk_score * 0.18),
        0.75,
        1.0,
    )


def _breadth_adjustment(
    breadth_score: float,
    breadth_risk_score: float,
    participation_score: float,
    leadership_score: float,
    mcclellan_score: float,
    price_ad_divergence: bool,
) -> float:
    adjustment = 1.0

    positive_confirmation = _clamp(
        max(0.0, breadth_score) * 0.08
        + max(0.0, participation_score) * 0.06
        + max(0.0, leadership_score) * 0.04
        + max(0.0, mcclellan_score) * 0.04,
        0.0,
        0.15,
    )

    negative_confirmation = _clamp(
        max(0.0, -breadth_score) * 0.10
        + max(0.0, -participation_score) * 0.07
        + max(0.0, -leadership_score) * 0.04
        + max(0.0, -mcclellan_score) * 0.04,
        0.0,
        0.20,
    )

    adjustment += positive_confirmation
    adjustment -= negative_confirmation
    adjustment -= breadth_risk_score * 0.04

    if price_ad_divergence:
        adjustment -= 0.08

    return _clamp(adjustment, 0.75, 1.12)


def _calibrate_confidence(
    confidence: float,
    trend_strength: float,
    trend_confirmation: float,
    volatility_risk_score: float,
    breadth_risk_score: float,
    participation_score: float,
    leadership_score: float,
    mcclellan_score: float,
    price_ad_divergence: bool,
    ema_alignment: str,
    structure: str,
) -> float:
    breadth_quality = (
        abs(participation_score) * 0.40
        + abs(leadership_score) * 0.30
        + abs(mcclellan_score) * 0.30
    )

    calibrated = confidence * (0.72 + (trend_strength * 0.22))
    calibrated += breadth_quality * 0.06

    calibrated *= 1.0 - (volatility_risk_score * 0.10)
    calibrated *= 1.0 - (breadth_risk_score * 0.06)

    calibrated += abs(trend_confirmation) * 0.50

    if price_ad_divergence:
        calibrated *= 0.92

    if _confidence_floor_applies(
        trend_strength=trend_strength,
        ema_alignment=ema_alignment,
        structure=structure,
    ):
        calibrated = max(calibrated, 0.72)

    return _clamp(calibrated, 0.0, 1.0)


def _confidence_floor_applies(
    trend_strength: float,
    ema_alignment: str,
    structure: str,
) -> bool:
    bullish_floor = (
        trend_strength >= 0.80
        and ema_alignment == "fully_bullish"
        and structure == "higher_highs_higher_lows"
    )

    bearish_floor = (
        trend_strength >= 0.80
        and ema_alignment == "fully_bearish"
        and structure == "lower_highs_lower_lows"
    )

    return bullish_floor or bearish_floor


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
