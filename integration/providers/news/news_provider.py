from typing import Any, Dict, List, Protocol, runtime_checkable


@runtime_checkable
class NewsProvider(Protocol):
    """
    Canonical news provider interface.

    ALL news providers MUST implement this interface.
    """

    async def get_financial_news(
        self,
        query: str,
        sort_by: str = "publishedAt",
        limit: int = 20,
    ) -> List[Dict[str, Any]]: ...

    async def get_market_news(
        self,
        symbol: str = "SPY",
        limit: int = 20,
    ) -> List[Dict[str, Any]]: ...
