from typing import Any

from domain.macro.models import MacroDataSnapshot


def analyze_liquidity_environment(
    macro_data: MacroDataSnapshot,
) -> dict[str, Any]:
    """
    Deterministic liquidity regime classifier.

    Purpose:
    - assess market liquidity conditions
    - infer risk appetite environment
    - support SPY swing trading regime logic

    Liquidity is derived from:
    - M2 money supply
    - interest rate environment
    - yield curve structure
    - volatility proxy (VIX)
    """

    m2 = macro_data.m2_money_supply
    fed_funds = macro_data.fed_funds_rate
    vix = macro_data.vix

    analysis: dict[str, Any] = {
        "liquidity_regime": "unknown",
        "liquidity_pressure": "neutral",
        "risk_environment": "neutral",
        "summary": "",
    }

    # ============================================================
    # VALIDATION
    # ============================================================

    if m2 is None and fed_funds is None:
        analysis["summary"] = "Insufficient liquidity data"
        return analysis

    # ============================================================
    # LIQUIDITY SCORE MODEL
    # ============================================================

    liquidity_score = 0

    # ------------------------------------------------------------
    # MONEY SUPPLY (M2)
    # ------------------------------------------------------------

    if m2 is not None:
        # NOTE: we are NOT modeling growth rate precisely here yet
        # This is a simplified level-based heuristic

        if m2 > 21_000_000:
            liquidity_score += 2
        elif m2 > 19_000_000:
            liquidity_score += 1
        elif m2 < 18_000_000:
            liquidity_score -= 2

    # ------------------------------------------------------------
    # INTEREST RATE ENVIRONMENT
    # ------------------------------------------------------------

    if fed_funds is not None:
        if fed_funds < 2.0:
            liquidity_score += 2  # very loose
        elif fed_funds < 4.0:
            liquidity_score += 1  # moderate
        elif fed_funds > 5.0:
            liquidity_score -= 2  # tight liquidity
        else:
            liquidity_score -= 1

    # ------------------------------------------------------------
    # VOLATILITY (RISK APPETITE PROXY)
    # ------------------------------------------------------------

    if vix is not None:
        if vix < 15:
            liquidity_score += 2  # risk-on environment
        elif vix < 20:
            liquidity_score += 1
        elif vix > 30:
            liquidity_score -= 2  # risk-off stress
        else:
            liquidity_score -= 1

    # ============================================================
    # REGIME CLASSIFICATION
    # ============================================================

    if liquidity_score >= 4:
        regime = "high_liquidity"
        pressure = "risk_on"
        risk_env = "bullish_liquidity_tailwind"

    elif liquidity_score >= 2:
        regime = "moderate_liquidity"
        pressure = "balanced"
        risk_env = "neutral"

    elif liquidity_score >= 0:
        regime = "tightening_liquidity"
        pressure = "risk_off_bias"
        risk_env = "fragile"

    else:
        regime = "liquidity_crunch"
        pressure = "risk_off"
        risk_env = "defensive"

    analysis["liquidity_regime"] = regime
    analysis["liquidity_pressure"] = pressure
    analysis["risk_environment"] = risk_env

    # ============================================================
    # SUMMARY
    # ============================================================

    analysis["summary"] = (
        f"Liquidity regime is {regime} with "
        f"{pressure} conditions and "
        f"{risk_env} market behavior."
    )

    return analysis
