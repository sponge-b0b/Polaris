import pytest

from integration.providers.backtesting.portfolio.simulated_portfolio_provider import (
    SimulatedPortfolioProvider,
)


@pytest.mark.asyncio
async def test_get_account_exposes_live_compatible_v2_fields() -> None:
    provider = SimulatedPortfolioProvider(initial_capital=100000.0)

    provider.apply_signal(
        symbol="SPY",
        side="long",
        price=100.0,
        capital_allocation=10000.0,
    )
    provider.apply_signal(
        symbol="SH",
        side="short",
        price=50.0,
        capital_allocation=5000.0,
    )

    account = await provider.get_account()

    assert account["id"] == "simulated-account"
    assert account["account_number"] == "SIMULATED"
    assert account["status"] == "ACTIVE"
    assert account["currency"] == "USD"
    assert account["last_equity"] == pytest.approx(100000.0)
    assert account["long_market_value"] == pytest.approx(10000.0)
    assert account["short_market_value"] == pytest.approx(-5000.0)
    assert account["initial_margin"] == pytest.approx(0.0)
    assert account["maintenance_margin"] == pytest.approx(0.0)
    assert account["last_maintenance_margin"] == pytest.approx(0.0)
    assert account["daytrade_count"] == 0
    assert account["pattern_day_trader"] is False
    assert account["trading_blocked"] is False
    assert account["transfers_blocked"] is False
    assert account["account_blocked"] is False
    assert account["trade_suspended_by_user"] is False
    assert account["shorting_enabled"] is True


@pytest.mark.asyncio
async def test_get_positions_exposes_live_compatible_v2_fields() -> None:
    provider = SimulatedPortfolioProvider(initial_capital=100000.0)

    provider.apply_signal(
        symbol="SPY",
        side="long",
        price=100.0,
        capital_allocation=10000.0,
    )
    provider.update_market(
        symbol="SPY",
        price=110.0,
    )

    positions = await provider.get_positions()

    assert len(positions) == 1
    position = positions[0]

    assert position["symbol"] == "SPY"
    assert position["asset_id"] == "sim-spy"
    assert position["exchange"] == "SIM"
    assert position["asset_class"] == "equity"
    assert position["asset_marginable"] is True
    assert position["sector"] == "simulated"
    assert position["beta"] == pytest.approx(1.0)
    assert position["qty"] == pytest.approx(100.0)
    assert position["quantity"] == pytest.approx(100.0)
    assert position["qty_available"] == pytest.approx(100.0)
    assert position["avg_entry_price"] == pytest.approx(100.0)
    assert position["entry_price"] == pytest.approx(100.0)
    assert position["current_price"] == pytest.approx(110.0)
    assert position["market_value"] == pytest.approx(11000.0)
    assert position["cost_basis"] == pytest.approx(10000.0)
    assert position["unrealized_pl"] == pytest.approx(1000.0)
    assert position["unrealized_plpc"] == pytest.approx(0.1)
    assert position["unrealized_intraday_pl"] == pytest.approx(0.0)
    assert position["unrealized_intraday_plpc"] == pytest.approx(0.0)
    assert position["side"] == "long"


@pytest.mark.asyncio
async def test_get_portfolio_history_exposes_alpaca_compatible_payload() -> None:
    provider = SimulatedPortfolioProvider(initial_capital=100000.0)

    provider.apply_signal(
        symbol="SPY",
        side="long",
        price=100.0,
        capital_allocation=10000.0,
    )
    provider.update_market(
        symbol="SPY",
        price=110.0,
    )

    history = await provider.get_portfolio_history()

    assert set(history) == {
        "timestamp",
        "equity",
        "profit_loss",
        "profit_loss_pct",
        "base_value",
        "timeframe",
        "cashflow",
    }
    assert history["timestamp"] == [0, 1, 2]
    assert history["equity"] == pytest.approx([100000.0, 100000.0, 101000.0])
    assert history["profit_loss"] == pytest.approx([0.0, 0.0, 1000.0])
    assert history["profit_loss_pct"] == pytest.approx([0.0, 0.0, 0.01])
    assert history["base_value"] == pytest.approx(100000.0)
    assert history["timeframe"] == "1D"
    assert history["cashflow"] == {}


@pytest.mark.asyncio
async def test_get_portfolio_history_returns_defensive_copies() -> None:
    provider = SimulatedPortfolioProvider(initial_capital=100000.0)

    first_history = await provider.get_portfolio_history()
    first_history["timestamp"].append(999)
    first_history["equity"].append(999.0)
    first_history["profit_loss"].append(999.0)
    first_history["profit_loss_pct"].append(999.0)

    next_history = await provider.get_portfolio_history()

    assert next_history["timestamp"] == [0]
    assert next_history["equity"] == pytest.approx([100000.0])
    assert next_history["profit_loss"] == pytest.approx([0.0])
    assert next_history["profit_loss_pct"] == pytest.approx([0.0])
