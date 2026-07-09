from typing import Dict, List, Any
from integration.providers.backtesting.market_events.simulated_events_provider import (
    SimulatedEventsProvider,
)
from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.providers.market_events.market_events_provider import (
    MarketEventsProvider,
)
from integration.providers.provider_telemetry import record_provider_call


class BacktestEventsProvider(MarketEventsProvider):
    def __init__(
        self,
        events_provider: SimulatedEventsProvider,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:

        self.events_provider = events_provider
        self.telemetry = telemetry

    async def get_fed_events(
        self,
        days_ahead: int = 14,
    ) -> List[Dict[str, Any]]:

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_fed_events",
            lambda: self.events_provider.get_fed_events(
                days_ahead=days_ahead,
            ),
        )

    async def get_economic_events(
        self,
        days_ahead: int = 14,
    ) -> List[Dict[str, Any]]:

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_economic_events",
            lambda: self.events_provider.get_economic_events(
                days_ahead=days_ahead,
            ),
        )

    async def get_earnings_events(
        self,
        horizon: str = "3month",
        symbols: set[str] | None = None,
    ) -> List[Dict[str, Any]]:

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_earnings_events",
            lambda: self.events_provider.get_earnings_events(
                horizon=horizon,
                symbols=symbols,
            ),
        )
