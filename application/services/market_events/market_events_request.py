from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_SYMBOL_CONSTITUENTS: frozenset[str] = frozenset(
    {
        "AAPL",
        "AMZN",
        "GOOG",
        "GOOGL",
        "META",
        "MSFT",
        "NVDA",
        "TSLA",
        "AVGO",
        "JPM",
        "V",
        "MA",
        "BRK-B",
        "LLY",
        "XOM",
        "UNH",
        "COST",
        "WMT",
        "AMD",
        "NFLX",
        "CRM",
        "ORCL",
        "ADBE",
        "BAC",
        "GS",
        "MS",
        "JNJ",
        "ABBV",
        "MRK",
        "HD",
        "LOW",
        "TGT",
        "CAT",
        "GE",
        "LIN",
    }
)


def default_symbol_constituents() -> frozenset[str]:
    return DEFAULT_SYMBOL_CONSTITUENTS


@dataclass(
    frozen=True,
    slots=True,
)
class MarketEventsRequest:
    """
    Request payload for market event state orchestration.
    """

    symbol: str = "SPY"
    lookahead_days: int = 10
    horizon: str = "3month"
    symbol_constituents: frozenset[str] = field(
        default_factory=default_symbol_constituents,
    )
