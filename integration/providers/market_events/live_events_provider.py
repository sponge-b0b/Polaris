from typing import Any

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.clients.market_events.alphavantage_events_client import (
    AlphaVantageEarningsClient,
)
from integration.clients.market_events.fed_events_client import FedEventsClient
from integration.clients.market_events.fred_events_client import FredEventsClient
from integration.providers.market_events.market_events_provider import (
    MarketEventsProvider,
)
from integration.providers.provider_telemetry import record_provider_call


class LiveEventsProvider(MarketEventsProvider):
    def __init__(
        self,
        fed_client: FedEventsClient,
        fred_client: FredEventsClient,
        earnings_client: AlphaVantageEarningsClient,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:

        self.fed_client = fed_client
        self.fred_client = fred_client
        self.earnings_client = earnings_client
        self.telemetry = telemetry

    async def get_fed_events(
        self,
        days_ahead: int = 14,
    ) -> list[dict[str, Any]]:

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_fed_events",
            lambda: self.fed_client.get_fed_events(
                days_ahead=days_ahead,
            ),
        )

    async def get_economic_events(
        self,
        days_ahead: int = 14,
    ) -> list[dict[str, Any]]:

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_economic_events",
            lambda: self.fred_client.get_economic_events(
                days_ahead=days_ahead,
            ),
        )

    async def get_earnings_events(
        self,
        horizon: str = "3month",
        symbols: set[str] | None = None,
    ) -> list[dict[str, Any]]:

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_earnings_events",
            lambda: self.earnings_client.get_earnings_calendar(
                horizon=horizon,
                symbols=symbols,
            ),
        )
