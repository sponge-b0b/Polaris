from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from application.services.base import ServiceDegradation, ServiceRequest, ServiceResult
from application.services.base.application_service import (
    ApplicationService,
    ValidatingApplicationService,
)
from application.services.news import headline_filtering
from application.services.news.news_request import NewsRequest
from application.services.news.news_result import NewsArticle, NewsResult

if TYPE_CHECKING:
    from integration.providers.news.news_provider import NewsProvider


class NewsService(ApplicationService, ValidatingApplicationService):
    """
    Polaris News Intelligence Engine.

    Pipeline:
    1. Fetch (multi-source)
    2. Headline filtering (NEW)
    3. Normalization
    4. Deduplication
    5. Scoring
    6. Ranking

    Output:
    Clean macro-relevant intelligence feed.
    """

    service_name = "news_service"

    def __init__(
        self,
        news_provider: NewsProvider,
    ) -> None:

        self.news_provider = news_provider

    async def run(
        self,
        request: ServiceRequest[NewsRequest],
    ) -> ServiceResult[NewsResult]:
        result, degradations = await self._execute_with_degradations(
            request.payload,
        )

        return ServiceResult.ok(
            request_id=request.request_id,
            request_name=request.request_name,
            result=result,
            degradations=degradations,
        )

    async def validate_request(
        self,
        request: ServiceRequest[NewsRequest],
    ) -> tuple[str, ...]:
        errors: list[str] = []

        if not isinstance(request.payload, NewsRequest):
            return (f"Unsupported service request: {request.request_name}",)

        if not request.payload.symbol.strip():
            errors.append(
                "symbol is required.",
            )

        if not request.payload.query.strip():
            errors.append(
                "query is required.",
            )

        if request.payload.limit < 1:
            errors.append(
                "limit must be at least 1.",
            )

        return tuple(errors)

    # ============================================================
    # MAIN ENTRYPOINT
    # ============================================================

    async def _execute(
        self,
        request: NewsRequest,
    ) -> NewsResult:
        result, _ = await self._execute_with_degradations(request)
        return result

    async def _execute_with_degradations(
        self,
        request: NewsRequest,
    ) -> tuple[NewsResult, tuple[ServiceDegradation, ...]]:

        symbol = request.symbol
        query = request.query
        limit = request.limit

        raw_news: list[dict[str, Any]] = []

        # ========================================================
        # FETCH MULTI-SOURCE
        # ========================================================

        provider_results = await asyncio.gather(
            self.news_provider.get_financial_news(
                query=query,
                limit=limit,
            ),
            self.news_provider.get_market_news(
                symbol=symbol,
            ),
            return_exceptions=True,
        )

        degradations: list[ServiceDegradation] = []
        for source_name, provider_result in zip(
            ("financial_news", "market_news"),
            provider_results,
            strict=False,
        ):
            if isinstance(provider_result, BaseException):
                if isinstance(provider_result, asyncio.CancelledError):
                    raise provider_result
                degradations.append(
                    ServiceDegradation(
                        code="provider_call_failed",
                        component=source_name,
                        summary=(
                            "News provider call failed; the service completed "
                            "with remaining provider data."
                        ),
                        error_type=type(provider_result).__name__,
                    )
                )
                continue

            if not isinstance(provider_result, list):
                degradations.append(
                    ServiceDegradation(
                        code="invalid_provider_payload",
                        component=source_name,
                        summary=(
                            "News provider returned an invalid payload; the service "
                            "completed with remaining provider data."
                        ),
                        error_type="InvalidProviderPayload",
                    )
                )
                continue

            raw_news.extend(provider_result)

        if len(degradations) == len(provider_results):
            raise RuntimeError("All news provider calls failed.")

        # ========================================================
        # 🧠 NEW: HEADLINE FILTERING LAYER (EARLY GATE)
        # ========================================================

        filtered_news = headline_filtering.filter(raw_news)

        # ========================================================
        # NORMALIZATION
        # ========================================================

        normalized = [self._normalize(article) for article in filtered_news]

        # ========================================================
        # DEDUPLICATION
        # ========================================================

        deduped = self._deduplicate(normalized)

        # ========================================================
        # SCORING
        # ========================================================

        scored = [self._score(article, symbol) for article in deduped]

        # ========================================================
        # SORT BY INTELLIGENCE VALUE
        # ========================================================

        scored.sort(
            key=lambda x: x["relevance_score"],
            reverse=True,
        )

        return (
            NewsResult(
                articles=tuple(
                    self._to_news_article(article) for article in scored[:limit]
                ),
            ),
            tuple(degradations),
        )

    def _to_news_article(
        self,
        article: dict[str, Any],
    ) -> NewsArticle:
        return NewsArticle(
            article_id=str(article["id"]),
            title=str(article["title"]),
            summary=str(article["summary"]),
            source=article["source"],
            url=article["url"],
            published_at=article["published_at"],
            headline_score=float(article["headline_score"]),
            relevance_score=float(article["relevance_score"]),
            sentiment_hint=float(article["sentiment_hint"]),
            raw=article["raw"],
        )

    # ============================================================
    # NORMALIZATION
    # ============================================================

    def _normalize(
        self,
        article: dict[str, Any],
    ) -> dict[str, Any]:

        title = article.get("title") or article.get("headline", "")
        summary = article.get("description") or article.get("summary", "")

        return {
            "id": self._generate_id(title, summary),
            "title": title,
            "summary": summary,
            "source": article.get("source", "unknown"),
            "url": article.get("url"),
            "published_at": (
                article.get("published_at")
                or article.get("publishedAt")
                or article.get("datetime")
            ),
            "headline_score": article.get("headline_score", 0.5),
            "raw": article,
        }

    # ============================================================
    # DEDUPLICATION
    # ============================================================

    def _deduplicate(
        self,
        articles: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        seen = set()
        output = []

        for a in articles:
            key = a["id"]

            if key in seen:
                continue

            seen.add(key)
            output.append(a)

        return output

    # ============================================================
    # SCORING ENGINE
    # ============================================================

    def _score(
        self,
        article: dict[str, Any],
        symbol: str,
    ) -> dict[str, Any]:

        text = (
            (article.get("title") or "").lower()
            + " "
            + (article.get("summary") or "").lower()
        )

        score = 0.2

        # ========================================================
        # HEADLINE FILTER BOOST (IMPORTANT INTEGRATION)
        # ========================================================

        score += article.get("headline_score", 0.5) * 0.4

        # ========================================================
        # SYMBOL RELEVANCE
        # ========================================================

        if symbol.lower() in text:
            score += 0.35

        # ========================================================
        # MACRO SIGNAL BOOST
        # ========================================================

        if any(
            k in text
            for k in [
                "fed",
                "inflation",
                "rates",
                "cpi",
                "yield",
                "liquidity",
                "recession",
            ]
        ):
            score += 0.25

        # ========================================================
        # MARKET EVENT BOOST
        # ========================================================

        if any(
            k in text
            for k in [
                "crash",
                "surge",
                "hawkish",
                "dovish",
                "shock",
            ]
        ):
            score += 0.15

        score = min(score, 1.0)

        article["relevance_score"] = score

        article["sentiment_hint"] = self._sentiment_hint(text)

        return article

    # ============================================================
    # SENTIMENT HEURISTIC
    # ============================================================

    def _sentiment_hint(self, text: str) -> float:

        bullish = ["rally", "surge", "beat", "growth", "upgrade"]
        bearish = ["crash", "miss", "recession", "downgrade", "drop"]

        score = 0.0

        for w in bullish:
            if w in text:
                score += 0.1

        for w in bearish:
            if w in text:
                score -= 0.1

        return max(-1.0, min(score, 1.0))

    # ============================================================
    # ID GENERATION
    # ============================================================

    def _generate_id(
        self,
        title: str,
        summary: str,
    ) -> str:

        import hashlib

        raw = (title + summary).encode("utf-8")

        return hashlib.md5(raw).hexdigest()
