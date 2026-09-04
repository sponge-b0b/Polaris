from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class SentimentSnapshotResult:
    """Typed result for sentiment snapshot orchestration."""

    symbol: str
    providers: dict[str, Any]
    features: dict[str, Any]
    sentiment: dict[str, Any]
    composite_sentiment: float
    market_regime: str
    market_bias: str
    confidence: float

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "providers": deepcopy(self.providers),
            "features": deepcopy(self.features),
            "sentiment": deepcopy(self.sentiment),
            "composite_sentiment": self.composite_sentiment,
            "market_regime": self.market_regime,
            "market_bias": self.market_bias,
            "confidence": self.confidence,
        }
