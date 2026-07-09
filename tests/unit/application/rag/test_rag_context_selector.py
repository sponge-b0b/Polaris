from __future__ import annotations

import pytest

from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_context import RagSource
from application.rag.retrieval.rag_context_selector import RagContextSelector
from application.rag.contracts.rag_request import RagRequest
from integration.providers.rag.reranking_provider import RerankRequest
from integration.providers.rag.reranking_provider import RerankResult


@pytest.mark.asyncio
async def test_context_selector_preserves_fallback_order_and_top_k() -> None:
    selector = RagContextSelector(reranking_provider=None, rerank_multiplier=3)
    contexts = (_context("a", 0.9), _context("b", 0.8), _context("c", 0.7))

    selected = await selector.select(
        request=RagRequest(query="risk", top_k=2),
        contexts=contexts,
    )

    assert [context.context_id for context in selected] == ["a", "b"]
    assert [context.rank for context in selected] == [1, 2]


@pytest.mark.asyncio
async def test_context_selector_preserves_reranker_scores_and_metadata() -> None:
    provider = FakeRerankingProvider()
    selector = RagContextSelector(reranking_provider=provider, rerank_multiplier=3)
    contexts = (_context("a", 0.9), _context("b", 0.8))

    selected = await selector.select(
        request=RagRequest(query="liquidity risk", top_k=1),
        contexts=contexts,
    )

    assert [context.context_id for context in selected] == ["b"]
    assert selected[0].score == 0.95
    assert selected[0].rank == 1
    assert selected[0].metadata == {
        "retrieval_score": 0.8,
        "rerank_score": 0.95,
    }
    assert provider.requests[0].query == "liquidity risk"


class FakeRerankingProvider:
    def __init__(self) -> None:
        self.requests: list[RerankRequest] = []

    async def rerank(
        self,
        request: RerankRequest,
    ) -> tuple[RerankResult, ...]:
        self.requests.append(request)
        return (RerankResult(candidate_id="b", score=0.95, rank=1),)


def _context(context_id: str, score: float) -> RagRetrievedContext:
    return RagRetrievedContext(
        context_id=context_id,
        text=f"Context {context_id}",
        source=RagSource(
            source_table="reports",
            source_id=context_id,
            source_type="report",
            document_id=f"document-{context_id}",
            title=f"Report {context_id}",
        ),
        score=score,
        rank=0,
        retrieval_route="hybrid",
    )
