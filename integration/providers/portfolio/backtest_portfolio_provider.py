from __future__ import annotations
from typing import Any

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.providers.portfolio.portfolio_provider import (
    PortfolioProvider,
)

from integration.providers.backtesting.portfolio.simulated_portfolio_provider import (
    SimulatedPortfolioProvider,
)
from integration.providers.provider_telemetry import record_provider_call


class BacktestPortfolioProvider(PortfolioProvider):
    """
    Simulated portfolio provider for backtesting.

    Supplies:
    - simulated account state
    - simulated positions
    """

    def __init__(
        self,
        portfolio_provider: SimulatedPortfolioProvider,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:

        self.portfolio_provider = portfolio_provider
        self.telemetry = telemetry

    @property
    def source(self) -> str:
        return "backtest"

    # ============================================================
    # ACCOUNT
    # ============================================================

    async def get_account(self) -> dict[str, Any]:

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_account",
            self.portfolio_provider.get_account,
        )

    # ============================================================
    # POSITIONS
    # ============================================================

    async def get_positions(self) -> list[dict[str, Any]]:

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_positions",
            self.portfolio_provider.get_positions,
        )

    # ============================================================
    # PORTFOLIO HISTORY
    # ============================================================

    async def get_portfolio_history(
        self,
        *,
        period: str = "1A",
        timeframe: str = "1D",
    ) -> dict[str, Any]:
        async def call() -> dict[str, Any]:
            return await self.portfolio_provider.get_portfolio_history(
                period=period,
                timeframe=timeframe,
            )

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_portfolio_history",
            call,
            attributes={
                "period": period,
                "timeframe": timeframe,
            },
        )
