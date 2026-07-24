from typing import Any

_REGIME_SCORE_BY_INFLATION = {
    "high_inflation": -2,
    "elevated_inflation": -2,
    "moderate_inflation": -1,
    "disinflationary": 2,
}

_REGIME_SCORE_BY_FED_STANCE = {
    "hawkish": -2,
    "neutral": -1,
    "dovish": 2,
}

_REGIME_SCORE_BY_LIQUIDITY = {
    "high_liquidity": 3,
    "moderate_liquidity": 1,
    "tightening_liquidity": -3,
    "liquidity_crunch": -3,
}

_REGIME_SCORE_BY_CURVE = {
    "steep_curve": 2,
    "normal_curve": 1,
    "flat_curve": -3,
    "inverted_curve": -3,
    "deep_inversion": -3,
}


def classify_economic_regime(
    inflation_analysis: dict[str, Any],
    fed_analysis: dict[str, Any],
    liquidity_analysis: dict[str, Any],
    yield_curve_analysis: dict[str, Any],
) -> dict[str, Any]:
    """Combine macro factor classifications into one market regime label."""

    inflation = inflation_analysis.get("inflation_regime", "unknown")
    fed = fed_analysis.get("fed_stance", "neutral")
    liquidity = liquidity_analysis.get("liquidity_regime", "unknown")
    curve = yield_curve_analysis.get("curve_regime", "unknown")

    score = _macro_regime_score(
        inflation=inflation,
        fed=fed,
        liquidity=liquidity,
        curve=curve,
    )
    regime = _economic_regime_for_score(score)
    market_bias = _market_bias_for_regime(regime)

    return {
        "economic_regime": regime,
        "market_bias": market_bias,
        "macro_score": score,
        "components": {
            "inflation": inflation,
            "fed": fed,
            "liquidity": liquidity,
            "curve": curve,
        },
        "summary": f"Macro regime is {regime} with {market_bias} and score {score}.",
    }


def _macro_regime_score(
    *,
    inflation: Any,
    fed: Any,
    liquidity: Any,
    curve: Any,
) -> int:
    return (
        _REGIME_SCORE_BY_INFLATION.get(inflation, 0)
        + _REGIME_SCORE_BY_FED_STANCE.get(fed, 0)
        + _REGIME_SCORE_BY_LIQUIDITY.get(liquidity, 0)
        + _REGIME_SCORE_BY_CURVE.get(curve, 0)
    )


def _economic_regime_for_score(score: int) -> str:
    if score >= 5:
        return "risk_on_expansion"
    if score >= 2:
        return "constructive_growth"
    if score >= -1:
        return "neutral_choppy"
    if score >= -4:
        return "risk_off"
    return "crisis_risk_off"


def _market_bias_for_regime(regime: str) -> str:
    if regime in {"risk_on_expansion", "constructive_growth"}:
        return "bullish_bias"
    if regime == "neutral_choppy":
        return "range_bound"
    return "bearish_bias"
