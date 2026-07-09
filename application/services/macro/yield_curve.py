from typing import Any

from domain.macro.models import MacroDataSnapshot


def analyze_yield_curve(
    macro_data: MacroDataSnapshot,
) -> dict[str, Any]:
    """
    Deterministic yield curve regime classifier.

    Purpose:
    - detect recession signals
    - evaluate risk sentiment shifts
    - support SPY macro regime transitions

    Core concept:
    - inverted curve = risk-off / recessionary pressure
    - steep curve = growth / risk-on environment
    """

    y2 = macro_data.treasury_2y
    y10 = macro_data.treasury_10y

    analysis: dict[str, Any] = {
        "curve_regime": "unknown",
        "curve_slope": None,
        "recession_signal": "neutral",
        "summary": "",
    }

    # ============================================================
    # VALIDATION
    # ============================================================

    if y2 is None or y10 is None:
        analysis["summary"] = "Insufficient yield curve data"
        return analysis

    # ============================================================
    # CALCULATE SPREAD
    # ============================================================

    spread = y10 - y2
    analysis["curve_slope"] = spread

    # ============================================================
    # REGIME CLASSIFICATION
    # ============================================================

    # ------------------------------------------------------------
    # SEVERELY INVERTED CURVE
    # ------------------------------------------------------------

    if spread < -0.5:
        regime = "deep_inversion"
        recession_signal = "high_recession_risk"

    # ------------------------------------------------------------
    # INVERTED CURVE
    # ------------------------------------------------------------

    elif spread < 0:
        regime = "inverted_curve"
        recession_signal = "elevated_recession_risk"

    # ------------------------------------------------------------
    # FLAT CURVE
    # ------------------------------------------------------------

    elif spread < 0.5:
        regime = "flat_curve"
        recession_signal = "uncertain_growth"

    # ------------------------------------------------------------
    # NORMAL CURVE
    # ------------------------------------------------------------

    elif spread < 1.5:
        regime = "normal_curve"
        recession_signal = "stable_growth"

    # ------------------------------------------------------------
    # STEEP CURVE
    # ------------------------------------------------------------

    else:
        regime = "steep_curve"
        recession_signal = "growth_expansion"

    analysis["curve_regime"] = regime
    analysis["recession_signal"] = recession_signal

    # ============================================================
    # INTERPRETATION LAYER
    # ============================================================

    if spread < 0:
        interpretation = "risk_off_bias"
    elif spread < 0.5:
        interpretation = "defensive_market"
    elif spread < 1.5:
        interpretation = "neutral_growth"
    else:
        interpretation = "risk_on_expansion"

    analysis["market_interpretation"] = interpretation

    # ============================================================
    # SUMMARY
    # ============================================================

    analysis["summary"] = (
        f"Yield curve is {regime} with "
        f"{spread:.2f} spread, "
        f"indicating {recession_signal} and "
        f"{interpretation} conditions."
    )

    return analysis
