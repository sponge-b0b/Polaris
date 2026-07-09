from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from newsapi import NewsApiClient as NewsRESTClient
from config.settings import Settings


class NewsApiNewsClient:
    """
    NewsAPI Provider Client.

    Purpose:
    - centralized NewsAPI access layer
    - standardized news retrieval
    - reusable across agents and engines
    - future-ready for retries/caching/rate limits

    Environment Variables:
    - NEWSAPI_API_KEY
    """

    def __init__(
        self,
        settings: Settings,
    ) -> None:

        self.api_key = settings.NEWSAPI_API_KEY

        if not self.api_key:
            raise ValueError("NEWSAPI_API_KEY not found in environment variables.")

        self.client = NewsRESTClient(api_key=self.api_key)

    # ============================================================
    # EVERYTHING SEARCH
    # ============================================================

    async def get_financial_news(
        self,
        query: str,
        language: str = "en",
        sort_by: str = "publishedAt",
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        Search all indexed articles.

        sort_by:
        - relevancy
        - popularity
        - publishedAt
        """

        response = await asyncio.to_thread(
            self.client.get_everything,
            q=query,
            language=language,
            sort_by=sort_by,
            page_size=page_size,
        )
        return self._normalize_response(response)

    # ============================================================
    # TOP HEADLINES
    # ============================================================

    async def get_top_headlines(
        self,
        category: Optional[str] = None,
        country: str = "us",
        page_size: int = 25,
    ) -> Dict[str, Any]:
        """
        Retrieve top headlines.

        categories:
        - business
        - technology
        - science
        - health
        """

        response = await asyncio.to_thread(
            self.client.get_top_headlines,
            category=category,
            country=country,
            page_size=page_size,
        )
        return self._normalize_response(response)

    # ============================================================
    # FINANCIAL MARKET NEWS
    # ============================================================

    async def get_market_news(
        self,
        symbols: Optional[List[str]] = None,
        page_size: int = 25,
    ) -> Dict[str, Any]:
        """
        Retrieve market-focused news.

        Example:
        - SPY
        - QQQ
        - Federal Reserve
        - Inflation
        """

        default_terms = [
            "S&P 500",
            "SPY",
            "Federal Reserve",
            "inflation",
            "interest rates",
            "market volatility",
        ]

        if symbols:
            default_terms.extend(symbols)

        query = " OR ".join(default_terms)

        return await self.get_financial_news(
            query=query,
            page_size=page_size,
        )

    # ============================================================
    # NORMALIZATION
    # ============================================================

    def _normalize_response(
        self,
        response: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Standardize NewsAPI responses.

        This creates a stable internal format
        independent of provider structure.
        """

        articles = []

        for article in response.get(
            "articles",
            [],
        ):
            articles.append(
                {
                    "source": (
                        article.get(
                            "source",
                            {},
                        ).get("name")
                    ),
                    "author": article.get("author"),
                    "title": article.get("title"),
                    "description": article.get("description"),
                    "url": article.get("url"),
                    "published_at": article.get("publishedAt"),
                    "content": article.get("content"),
                }
            )

        return {
            "status": response.get(
                "status",
                "unknown",
            ),
            "total_results": response.get(
                "totalResults",
                0,
            ),
            "articles": articles,
        }
