from typing import Any

from integration.providers.news.news_provider import NewsProvider


class SimulatedNewsProvider(NewsProvider):
    def __init__(
        self,
    ) -> None:
        pass

    async def get_financial_news(
        self,
        query: str,
        sort_by: str = "publishedAt",
        limit: int = 20,
    ) -> list[dict[str, Any]]:

        return []

    async def get_market_news(
        self,
        symbol: str = "SPY",
        limit: int = 20,
    ) -> list[dict[str, Any]]:

        return []
