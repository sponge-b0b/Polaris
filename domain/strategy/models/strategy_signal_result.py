from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class StrategySignalResult:
    """
    Canonical strategy intelligence result.
    """

    directional_score: float = 0.0

    confidence: float = 0.0

    regime: str = "neutral"

    signals: list[str] = field(
        default_factory=list,
    )

    risks: list[str] = field(
        default_factory=list,
    )

    recommendations: list[str] = field(
        default_factory=list,
    )

    features: dict[str, Any] = field(
        default_factory=dict,
    )

    llm_response: Any | None = None

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "directional_score": self.directional_score,
            "confidence": self.confidence,
            "regime": self.regime,
            "signals": self.signals,
            "risks": self.risks,
            "recommendations": self.recommendations,
            "features": self.features,
            "llm_response": self.llm_response,
        }
