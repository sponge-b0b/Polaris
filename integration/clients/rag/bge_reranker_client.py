from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Mapping
from typing import Protocol

import httpx


@dataclass(
    frozen=True,
    slots=True,
)
class BgeRerankItem:
    index: int
    score: float


class AsyncHttpClient(Protocol):
    async def post(
        self,
        url: str,
        *,
        json: Mapping[str, object],
    ) -> httpx.Response: ...


class BgeRerankerClient:
    """Vendor HTTP client for the Hugging Face TEI rerank endpoint."""

    def __init__(
        self,
        *,
        endpoint: str,
        client: AsyncHttpClient | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        normalized_endpoint = endpoint.strip()
        if not normalized_endpoint:
            raise ValueError("endpoint cannot be empty.")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        self._endpoint = normalized_endpoint
        self._client = client
        self._timeout_seconds = timeout_seconds

    async def rerank(
        self,
        *,
        query: str,
        texts: tuple[str, ...],
    ) -> tuple[BgeRerankItem, ...]:
        if not query.strip():
            raise ValueError("query cannot be empty.")
        if not texts:
            return ()
        request_payload = {
            "query": query,
            "texts": list(texts),
            "truncate": True,
        }
        if self._client is not None:
            response = await self._client.post(
                self._endpoint,
                json=request_payload,
            )
        else:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    self._endpoint,
                    json=request_payload,
                )
        response.raise_for_status()
        response_payload = response.json()
        if not isinstance(response_payload, list):
            raise TypeError("BGE reranker response must be a list.")
        items = tuple(
            _item_from_payload(item, candidate_count=len(texts))
            for item in response_payload
        )
        if len({item.index for item in items}) != len(items):
            raise ValueError("BGE reranker response contains duplicate indexes.")
        return items


def _item_from_payload(
    payload: Any,
    *,
    candidate_count: int,
) -> BgeRerankItem:
    if not isinstance(payload, Mapping):
        raise TypeError("BGE reranker result must be an object.")
    index = payload.get("index")
    score = payload.get("score")
    if not isinstance(index, int):
        raise TypeError("BGE reranker result index must be an integer.")
    if index < 0 or index >= candidate_count:
        raise ValueError("BGE reranker result index is outside the candidate range.")
    if not isinstance(score, int | float):
        raise TypeError("BGE reranker result score must be numeric.")
    return BgeRerankItem(
        index=index,
        score=float(score),
    )
