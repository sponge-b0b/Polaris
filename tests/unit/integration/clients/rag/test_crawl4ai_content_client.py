from __future__ import annotations

import asyncio
from collections.abc import Mapping
from hashlib import sha256
from types import SimpleNamespace

import pytest

from integration.clients.rag.crawl4ai_content_client import (
    Crawl4AiContentClient,
    Crawl4AiContentClientConfig,
)
from integration.clients.rag.web_retrieval_models import WebSearchCandidate


@pytest.mark.asyncio
async def test_crawl4ai_client_returns_successful_markdown_documents() -> None:
    crawler = FakeCrawler(
        {
            "https://example.com/market": SimpleNamespace(
                success=True,
                markdown="# Market Update\n\nBreadth improved.",
                metadata={"title": "Fetched Market Update"},
            )
        }
    )
    client = Crawl4AiContentClient(crawler=crawler)

    documents = await client.crawl((_candidate("https://example.com/market"),))

    assert len(documents) == 1
    assert documents[0].url == "https://example.com/market"
    assert documents[0].title == "Fetched Market Update"
    assert documents[0].markdown == "# Market Update\n\nBreadth improved."
    assert (
        documents[0].content_hash
        == sha256(b"# Market Update\n\nBreadth improved.").hexdigest()
    )
    assert crawler.urls == ["https://example.com/market"]


@pytest.mark.asyncio
async def test_crawl4ai_client_ignores_failed_and_empty_pages() -> None:
    crawler = FakeCrawler(
        {
            "https://example.com/fail": SimpleNamespace(
                success=False,
                markdown="# Failed",
            ),
            "https://example.com/empty": SimpleNamespace(success=True, markdown=" "),
            "https://example.com/good": SimpleNamespace(
                success=True,
                markdown="# Good",
            ),
        }
    )
    client = Crawl4AiContentClient(crawler=crawler)

    documents = await client.crawl(
        (
            _candidate("https://example.com/fail"),
            _candidate("https://example.com/empty"),
            _candidate("https://example.com/good"),
        )
    )

    assert [document.url for document in documents] == ["https://example.com/good"]


@pytest.mark.asyncio
async def test_crawl4ai_client_respects_concurrency_limit() -> None:
    crawler = FakeCrawler(
        {
            f"https://example.com/{index}": SimpleNamespace(
                success=True,
                markdown=f"# Page {index}",
            )
            for index in range(5)
        },
        delay_seconds=0.01,
    )
    client = Crawl4AiContentClient(
        config=Crawl4AiContentClientConfig(max_concurrency=2),
        crawler=crawler,
    )

    documents = await client.crawl(
        tuple(_candidate(f"https://example.com/{index}") for index in range(5))
    )

    assert len(documents) == 5
    assert crawler.max_active == 2


@pytest.mark.asyncio
async def test_crawl4ai_client_uses_title_fallback_to_url() -> None:
    crawler = FakeCrawler(
        {
            "https://example.com/untitled": SimpleNamespace(
                success=True,
                markdown="# Untitled",
            )
        }
    )
    client = Crawl4AiContentClient(crawler=crawler)

    documents = await client.crawl(
        (
            WebSearchCandidate(
                url="https://example.com/untitled",
                title="https://example.com/untitled",
                snippet=None,
                rank=1,
                score=None,
                source_engine=None,
            ),
        )
    )

    assert documents[0].title == "https://example.com/untitled"


@pytest.mark.asyncio
async def test_crawl4ai_client_supports_nested_markdown_payloads() -> None:
    crawler = FakeCrawler(
        {
            "https://example.com/nested": SimpleNamespace(
                success=True,
                markdown=SimpleNamespace(fit_markdown="# Fit Markdown"),
            )
        }
    )
    client = Crawl4AiContentClient(crawler=crawler)

    documents = await client.crawl((_candidate("https://example.com/nested"),))

    assert documents[0].markdown == "# Fit Markdown"


@pytest.mark.asyncio
async def test_crawl4ai_client_deduplicates_candidate_urls() -> None:
    crawler = FakeCrawler(
        {
            "https://example.com/market": SimpleNamespace(
                success=True,
                markdown="# Market",
            )
        }
    )
    client = Crawl4AiContentClient(crawler=crawler)

    documents = await client.crawl(
        (
            _candidate("https://example.com/market"),
            _candidate("https://example.com/market"),
        )
    )

    assert len(documents) == 1
    assert crawler.urls == ["https://example.com/market"]


def test_crawl4ai_client_config_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="timeout_seconds must be positive."):
        Crawl4AiContentClientConfig(timeout_seconds=0)
    with pytest.raises(ValueError, match="max_concurrency must be at least 1."):
        Crawl4AiContentClientConfig(max_concurrency=0)
    with pytest.raises(ValueError, match="user_agent cannot be empty when provided."):
        Crawl4AiContentClientConfig(user_agent=" ")


class FakeCrawler:
    def __init__(
        self,
        responses: Mapping[str, object],
        *,
        delay_seconds: float = 0.0,
    ) -> None:
        self._responses = responses
        self._delay_seconds = delay_seconds
        self.urls: list[str] = []
        self.active = 0
        self.max_active = 0

    async def arun(self, url: str, config: object | None = None) -> object:
        del config
        self.urls.append(url)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            if self._delay_seconds:
                await asyncio.sleep(self._delay_seconds)
            return self._responses[url]
        finally:
            self.active -= 1


def _candidate(url: str) -> WebSearchCandidate:
    return WebSearchCandidate(
        url=url,
        title="Candidate title",
        snippet=None,
        rank=1,
        score=None,
        source_engine="searxng",
    )
