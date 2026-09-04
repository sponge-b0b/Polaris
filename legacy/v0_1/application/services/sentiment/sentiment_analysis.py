from __future__ import annotations

from typing import Any


def build_features(
    sentiment_snapshot: dict[str, Any],
    previous_snapshot: dict[str, Any] | None = None,
    risk_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build deterministic sentiment features.
    """

    raw_score = _clamp(sentiment_snapshot.get("sentiment_score", 0.0))

    overall_sentiment = sentiment_snapshot.get(
        "overall_sentiment",
        "neutral",
    )
    components = sentiment_snapshot.get("components", {})

    news = _clamp(components.get("news", raw_score))
    social = _clamp(components.get("social", raw_score))
    insider = _clamp(components.get("insider", raw_score))

    sentiment_score = _clamp(raw_score)

    news_social_div = abs(news - social)
    news_insider_div = abs(news - insider)
    social_insider_div = abs(social - insider)

    avg_divergence = (news_social_div + news_insider_div + social_insider_div) / 3.0

    avg_divergence = min(avg_divergence, 2.0)

    stability = _clamp_01(1.0 - (avg_divergence / 2.0))

    if previous_snapshot:
        prev = _clamp(
            previous_snapshot.get(
                "sentiment_score",
                sentiment_score,
            )
        )
        raw_momentum = sentiment_score - prev
    else:
        raw_momentum = 0.0

    momentum = _clamp(raw_momentum * 0.5)
    regime_bias = _map_regime_bias(overall_sentiment)

    risk_multiplier = 1.0

    if risk_state:
        volatility = abs(float(risk_state.get("volatility", 0.0)))
        drawdown = abs(float(risk_state.get("drawdown_risk", 0.0)))

        risk_multiplier = max(
            0.25,
            1.0 - (volatility * 0.25) - (drawdown * 0.35),
        )

    directional_signal = _clamp(
        (sentiment_score * 0.55 + regime_bias * 0.20 + momentum * 0.25)
        * stability
        * risk_multiplier
    )

    interpretation = _classify(directional_signal)

    return {
        "sentiment_score": sentiment_score,
        "directional_signal": directional_signal,
        "sentiment_regime": overall_sentiment,
        "interpretation": interpretation,
        "components": {
            "news": news,
            "social": social,
            "insider": insider,
        },
        "divergence": {
            "news_social": news_social_div,
            "news_insider": news_insider_div,
            "social_insider": social_insider_div,
            "avg_divergence": avg_divergence,
        },
        "momentum": momentum,
        "stability": stability,
        "regime_bias": regime_bias,
        "risk_multiplier": risk_multiplier,
        "raw": sentiment_snapshot,
    }


def _map_regime_bias(
    regime: str,
) -> float:
    mapping = {
        "strongly_bullish": 1.0,
        "bullish": 0.6,
        "moderately_bullish": 0.3,
        "neutral": 0.0,
        "moderately_bearish": -0.3,
        "bearish": -0.6,
        "strongly_bearish": -1.0,
    }

    return mapping.get(regime, 0.0)


def _classify(
    signal: float,
) -> str:
    if signal >= 0.75:
        return "high_conviction_bullish"

    if signal >= 0.35:
        return "moderate_bullish"

    if signal <= -0.75:
        return "high_conviction_bearish"

    if signal <= -0.35:
        return "moderate_bearish"

    return "neutral_choppy"


def _clamp(
    value: float,
) -> float:
    try:
        return max(-1.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _clamp_01(
    value: float,
) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0
