from typing import Any

from integration.providers.market_events.market_events_provider import (
    MarketEventsProvider,
)


class SimulatedEventsProvider(MarketEventsProvider):
    """
    Deterministic Backtest Market Events Provider

    ============================================================
    PURPOSE
    ============================================================
    """

    def __init__(
        self,
    ) -> None:
        pass

    async def get_fed_events(
        self,
        days_ahead: int = 14,
    ) -> list[dict[str, Any]]:

        return []

    async def get_economic_events(
        self,
        days_ahead: int = 14,
    ) -> list[dict[str, Any]]:

        return []

    async def get_earnings_events(
        self,
        horizon: str = "3month",
        symbols: set[str] | None = None,
    ) -> list[dict[str, Any]]:

        return []
