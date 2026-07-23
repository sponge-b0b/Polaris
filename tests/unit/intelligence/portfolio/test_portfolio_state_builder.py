from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import pytest

from application.services.base import ServiceResult, ServiceRunner
from application.services.portfolio.portfolio_result import PortfolioAnalysisResult
from application.services.portfolio.portfolio_service import PortfolioService
from core.runtime.state.runtime_context import RuntimeContext
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from domain.portfolio.models.portfolio_state import PortfolioState
from intelligence.portfolio.management.portfolio_state_builder import (
    PortfolioStateBuilder,
)


@pytest.mark.asyncio
async def test_portfolio_state_builder_surfaces_v2_portfolio_state_fields() -> None:
    telemetry = _FakeTelemetry()
    service_runner = _FakeServiceRunner(
        _portfolio_payload(),
    )
    builder = PortfolioStateBuilder(
        portfolio_service=cast(
            PortfolioService,
            object(),
        ),
        service_runner=cast(
            ServiceRunner[Any, Any],
            service_runner,
        ),
        intelligence_telemetry=cast(
            IntelligenceTelemetry,
            telemetry,
        ),
    )
    context = RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
        workflow_inputs={
            "symbol": "spy",
        },
    )

    output = await builder._execute(
        context,
    )

    assert output.success is True
    features = output.outputs["features"]
    portfolio_state = features["portfolio_state"]
    positions_state = features["positions_state"]
    equity_state = features["equity_state"]
    risk_features = features["risk_features"]

    assert output.outputs["canonical_portfolio_state"]["account_id"] == "account-1"
    assert output.outputs["positions"] == [
        {
            "symbol": "SPY",
            "market_value": 70_000.0,
            "exposure_weight": 0.70,
        },
        {
            "symbol": "AAPL",
            "market_value": 15_000.0,
            "exposure_weight": 0.15,
        },
    ]
    assert output.outputs["exposures"]["gross_exposure"] == 0.85
    assert output.outputs["risk_metrics"]["risk_intensity"] == 0.33
    assert output.outputs["allocation_data"]["asset_class_exposure"] == {
        "equity": 0.85,
    }
    assert output.outputs["provider_source"] == "test-provider"

    assert portfolio_state["positions"] == [
        {
            "symbol": "WRONG",
        }
    ]
    assert positions_state["positions"] == [
        {
            "symbol": "SPY",
            "market_value": 70_000.0,
        },
        {
            "symbol": "AAPL",
            "market_value": 15_000.0,
        },
    ]
    assert positions_state["positions"] != portfolio_state["positions"]
    assert positions_state["position_count"] == 2
    assert positions_state["risk_signals"] == [
        "position_concentration_normal",
    ]
    assert positions_state["gross_exposure"] == 0.85

    assert equity_state["cash_ratio"] == 0.15
    assert equity_state["buying_power_ratio"] == 0.40
    assert equity_state["regt_buying_power"] == 35_000.0
    assert equity_state["daytrading_buying_power"] == 80_000.0
    assert equity_state["maintenance_margin"] == 12_000.0
    assert equity_state["margin_utilization_ratio"] == 0.30
    assert equity_state["initial_margin_ratio"] == 0.25
    assert equity_state["pattern_day_trader"] is True
    assert equity_state["trading_blocked"] is False
    assert equity_state["transfers_blocked"] is False
    assert equity_state["account_blocked"] is False
    assert equity_state["trade_suspended_by_user"] is False
    assert equity_state["shorting_enabled"] is True
    assert equity_state["risk_signals"] == [
        "margin_utilization_normal",
    ]

    assert risk_features["cash_buffer"] == 0.15
    assert risk_features["cash_ratio"] == 0.15
    assert risk_features["buying_power_ratio"] == 0.40
    assert risk_features["margin_utilization"] == 0.30
    assert risk_features["margin_utilization_ratio"] == 0.30
    assert risk_features["initial_margin_ratio"] == 0.25
    assert risk_features["maintenance_margin"] == 12_000.0
    assert risk_features["account_health"] == "healthy"
    assert risk_features["pattern_day_trader"] is True
    assert risk_features["shorting_enabled"] is True
    assert risk_features["portfolio_heat"] == 0.22
    assert risk_features["beta_risk"] == 0.18

    assert output.execution_metadata["position_count"] == 2
    assert telemetry.payloads == [
        {
            "symbol": "SPY",
            "position_count": 2,
            "drawdown_percent": 0.05,
        }
    ]


class _FakeServiceRunner:
    def __init__(
        self,
        state: dict[str, Any],
    ) -> None:
        self.state = state

    async def run(
        self,
        *,
        service: object,
        request: object,
    ) -> ServiceResult[PortfolioAnalysisResult]:
        request_id = getattr(
            request,
            "request_id",
            "request-1",
        )

        return ServiceResult.ok(
            request_id=request_id,
            request_name="PortfolioAnalysisRequest",
            result=PortfolioAnalysisResult(
                portfolio_state=self.state["portfolio_state"],
                positions_state=self.state["positions_state"],
                equity_state=self.state["equity_state"],
                canonical_portfolio_state=_canonical_portfolio_state(),
                positions=(
                    {
                        "symbol": "SPY",
                        "market_value": 70_000.0,
                        "exposure_weight": 0.70,
                    },
                    {
                        "symbol": "AAPL",
                        "market_value": 15_000.0,
                        "exposure_weight": 0.15,
                    },
                ),
                exposures={
                    "gross_exposure": 0.85,
                    "net_exposure": 0.85,
                    "sector_exposure": {"ETF": 0.70, "Technology": 0.15},
                    "asset_class_exposure": {"equity": 0.85},
                },
                risk_metrics={
                    "risk_intensity": 0.33,
                    "drawdown_percent": 0.05,
                },
                allocation_data={
                    "asset_class_exposure": {"equity": 0.85},
                },
                current_equity=100_000.0,
                peak_equity=105_000.0,
                drawdown_absolute=5_000.0,
                drawdown_percent=0.05,
                provider_source="test-provider",
                history_period="1A",
                history_timeframe="1D",
            ),
        )


class _FakeTelemetry:
    def __init__(
        self,
    ) -> None:
        self.payloads: list[dict[str, Any]] = []

    async def emit_agent_signal(
        self,
        *,
        agent_name: str,
        signal_name: str,
        confidence: float,
        context: object | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.payloads.append(
            dict(payload or {}),
        )


def _portfolio_payload() -> dict[str, Any]:
    return {
        "portfolio_state": {
            "positions": [
                {
                    "symbol": "WRONG",
                }
            ],
            "portfolio_value": 100_000.0,
            "equity": 100_000.0,
            "cash": 15_000.0,
            "cash_pct": 0.15,
            "position_count": 99,
            "gross_exposure": 0.85,
            "net_exposure": 0.85,
            "long_exposure": 0.85,
            "short_exposure": 0.0,
            "leverage": 1.0,
            "largest_position_pct": 0.70,
            "concentration_score": 0.40,
            "diversification_score": 0.60,
            "sector_exposure": {
                "ETF": 0.70,
                "Technology": 0.15,
            },
            "asset_class_exposure": {
                "equity": 0.85,
            },
            "beta_exposure": 1.05,
            "beta_risk": 0.18,
            "portfolio_heat": 0.22,
            "risk_intensity": 0.33,
            "portfolio_regime": "balanced",
            "directional_bias": "long",
            "realized_pnl": 1250.0,
            "unrealized_pnl": 3500.0,
            "pnl_total": 4750.0,
            "risk_signals": [
                "portfolio_risk_normal",
            ],
        },
        "positions_state": {
            "positions": [
                {
                    "symbol": "SPY",
                    "market_value": 70_000.0,
                },
                {
                    "symbol": "AAPL",
                    "market_value": 15_000.0,
                },
            ],
            "gross_exposure": 0.85,
            "net_exposure": 0.85,
            "long_exposure": 0.85,
            "short_exposure": 0.0,
            "concentration_risk": 0.40,
            "leverage_risk": 0.0,
            "position_count": 2,
            "long_position_count": 2,
            "short_position_count": 0,
            "risk_signals": [
                "position_concentration_normal",
            ],
        },
        "equity_state": {
            "equity": 100_000.0,
            "last_equity": 99_000.0,
            "portfolio_value": 100_000.0,
            "cash": 15_000.0,
            "buying_power": 40_000.0,
            "regt_buying_power": 35_000.0,
            "daytrading_buying_power": 80_000.0,
            "non_marginable_buying_power": 10_000.0,
            "options_buying_power": 20_000.0,
            "peak_equity": 105_000.0,
            "drawdown_absolute": 5_000.0,
            "drawdown_percent": 0.05,
            "capital_base": 95_000.0,
            "equity_retention_ratio": 1.05,
            "cash_ratio": 0.15,
            "buying_power_ratio": 0.40,
            "long_market_value": 85_000.0,
            "short_market_value": 0.0,
            "gross_market_value": 85_000.0,
            "net_market_value": 85_000.0,
            "long_exposure_ratio": 0.85,
            "short_exposure_ratio": 0.0,
            "gross_exposure_ratio": 0.85,
            "net_exposure_ratio": 0.85,
            "initial_margin": 25_000.0,
            "maintenance_margin": 12_000.0,
            "last_maintenance_margin": 11_500.0,
            "margin_utilization_ratio": 0.30,
            "initial_margin_ratio": 0.25,
            "multiplier": 2.0,
            "accrued_fees": 12.5,
            "pending_transfer_in": 0.0,
            "pending_transfer_out": 0.0,
            "daytrade_count": 1,
            "pattern_day_trader": True,
            "trading_blocked": False,
            "transfers_blocked": False,
            "account_blocked": False,
            "trade_suspended_by_user": False,
            "shorting_enabled": True,
            "options_approved_level": 2,
            "options_trading_level": 2,
            "account_health": "healthy",
            "risk_signals": [
                "margin_utilization_normal",
            ],
        },
    }


def _canonical_portfolio_state() -> PortfolioState:
    return PortfolioState(
        account_id="account-1",
        timestamp=datetime(2026, 7, 10, 13, 30, tzinfo=UTC),
        equity=100_000.0,
        peak_equity=105_000.0,
        portfolio_value=100_000.0,
        cash=15_000.0,
        buying_power=40_000.0,
        last_equity=99_000.0,
        cash_ratio=0.15,
        buying_power_ratio=0.40,
        drawdown_absolute=5_000.0,
        drawdown_percent=0.05,
        gross_exposure=0.85,
        net_exposure=0.85,
        long_exposure=0.85,
        short_exposure=0.0,
        leverage=1.0,
        risk_intensity=0.33,
        sector_exposure={"ETF": 0.70, "Technology": 0.15},
        asset_class_exposure={"equity": 0.85},
        risk_signals={"portfolio_risk_normal": True},
        snapshot_id="snapshot-1",
    )
