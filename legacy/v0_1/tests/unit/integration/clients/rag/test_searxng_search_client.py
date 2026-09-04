from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from integration.clients.rag.searxng_search_client import SearxngSearchClient


@pytest.mark.asyncio
async def test_searxng_client_requests_json_search_results() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "url": "https://example.com/market",
                        "title": "Market Update",
                        "content": "Breadth improved.",
                        "score": 0.82,
                        "engine": "duckduckgo",
                    }
                ]
            },
        )

    async with _http_client(handler) as http_client:
        client = SearxngSearchClient(
            base_url="http://searxng.local",
            timeout_seconds=7.0,
            safe_search=2,
            language="en-US",
            categories="general,news",
            client=http_client,
        )

        results = await client.search(query="SPY breadth", limit=3)

    assert len(results) == 1
    assert results[0].url == "https://example.com/market"
    assert results[0].title == "Market Update"
    assert results[0].snippet == "Breadth improved."
    assert results[0].rank == 1
    assert results[0].score == 0.82
    assert results[0].source_engine == "duckduckgo"
    assert captured[0].url.path == "/search"
    assert captured[0].url.params["q"] == "SPY breadth"
    assert captured[0].url.params["format"] == "json"
    assert captured[0].url.params["language"] == "en-US"
    assert captured[0].url.params["categories"] == "general,news"
    assert captured[0].url.params["safesearch"] == "2"


@pytest.mark.asyncio
async def test_searxng_client_uses_url_and_snippet_fallbacks() -> None:
    async with _http_client(
        lambda _request: httpx.Response(
            200,
            json={
                "results": [
                    {
                        "url": "https://example.com/untitled",
                        "title": " ",
                        "snippet": "Snippet fallback.",
                        "score": "0.7",
                        "engines": ["brave", "bing"],
                    }
                ]
            },
        )
    ) as http_client:
        client = SearxngSearchClient(
            base_url="http://searxng.local",
            client=http_client,
        )

        results = await client.search(query="portfolio risk", limit=3)

    assert results[0].title == "https://example.com/untitled"
    assert results[0].snippet == "Snippet fallback."
    assert results[0].score == 0.7
    assert results[0].source_engine == "brave,bing"


@pytest.mark.asyncio
async def test_searxng_client_deduplicates_and_skips_malformed_results() -> None:
    async with _http_client(
        lambda _request: httpx.Response(
            200,
            json={
                "results": [
                    {"url": " ", "title": "missing url"},
                    {"url": "https://example.com/a", "title": "A"},
                    {"url": "https://example.com/a", "title": "A duplicate"},
                    {"url": "https://example.com/b", "title": "B"},
                ]
            },
        )
    ) as http_client:
        client = SearxngSearchClient(
            base_url="http://searxng.local",
            client=http_client,
        )

        results = await client.search(query="market", limit=10)

    assert [result.url for result in results] == [
        "https://example.com/a",
        "https://example.com/b",
    ]
    assert [result.rank for result in results] == [1, 2]


@pytest.mark.asyncio
async def test_searxng_client_returns_empty_tuple_for_empty_result_set() -> None:
    async with _http_client(
        lambda _request: httpx.Response(200, json={"results": []})
    ) as http_client:
        client = SearxngSearchClient(
            base_url="http://searxng.local",
            client=http_client,
        )

        assert await client.search(query="market", limit=3) == ()


@pytest.mark.asyncio
async def test_searxng_client_raises_for_non_successful_response() -> None:
    async with _http_client(lambda _request: httpx.Response(503)) as http_client:
        client = SearxngSearchClient(
            base_url="http://searxng.local",
            client=http_client,
        )

        with pytest.raises(httpx.HTTPStatusError):
            await client.search(query="market", limit=3)


@pytest.mark.asyncio
async def test_searxng_client_raises_for_malformed_json() -> None:
    async with _http_client(
        lambda _request: httpx.Response(200, content=b"not-json")
    ) as http_client:
        client = SearxngSearchClient(
            base_url="http://searxng.local",
            client=http_client,
        )

        with pytest.raises(ValueError, match="SearXNG returned malformed JSON."):
            await client.search(query="market", limit=3)


@pytest.mark.asyncio
async def test_searxng_client_validates_query_and_limit() -> None:
    async with _http_client(lambda _request: httpx.Response(200)) as http_client:
        client = SearxngSearchClient(
            base_url="http://searxng.local",
            client=http_client,
        )

        with pytest.raises(ValueError, match="query cannot be empty."):
            await client.search(query=" ", limit=3)
        with pytest.raises(ValueError, match="limit must be positive."):
            await client.search(query="market", limit=0)


def _http_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))
