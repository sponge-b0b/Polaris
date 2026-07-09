from __future__ import annotations

from typing import cast

import pytest

from integration.clients.rag.bge_reranker_client import BgeRerankItem
from integration.clients.rag.bge_reranker_client import BgeRerankerClient
from integration.providers.rag.bge_reranking_provider import BgeRerankingProvider
from integration.providers.rag.reranking_provider import RerankCandidate
from integration.providers.rag.reranking_provider import RerankRequest


@pytest.mark.asyncio
async def test_bge_reranking_provider_returns_deterministic_platform_order() -> None:
    client = FakeBgeRerankerClient(
        items=(
            BgeRerankItem(index=2, score=0.4),
            BgeRerankItem(index=1, score=0.9),
            BgeRerankItem(index=0, score=0.9),
        )
    )
    provider = BgeRerankingProvider(cast(BgeRerankerClient, client))

    results = await provider.rerank(
        RerankRequest(
            query="market risk",
            candidates=(
                RerankCandidate("a", "market risk"),
                RerankCandidate("b", "risk outlook"),
                RerankCandidate("c", "earnings calendar"),
            ),
            top_k=2,
        )
    )

    assert [(result.candidate_id, result.score, result.rank) for result in results] == [
        ("a", 0.9, 1),
        ("b", 0.9, 2),
    ]
    assert client.calls == [
        ("market risk", ("market risk", "risk outlook", "earnings calendar"))
    ]


class FakeBgeRerankerClient:
    def __init__(self, *, items: tuple[BgeRerankItem, ...]) -> None:
        self.items = items
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    async def rerank(
        self,
        *,
        query: str,
        texts: tuple[str, ...],
    ) -> tuple[BgeRerankItem, ...]:
        self.calls.append((query, texts))
        return self.items
