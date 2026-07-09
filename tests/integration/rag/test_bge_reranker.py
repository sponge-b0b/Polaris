from __future__ import annotations

import httpx
import pytest

from config.settings import Settings
from integration.clients.rag.bge_reranker_client import BgeRerankerClient


@pytest.mark.asyncio
async def test_live_bge_reranker_orders_relevant_text_when_available() -> None:
    settings = Settings()
    client = BgeRerankerClient(
        endpoint=settings.RAG_RERANKER_ENDPOINT,
        timeout_seconds=60.0,
    )

    try:
        results = await client.rerank(
            query="liquidity risk and market stress",
            texts=(
                "The earnings calendar lists reporting dates.",
                "Liquidity risk increased as market stress widened bid ask spreads.",
            ),
        )
    except (httpx.HTTPError, OSError) as exc:
        pytest.skip(
            f"BGE reranker is not available at {settings.RAG_RERANKER_ENDPOINT}: {exc}"
        )

    assert results
    assert results[0].index == 1
    assert results[0].score > results[-1].score
