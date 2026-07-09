from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import cast

import pytest

from application.persistence.portfolio import PortfolioPersistenceService
from application.services.base import ServiceRequest
from application.services.portfolio.portfolio_request import (
    PortfolioAnalysisRequest,
)
from application.services.portfolio.portfolio_service import PortfolioService
from core.storage.persistence.portfolio import PortfolioExpansionPersistenceBundle
from core.storage.persistence.portfolio import PortfolioExpansionPersistenceResult
from core.storage.persistence.serializers.portfolio_state_serializer import (
    PortfolioStateSerializer,
)
from domain.portfolio.models.portfolio_state import PortfolioState


class SparsePortfolioProvider:
    @property
    def source(self) -> str:
        return "sparse"

    async def get_account(self) -> dict[str, Any]:
        return {
            "id": "acct-sparse",
        }

    async def get_positions(self) -> list[dict[str, Any]]:
        return []

    async def get_portfolio_history(self) -> dict[str, Any]:
        return {}


class RepresentativePortfolioProvider:
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

    async def get_portfolio_history(self) -> dict[str, Any]:
        return {
            "timestamp": [1780689600],
            "equity": [100000.0],
            "profit_loss": [5000.0],
            "profit_loss_pct": [0.05],
            "base_value": 95000.0,
            "timeframe": "1D",
            "cashflow": {},
        }


class SerializingPortfolioRepository:
    def __init__(self) -> None:
        self.persisted_state: PortfolioState | None = None
        self.persisted_history_state: PortfolioState | None = None
        self.latest_state: PortfolioState | None = None

    async def get_latest(
        self,
        account_id: str,
    ) -> PortfolioState | None:
        if self.latest_state is None:
            return None
        if self.latest_state.account_id == account_id:
            return self.latest_state
        return None

    async def persist_snapshot(
        self,
        state: PortfolioState,
    ) -> None:
        latest_model = PortfolioStateSerializer.to_latest_model(
            state,
        )
        history_model = PortfolioStateSerializer.to_history_model(
            state,
        )
        self.persisted_state = PortfolioStateSerializer.from_latest_model(
            latest_model,
        )
        self.persisted_history_state = PortfolioStateSerializer.from_history_model(
            history_model,
        )
        self.latest_state = self.persisted_state

    async def get_history(
        self,
        account_id: str,
        start: datetime,
        end: datetime,
    ) -> list[PortfolioState]:
        if self.persisted_history_state is None:
            return []
        if self.persisted_history_state.account_id != account_id:
            return []
        if not start <= self.persisted_history_state.timestamp <= end:
            return []
        return [
            self.persisted_history_state,
        ]


class CapturingPortfolioRepository:
    def __init__(self) -> None:
        self.persisted_state: PortfolioState | None = None

    async def get_latest(
        self,
        account_id: str,
    ) -> None:
        assert account_id == "acct-123"
        return None

    async def persist_snapshot(
        self,
        state: PortfolioState,
    ) -> None:
        self.persisted_state = state

    async def get_history(
        self,
        account_id: str,
        start: datetime,
        end: datetime,
    ) -> list[PortfolioState]:
        return []


class CapturingPortfolioExpansionRepository:
    def __init__(self) -> None:
        self.bundle: PortfolioExpansionPersistenceBundle | None = None

    async def persist_portfolio_expansion_bundle(
        self,
        bundle: PortfolioExpansionPersistenceBundle,
    ) -> PortfolioExpansionPersistenceResult:
        self.bundle = bundle
        account_id = (
            bundle.equity_history_points[0].account_id
            if bundle.equity_history_points
            else "empty-portfolio-expansion-bundle"
        )
        return PortfolioExpansionPersistenceResult.succeeded(
            account_id=account_id,
            records_persisted=len(bundle.equity_history_points),
        )


def _persistence_service(
    state_repository: object,
) -> tuple[PortfolioPersistenceService, CapturingPortfolioExpansionRepository]:
    expansion_repository = CapturingPortfolioExpansionRepository()
    return (
        PortfolioPersistenceService(
            cast(Any, expansion_repository),
            cast(Any, state_repository),
        ),
        expansion_repository,
    )


@pytest.mark.asyncio
async def test_portfolio_service_persists_fully_mapped_v2_state() -> None:
    repository = CapturingPortfolioRepository()
    persistence_service, expansion_repository = _persistence_service(repository)
    service = PortfolioService(
        portfolio_provider=RepresentativePortfolioProvider(),
        portfolio_persistence_service=persistence_service,
    )

    result = await service.run(
        ServiceRequest(
            payload=PortfolioAnalysisRequest(
                symbol="SPY",
            ),
        )
    )

    assert result.success is True
    state = repository.persisted_state
    assert state is not None
    assert expansion_repository.bundle is not None
    assert len(expansion_repository.bundle.equity_history_points) == 1
    history_point = expansion_repository.bundle.equity_history_points[0]
    assert history_point.account_id == "acct-123"
    assert history_point.source == "alpaca"
    assert history_point.timeframe == "1D"
    assert history_point.observed_at.isoformat() == "2026-06-05T20:00:00+00:00"
    assert history_point.equity == 100000.0
    assert history_point.profit_loss == 5000.0
    assert history_point.profit_loss_pct == 0.05
    assert history_point.base_value == 95000.0

    assert state.account_id == "acct-123"
    assert state.schema_version == 2
    assert state.equity == pytest.approx(100000.0)
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
async def test_portfolio_service_v2_fields_survive_serializer_boundary() -> None:
    repository = SerializingPortfolioRepository()
    persistence_service, expansion_repository = _persistence_service(repository)
    service = PortfolioService(
        portfolio_provider=RepresentativePortfolioProvider(),
        portfolio_persistence_service=persistence_service,
    )

    result = await service.run(
        ServiceRequest(
            payload=PortfolioAnalysisRequest(
                symbol="SPY",
            ),
        )
    )

    assert result.success is True
    assert repository.persisted_state is not None
    assert repository.persisted_history_state == repository.persisted_state

    state = repository.persisted_state
    assert state.account_id == "acct-123"
    assert state.schema_version == 2
    assert state.unrealized_intraday_pnl == pytest.approx(500.0)
    assert state.margin_utilization_ratio == pytest.approx(0.1)
    assert state.pattern_day_trader is True
    assert state.trading_blocked is True
    assert state.trade_suspended_by_user is True
    assert state.shorting_enabled is False
    assert state.sector_exposure == {
        "technology": pytest.approx(0.3),
    }
    assert state.asset_class_exposure == {
        "equity": pytest.approx(0.3),
    }
    assert state.risk_signals["directional_bias"] == "long"


@pytest.mark.asyncio
async def test_portfolio_service_defaults_missing_provider_data_safely() -> None:
    repository = SerializingPortfolioRepository()
    persistence_service, expansion_repository = _persistence_service(repository)
    service = PortfolioService(
        portfolio_provider=SparsePortfolioProvider(),
        portfolio_persistence_service=persistence_service,
    )

    result = await service.run(
        ServiceRequest(
            payload=PortfolioAnalysisRequest(
                symbol="SPY",
            ),
        )
    )

    assert result.success is True
    assert repository.persisted_state is not None
    assert expansion_repository.bundle is not None
    assert expansion_repository.bundle.equity_history_points == ()

    state = repository.persisted_state
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
