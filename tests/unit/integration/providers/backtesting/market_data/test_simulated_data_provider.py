from __future__ import annotations

import pandas as pd
import pytest

from integration.providers.backtesting.market_data.simulated_data_provider import (
    SimulatedDataProvider,
)
from domain.market.models import SP500Data


@pytest.mark.asyncio
async def test_simulated_provider_exposes_sp500_market_context_schema() -> None:
    provider = SimulatedDataProvider()

    sp500_data = await provider.get_sp500_data(365)
    frame = sp500_data.analytics

    expected_columns = [
        "market_cap_index",
        "advances_count",
        "declines_count",
        "unchanged_count",
        "active_count",
        "pct_above_50dma",
        "pct_above_200dma",
        "new_highs",
        "new_lows",
        "net_breadth",
        "breadth_percent",
        "ad_line",
        "ad_ratio",
    ]
    forbidden_columns = {
        "new_high_low_diff",
        "new_high_low_ratio",
        "ad_line_ema_10",
        "ad_line_ema_20",
        "ad_line_slope_5",
        "price_ad_divergence",
    }

    assert isinstance(sp500_data, SP500Data)
    assert isinstance(frame, pd.DataFrame)
    assert len(frame) == 364
    assert list(frame.columns) == expected_columns
    assert forbidden_columns.isdisjoint(frame.columns)
    assert not frame.empty
    assert frame.index.is_monotonic_increasing
    assert len(sp500_data.top_50_constituents) == 50
    assert len(sp500_data.market_caps) == 500


@pytest.mark.asyncio
async def test_simulated_sp500_data_is_deterministic() -> None:
    provider = SimulatedDataProvider()

    first = await provider.get_sp500_data(180)
    second = await provider.get_sp500_data(180)

    pd.testing.assert_frame_equal(first.analytics, second.analytics)
    assert first.top_50_constituents == second.top_50_constituents
    assert first.market_caps == second.market_caps


@pytest.mark.asyncio
async def test_simulated_sp500_data_matches_market_data_provider_days_contract() -> (
    None
):
    provider = SimulatedDataProvider()

    sp500_data = await provider.get_sp500_data(10)
    frame = sp500_data.analytics

    assert len(frame) == 299
    assert (frame["active_count"] > 0).all()
    assert (frame["declines_count"] > 0).all()
    assert frame["ad_ratio"].notna().all()
    assert frame["market_cap_index"].iloc[-1] > frame["market_cap_index"].iloc[0]
