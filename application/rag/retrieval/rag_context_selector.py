from __future__ import annotations

from dataclasses import replace
from typing import cast

from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_request import RagRequest
from core.storage.persistence.rag import JsonObject
from integration.providers.rag.reranking_provider import (
    RerankCandidate,
    RerankingProvider,
    RerankRequest,
)


class RagContextSelector:
    """Rerank and select the final bounded retrieval context."""

    def __init__(
        self,
        *,
        reranking_provider: RerankingProvider | None,
        rerank_multiplier: int,
    ) -> None:
        self._reranking_provider = reranking_provider
        self._rerank_multiplier = rerank_multiplier

    @property
    def reranker_enabled(self) -> bool:
        return self._reranking_provider is not None

    async def select(
        self,
        *,
        request: RagRequest,
        contexts: tuple[RagRetrievedContext, ...],
    ) -> tuple[RagRetrievedContext, ...]:
        candidates = contexts[: request.top_k * self._rerank_multiplier]
        if not candidates:
            return ()
        if self._reranking_provider is None:
            return tuple(
                replace(context, rank=rank)
                for rank, context in enumerate(candidates[: request.top_k], start=1)
            )
        results = await self._reranking_provider.rerank(
            RerankRequest(
                query=request.normalized_query,
                candidates=tuple(
                    RerankCandidate(candidate_id=context.context_id, text=context.text)
                    for context in candidates
                ),
                top_k=request.top_k,
            )
        )
        context_by_id = {context.context_id: context for context in candidates}
        return tuple(
            replace(
                context_by_id[result.candidate_id],
                score=result.score,
                rank=result.rank,
                metadata=cast(
                    JsonObject,
                    {
                        **dict(context_by_id[result.candidate_id].metadata),
                        "retrieval_score": context_by_id[result.candidate_id].score,
                        "rerank_score": result.score,
                    },
                ),
            )
            for result in results
            if result.candidate_id in context_by_id
        )
