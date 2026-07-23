from typing import Any

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.providers.news.news_provider import NewsProvider
from integration.providers.provider_telemetry import record_provider_call


class BacktestNewsProvider(NewsProvider):
    def __init__(
        self,
        news_provider: NewsProvider,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:

        self.news_provider = news_provider
        self.telemetry = telemetry

    async def get_financial_news(
        self,
        query: str,
        sort_by: str = "publishedAt",
        limit: int = 20,
    ) -> list[dict[str, Any]]:

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_financial_news",
            lambda: self.news_provider.get_financial_news(
                query=query,
                sort_by=sort_by,
                limit=limit,
            ),
        )

    async def get_market_news(
        self,
        symbol: str = "SPY",
        limit: int = 20,
    ) -> list[dict[str, Any]]:

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_market_news",
            lambda: self.news_provider.get_market_news(
                symbol=symbol,
                limit=limit,
            ),
        )
