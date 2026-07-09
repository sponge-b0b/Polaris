from __future__ import annotations

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.clients.rag.bge_m3_embedding_client import BgeM3EmbeddingClient
from integration.providers.provider_telemetry import record_provider_call
from integration.providers.rag.embedding_provider import EmbeddingRequest
from integration.providers.rag.embedding_provider import EmbeddingVector
from integration.providers.rag.embedding_provider import SparseEmbeddingVector


class BgeM3EmbeddingProvider:
    """Platform-facing provider for native BGE-M3 dense and sparse embeddings."""

    def __init__(
        self,
        client: BgeM3EmbeddingClient,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:
        self._client = client
        self._telemetry = telemetry

    async def embed_texts(
        self,
        request: EmbeddingRequest,
    ) -> tuple[EmbeddingVector, ...]:
        return await record_provider_call(
            self._telemetry,
            self.__class__.__name__,
            "embed_texts",
            lambda: self._embed_texts(request),
            attributes={"model": request.model, "input_count": len(request.inputs)},
        )

    async def _embed_texts(
        self,
        request: EmbeddingRequest,
    ) -> tuple[EmbeddingVector, ...]:
        embeddings = await self._client.embed_texts(
            tuple(item.text for item in request.inputs)
        )
        if len(embeddings) != len(request.inputs):
            raise ValueError("BGE-M3 embedding count does not match input count.")
        return tuple(
            EmbeddingVector(
                text_id=item.text_id,
                dense_vector=embedding.dense_vector,
                sparse_vector=SparseEmbeddingVector(
                    indices=embedding.sparse_indices,
                    values=embedding.sparse_values,
                ),
                model=request.model,
                metadata={
                    "provider": "FlagEmbedding",
                    "input_metadata": dict(item.metadata),
                },
            )
            for item, embedding in zip(request.inputs, embeddings, strict=True)
        )
