from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class PortfolioAnalysisRequest:
    """
    Request payload for portfolio analysis orchestration.
    """

    symbol: str = "SPY"
