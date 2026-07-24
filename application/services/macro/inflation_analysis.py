from typing import Any

from domain.macro.models import MacroDataSnapshot


def analyze_inflation_environment(
    macro_data: MacroDataSnapshot,
) -> dict[str, Any]:
    """Classify CPI, core CPI, and PCE into an inflation regime."""

    cpi = macro_data.cpi
    core_cpi = macro_data.core_cpi
    pce = macro_data.pce

    if cpi is None and core_cpi is None:
        return {
            "inflation_regime": "unknown",
            "inflation_pressure": "neutral",
            "trend": "flat",
            "summary": "Insufficient inflation data",
        }

    inflation_score = _cpi_score(cpi) + _core_cpi_score(core_cpi) + _pce_score(pce)
    regime, pressure = _inflation_regime(inflation_score)
    trend = _inflation_trend(cpi=cpi, core_cpi=core_cpi)

    return {
        "inflation_regime": regime,
        "inflation_pressure": pressure,
        "trend": trend,
        "summary": (
            f"Inflation regime is {regime} with {pressure} and {trend} trend behavior."
        ),
    }


def _cpi_score(cpi: float | None) -> int:
    if cpi is None:
        return 0
    if cpi > 5.0:
        return 2
    if cpi > 3.0:
        return 1
    if cpi < 2.0:
        return -1
    return 0


def _core_cpi_score(core_cpi: float | None) -> int:
    if core_cpi is None:
        return 0
    if core_cpi > 4.0:
        return 2
    if core_cpi > 3.0:
        return 1
    if core_cpi < 2.0:
        return -1
    return 0


def _pce_score(pce: float | None) -> int:
    if pce is None:
        return 0
    if pce > 3.5:
        return 2
    if pce > 2.5:
        return 1
    if pce < 2.0:
        return -1
    return 0


def _inflation_regime(score: int) -> tuple[str, str]:
    if score >= 4:
        return "high_inflation", "inflationary_pressure"
    if score >= 2:
        return "elevated_inflation", "moderate_pressure"
    if score >= 0:
        return "moderate_inflation", "balanced"
    return "disinflationary", "deflationary_tendency"


def _inflation_trend(
    *,
    cpi: float | None,
    core_cpi: float | None,
) -> str:
    if not cpi or not core_cpi:
        return "unknown"
    if cpi > core_cpi:
        return "sticky_inflation"
    if cpi < core_cpi:
        return "cooling_inflation"
    return "stable"
