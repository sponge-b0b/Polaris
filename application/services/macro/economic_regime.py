from typing import Dict


def classify_economic_regime(
    inflation_analysis: Dict,
    fed_analysis: Dict,
    liquidity_analysis: Dict,
    yield_curve_analysis: Dict,
) -> Dict:
    """
    Polaris Macro Regime Classifier.

    Purpose:
    - combine all macro factors into a single regime
    - produce SPY-friendly market state classification
    - act as final macro decision layer

    Inputs:
    - inflation regime
    - fed stance
    - liquidity conditions
    - yield curve structure

    Output:
    - unified economic regime
    - risk posture
    - market environment label
    """

    # ============================================================
    # EXTRACT INPUT SIGNALS
    # ============================================================

    inflation = inflation_analysis.get(
        "inflation_regime",
        "unknown",
    )

    fed = fed_analysis.get(
        "fed_stance",
        "neutral",
    )

    liquidity = liquidity_analysis.get(
        "liquidity_regime",
        "unknown",
    )

    curve = yield_curve_analysis.get(
        "curve_regime",
        "unknown",
    )

    # ============================================================
    # REGIME SCORING SYSTEM
    # ============================================================

    score = 0

    # ------------------------------------------------------------
    # INFLATION IMPACT
    # ------------------------------------------------------------

    if inflation in (
        "high_inflation",
        "elevated_inflation",
    ):
        score -= 2

    elif inflation in ("moderate_inflation",):
        score -= 1

    elif inflation in ("disinflationary",):
        score += 2

    # ------------------------------------------------------------
    # FED POLICY IMPACT
    # ------------------------------------------------------------

    if fed == "hawkish":
        score -= 2

    elif fed == "neutral":
        score -= 1

    elif fed == "dovish":
        score += 2

    # ------------------------------------------------------------
    # LIQUIDITY IMPACT
    # ------------------------------------------------------------

    if liquidity == "high_liquidity":
        score += 3

    elif liquidity == "moderate_liquidity":
        score += 1

    elif liquidity in (
        "tightening_liquidity",
        "liquidity_crunch",
    ):
        score -= 3

    # ------------------------------------------------------------
    # YIELD CURVE IMPACT
    # ------------------------------------------------------------

    if curve == "steep_curve":
        score += 2

    elif curve == "normal_curve":
        score += 1

    elif curve in (
        "flat_curve",
        "inverted_curve",
        "deep_inversion",
    ):
        score -= 3

    # ============================================================
    # FINAL REGIME CLASSIFICATION
    # ============================================================

    if score >= 5:
        regime = "risk_on_expansion"

    elif score >= 2:
        regime = "constructive_growth"

    elif score >= -1:
        regime = "neutral_choppy"

    elif score >= -4:
        regime = "risk_off"

    else:
        regime = "crisis_risk_off"

    # ============================================================
    # MARKET INTERPRETATION
    # ============================================================

    if regime in (
        "risk_on_expansion",
        "constructive_growth",
    ):
        market_bias = "bullish_bias"

    elif regime == "neutral_choppy":
        market_bias = "range_bound"

    else:
        market_bias = "bearish_bias"

    # ============================================================
    # OUTPUT
    # ============================================================

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
        "summary": (f"Macro regime is {regime} with {market_bias} and score {score}."),
    }
