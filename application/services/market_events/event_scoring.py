from typing import Any

"""
Polaris Market Event Scoring Engine (CORE INTELLIGENCE LAYER)

PURPOSE:
--------
Converts heterogeneous market events into a unified:
- impact score
- volatility contribution
- regime pressure signal

This is the CENTRAL normalization brain for:
- economic calendar events
- Fed events
- earnings events

OUTPUT IS USED BY:
------------------
- MarketEventsService
- StrategySynthesisAgent
- RiskAggregatorAgent
"""

# ============================================================
# MAIN SCORING ENTRY POINT
# ============================================================


def score_event(
    event: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert raw normalized event into scored event.
    """

    event_type = event.get("event_type", "unknown")

    base_impact = float(event.get("impact", 0.5))

    # ========================================================
    # TYPE-BASED SCORING WEIGHTS
    # ========================================================

    if event_type == "fed":
        scored = _score_fed_event(event, base_impact)

    elif event_type == "macro":
        scored = _score_macro_event(event, base_impact)

    elif event_type == "earnings":
        scored = _score_earnings_event(event, base_impact)

    else:
        scored = _default_score(event, base_impact)

    # ========================================================
    # FINAL NORMALIZATION
    # ========================================================

    scored["impact_score"] = min(
        max(scored["impact_score"], 0.0),
        1.0,
    )

    scored["volatility_score"] = min(
        max(scored["volatility_score"], 0.0),
        1.0,
    )

    return scored


# ============================================================
# FED EVENT SCORING
# ============================================================


def _score_fed_event(
    event: dict[str, Any],
    base: float,
) -> dict[str, Any]:

    subtype = event.get("subtype", "speech")

    # Fed events dominate macro structure
    multiplier = {
        "rate_decision": 1.6,
        "speech": 1.4,
        "minutes": 1.2,
    }.get(subtype, 1.0)

    impact_score = base * multiplier
    volatility_score = impact_score * 1.1

    return {
        **event,
        "impact_score": impact_score,
        "volatility_score": volatility_score,
        "regime_weight": 1.0,
        "category": "monetary_policy",
    }


# ============================================================
# MACRO EVENT SCORING
# ============================================================


def _score_macro_event(
    event: dict[str, Any],
    base: float,
) -> dict[str, Any]:

    # macro events are slower-moving but regime-relevant
    importance_weight = 1.2

    impact_score = base * importance_weight
    volatility_score = base * 0.8

    return {
        **event,
        "impact_score": impact_score,
        "volatility_score": volatility_score,
        "regime_weight": 0.8,
        "category": "macro_data",
    }


# ============================================================
# EARNINGS EVENT SCORING
# ============================================================


def _score_earnings_event(
    event: dict[str, Any],
    base: float,
) -> dict[str, Any]:

    weight = float(event.get("market_cap_weight", 0.01))

    # nonlinear amplification for mega caps
    amplification = 1.0 + (weight * 4.0)

    impact_score = base * amplification

    volatility_score = impact_score * 1.3

    return {
        **event,
        "impact_score": impact_score,
        "volatility_score": volatility_score,
        "regime_weight": 0.6,
        "category": "earnings_volatility",
    }


# ============================================================
# DEFAULT SCORING
# ============================================================


def _default_score(
    event: dict[str, Any],
    base: float,
) -> dict[str, Any]:

    return {
        **event,
        "impact_score": base,
        "volatility_score": base * 0.5,
        "regime_weight": 0.5,
        "category": "unknown",
    }
