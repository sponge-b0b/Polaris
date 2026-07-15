from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class WebSearchCandidate:
    """Typed search-discovery candidate returned by web search clients."""

    url: str
    title: str
    snippet: str | None
    rank: int
    score: float | None
    source_engine: str | None

    def __post_init__(self) -> None:
        if not self.url.strip():
            raise ValueError("url cannot be empty.")
        if not self.title.strip():
            raise ValueError("title cannot be empty.")
        if self.snippet is not None and not self.snippet.strip():
            raise ValueError("snippet cannot be empty when provided.")
        if self.rank < 0:
            raise ValueError("rank cannot be negative.")
        if self.score is not None and self.score < 0:
            raise ValueError("score cannot be negative.")
        if self.source_engine is not None and not self.source_engine.strip():
            raise ValueError("source_engine cannot be empty when provided.")


@dataclass(frozen=True, slots=True)
class CrawledWebDocument:
    """Typed crawled web document returned by content-acquisition clients."""

    url: str
    title: str
    markdown: str
    content_hash: str
    fetched_at: datetime

    def __post_init__(self) -> None:
        for field_name in ("url", "title", "markdown", "content_hash"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} cannot be empty.")
