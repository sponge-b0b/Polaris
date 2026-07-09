from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from typing import Mapping
from typing import Protocol


@dataclass(frozen=True, slots=True)
class FirecrawlWebResult:
    url: str
    title: str
    content: str

    def __post_init__(self) -> None:
        for field_name in ("url", "title", "content"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} cannot be empty.")


class FirecrawlSdkSearchClient(Protocol):
    async def search(self, query: str, **kwargs: Any) -> object: ...


class FirecrawlWebSearchClient(Protocol):
    async def search(
        self,
        *,
        query: str,
        limit: int,
    ) -> tuple[FirecrawlWebResult, ...]: ...


class FirecrawlWebClient:
    """Vendor client for transient Firecrawl web search results."""

    def __init__(
        self,
        *,
        api_key: str | None,
        api_url: str,
        timeout_seconds: float = 30.0,
        client: FirecrawlSdkSearchClient | None = None,
    ) -> None:
        if not api_url.strip():
            raise ValueError("api_url cannot be empty.")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        if client is None:
            from firecrawl import AsyncFirecrawl

            client = AsyncFirecrawl(
                api_key=api_key,
                api_url=api_url,
                timeout=timeout_seconds,
            )
        self._client = client

    async def search(
        self,
        *,
        query: str,
        limit: int,
    ) -> tuple[FirecrawlWebResult, ...]:
        if not query.strip():
            raise ValueError("query cannot be empty.")
        if limit <= 0:
            raise ValueError("limit must be positive.")

        response = await self._client.search(
            query,
            sources=["web"],
            limit=limit,
            scrape_options={
                "formats": ["markdown"],
                "only_main_content": True,
                "remove_base64_images": True,
            },
        )
        web_results = _field(response, "web")
        if not isinstance(web_results, Sequence) or isinstance(web_results, str):
            return ()
        normalized: list[FirecrawlWebResult] = []
        for result in web_results:
            item = _normalize_result(result)
            if item is not None:
                normalized.append(item)
        return tuple(normalized[:limit])


def _normalize_result(payload: object) -> FirecrawlWebResult | None:
    metadata = _field(payload, "metadata")
    url = _text(_field(payload, "url")) or _text(_field(metadata, "url"))
    title = _text(_field(payload, "title")) or _text(_field(metadata, "title"))
    content = (
        _text(_field(payload, "markdown"))
        or _text(_field(payload, "summary"))
        or _text(_field(payload, "description"))
    )
    if url is None or content is None:
        return None
    return FirecrawlWebResult(
        url=url,
        title=title or url,
        content=content,
    )


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
