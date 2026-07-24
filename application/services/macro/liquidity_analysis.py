from typing import Any

from domain.macro.models import MacroDataSnapshot


def analyze_liquidity_environment(
    macro_data: MacroDataSnapshot,
) -> dict[str, Any]:
    """Classify deterministic market liquidity conditions."""

    m2 = macro_data.m2_money_supply
    fed_funds = macro_data.fed_funds_rate
    vix = macro_data.vix

    if m2 is None and fed_funds is None:
        return {
            "liquidity_regime": "unknown",
            "liquidity_pressure": "neutral",
            "risk_environment": "neutral",
            "summary": "Insufficient liquidity data",
        }

    liquidity_score = (
        _money_supply_score(m2)
        + _liquidity_rate_score(fed_funds)
        + _volatility_liquidity_score(vix)
    )
    regime, pressure, risk_env = _liquidity_regime(liquidity_score)

    return {
        "liquidity_regime": regime,
        "liquidity_pressure": pressure,
        "risk_environment": risk_env,
        "summary": (
            f"Liquidity regime is {regime} with "
            f"{pressure} conditions and "
            f"{risk_env} market behavior."
        ),
    }


def _money_supply_score(m2: float | None) -> int:
    if m2 is None:
        return 0
    if m2 > 21_000_000:
        return 2
    if m2 > 19_000_000:
        return 1
    if m2 < 18_000_000:
        return -2
    return 0


def _liquidity_rate_score(fed_funds: float | None) -> int:
    if fed_funds is None:
        return 0
    if fed_funds < 2.0:
        return 2
    if fed_funds < 4.0:
        return 1
    if fed_funds > 5.0:
        return -2
    return -1


def _volatility_liquidity_score(vix: float | None) -> int:
    if vix is None:
        return 0
    if vix < 15:
        return 2
    if vix < 20:
        return 1
    if vix > 30:
        return -2
    return -1


def _liquidity_regime(score: int) -> tuple[str, str, str]:
    if score >= 4:
        return "high_liquidity", "risk_on", "bullish_liquidity_tailwind"
    if score >= 2:
        return "moderate_liquidity", "balanced", "neutral"
    if score >= 0:
        return "tightening_liquidity", "risk_off_bias", "fragile"
    return "liquidity_crunch", "risk_off", "defensive"
