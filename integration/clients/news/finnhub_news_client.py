from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from config.settings import Settings

logger = logging.getLogger(__name__)


class FinnhubNewsClient:
    """Finnhub market and company news client."""

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, settings: Settings, timeout: int = 10) -> None:
        self.api_key = settings.FINNHUB_API_KEY
        self.timeout = timeout
        if not self.api_key:
            raise ValueError("Missing FINNHUB_API_KEY environment variable.")

    async def get_all_news(
        self,
        symbol: str = "SPY",
        limit: int = 20,
        client: httpx.AsyncClient | None = None,
    ) -> list[dict[str, Any]]:
        if client is not None:
            return await self._collect_all_news(
                symbol=symbol,
                limit=limit,
                client=client,
            )
        async with httpx.AsyncClient(timeout=self.timeout) as owned_client:
            return await self._collect_all_news(
                symbol=symbol,
                limit=limit,
                client=owned_client,
            )

    async def _collect_all_news(
        self,
        *,
        symbol: str,
        limit: int,
        client: httpx.AsyncClient,
    ) -> list[dict[str, Any]]:
        results = await asyncio.gather(
            self.get_company_news(symbol=symbol, limit=limit, client=client),
            self.get_market_news(category="general", limit=limit, client=client),
            return_exceptions=True,
        )
        all_news: list[dict[str, Any]] = []
        failures = 0
        for source, result in zip(("company_news", "market_news"), results):
            if isinstance(result, asyncio.CancelledError):
                raise result
            if isinstance(result, BaseException):
                failures += 1
                logger.warning(
                    "Finnhub news source failed",
                    extra={"news_source": source, "error_type": type(result).__name__},
                    exc_info=(type(result), result, result.__traceback__),
                )
                continue
            all_news.extend(result)
        if failures == len(results):
            raise RuntimeError("All Finnhub news sources failed.")
        return all_news

    async def get_company_news(
        self,
        symbol: str = "SPY",
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 20,
        client: httpx.AsyncClient | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"symbol": symbol}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        data = await self._get_with_optional_client(
            endpoint="company-news",
            params=params,
            client=client,
        )
        return self._normalize(data, limit)

    async def get_market_news(
        self,
        category: str = "general",
        limit: int = 20,
        client: httpx.AsyncClient | None = None,
    ) -> list[dict[str, Any]]:
        data = await self._get_with_optional_client(
            endpoint="news",
            params={"category": category},
            client=client,
        )
        return self._normalize(data, limit)

    async def _get_with_optional_client(
        self,
        *,
        endpoint: str,
        params: dict[str, Any],
        client: httpx.AsyncClient | None,
    ) -> list[dict[str, Any]]:
        if client is not None:
            return await self._get(endpoint=endpoint, params=params, client=client)
        async with httpx.AsyncClient(timeout=self.timeout) as owned_client:
            return await self._get(
                endpoint=endpoint,
                params=params,
                client=owned_client,
            )

    async def _get(
        self,
        *,
        endpoint: str,
        params: dict[str, Any],
        client: httpx.AsyncClient,
    ) -> list[dict[str, Any]]:
        request_params = {**params, "token": self.api_key}
        response = await client.get(
            f"{self.BASE_URL}/{endpoint}",
            params=request_params,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError(
                f"Finnhub endpoint {endpoint} returned a non-list payload."
            )
        return [item for item in payload if isinstance(item, dict)]

    def _normalize(
        self,
        articles: list[dict[str, Any]],
        limit: int,
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": article.get("id"),
                "headline": article.get("headline"),
                "summary": article.get("summary"),
                "source": "finnhub",
                "url": article.get("url"),
                "image": article.get("image"),
                "category": article.get("category"),
                "datetime": article.get("datetime"),
                "related": article.get("related"),
                "relevance_score": 0.5,
                "sentiment_hint": 0.0,
            }
            for article in articles[:limit]
        ]
