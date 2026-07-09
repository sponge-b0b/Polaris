import pytest

from integration.providers.backtesting.portfolio.simulated_portfolio_provider import (
    SimulatedPortfolioProvider,
)
from integration.providers.portfolio.backtest_portfolio_provider import (
    BacktestPortfolioProvider,
)


@pytest.mark.asyncio
async def test_backtest_portfolio_provider_exposes_simulated_v2_fields() -> None:
    simulated_provider = SimulatedPortfolioProvider(initial_capital=100000.0)
    backtest_provider = BacktestPortfolioProvider(
        portfolio_provider=simulated_provider,
    )

    simulated_provider.apply_signal(
        symbol="SPY",
        side="long",
        price=100.0,
        capital_allocation=10000.0,
    )

    account = await backtest_provider.get_account()
    positions = await backtest_provider.get_positions()

    assert account["id"] == "simulated-account"
    assert account["long_market_value"] == pytest.approx(10000.0)
    assert account["maintenance_margin"] == pytest.approx(0.0)
    assert account["trading_blocked"] is False
    assert account["daytrade_count"] == 0

    assert len(positions) == 1
    assert positions[0]["cost_basis"] == pytest.approx(10000.0)
    assert positions[0]["unrealized_plpc"] == pytest.approx(0.0)
    assert positions[0]["asset_class"] == "equity"
    assert positions[0]["sector"] == "simulated"
    assert positions[0]["beta"] == pytest.approx(1.0)
