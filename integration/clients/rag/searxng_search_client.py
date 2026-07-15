from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from typing import Any

import httpx

from integration.clients.rag.web_retrieval_models import WebSearchCandidate


class SearxngSearchClient:
    """Vendor client for SearXNG search discovery."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 15.0,
        safe_search: int = 1,
        language: str = "en",
        categories: str = "general",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("base_url cannot be empty.")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        if safe_search < 0:
            raise ValueError("safe_search cannot be negative.")
        if not language.strip():
            raise ValueError("language cannot be empty.")
        if not categories.strip():
            raise ValueError("categories cannot be empty.")
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._safe_search = safe_search
        self._language = language
        self._categories = categories
        self._client = client

    async def search(
        self,
        *,
        query: str,
        limit: int,
    ) -> tuple[WebSearchCandidate, ...]:
        if not query.strip():
            raise ValueError("query cannot be empty.")
        if limit <= 0:
            raise ValueError("limit must be positive.")

        if self._client is not None:
            return await self._search_with_client(
                query=query, limit=limit, client=self._client
            )

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as owned_client:
            return await self._search_with_client(
                query=query,
                limit=limit,
                client=owned_client,
            )

    async def _search_with_client(
        self,
        *,
        query: str,
        limit: int,
        client: httpx.AsyncClient,
    ) -> tuple[WebSearchCandidate, ...]:
        response = await client.get(
            f"{self._base_url}/search",
            params={
                "q": query,
                "format": "json",
                "language": self._language,
                "categories": self._categories,
                "safesearch": self._safe_search,
            },
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        payload = _json(response)
        results = payload.get("results")
        if not isinstance(results, Sequence) or isinstance(results, str):
            return ()

        candidates: list[WebSearchCandidate] = []
        seen_urls: set[str] = set()
        for result in results:
            if not isinstance(result, Mapping):
                continue
            candidate = _normalize_candidate(result, rank=len(candidates) + 1)
            if candidate is None or candidate.url in seen_urls:
                continue
            seen_urls.add(candidate.url)
            candidates.append(candidate)
            if len(candidates) >= limit:
                break
        return tuple(candidates)


def _json(response: httpx.Response) -> Mapping[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError("SearXNG returned malformed JSON.") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("SearXNG search response must be a JSON object.")
    return payload


def _normalize_candidate(
    result: Mapping[object, object],
    *,
    rank: int,
) -> WebSearchCandidate | None:
    url = _text(result.get("url"))
    if url is None:
        return None
    title = _text(result.get("title")) or url
    snippet = _text(result.get("content")) or _text(result.get("snippet"))
    return WebSearchCandidate(
        url=url,
        title=title,
        snippet=snippet,
        rank=rank,
        score=_score(result.get("score")),
        source_engine=_source_engine(result),
    )


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _score(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        normalized = float(value)
    elif isinstance(value, str):
        try:
            normalized = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    if normalized < 0:
        return None
    return normalized


def _source_engine(result: Mapping[object, object]) -> str | None:
    engine = _text(result.get("engine"))
    if engine is not None:
        return engine
    engines = result.get("engines")
    if not isinstance(engines, Sequence) or isinstance(engines, str):
        return None
    names = [_text(engine_name) for engine_name in engines]
    normalized = ",".join(name for name in names if name is not None)
    return normalized or None
