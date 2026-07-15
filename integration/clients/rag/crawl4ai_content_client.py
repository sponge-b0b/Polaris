from __future__ import annotations

import asyncio
from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from hashlib import sha256
from typing import Protocol

from integration.clients.rag.web_retrieval_models import CrawledWebDocument
from integration.clients.rag.web_retrieval_models import WebSearchCandidate


class Crawl4AiCrawler(Protocol):
    async def arun(self, url: str, config: object | None = None) -> object: ...


@dataclass(frozen=True, slots=True)
class Crawl4AiContentClientConfig:
    timeout_seconds: float = 30.0
    headless: bool = True
    cache_enabled: bool = True
    max_concurrency: int = 4
    user_agent: str | None = None

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        if self.max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1.")
        if self.user_agent is not None and not self.user_agent.strip():
            raise ValueError("user_agent cannot be empty when provided.")


class Crawl4AiContentClient:
    """Crawl4AI-backed client for clean Markdown content acquisition."""

    def __init__(
        self,
        *,
        config: Crawl4AiContentClientConfig | None = None,
        crawler: Crawl4AiCrawler | None = None,
    ) -> None:
        self._config = config or Crawl4AiContentClientConfig()
        self._crawler = crawler

    async def crawl(
        self,
        candidates: Sequence[WebSearchCandidate],
    ) -> tuple[CrawledWebDocument, ...]:
        if not candidates:
            return ()
        unique_candidates = _deduplicate_candidates(candidates)
        if self._crawler is not None:
            return await self._crawl_with_crawler(self._crawler, unique_candidates)

        from crawl4ai import AsyncWebCrawler

        async with AsyncWebCrawler(config=self._browser_config()) as crawler:
            return await self._crawl_with_crawler(crawler, unique_candidates)

    async def _crawl_with_crawler(
        self,
        crawler: Crawl4AiCrawler,
        candidates: tuple[WebSearchCandidate, ...],
    ) -> tuple[CrawledWebDocument, ...]:
        run_config = self._run_config()
        semaphore = asyncio.Semaphore(self._config.max_concurrency)

        async def crawl_one(candidate: WebSearchCandidate) -> CrawledWebDocument | None:
            async with semaphore:
                try:
                    result = await asyncio.wait_for(
                        crawler.arun(candidate.url, config=run_config),
                        timeout=self._config.timeout_seconds,
                    )
                except TimeoutError:
                    return None
                return _normalize_document(candidate, result)

        documents = await asyncio.gather(
            *(crawl_one(candidate) for candidate in candidates),
        )
        return tuple(document for document in documents if document is not None)

    def _browser_config(self) -> object:
        from crawl4ai import BrowserConfig

        kwargs: dict[str, object] = {
            "headless": self._config.headless,
            "verbose": False,
        }
        if self._config.user_agent is not None:
            kwargs["headers"] = {"User-Agent": self._config.user_agent}
            kwargs["user_agent"] = self._config.user_agent
        return BrowserConfig(**kwargs)

    def _run_config(self) -> object:
        from crawl4ai import CacheMode
        from crawl4ai import CrawlerRunConfig

        return CrawlerRunConfig(
            cache_mode=(
                CacheMode.ENABLED if self._config.cache_enabled else CacheMode.BYPASS
            ),
            only_text=False,
            page_timeout=int(self._config.timeout_seconds * 1000),
            remove_forms=True,
            exclude_external_images=True,
            verbose=False,
        )


def _deduplicate_candidates(
    candidates: Sequence[WebSearchCandidate],
) -> tuple[WebSearchCandidate, ...]:
    unique: list[WebSearchCandidate] = []
    seen_urls: set[str] = set()
    for candidate in candidates:
        if candidate.url in seen_urls:
            continue
        seen_urls.add(candidate.url)
        unique.append(candidate)
    return tuple(unique)


def _normalize_document(
    candidate: WebSearchCandidate,
    result: object,
) -> CrawledWebDocument | None:
    if _failed(result):
        return None
    markdown = _markdown_text(_field(result, "markdown"))
    if markdown is None:
        return None
    title = _result_title(result) or candidate.title or candidate.url
    return CrawledWebDocument(
        url=candidate.url,
        title=title,
        markdown=markdown,
        content_hash=sha256(markdown.encode("utf-8")).hexdigest(),
        fetched_at=datetime.now(UTC),
    )


def _failed(result: object) -> bool:
    success = _field(result, "success")
    return isinstance(success, bool) and not success


def _result_title(result: object) -> str | None:
    title = _text(_field(result, "title"))
    if title is not None:
        return title
    metadata = _field(result, "metadata")
    if isinstance(metadata, Mapping):
        return _text(metadata.get("title"))
    return None


def _markdown_text(value: object) -> str | None:
    direct = _text(value)
    if direct is not None:
        return direct
    for field_name in ("fit_markdown", "raw_markdown", "markdown"):
        nested = _text(_field(value, field_name))
        if nested is not None:
            return nested
    return None


def _field(payload: object, name: str) -> object | None:
    if payload is None:
        return None
    if isinstance(payload, Mapping):
        return payload.get(name)
    return getattr(payload, name, None)


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None
