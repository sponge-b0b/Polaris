from typing import Any

from domain.macro.models import MacroDataSnapshot


def analyze_fed_environment(
    macro_data: MacroDataSnapshot,
) -> dict[str, Any]:
    """Analyze Federal Reserve policy stance from macroeconomic inputs."""

    fed_funds = macro_data.fed_funds_rate
    if fed_funds is None:
        return {
            "fed_stance": "neutral",
            "policy_pressure": "balanced",
            "rate_environment": "uncertain",
            "summary": "Insufficient data for Fed analysis",
        }

    inflation_pressure = _inflation_policy_pressure(
        inflation=macro_data.cpi,
        core_inflation=macro_data.core_cpi,
    )
    labor_pressure = _labor_policy_pressure(macro_data.unemployment_rate)
    rate_env = _rate_environment(fed_funds)
    fed_stance = _fed_stance(inflation_pressure + labor_pressure)
    policy_pressure = _policy_pressure(
        inflation_pressure=inflation_pressure,
        labor_pressure=labor_pressure,
    )

    return {
        "fed_stance": fed_stance,
        "policy_pressure": policy_pressure,
        "rate_environment": rate_env,
        "summary": (
            f"Fed stance is {fed_stance} with "
            f"{rate_env} environment and "
            f"{policy_pressure} policy pressure."
        ),
    }


def _inflation_policy_pressure(
    *,
    inflation: float | None,
    core_inflation: float | None,
) -> int:
    pressure = 0
    if inflation is not None:
        pressure += int(inflation > 3.0)
        pressure += int(inflation > 5.0)
    if core_inflation is not None and core_inflation > 3.0:
        pressure += 1
    return pressure


def _labor_policy_pressure(unemployment: float | None) -> int:
    if unemployment is None:
        return 0
    if unemployment < 4.0:
        return 1
    if unemployment > 5.0:
        return -1
    return 0


def _rate_environment(fed_funds: float) -> str:
    if fed_funds < 2.0:
        return "low_rate"
    if fed_funds < 4.0:
        return "moderate_rate"
    return "high_rate"


def _fed_stance(total_pressure: int) -> str:
    if total_pressure >= 2:
        return "hawkish"
    if total_pressure <= -1:
        return "dovish"
    return "neutral"


def _policy_pressure(
    *,
    inflation_pressure: int,
    labor_pressure: int,
) -> str:
    if inflation_pressure > 1:
        return "tightening_bias"
    if labor_pressure < 0:
        return "easing_bias"
    return "balanced"
