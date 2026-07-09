from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class SP500Data:
    """Canonical S&P 500 breadth and constituent market-data snapshot."""

    analytics: pd.DataFrame
    top_50_constituents: list[str]
    market_caps: dict[str, float]
