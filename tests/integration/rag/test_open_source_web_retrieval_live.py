from __future__ import annotations

import os

import pytest

from config.settings import Settings
from integration.clients.rag.crawl4ai_content_client import Crawl4AiContentClient
from integration.clients.rag.crawl4ai_content_client import Crawl4AiContentClientConfig
from integration.clients.rag.searxng_search_client import SearxngSearchClient
from integration.clients.rag.web_retrieval_models import WebSearchCandidate
from integration.providers.rag.open_source_web_retrieval_provider import (
    OpenSourceWebRetrievalProvider,
)
from integration.providers.rag.web_retrieval_provider import WebRetrievalRequest

LIVE_TEST_ENV = "CRAWL4AI_LIVE_TEST"

pytestmark = pytest.mark.skipif(
    os.environ.get(LIVE_TEST_ENV, "").strip().lower() not in {"1", "true", "yes"},
    reason=f"set {LIVE_TEST_ENV}=true to run live SearXNG + Crawl4AI tests",
)


def _settings() -> Settings:
    return Settings(
        RAG_WEB_FALLBACK_ENABLED=True,
        CRAWL4AI_TIMEOUT_SECONDS=15.0,
        CRAWL4AI_CACHE_ENABLED=False,
        CRAWL4AI_MAX_CONCURRENCY=2,
    )


def _crawl_client(settings: Settings) -> Crawl4AiContentClient:
    return Crawl4AiContentClient(
        config=Crawl4AiContentClientConfig(
            timeout_seconds=settings.CRAWL4AI_TIMEOUT_SECONDS,
            headless=settings.CRAWL4AI_HEADLESS,
            cache_enabled=settings.CRAWL4AI_CACHE_ENABLED,
            max_concurrency=settings.CRAWL4AI_MAX_CONCURRENCY,
            user_agent=settings.CRAWL4AI_USER_AGENT,
        )
    )


@pytest.mark.asyncio
async def test_live_searxng_returns_candidate_urls() -> None:
    settings = _settings()
    client = SearxngSearchClient(
        base_url=settings.SEARXNG_BASE_URL,
        timeout_seconds=5.0,
        safe_search=settings.SEARXNG_SAFE_SEARCH,
        language=settings.SEARXNG_LANGUAGE,
        categories=settings.SEARXNG_CATEGORIES,
    )

    candidates = await client.search(
        query="example domain",
        limit=3,
    )

    assert candidates
    assert all(
        candidate.url.startswith(("http://", "https://")) for candidate in candidates
    )
    assert candidates[0].rank == 1


@pytest.mark.asyncio
async def test_live_crawl4ai_extracts_markdown_from_known_page() -> None:
    settings = _settings()
    client = _crawl_client(settings)
    documents = await client.crawl(
        (
            WebSearchCandidate(
                url="https://example.com",
                title="Example Domain",
                snippet="Known stable example page.",
                rank=1,
                score=1.0,
                source_engine="integration-test",
            ),
        )
    )

    assert documents
    document = documents[0]
    assert document.url == "https://example.com"
    assert "Example Domain" in document.markdown
    assert document.content_hash


@pytest.mark.asyncio
async def test_live_open_source_provider_returns_sanitized_transient_context() -> None:
    settings = _settings()
    provider = OpenSourceWebRetrievalProvider(
        search_client=SearxngSearchClient(
            base_url=settings.SEARXNG_BASE_URL,
            timeout_seconds=5.0,
            safe_search=settings.SEARXNG_SAFE_SEARCH,
            language=settings.SEARXNG_LANGUAGE,
            categories=settings.SEARXNG_CATEGORIES,
        ),
        content_client=_crawl_client(settings),
    )

    contexts = await provider.retrieve(
        WebRetrievalRequest(
            request_id="rag_live_web_fallback_test",
            query="example domain",
            top_k=1,
        )
    )

    assert contexts
    context = contexts[0]
    assert context.text.strip()
    assert context.retrieval_route == "web_fallback"
    assert context.source.source_table == "external_web"
    assert context.source.source_type == "web_fallback"
    assert context.metadata["provider"] == "searxng+crawl4ai"
    assert context.metadata["search_provider"] == "searxng"
    assert context.metadata["crawl_provider"] == "crawl4ai"
    assert context.metadata["transient"] is True
    assert context.metadata["untrusted"] is True
    assert "security_signals" in context.metadata
