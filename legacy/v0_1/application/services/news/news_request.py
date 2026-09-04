from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class NewsRequest:
    """
    Request payload for news intelligence orchestration.
    """

    query: str = "SPY OR S&P 500 OR inflation OR Fed OR rates"
    symbol: str = "SPY"
    limit: int = 20
