from __future__ import annotations

from typing import Any


def synthesize(
    features: dict[str, Any],
) -> dict[str, Any]:
    """
    Synthesize deterministic sentiment features into a fused state.
    """

    sentiment_score = _clamp_score(features.get("sentiment_score", 0.0))

    directional_signal = _clamp_score(features.get("directional_signal", 0.0))

    momentum = _clamp_score(features.get("momentum", 0.0))

    stability = _clamp_unit(features.get("stability", 1.0))

    divergence = float(features.get("divergence", {}).get("avg_divergence", 0.0))

    risk_multiplier = _clamp_unit(features.get("risk_multiplier", 1.0))

    components = features.get("components", {})

    news_signal = _clamp_score(components.get("news", sentiment_score))

    social_signal = _clamp_score(components.get("social", sentiment_score))

    insider_signal = _clamp_score(components.get("insider", sentiment_score))

    stability_weight = 0.65 + (stability * 0.20)

    composite = (
        directional_signal * 0.38
        + sentiment_score * 0.22
        + news_signal * 0.15
        + social_signal * 0.10
        + insider_signal * 0.10
        + momentum * 0.05
    )

    composite *= stability_weight
    composite *= risk_multiplier
    composite = _clamp_score(composite)

    confidence = _compute_confidence(
        composite=composite,
        stability=stability,
        divergence=divergence,
    )

    regime = _classify_regime(composite)

    unstable = abs(momentum) > 0.7 and divergence > 1.5

    if unstable:
        regime = f"unstable_{regime}"

    return {
        "composite_sentiment": composite,
        "confidence": confidence,
        "regime": regime,
        "momentum": momentum,
        "stability": stability,
        "divergence": divergence,
        "market_bias": _classify_bias(composite),
        "fusion_components": {
            "directional_signal": directional_signal,
            "sentiment_score": sentiment_score,
            "news_signal": news_signal,
            "social_signal": social_signal,
            "insider_signal": insider_signal,
        },
    }


def _compute_confidence(
    composite: float,
    stability: float,
    divergence: float,
) -> float:
    directional_strength = abs(composite)

    confidence = directional_strength * 0.55 + stability * 0.35

    confidence -= min(divergence / 4.0, 0.25)

    return _clamp_unit(confidence)


def _classify_regime(
    composite: float,
) -> str:
    if composite >= 0.65:
        return "strong_risk_on"

    if composite >= 0.25:
        return "risk_on"

    if composite <= -0.65:
        return "strong_risk_off"

    if composite <= -0.25:
        return "risk_off"

    return "neutral"


def _classify_bias(
    composite: float,
) -> str:
    if composite >= 0.45:
        return "bullish"

    if composite <= -0.45:
        return "bearish"

    return "neutral"


def _clamp_score(
    value: float,
) -> float:
    return max(-1.0, min(1.0, float(value)))


def _clamp_unit(
    value: float,
) -> float:
    return max(0.0, min(1.0, float(value)))
