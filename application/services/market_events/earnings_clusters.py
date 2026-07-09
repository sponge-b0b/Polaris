from typing import Any, Dict, List

"""
Polaris Earnings Events Engine

PURPOSE:
--------
Tracks earnings-driven volatility clusters across:
- SPY constituents (aggregate impact)
- key mega-cap drivers (AAPL, MSFT, NVDA, AMZN, etc.)

ROLE IN SYSTEM:
--------------
Earnings do NOT define macro regime.

They define:
- volatility expansion windows
- dispersion risk
- short-term directional noise
"""


def get_clusters(
    events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Convert earnings events into volatility-impact events.
    """

    normalized = []

    for event in events:
        weight = event.get("market_cap_weight", 0.01)

        # ====================================================
        # VOLATILITY MODEL
        # ====================================================
        # Earnings impact is nonlinear:
        # - larger caps → systemic SPY volatility
        # - clustered earnings → volatility spikes

        base_volatility = 0.4

        volatility_score = base_volatility + (weight * 5.0)

        volatility_score = min(volatility_score, 1.0)

        # ====================================================
        # DIRECTIONAL BIAS (neutral by default)
        # ====================================================

        bias = "neutral"

        # ====================================================
        # EVENT OBJECT
        # ====================================================

        normalized.append(
            {
                "name": f"{event.get('company')} Earnings",
                "event_type": "earnings",
                "timestamp": event.get("report_date"),
                "symbol": event.get("symbol"),
                "impact": volatility_score,
                "volatility_score": volatility_score,
                "direction_bias": bias,
                "market_cap_weight": weight,
                "source": "earnings_events",
            }
        )

    return normalized
