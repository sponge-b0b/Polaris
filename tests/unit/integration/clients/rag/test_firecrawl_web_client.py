from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from integration.clients.rag.firecrawl_web_client import FirecrawlWebClient


class FakeFirecrawlSdkClient:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def search(self, query: str, **kwargs: Any) -> object:
        self.calls.append((query, kwargs))
        return self.response


@pytest.mark.asyncio
async def test_firecrawl_client_uses_official_async_search_contract() -> None:
    sdk = FakeFirecrawlSdkClient(
        SimpleNamespace(
            web=[
                SimpleNamespace(
                    url="https://example.com/market",
                    title="Market Update",
                    markdown="Breadth improved.",
                )
            ]
        )
    )
    client = FirecrawlWebClient(
        api_key="test-key",
        api_url="https://firecrawl.test",
        client=sdk,
    )

    results = await client.search(query="SPY breadth", limit=3)

    assert results[0].url == "https://example.com/market"
    assert results[0].content == "Breadth improved."
    assert sdk.calls == [
        (
            "SPY breadth",
            {
                "sources": ["web"],
                "limit": 3,
                "scrape_options": {
                    "formats": ["markdown"],
                    "only_main_content": True,
                    "remove_base64_images": True,
                },
            },
        )
    ]


@pytest.mark.asyncio
async def test_firecrawl_client_normalizes_mapping_and_document_metadata() -> None:
    sdk = FakeFirecrawlSdkClient(
        {
            "web": [
                {
                    "metadata": {
                        "url": "https://example.com/document",
                        "title": "Document Result",
                    },
                    "summary": "Document summary.",
                },
                {"url": "https://example.com/missing-content"},
            ]
        }
    )
    client = FirecrawlWebClient(
        api_key=None,
        api_url="http://localhost:3002",
        client=sdk,
    )

    results = await client.search(query="market context", limit=2)

    assert len(results) == 1
    assert results[0].title == "Document Result"
    assert results[0].content == "Document summary."
