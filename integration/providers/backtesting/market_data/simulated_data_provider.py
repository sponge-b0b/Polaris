from __future__ import annotations

import math

import pandas as pd

from domain.market.models import SP500Data
from integration.providers.market_data.market_data_provider import MarketDataProvider


class SimulatedDataProvider(MarketDataProvider):
    """
    Deterministic backtest market data provider.

    Produces replay-friendly synthetic series with the canonical provider
    contract expected by TechnicalAnalysisService. This prevents local CLI and
    integration runs from depending on network market data while preserving the
    provider -> service -> agent layering.
    """

    async def get_symbol_data(
        self,
        symbol: str,
        days: int,
    ) -> pd.DataFrame:
        row_count = max(
            int(days),
            300,
        )
        index = pd.date_range(
            end=pd.Timestamp("2026-01-01"),
            periods=row_count,
            freq="D",
        )

        base = 400.0 + (sum(ord(char) for char in symbol.upper()) % 25)
        closes: list[float] = []
        for offset in range(row_count):
            trend = offset * 0.12
            cycle = math.sin(offset / 9.0) * 2.5
            closes.append(base + trend + cycle)

        frame = pd.DataFrame(
            {
                "open": [value - 0.6 for value in closes],
                "high": [value + 1.4 for value in closes],
                "low": [value - 1.8 for value in closes],
                "close": closes,
                "volume": [1_000_000 + (idx % 20) * 10_000 for idx in range(row_count)],
            },
            index=index,
        )
        return frame

    async def get_vix_data(
        self,
        days: int,
    ) -> pd.DataFrame:
        return self._context_series(
            days=days,
            base=17.0,
            amplitude=1.8,
            column="close",
        )

    async def get_vvix_data(
        self,
        days: int,
    ) -> pd.DataFrame:
        return self._context_series(
            days=days,
            base=85.0,
            amplitude=4.5,
            column="close",
        )

    async def get_sp500_data(
        self,
        days: int,
    ) -> SP500Data:
        raw_row_count = max(days, 300)
        index = pd.date_range(
            end=pd.Timestamp("2026-01-01"),
            periods=raw_row_count,
            freq="D",
        )

        constituent_count = 500
        constituents = [f"STOCK{i}" for i in range(1, constituent_count + 1)]
        market_caps = {
            symbol: float(1_000_000_000 + (constituent_count - idx) * 5_000_000)
            for idx, symbol in enumerate(
                constituents,
            )
        }
        top_50_constituents = [
            symbol
            for symbol, _ in sorted(
                market_caps.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:50]
        ]

        advances_count: list[int] = []
        declines_count: list[int] = []
        unchanged_count: list[int] = []
        market_cap_index: list[float] = []

        index_level = 100.0
        for offset in range(raw_row_count):
            breadth_cycle = math.sin(offset / 8.0)
            trend_bias = 24.0 * math.sin(offset / 55.0)
            advances = int(250.0 + breadth_cycle * 90.0 + trend_bias)
            advances = max(
                60,
                min(
                    constituent_count - 60,
                    advances,
                ),
            )

            unchanged = 4 + (offset % 9)
            declines = constituent_count - advances - unchanged
            if declines < 0:
                unchanged = max(
                    0,
                    constituent_count - advances,
                )
                declines = constituent_count - advances - unchanged

            daily_return = 0.0007 + (advances - declines) / constituent_count * 0.0012
            index_level *= 1.0 + daily_return

            advances_count.append(advances)
            declines_count.append(declines)
            unchanged_count.append(unchanged)
            market_cap_index.append(index_level)

        frame = pd.DataFrame(
            {
                "market_cap_index": market_cap_index,
                "advances_count": advances_count,
                "declines_count": declines_count,
                "unchanged_count": unchanged_count,
            },
            index=index,
        )

        frame["active_count"] = frame["advances_count"] + frame["declines_count"]
        frame["pct_above_50dma"] = (
            0.55
            + pd.Series(
                [math.sin(offset / 14.0) * 0.18 for offset in range(raw_row_count)],
                index=index,
            )
        ).clip(
            0.0,
            1.0,
        )
        frame["pct_above_200dma"] = (
            0.58
            + pd.Series(
                [math.sin(offset / 31.0) * 0.16 for offset in range(raw_row_count)],
                index=index,
            )
        ).clip(
            0.0,
            1.0,
        )
        frame["new_highs"] = [
            max(
                0,
                int(18.0 + math.sin(offset / 17.0) * 16.0),
            )
            for offset in range(raw_row_count)
        ]
        frame["new_lows"] = [
            max(
                0,
                int(12.0 + math.cos(offset / 19.0) * 10.0),
            )
            for offset in range(raw_row_count)
        ]
        frame["net_breadth"] = frame["advances_count"] - frame["declines_count"]
        frame["breadth_percent"] = frame["advances_count"] / frame["active_count"]
        frame["ad_line"] = frame["net_breadth"].fillna(0.0).cumsum()
        frame["ad_ratio"] = frame["advances_count"] / frame["declines_count"]

        analytics = frame.iloc[1:].copy()

        return SP500Data(
            analytics=analytics,
            top_50_constituents=top_50_constituents,
            market_caps=market_caps,
        )

    def _context_series(
        self,
        *,
        days: int,
        base: float,
        amplitude: float,
        column: str,
    ) -> pd.DataFrame:
        row_count = max(
            int(days),
            300,
        )
        index = pd.date_range(
            end=pd.Timestamp("2026-01-01"),
            periods=row_count,
            freq="D",
        )
        values = [base + math.sin(idx / 13.0) * amplitude for idx in range(row_count)]
        return pd.DataFrame(
            {column: values},
            index=index,
        )
