from __future__ import annotations

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.clients.rag.bge_reranker_client import BgeRerankerClient
from integration.providers.provider_telemetry import record_provider_call
from integration.providers.rag.reranking_provider import (
    RerankingProvider,
    RerankRequest,
    RerankResult,
)


class BgeRerankingProvider(RerankingProvider):
    """Platform-facing reranker backed by the BGE TEI service."""

    def __init__(
        self,
        client: BgeRerankerClient,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:
        self._client = client
        self._telemetry = telemetry

    async def rerank(
        self,
        request: RerankRequest,
    ) -> tuple[RerankResult, ...]:
        items = await record_provider_call(
            self._telemetry,
            self.__class__.__name__,
            "rerank",
            lambda: self._client.rerank(
                query=request.query,
                texts=tuple(candidate.text for candidate in request.candidates),
            ),
        )
        results = tuple(
            RerankResult(
                candidate_id=request.candidates[item.index].candidate_id,
                score=item.score,
                rank=rank,
            )
            for rank, item in enumerate(
                sorted(items, key=lambda item: (-item.score, item.index)),
                start=1,
            )
        )
        return results[: request.top_k]
