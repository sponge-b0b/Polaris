from __future__ import annotations

from typing import Any
from typing import Mapping

DEFAULT_EVENT_SYMBOLS = frozenset(
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


def extract_symbol_constituents(market_context: Any) -> frozenset[str]:
    source = _mapping(market_context)
    raw_symbols = source.get("top_50_constituents")
    if not isinstance(raw_symbols, (list, tuple, set, frozenset)):
        return DEFAULT_EVENT_SYMBOLS
    symbols = frozenset(
        symbol.strip().upper()
        for symbol in raw_symbols
        if isinstance(symbol, str) and symbol.strip()
    )
    return symbols or DEFAULT_EVENT_SYMBOLS


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}
