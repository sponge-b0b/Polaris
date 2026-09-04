from __future__ import annotations

import httpx
import pytest

from integration.clients.rag.bge_reranker_client import BgeRerankerClient


@pytest.mark.asyncio
async def test_bge_reranker_client_sends_tei_payload_and_parses_results() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json=[
                {"index": 1, "score": 0.91},
                {"index": 0, "score": 0.22},
            ],
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = BgeRerankerClient(
            endpoint="http://reranker/rerank",
            client=http_client,
        )
        results = await client.rerank(
            query="liquidity risk",
            texts=("calendar", "liquidity pressure"),
        )

    assert [(item.index, item.score) for item in results] == [
        (1, 0.91),
        (0, 0.22),
    ]
    assert requests[0].url == httpx.URL("http://reranker/rerank")
    assert requests[0].read().decode() == (
        '{"query":"liquidity risk","texts":["calendar",'
        '"liquidity pressure"],"truncate":true}'
    )


@pytest.mark.asyncio
async def test_bge_reranker_client_rejects_duplicate_candidate_indexes() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {"index": 0, "score": 0.8},
                {"index": 0, "score": 0.7},
            ],
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = BgeRerankerClient(
            endpoint="http://reranker/rerank",
            client=http_client,
        )
        with pytest.raises(ValueError, match="duplicate indexes"):
            await client.rerank(query="risk", texts=("risk evidence",))
