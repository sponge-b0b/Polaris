from typing import Any

from domain.macro.models import MacroDataSnapshot


def analyze_fed_environment(
    macro_data: MacroDataSnapshot,
) -> dict[str, Any]:
    """
    Analyze Federal Reserve policy stance
    from macroeconomic inputs.

    This module is deterministic:
    - no LLM
    - no external APIs
    - pure rule-based classification

    Output is used by MacroService.
    """

    fed_funds = macro_data.fed_funds_rate

    inflation = macro_data.cpi

    core_inflation = macro_data.core_cpi

    unemployment = macro_data.unemployment_rate

    analysis: dict[str, Any] = {
        "fed_stance": "neutral",
        "policy_pressure": "balanced",
        "rate_environment": "uncertain",
        "summary": "",
    }

    # ============================================================
    # BASIC VALIDATION
    # ============================================================

    if fed_funds is None:
        analysis["summary"] = "Insufficient data for Fed analysis"
        return analysis

    # ============================================================
    # INFLATION PRESSURE SIGNAL
    # ============================================================

    inflation_pressure = 0

    if inflation is not None:
        if inflation > 3.0:
            inflation_pressure += 1
        if inflation > 5.0:
            inflation_pressure += 1

    if core_inflation is not None:
        if core_inflation > 3.0:
            inflation_pressure += 1

    # ============================================================
    # LABOR MARKET SIGNAL
    # ============================================================

    labor_pressure = 0

    if unemployment is not None:
        if unemployment < 4.0:
            labor_pressure += 1  # tight labor market

        if unemployment > 5.0:
            labor_pressure -= 1  # weakening economy

    # ============================================================
    # RATE CONTEXT CLASSIFICATION
    # ============================================================

    if fed_funds < 2.0:
        rate_env = "low_rate"
    elif fed_funds < 4.0:
        rate_env = "moderate_rate"
    else:
        rate_env = "high_rate"

    analysis["rate_environment"] = rate_env

    # ============================================================
    # FED STANCE CLASSIFICATION
    # ============================================================

    total_pressure = inflation_pressure + labor_pressure

    if total_pressure >= 2:
        fed_stance = "hawkish"
    elif total_pressure <= -1:
        fed_stance = "dovish"
    else:
        fed_stance = "neutral"

    analysis["fed_stance"] = fed_stance

    # ============================================================
    # POLICY PRESSURE
    # ============================================================

    if inflation_pressure > 1:
        policy_pressure = "tightening_bias"
    elif labor_pressure < 0:
        policy_pressure = "easing_bias"
    else:
        policy_pressure = "balanced"

    analysis["policy_pressure"] = policy_pressure

    # ============================================================
    # SUMMARY
    # ============================================================

    analysis["summary"] = (
        f"Fed stance is {fed_stance} with "
        f"{rate_env} environment and "
        f"{policy_pressure} policy pressure."
    )

    return analysis
