from __future__ import annotations

from typing import Any

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.clients.news.finnhub_news_client import FinnhubNewsClient
from integration.clients.news.newsapi_news_client import NewsApiNewsClient
from integration.providers.news.news_provider import NewsProvider
from integration.providers.provider_telemetry import record_provider_call


class LiveNewsProvider(NewsProvider):
    def __init__(
        self,
        finnhub_news_client: FinnhubNewsClient,
        newsapi_news_client: NewsApiNewsClient,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:

        self.finnhub_news_client = finnhub_news_client
        self.newsapi_news_client = newsapi_news_client
        self.telemetry = telemetry

    async def get_financial_news(
        self,
        query: str,
        sort_by: str = "publishedAt",
        limit: int = 20,
    ) -> list[dict[str, Any]]:

        async def fetch_financial_news() -> list[dict[str, Any]]:
            response = await self.newsapi_news_client.get_financial_news(
                query=query,
                sort_by=sort_by,
                page_size=limit,
            )
            articles = response.get(
                "articles",
                [],
            )

            if not isinstance(
                articles,
                list,
            ):
                return []

            return [
                article
                for article in articles
                if isinstance(
                    article,
                    dict,
                )
            ]

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_financial_news",
            fetch_financial_news,
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
            lambda: self.finnhub_news_client.get_all_news(
                symbol=symbol,
                limit=limit,
            ),
        )
