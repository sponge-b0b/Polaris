from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class NewsArticle:
    """Normalized news article produced by the news application service."""

    article_id: str
    title: str
    summary: str
    source: Any
    url: Any
    published_at: Any
    headline_score: float
    relevance_score: float
    sentiment_hint: float
    raw: dict[str, Any]

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "id": self.article_id,
            "title": self.title,
            "summary": self.summary,
            "source": deepcopy(self.source),
            "url": deepcopy(self.url),
            "published_at": deepcopy(self.published_at),
            "headline_score": self.headline_score,
            "relevance_score": self.relevance_score,
            "sentiment_hint": self.sentiment_hint,
            "raw": deepcopy(self.raw),
        }


@dataclass(
    frozen=True,
    slots=True,
)
class NewsResult:
    """Typed result for news intelligence orchestration."""

    articles: tuple[NewsArticle, ...]

    def to_list(
        self,
    ) -> list[dict[str, Any]]:
        return [article.to_dict() for article in self.articles]
