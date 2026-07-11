from __future__ import annotations

from typing import Any

import pytest

from application.services.base import ServiceRequest
from application.services.portfolio.portfolio_request import (
    PortfolioAnalysisRequest,
)
from application.services.portfolio.portfolio_service import PortfolioService


class SparsePortfolioProvider:
    def __init__(self) -> None:
        self.history_requests: list[dict[str, str]] = []

    @property
    def source(self) -> str:
        return "sparse"

    async def get_account(self) -> dict[str, Any]:
        return {
            "id": "acct-sparse",
        }

    async def get_positions(self) -> list[dict[str, Any]]:
        return []

    async def get_portfolio_history(
        self,
        *,
        period: str = "1A",
        timeframe: str = "1D",
    ) -> dict[str, Any]:
        self.history_requests.append(
            {
                "period": period,
                "timeframe": timeframe,
            }
        )
        return {}


class RepresentativePortfolioProvider:
    def __init__(self) -> None:
        self.history_requests: list[dict[str, str]] = []

    @property
    def source(self) -> str:
        return "alpaca"

    async def get_account(self) -> dict[str, Any]:
        return {
            "id": "acct-123",
            "account_number": "account-123",
            "status": "ACTIVE",
            "currency": "USD",
            "equity": 100000.0,
            "last_equity": 98000.0,
            "portfolio_value": 100000.0,
            "cash": 60000.0,
            "buying_power": 120000.0,
            "long_market_value": 30000.0,
            "short_market_value": -5000.0,
            "initial_margin": 4000.0,
            "maintenance_margin": 10000.0,
            "last_maintenance_margin": 9000.0,
            "daytrade_count": 2,
            "pattern_day_trader": True,
            "trading_blocked": True,
            "transfers_blocked": True,
            "account_blocked": False,
            "trade_suspended_by_user": True,
            "shorting_enabled": False,
        }

    async def get_positions(self) -> list[dict[str, Any]]:
        return [
            {
                "symbol": "SPY",
                "quantity": 300.0,
                "qty_available": 300.0,
                "entry_price": 90.0,
                "avg_entry_price": 90.0,
                "current_price": 100.0,
                "market_value": 30000.0,
                "cost_basis": 27000.0,
                "unrealized_pl": 3000.0,
                "unrealized_plpc": 3000.0 / 27000.0,
                "unrealized_intraday_pl": 500.0,
                "unrealized_intraday_plpc": 500.0 / 27000.0,
                "side": "long",
                "sector": "technology",
                "asset_class": "equity",
                "beta": 1.2,
            }
        ]

    async def get_portfolio_history(
        self,
        *,
        period: str = "1A",
        timeframe: str = "1D",
    ) -> dict[str, Any]:
        self.history_requests.append(
            {
                "period": period,
                "timeframe": timeframe,
            }
        )
        return {
            "timestamp": [1780689600],
            "equity": [125000.0],
            "profit_loss": [5000.0],
            "profit_loss_pct": [0.05],
            "base_value": 95000.0,
            "timeframe": timeframe,
            "cashflow": {},
        }


@pytest.mark.asyncio
async def test_portfolio_service_returns_fully_mapped_v2_state_without_persisting() -> (
    None
):
    provider = RepresentativePortfolioProvider()
    service = PortfolioService(
        portfolio_provider=provider,
    )

    result = await service.run(
        ServiceRequest(
            payload=PortfolioAnalysisRequest(
                symbol="SPY",
            ),
        )
    )

    assert result.success is True
    assert result.result is not None
    assert provider.history_requests == [
        {
            "period": "1A",
            "timeframe": "1D",
        }
    ]
    assert result.result.current_equity == pytest.approx(100000.0)
    assert result.result.peak_equity == pytest.approx(125000.0)
    assert result.result.drawdown_absolute == pytest.approx(25000.0)
    assert result.result.drawdown_percent == pytest.approx(0.2)
    assert result.result.provider_source == "alpaca"
    assert result.result.history_period == "1A"
    assert result.result.history_timeframe == "1D"
    assert result.result.canonical_portfolio_state is not None
    assert result.result.canonical_portfolio_state.peak_equity == pytest.approx(
        125000.0,
    )
    assert len(result.result.equity_history_points) == 1
    assert result.result.exposures is not None
    assert result.result.exposures["gross_exposure"] == pytest.approx(0.3)
    assert result.result.risk_metrics is not None
    assert result.result.risk_metrics["drawdown_percent"] == pytest.approx(0.2)
    assert result.result.allocation_data is not None
    assert result.result.allocation_data["positions"][0]["symbol"] == "SPY"
    serialized = result.result.to_dict()
    assert serialized["canonical_portfolio_state"]["account_id"] == "acct-123"
    assert serialized["equity_history_points"][0]["source"] == "alpaca"
    state = result.result.canonical_portfolio_state
    assert state is not None
    history_point = result.result.equity_history_points[0]
    assert history_point.account_id == "acct-123"
    assert history_point.source == "alpaca"
    assert history_point.timeframe == "1D"
    assert history_point.observed_at.isoformat() == "2026-06-05T20:00:00+00:00"
    assert history_point.equity == 125000.0
    assert history_point.profit_loss == 5000.0
    assert history_point.profit_loss_pct == 0.05
    assert history_point.base_value == 95000.0

    assert state.account_id == "acct-123"
    assert state.schema_version == 2
    assert state.equity == pytest.approx(100000.0)
    assert state.peak_equity == pytest.approx(125000.0)
    assert state.drawdown_absolute == pytest.approx(25000.0)
    assert state.drawdown_percent == pytest.approx(0.2)
    assert state.last_equity == pytest.approx(98000.0)
    assert state.cash_ratio == pytest.approx(0.6)
    assert state.buying_power_ratio == pytest.approx(1.2)
    assert state.realized_pnl == pytest.approx(2000.0)
    assert state.unrealized_pnl == pytest.approx(3000.0)
    assert state.unrealized_pnl_pct == pytest.approx(3000.0 / 27000.0)
    assert state.unrealized_intraday_pnl == pytest.approx(500.0)
    assert state.unrealized_intraday_pnl_pct == pytest.approx(
        500.0 / 27000.0,
    )
    assert state.pnl_total == pytest.approx(5000.0)
    assert state.long_market_value == pytest.approx(30000.0)
    assert state.short_market_value == pytest.approx(-5000.0)
    assert state.gross_market_value == pytest.approx(35000.0)
    assert state.net_market_value == pytest.approx(25000.0)
    assert state.gross_exposure == pytest.approx(0.3)
    assert state.net_exposure == pytest.approx(0.3)
    assert state.long_exposure == pytest.approx(0.3)
    assert state.short_exposure == pytest.approx(0.0)
    assert state.leverage == pytest.approx(0.3)
    assert state.largest_position_pct == pytest.approx(0.3)
    assert state.beta_exposure == pytest.approx(0.36)
    assert state.initial_margin == pytest.approx(4000.0)
    assert state.maintenance_margin == pytest.approx(10000.0)
    assert state.last_maintenance_margin == pytest.approx(9000.0)
    assert state.margin_utilization_ratio == pytest.approx(0.1)
    assert state.initial_margin_ratio == pytest.approx(0.04)
    assert state.daytrade_count == 2
    assert state.pattern_day_trader is True
    assert state.trading_blocked is True
    assert state.transfers_blocked is True
    assert state.account_blocked is False
    assert state.trade_suspended_by_user is True
    assert state.shorting_enabled is False
    assert state.position_count == 1
    assert state.portfolio_regime == "balanced"
    assert state.directional_bias == "long"
    assert state.sector_exposure == {
        "technology": pytest.approx(0.3),
    }
    assert state.asset_class_exposure == {
        "equity": pytest.approx(0.3),
    }
    assert state.risk_signals["pattern_day_trader"] is True
    assert state.risk_signals["trading_blocked"] is True
    assert state.risk_signals["high_beta"] is False
    assert state.risk_signals["directional_bias"] == "long"


@pytest.mark.asyncio
async def test_portfolio_service_v2_fields_survive_result_serialization() -> None:
    service = PortfolioService(
        portfolio_provider=RepresentativePortfolioProvider(),
    )

    result = await service.run(
        ServiceRequest(
            payload=PortfolioAnalysisRequest(
                symbol="SPY",
            ),
        )
    )

    assert result.success is True
    assert result.result is not None
    serialized = result.result.to_dict()
    state = serialized["canonical_portfolio_state"]
    assert state["account_id"] == "acct-123"
    assert state["schema_version"] == 2
    assert state["unrealized_intraday_pnl"] == pytest.approx(500.0)
    assert state["margin_utilization_ratio"] == pytest.approx(0.1)
    assert state["pattern_day_trader"] is True
    assert state["trading_blocked"] is True
    assert state["trade_suspended_by_user"] is True
    assert state["shorting_enabled"] is False
    assert state["sector_exposure"] == {
        "technology": pytest.approx(0.3),
    }
    assert state["asset_class_exposure"] == {
        "equity": pytest.approx(0.3),
    }
    assert state["risk_signals"]["directional_bias"] == "long"


@pytest.mark.asyncio
async def test_portfolio_service_defaults_missing_provider_data_safely() -> None:
    service = PortfolioService(
        portfolio_provider=SparsePortfolioProvider(),
    )

    result = await service.run(
        ServiceRequest(
            payload=PortfolioAnalysisRequest(
                symbol="SPY",
            ),
        )
    )

    assert result.success is True
    assert result.result is not None
    assert result.result.equity_history_points == ()

    state = result.result.canonical_portfolio_state
    assert state is not None
    assert state.account_id == "acct-sparse"
    assert state.schema_version == 2
    assert state.equity == 0.0
    assert state.cash_ratio == 0.0
    assert state.buying_power_ratio == 0.0
    assert state.position_count == 0
    assert state.portfolio_regime == "flat"
    assert state.directional_bias == "neutral"
    assert state.account_health == "illiquid"
    assert state.sector_exposure == {}
    assert state.asset_class_exposure == {}
    assert state.pattern_day_trader is False
    assert state.trading_blocked is False
    assert state.shorting_enabled is False
    assert state.risk_signals["low_cash_buffer"] is True
