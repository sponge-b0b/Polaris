from typing import Any

from domain.macro.models import MacroDataSnapshot


def analyze_inflation_environment(  # noqa: C901
    macro_data: MacroDataSnapshot,
) -> dict[str, Any]:
    """
    Deterministic inflation regime classifier.

    Purpose:
    - interpret CPI + core CPI + PCE signals
    - classify inflation environment for SPY macro context

    This is NOT forecasting.
    This is regime labeling only.
    """

    cpi = macro_data.cpi
    core_cpi = macro_data.core_cpi
    pce = macro_data.pce

    analysis: dict[str, Any] = {
        "inflation_regime": "unknown",
        "inflation_pressure": "neutral",
        "trend": "flat",
        "summary": "",
    }

    # ============================================================
    # VALIDATION
    # ============================================================

    if cpi is None and core_cpi is None:
        analysis["summary"] = "Insufficient inflation data"
        return analysis

    # ============================================================
    # INFLATION LEVEL CLASSIFICATION
    # ============================================================

    inflation_score = 0

    # CPI SIGNAL
    if cpi is not None:
        if cpi > 5.0:
            inflation_score += 2
        elif cpi > 3.0:
            inflation_score += 1
        elif cpi < 2.0:
            inflation_score -= 1

    # CORE CPI SIGNAL
    if core_cpi is not None:
        if core_cpi > 4.0:
            inflation_score += 2
        elif core_cpi > 3.0:
            inflation_score += 1
        elif core_cpi < 2.0:
            inflation_score -= 1

    # PCE SIGNAL (Fed preferred metric)
    if pce is not None:
        if pce > 3.5:
            inflation_score += 2
        elif pce > 2.5:
            inflation_score += 1
        elif pce < 2.0:
            inflation_score -= 1

    # ============================================================
    # REGIME CLASSIFICATION
    # ============================================================

    if inflation_score >= 4:
        regime = "high_inflation"
        pressure = "inflationary_pressure"

    elif inflation_score >= 2:
        regime = "elevated_inflation"
        pressure = "moderate_pressure"

    elif inflation_score >= 0:
        regime = "moderate_inflation"
        pressure = "balanced"

    else:
        regime = "disinflationary"
        pressure = "deflationary_tendency"

    analysis["inflation_regime"] = regime
    analysis["inflation_pressure"] = pressure

    # ============================================================
    # TREND ESTIMATION (SIMPLE HEURISTIC)
    # ============================================================

    if cpi and core_cpi:
        if cpi > core_cpi:
            trend = "sticky_inflation"
        elif cpi < core_cpi:
            trend = "cooling_inflation"
        else:
            trend = "stable"
    else:
        trend = "unknown"

    analysis["trend"] = trend

    # ============================================================
    # SUMMARY
    # ============================================================

    analysis["summary"] = (
        f"Inflation regime is {regime} with {pressure} and {trend} trend behavior."
    )

    return analysis
