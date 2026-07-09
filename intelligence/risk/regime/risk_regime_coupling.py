from __future__ import annotations

from typing import Any

from intelligence.analysts.technical.technical_breadth_context import (
    TechnicalBreadthContext,
)

"""
Polaris Risk-Regime Coupling Layer V2 (Production)

IMPROVEMENTS:
-------------
- Aligns with calibrated technical regime output
- Prevents double-dampening of risk signals
- Stabilizes strong trend behavior (SPY regime fix)
- Reduces over-defensive neutral market bias
- Adds smoother risk modulation curve
"""

# ============================================================
# MAIN ENTRY
# ============================================================


def apply(
    risk: dict[str, Any],
    technical_regime: dict[str, Any],
    volatility: dict[str, Any],
    breadth_context: TechnicalBreadthContext | None = None,
) -> dict[str, Any]:

    # ========================================================
    # CORE RISK INPUTS
    # ========================================================

    composite_risk = float(risk["composite_risk"])
    risk_pressure = float(risk["risk_pressure"])
    stability = float(risk["stability_score"])

    # ========================================================
    # TECHNICAL INPUTS (CALIBRATED SYSTEM)
    # ========================================================

    regime = technical_regime.get("regime", "neutral")

    calibrated_score = float(technical_regime.get("directional_technical_score", 0.0))

    confidence = float(technical_regime.get("confidence", 0.5))

    execution_readiness = float(technical_regime.get("execution_readiness", confidence))

    # fallback safety
    signal_quality = float(technical_regime.get("signal_quality", confidence))

    vol_score = float(volatility.get("volatility_score", 0.5))

    # ========================================================
    # 1. REGIME MULTIPLIER (SOFTENED & STABILIZED)
    # ========================================================

    regime_multiplier = _regime_multiplier(
        regime=regime,
        calibrated_score=calibrated_score,
        confidence=confidence,
        execution_readiness=execution_readiness,
    )

    # ========================================================
    # 2. VOLATILITY MODIFIER (REDUCED IMPACT)
    # ========================================================

    volatility_modifier = _volatility_modifier(vol_score)

    # ========================================================
    # 3. BREADTH MODIFIERS (CONFIRMATION CONTEXT)
    # ========================================================

    breadth_modifier = _breadth_modifier(
        breadth_context,
    )

    breadth_pressure_adjustment = _breadth_pressure_adjustment(
        breadth_context,
    )

    # ========================================================
    # 4. STABILITY BUFFER (SMOOTHED)
    # ========================================================

    stability_buffer = 0.60 + (stability * 0.40)

    # ========================================================
    # 5. SIGNAL QUALITY BUFFER (LESS AGGRESSIVE)
    # ========================================================

    quality_buffer = 0.75 + (signal_quality * 0.25)

    # ========================================================
    # 6. ADJUSTED RISK COMPONENTS
    # ========================================================

    adjusted_risk_pressure = _clamp_01(
        (risk_pressure * regime_multiplier) + breadth_pressure_adjustment,
    )
    adjusted_composite_risk = _clamp_01(
        composite_risk * regime_multiplier * volatility_modifier * breadth_modifier,
    )

    # ========================================================
    # 7. FINAL RISK SCORE (SIMPLIFIED WEIGHTING)
    # ========================================================

    adjusted_risk_score = (
        adjusted_composite_risk * 0.50
        + adjusted_risk_pressure * 0.30
        + (1.0 - stability) * 0.20
    )

    # Apply buffers (reduced compounding risk)
    adjusted_risk_score *= quality_buffer
    adjusted_risk_score *= stability_buffer

    # ========================================================
    # HARD CLAMP
    # ========================================================

    adjusted_risk_score = _clamp(
        adjusted_risk_score,
        minimum=-1.0,
        maximum=1.0,
    )

    # ========================================================
    # RISK INTENSITY CLASSIFICATION
    # ========================================================

    risk_intensity = _classify_intensity(adjusted_risk_score)

    # ========================================================
    # OUTPUT
    # ========================================================

    return {
        "adjusted_composite_risk": adjusted_composite_risk,
        "adjusted_risk_pressure": adjusted_risk_pressure,
        "adjusted_risk_score": adjusted_risk_score,
        "risk_intensity": risk_intensity,
        "modifiers": {
            "regime_multiplier": regime_multiplier,
            "volatility_modifier": volatility_modifier,
            "breadth_modifier": breadth_modifier,
            "breadth_pressure_adjustment": breadth_pressure_adjustment,
            "quality_buffer": quality_buffer,
            "stability_buffer": stability_buffer,
        },
        "inputs": {
            "original_composite_risk": composite_risk,
            "risk_pressure": risk_pressure,
            "stability": stability,
            "tech_regime": regime,
            "calibrated_score": calibrated_score,
            "confidence": confidence,
            "execution_readiness": execution_readiness,
            "breadth_context": _breadth_context_payload(
                breadth_context,
            ),
        },
    }


# ============================================================
# REGIME MULTIPLIER (SMOOTHED CURVE LOGIC)
# ============================================================


def _regime_multiplier(
    regime: str,
    calibrated_score: float,
    confidence: float,
    execution_readiness: float,
) -> float:

    directional_strength = abs(calibrated_score)

    # ========================================================
    # STRONG TREND (LESS AGGRESSIVE THAN BEFORE)
    # ========================================================

    if (
        directional_strength >= 0.75
        and confidence >= 0.70
        and execution_readiness >= 0.70
    ):
        return 0.88  # was 0.82 → softened

    # ========================================================
    # HEALTHY TREND
    # ========================================================

    if directional_strength >= 0.45 and confidence >= 0.55:
        return 0.95  # slightly less aggressive

    # ========================================================
    # NEUTRAL MARKET
    # ========================================================

    if regime == "neutral":
        return 1.05  # reduced from 1.10

    # ========================================================
    # LOW CONFIDENCE
    # ========================================================

    if confidence < 0.40:
        return 1.08  # reduced from 1.15

    return 1.0


# ============================================================
# VOLATILITY MODIFIER (REDUCED PENALTY CURVE)
# ============================================================


def _volatility_modifier(vol_score: float) -> float:

    # high stability
    if vol_score >= 0.80:
        return 0.93  # softened

    # normal regime
    if vol_score >= 0.55:
        return 1.0

    # unstable
    return 1.10  # reduced from 1.15


# ============================================================
# BREADTH MODIFIERS
# ============================================================


def _breadth_modifier(
    breadth_context: TechnicalBreadthContext | None,
) -> float:
    if breadth_context is None or not breadth_context.has_breadth_data:
        return 1.0

    if breadth_context.is_strong:
        return 0.94

    pressure_delta = max(
        0.0,
        breadth_context.risk_pressure - 0.50,
    )
    confirmation_penalty = (
        max(
            0.0,
            -breadth_context.confirmation_score,
        )
        * 0.08
    )

    modifier = 1.0 + min(
        0.12,
        (pressure_delta * 0.16) + confirmation_penalty,
    )

    if breadth_context.price_ad_divergence:
        modifier += 0.04

    return min(
        1.16,
        modifier,
    )


def _breadth_pressure_adjustment(
    breadth_context: TechnicalBreadthContext | None,
) -> float:
    if breadth_context is None or not breadth_context.has_breadth_data:
        return 0.0

    if breadth_context.is_strong:
        return -0.04

    adjustment = (
        max(
            0.0,
            breadth_context.risk_pressure - 0.50,
        )
        * 0.12
    )

    if breadth_context.price_ad_divergence:
        adjustment += 0.04

    if breadth_context.participation_score <= -0.25:
        adjustment += 0.03

    if breadth_context.mcclellan_score <= -0.25:
        adjustment += 0.02

    return min(
        0.12,
        adjustment,
    )


def _breadth_context_payload(
    breadth_context: TechnicalBreadthContext | None,
) -> dict[str, Any]:
    if breadth_context is None:
        return TechnicalBreadthContext.unavailable().to_dict()

    return breadth_context.to_dict()


# ============================================================
# INTENSITY CLASSIFIER (UNCHANGED)
# ============================================================


def _classify_intensity(score: float) -> str:

    if score >= 0.60:
        return "high_risk"

    if score >= 0.25:
        return "moderate_risk"

    if score <= -0.60:
        return "risk_favorable"

    if score <= -0.25:
        return "low_risk"

    return "neutral"


def _clamp_01(
    value: float,
) -> float:
    return _clamp(
        value,
        minimum=0.0,
        maximum=1.0,
    )


def _clamp(
    value: float,
    *,
    minimum: float,
    maximum: float,
) -> float:
    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )
