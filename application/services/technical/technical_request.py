from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class TechnicalAnalysisRequest:
    """
    Request payload for technical analysis orchestration.
    """

    symbol: str = "SPY"
    days: int = 365
