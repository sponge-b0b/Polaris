from typing import Any, Dict, List

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.providers.portfolio.portfolio_provider import (
    PortfolioProvider,
)

from integration.clients.portfolio.alpaca_portfolio_client import (
    AlpacaPortfolioClient,
)
from integration.providers.provider_telemetry import record_provider_call


class LivePortfolioProvider(PortfolioProvider):
    """
    Live portfolio provider.
    """

    def __init__(
        self,
        portfolio_client: AlpacaPortfolioClient,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:

        self.portfolio_client = portfolio_client
        self.telemetry = telemetry

    @property
    def source(self) -> str:
        return "alpaca"

    # ============================================================
    # ACCOUNT
    # ============================================================

    async def get_account(self) -> Dict[str, Any]:

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_account",
            self.portfolio_client.get_account,
        )

    # ============================================================
    # POSITIONS
    # ============================================================

    async def get_positions(self) -> List[Dict[str, Any]]:

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_positions",
            self.portfolio_client.get_positions,
        )

    # ============================================================
    # PORTFOLIO HISTORY
    # ============================================================

    async def get_portfolio_history(self) -> Dict[str, Any]:

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_portfolio_history",
            self.portfolio_client.get_portfolio_history,
        )
