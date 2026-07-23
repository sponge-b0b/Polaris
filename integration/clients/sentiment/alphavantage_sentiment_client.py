from __future__ import annotations

from typing import Any

import httpx

from config.settings import Settings
from core.utils.utils import _safe_float


class AlphaVantageSentimentClient:
    """
    Alpha Vantage News Sentiment Client.

    PURPOSE:
    --------
    - fetch ticker-specific news sentiment
    - aggregate article sentiment into canonical snapshot
    - normalize Alpha Vantage output for internal systems

    OUTPUT:
    -------
    Canonical sentiment snapshot:

    {
        "sentiment_score": float,
        "overall_sentiment": str,
        "confidence_score": float,

        "components": {
            "news": float,
            "macro": float,
            "social": float,
        },

        "article_count": int,
        "raw_feed": [...]
    }

    SCORE RANGE:
    ------------
    -1.0 -> strongly bearish
     0.0 -> neutral
    +1.0 -> strongly bullish
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(
        self,
        settings: Settings,
        timeout: int = 15,
        max_articles: int = 20,
    ) -> None:

        self.api_key = settings.ALPHAVANTAGE_API_KEY
        self.timeout = timeout
        self.max_articles = max_articles

        if not self.api_key:
            raise ValueError("Missing ALPHAVANTAGE_API_KEY environment variable.")

    # ============================================================
    # MAIN ENTRY
    # ============================================================

    async def get_news_sentiment(
        self,
        symbol: str = "SPY",
        client: httpx.AsyncClient | None = None,
    ) -> dict[str, Any]:

        if client is not None:
            raw = await self._fetch_news_sentiment(symbol, client)
        else:
            async with httpx.AsyncClient() as client:
                raw = await self._fetch_news_sentiment(symbol, client)

        feed = raw.get("feed", [])
        if not feed:
            return self._empty_response(symbol)

        # ========================================================
        # ARTICLE AGGREGATION
        # ========================================================

        weighted_scores: list[float] = []
        relevance_scores: list[float] = []

        article_sentiments = []

        for article in feed:
            ticker_data = self._extract_ticker_data(
                article,
                symbol,
            )

            if not ticker_data:
                continue

            sentiment_score = _safe_float(
                ticker_data.get(
                    "ticker_sentiment_score",
                    0.0,
                )
            )

            relevance_score = _safe_float(
                ticker_data.get(
                    "relevance_score",
                    0.0,
                )
            )

            weighted_sentiment = sentiment_score * relevance_score

            weighted_scores.append(weighted_sentiment)

            relevance_scores.append(relevance_score)

            article_sentiments.append(
                {
                    "title": article.get(
                        "title",
                        "",
                    ),
                    "time_published": article.get(
                        "time_published",
                        "",
                    ),
                    "source": article.get(
                        "source",
                        "",
                    ),
                    "sentiment_score": sentiment_score,
                    "relevance_score": relevance_score,
                    "weighted_score": weighted_sentiment,
                    "sentiment_label": ticker_data.get(
                        "ticker_sentiment_label",
                        "neutral",
                    ),
                }
            )

        # ========================================================
        # EMPTY GUARD
        # ========================================================

        if not weighted_scores:
            return self._empty_response(symbol)

        # ========================================================
        # FINAL COMPOSITE SCORE
        # ========================================================

        total_relevance = sum(relevance_scores) or 1.0

        composite_score = sum(weighted_scores) / total_relevance

        composite_score = max(
            -1.0,
            min(composite_score, 1.0),
        )

        # ========================================================
        # CONFIDENCE MODEL
        # ========================================================

        confidence = self._compute_confidence(
            weighted_scores,
            relevance_scores,
        )

        # ========================================================
        # REGIME CLASSIFICATION
        # ========================================================

        overall_sentiment = self._classify_sentiment(composite_score)

        # ========================================================
        # FINAL SNAPSHOT
        # ========================================================

        return {
            "symbol": symbol,
            "sentiment_score": composite_score,
            "overall_sentiment": overall_sentiment,
            "confidence_score": confidence,
            # ====================================================
            # COMPONENTS
            # ====================================================
            "components": {
                "news": composite_score,
                # placeholders for future expansion
                "macro": 0.0,
                "social": 0.0,
            },
            "article_count": len(article_sentiments),
            # ====================================================
            # RAW ARTICLE DATA
            # ====================================================
            "articles": article_sentiments,
            "raw_feed": feed,
        }

    # ============================================================
    # API FETCH
    # ============================================================

    async def _fetch_news_sentiment(
        self, symbol: str, client: httpx.AsyncClient
    ) -> dict[str, Any]:

        params: dict[str, str | int | float | bool | None] = {
            "function": "NEWS_SENTIMENT",
            "tickers": symbol,
            "apikey": self.api_key,
            "limit": self.max_articles,
        }

        response = await client.get(
            self.BASE_URL,
            params=params,
            timeout=self.timeout,
        )

        response.raise_for_status()
        return response.json()

    # ============================================================
    # TICKER EXTRACTION
    # ============================================================

    def _extract_ticker_data(
        self,
        article: dict[str, Any],
        symbol: str,
    ) -> dict[str, Any] | None:

        ticker_sentiment = article.get(
            "ticker_sentiment",
            [],
        )

        for item in ticker_sentiment:
            if item.get("ticker", "").upper() == symbol.upper():
                return item

        return None

    # ============================================================
    # CONFIDENCE MODEL
    # ============================================================

    def _compute_confidence(
        self,
        weighted_scores: list[float],
        relevance_scores: list[float],
    ) -> float:

        if not weighted_scores:
            return 0.0

        # ========================================================
        # DISPERSION / DIVERGENCE
        # ========================================================

        mean_score = sum(weighted_scores) / len(weighted_scores)

        variance = sum((score - mean_score) ** 2 for score in weighted_scores) / len(
            weighted_scores
        )

        divergence_penalty = min(
            variance,
            1.0,
        )

        # ========================================================
        # RELEVANCE CONFIDENCE
        # ========================================================

        avg_relevance = sum(relevance_scores) / len(relevance_scores)

        confidence = avg_relevance * (1.0 - divergence_penalty)

        return max(
            0.0,
            min(confidence, 1.0),
        )

    # ============================================================
    # REGIME CLASSIFICATION
    # ============================================================

    def _classify_sentiment(
        self,
        score: float,
    ) -> str:

        if score >= 0.60:
            return "strongly_bullish"

        if score >= 0.20:
            return "moderately_bullish"

        if score <= -0.60:
            return "strongly_bearish"

        if score <= -0.20:
            return "moderately_bearish"

        return "neutral"

    # ============================================================
    # EMPTY RESPONSE
    # ============================================================

    def _empty_response(
        self,
        symbol: str,
    ) -> dict[str, Any]:

        return {
            "symbol": symbol,
            "sentiment_score": 0.0,
            "overall_sentiment": "neutral",
            "confidence_score": 0.0,
            "components": {
                "news": 0.0,
                "macro": 0.0,
                "social": 0.0,
            },
            "article_count": 0,
            "articles": [],
            "raw_feed": [],
        }
