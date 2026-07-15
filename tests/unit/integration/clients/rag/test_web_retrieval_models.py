from __future__ import annotations

from datetime import UTC
from datetime import datetime

import pytest

from integration.clients.rag.web_retrieval_models import CrawledWebDocument
from integration.clients.rag.web_retrieval_models import WebSearchCandidate


def test_web_search_candidate_preserves_typed_fields() -> None:
    candidate = WebSearchCandidate(
        url="https://example.com/market",
        title="Market Update",
        snippet="Breadth improved.",
        rank=1,
        score=0.82,
        source_engine="bing",
    )

    assert candidate.url == "https://example.com/market"
    assert candidate.title == "Market Update"
    assert candidate.snippet == "Breadth improved."
    assert candidate.rank == 1
    assert candidate.score == 0.82
    assert candidate.source_engine == "bing"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"url": " "}, "url cannot be empty."),
        ({"title": " "}, "title cannot be empty."),
        ({"snippet": " "}, "snippet cannot be empty when provided."),
        ({"rank": -1}, "rank cannot be negative."),
        ({"score": -0.1}, "score cannot be negative."),
        ({"source_engine": " "}, "source_engine cannot be empty when provided."),
    ],
)
def test_web_search_candidate_rejects_invalid_fields(
    kwargs: dict[str, object],
    message: str,
) -> None:
    fields: dict[str, object] = {
        "url": "https://example.com/market",
        "title": "Market Update",
        "snippet": None,
        "rank": 0,
        "score": None,
        "source_engine": None,
    }
    fields.update(kwargs)

    with pytest.raises(ValueError, match=message):
        WebSearchCandidate(**fields)  # type: ignore[arg-type]


def test_crawled_web_document_preserves_typed_fields() -> None:
    fetched_at = datetime(2026, 7, 15, tzinfo=UTC)

    document = CrawledWebDocument(
        url="https://example.com/market",
        title="Market Update",
        markdown="# Market Update\n\nBreadth improved.",
        content_hash="abc123",
        fetched_at=fetched_at,
    )

    assert document.url == "https://example.com/market"
    assert document.title == "Market Update"
    assert document.markdown == "# Market Update\n\nBreadth improved."
    assert document.content_hash == "abc123"
    assert document.fetched_at is fetched_at


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"url": " "}, "url cannot be empty."),
        ({"title": " "}, "title cannot be empty."),
        ({"markdown": " "}, "markdown cannot be empty."),
        ({"content_hash": " "}, "content_hash cannot be empty."),
    ],
)
def test_crawled_web_document_rejects_invalid_text_fields(
    kwargs: dict[str, object],
    message: str,
) -> None:
    fields: dict[str, object] = {
        "url": "https://example.com/market",
        "title": "Market Update",
        "markdown": "# Market Update",
        "content_hash": "abc123",
        "fetched_at": datetime(2026, 7, 15, tzinfo=UTC),
    }
    fields.update(kwargs)

    with pytest.raises(ValueError, match=message):
        CrawledWebDocument(**fields)  # type: ignore[arg-type]
