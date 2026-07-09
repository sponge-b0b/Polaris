from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class TechnicalAnalysisResult:
    """Typed result for deterministic technical-analysis orchestration."""

    symbol: str
    technical_score: float
    snapshot: dict[str, Any]
    market_context: dict[str, Any]
    micro_regime: dict[str, Any]
    trend: dict[str, Any]
    volatility: dict[str, Any]
    breadth: dict[str, Any]
    raw_regime: dict[str, Any]
    regime: dict[str, Any]

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "technical_score": self.technical_score,
            "snapshot": deepcopy(self.snapshot),
            "market_context": deepcopy(self.market_context),
            "micro_regime": deepcopy(self.micro_regime),
            "trend": deepcopy(self.trend),
            "volatility": deepcopy(self.volatility),
            "breadth": deepcopy(self.breadth),
            "raw_regime": deepcopy(self.raw_regime),
            "regime": deepcopy(self.regime),
        }
