from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class MarketEventsResult:
    """Typed result for market-event state orchestration."""

    symbol: str
    market_pressure_score: float
    volatility_pressure: float
    volatility_forecast: str
    regime_bias: str
    events: tuple[dict[str, Any], ...]
    high_impact_events: tuple[dict[str, Any], ...]
    event_count: int
    high_impact_count: int
    risk_projection: dict[str, Any]

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "market_pressure_score": self.market_pressure_score,
            "volatility_pressure": self.volatility_pressure,
            "volatility_forecast": self.volatility_forecast,
            "regime_bias": self.regime_bias,
            "events": deepcopy(list(self.events)),
            "high_impact_events": deepcopy(list(self.high_impact_events)),
            "event_count": self.event_count,
            "high_impact_count": self.high_impact_count,
            "risk_projection": deepcopy(self.risk_projection),
        }
