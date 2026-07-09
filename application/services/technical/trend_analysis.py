from __future__ import annotations

from typing import Any, Dict
from core.utils.utils import _clamp, _safe_float


def stability_to_risk(
    stability_score: float,
) -> float:
    """
    Convert stability/directional health score [-1, +1]
    to risk score [0, 1].

    +1 = bullish / healthy trend -> 0 risk
     0 = neutral / mixed trend   -> 0.5 risk
    -1 = bearish / weak trend    -> 1 risk
    """

    return _clamp(
        (1.0 - stability_score) / 2.0,
        0.0,
        1.0,
    )


# ============================================================
# MAIN ENTRY
# ============================================================


def analyze(
    technical_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Analyze trend using the technical result produced by
    technical_indicators.compute().

    Expected input:

        {
            "snapshot": {
                "close": ...,
                "ema_8": ...,
                "ema_21": ...,
                "ema_50": ...,
                "ema_200": ...,
                "rsi_14": ...,
                "macd": ...,
                "macd_signal": ...,
                "macd_histogram": ...
            }
        }

    Output score contracts:

        trend_score      [-1, +1]
        trend_risk_score [0, 1]
        trend_strength   [0, 1]
        confidence       [0, 1]
    """

    snapshot = dict(
        technical_result.get(
            "snapshot",
            {},
        )
    )

    close = _safe_float(
        snapshot.get("close"),
    )

    ema_8 = _safe_float(
        snapshot.get("ema_8"),
    )

    ema_21 = _safe_float(
        snapshot.get("ema_21"),
    )

    ema_50 = _safe_float(
        snapshot.get("ema_50"),
    )

    ema_200 = _safe_float(
        snapshot.get("ema_200"),
    )

    rsi = _safe_float(
        snapshot.get("rsi_14"),
    )

    macd = _safe_float(
        snapshot.get("macd"),
    )

    macd_signal = _safe_float(
        snapshot.get("macd_signal"),
    )

    macd_histogram = _safe_float(
        snapshot.get("macd_histogram"),
    )

    primary_trend = _determine_primary_trend(
        close=close,
        ema_8=ema_8,
        ema_21=ema_21,
        ema_50=ema_50,
        ema_200=ema_200,
    )

    ema_alignment = _determine_ema_alignment(
        ema_8=ema_8,
        ema_21=ema_21,
        ema_50=ema_50,
        ema_200=ema_200,
    )

    trend_strength = _calculate_trend_strength(
        close=close,
        ema_21=ema_21,
        ema_50=ema_50,
        ema_200=ema_200,
        rsi=rsi,
        macd_histogram=macd_histogram,
    )

    momentum_confirmation = _determine_momentum_confirmation(
        macd=macd,
        macd_signal=macd_signal,
        rsi=rsi,
    )

    price_location = _determine_price_location(
        close=close,
        ema_21=ema_21,
        ema_50=ema_50,
        ema_200=ema_200,
    )

    structure = _determine_structure(
        close=close,
        ema_21=ema_21,
        ema_50=ema_50,
        ema_200=ema_200,
    )

    trend_persistence = _determine_persistence(
        trend_strength=trend_strength,
        momentum_confirmation=momentum_confirmation,
        ema_alignment=ema_alignment,
    )

    trend_score = _compute_trend_score(
        primary_trend=primary_trend,
        ema_alignment=ema_alignment,
        rsi=rsi,
        macd_histogram=macd_histogram,
        structure=structure,
    )

    trend_risk_score = stability_to_risk(
        trend_score,
    )

    trend_regime = _classify_trend_regime(
        trend_score,
    )

    trend_quality = _determine_trend_quality(
        trend_strength=trend_strength,
        ema_alignment=ema_alignment,
        rsi=rsi,
    )

    confidence = _compute_confidence(
        trend_strength=trend_strength,
        trend_score=trend_score,
        ema_alignment=ema_alignment,
        structure=structure,
        momentum_confirmation=momentum_confirmation,
    )

    strategy_environment = _determine_strategy_environment(
        trend_score=trend_score,
        trend_strength=trend_strength,
        trend_regime=trend_regime,
    )

    return {
        "primary_trend": primary_trend,
        "trend_regime": trend_regime,
        "trend_strength": trend_strength,
        "trend_quality": trend_quality,
        "trend_persistence": trend_persistence,
        "ema_alignment": ema_alignment,
        "momentum_confirmation": momentum_confirmation,
        "price_location": price_location,
        "structure": structure,
        "trend_score": trend_score,
        "directional_bias_score": trend_score,
        "trend_risk_score": trend_risk_score,
        "confidence": confidence,
        "strategy_environment": strategy_environment,
        "components": {
            "ema_alignment_score": _ema_alignment_score(
                ema_alignment,
            ),
            "primary_trend_score": _primary_trend_score(
                primary_trend,
            ),
            "rsi_pressure_score": _rsi_pressure_score(
                rsi,
            ),
            "macd_score": _macd_score(
                macd_histogram,
            ),
            "structure_score": _structure_score(
                structure,
            ),
        },
    }


# ============================================================
# PRIMARY TREND
# ============================================================


def _determine_primary_trend(
    close: float,
    ema_8: float,
    ema_21: float,
    ema_50: float,
    ema_200: float,
) -> str:
    if close > ema_8 > ema_21 > ema_50 > ema_200:
        return "strong_bullish"

    if close > ema_21 > ema_50 > ema_200:
        return "bullish"

    if close < ema_8 < ema_21 < ema_50 < ema_200:
        return "strong_bearish"

    if close < ema_21 < ema_50 < ema_200:
        return "bearish"

    return "neutral"


# ============================================================
# EMA ALIGNMENT
# ============================================================


def _determine_ema_alignment(
    ema_8: float,
    ema_21: float,
    ema_50: float,
    ema_200: float,
) -> str:
    if ema_8 > ema_21 > ema_50 > ema_200:
        return "fully_bullish"

    if ema_8 < ema_21 < ema_50 < ema_200:
        return "fully_bearish"

    if ema_21 > ema_50 > ema_200:
        return "bullish"

    if ema_21 < ema_50 < ema_200:
        return "bearish"

    return "mixed"


# ============================================================
# TREND STRENGTH
# ============================================================


def _calculate_trend_strength(
    close: float,
    ema_21: float,
    ema_50: float,
    ema_200: float,
    rsi: float,
    macd_histogram: float,
) -> float:
    score = 0.0

    if close > ema_21:
        score += 0.25

    if ema_21 > ema_50:
        score += 0.25

    if ema_50 > ema_200:
        score += 0.25

    if rsi > 60:
        score += 0.15

    elif rsi < 40:
        score -= 0.15

    if macd_histogram > 0:
        score += 0.10

    elif macd_histogram < 0:
        score -= 0.10

    return _clamp(
        score,
        0.0,
        1.0,
    )


# ============================================================
# QUALITY / MOMENTUM / STRUCTURE
# ============================================================


def _determine_trend_quality(
    trend_strength: float,
    ema_alignment: str,
    rsi: float,
) -> str:
    if (
        trend_strength > 0.80
        and ema_alignment
        in {
            "fully_bullish",
            "fully_bearish",
        }
        and 45 <= rsi <= 75
    ):
        return "high_quality"

    if trend_strength > 0.55:
        return "moderate_quality"

    return "low_quality"


def _determine_momentum_confirmation(
    macd: float,
    macd_signal: float,
    rsi: float,
) -> str:
    if macd > macd_signal and rsi > 55:
        return "bullish_confirmation"

    if macd < macd_signal and rsi < 45:
        return "bearish_confirmation"

    return "mixed_confirmation"


def _determine_price_location(
    close: float,
    ema_21: float,
    ema_50: float,
    ema_200: float,
) -> str:
    if close > ema_21 > ema_50:
        return "above_value"

    if close < ema_21 < ema_50:
        return "below_value"

    if close > ema_200:
        return "above_long_term_trend"

    return "inside_value"


def _determine_structure(
    close: float,
    ema_21: float,
    ema_50: float,
    ema_200: float,
) -> str:
    if close > ema_21 > ema_50 > ema_200:
        return "higher_highs_higher_lows"

    if close < ema_21 < ema_50 < ema_200:
        return "lower_highs_lower_lows"

    return "range_bound"


def _determine_persistence(
    trend_strength: float,
    momentum_confirmation: str,
    ema_alignment: str,
) -> str:
    score = 0

    if trend_strength > 0.75:
        score += 1

    if momentum_confirmation != "mixed_confirmation":
        score += 1

    if ema_alignment in {
        "fully_bullish",
        "fully_bearish",
    }:
        score += 1

    if score == 3:
        return "stable"

    if score == 2:
        return "developing"

    return "fragile"


# ============================================================
# SCORE COMPONENTS
# ============================================================


def _compute_trend_score(
    primary_trend: str,
    ema_alignment: str,
    rsi: float,
    macd_histogram: float,
    structure: str,
) -> float:
    score = (
        _ema_alignment_score(
            ema_alignment,
        )
        * 0.35
        + _primary_trend_score(
            primary_trend,
        )
        * 0.30
        + _structure_score(
            structure,
        )
        * 0.20
        + _rsi_pressure_score(
            rsi,
        )
        * 0.10
        + _macd_score(
            macd_histogram,
        )
        * 0.05
    )

    return _clamp(
        score,
    )


def _ema_alignment_score(
    ema_alignment: str,
) -> float:
    mapping = {
        "fully_bullish": 1.0,
        "bullish": 0.6,
        "mixed": 0.0,
        "bearish": -0.6,
        "fully_bearish": -1.0,
    }

    return mapping.get(
        ema_alignment,
        0.0,
    )


def _primary_trend_score(
    primary_trend: str,
) -> float:
    mapping = {
        "strong_bullish": 1.0,
        "bullish": 0.6,
        "neutral": 0.0,
        "bearish": -0.6,
        "strong_bearish": -1.0,
    }

    return mapping.get(
        primary_trend,
        0.0,
    )


def _structure_score(
    structure: str,
) -> float:
    mapping = {
        "higher_highs_higher_lows": 1.0,
        "range_bound": 0.0,
        "lower_highs_lower_lows": -1.0,
    }

    return mapping.get(
        structure,
        0.0,
    )


def _rsi_pressure_score(
    rsi: float,
) -> float:
    if rsi >= 75:
        return -0.35

    if 60 <= rsi < 75:
        return 0.50

    if 50 <= rsi < 60:
        return 0.20

    if 40 <= rsi < 50:
        return -0.20

    if 25 < rsi < 40:
        return -0.50

    if rsi <= 25:
        return 0.35

    return 0.0


def _macd_score(
    macd_histogram: float,
) -> float:
    if macd_histogram > 0:
        return 1.0

    if macd_histogram < 0:
        return -1.0

    return 0.0


# ============================================================
# REGIME / CONFIDENCE
# ============================================================


def _classify_trend_regime(
    trend_score: float,
) -> str:
    if trend_score >= 0.60:
        return "strong_bullish"

    if trend_score >= 0.20:
        return "bullish"

    if trend_score <= -0.60:
        return "strong_bearish"

    if trend_score <= -0.20:
        return "bearish"

    return "neutral"


def _compute_confidence(
    trend_strength: float,
    trend_score: float,
    ema_alignment: str,
    structure: str,
    momentum_confirmation: str,
) -> float:
    confidence = (
        trend_strength * 0.40
        + abs(trend_score) * 0.25
        + abs(
            _ema_alignment_score(
                ema_alignment,
            )
        )
        * 0.15
        + abs(
            _structure_score(
                structure,
            )
        )
        * 0.10
        + (0.10 if momentum_confirmation != "mixed_confirmation" else 0.0)
    )

    return _clamp(
        confidence,
        0.0,
        1.0,
    )


# ============================================================
# STRATEGY ENVIRONMENT
# ============================================================


def _determine_strategy_environment(
    trend_score: float,
    trend_strength: float,
    trend_regime: str,
) -> Dict[str, float]:
    bull = 1.0
    bear = 1.0
    sideways = 1.0

    if trend_regime == "strong_bullish":
        bull *= 1.25
        bear *= 0.75
        sideways *= 0.85

    elif trend_regime == "bullish":
        bull *= 1.10
        bear *= 0.90
        sideways *= 0.95

    elif trend_regime == "strong_bearish":
        bull *= 0.70
        bear *= 1.20
        sideways *= 1.05

    elif trend_regime == "bearish":
        bull *= 0.85
        bear *= 1.10
        sideways *= 1.05

    if trend_strength < 0.35:
        bull *= 0.90
        bear *= 0.90
        sideways *= 1.15

    if (
        abs(
            trend_score,
        )
        < 0.20
    ):
        sideways *= 1.10

    return {
        "bull": bull,
        "bear": bear,
        "sideways": sideways,
    }
