from typing import Protocol, Dict, List, Any, runtime_checkable


@runtime_checkable
class MarketEventsProvider(Protocol):
    """
    Canonical market events provider interface.

    ALL market events providers MUST implement this interface.
    """

    async def get_fed_events(
        self,
        days_ahead: int = 14,
    ) -> List[Dict[str, Any]]: ...

    async def get_economic_events(
        self,
        days_ahead: int = 14,
    ) -> List[Dict[str, Any]]: ...

    async def get_earnings_events(
        self,
        horizon: str = "3month",
        symbols: set[str] | None = None,
    ) -> List[Dict[str, Any]]: ...
