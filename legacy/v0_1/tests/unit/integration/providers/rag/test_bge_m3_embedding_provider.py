from __future__ import annotations

from typing import cast

import pytest

from integration.clients.rag.bge_m3_embedding_client import (
    BgeM3Embedding,
    BgeM3EmbeddingClient,
)
from integration.providers.rag.bge_m3_embedding_provider import BgeM3EmbeddingProvider
from integration.providers.rag.embedding_provider import (
    EmbeddingInput,
    EmbeddingRequest,
)


class FakeBgeM3EmbeddingClient:
    def __init__(self) -> None:
        self.text_batches: list[tuple[str, ...]] = []

    async def embed_texts(self, texts: tuple[str, ...]) -> tuple[BgeM3Embedding, ...]:
        self.text_batches.append(texts)
        return (
            BgeM3Embedding(
                dense_vector=(0.1, 0.2),
                sparse_indices=(2, 9),
                sparse_values=(0.8, 0.3),
            ),
        )


@pytest.mark.asyncio
async def test_bge_m3_provider_maps_native_output_to_platform_contract() -> None:
    client = FakeBgeM3EmbeddingClient()
    provider = BgeM3EmbeddingProvider(cast(BgeM3EmbeddingClient, client))

    vectors = await provider.embed_texts(
        EmbeddingRequest(
            model="BAAI/bge-m3",
            inputs=(
                EmbeddingInput(
                    text_id="chunk-1",
                    text="Market breadth improved.",
                    metadata={"symbol": "SPY"},
                ),
            ),
        )
    )

    assert client.text_batches == [("Market breadth improved.",)]
    assert vectors[0].dense_vector == (0.1, 0.2)
    assert vectors[0].sparse_vector.indices == (2, 9)
    assert vectors[0].sparse_vector.values == (0.8, 0.3)
    assert vectors[0].model == "BAAI/bge-m3"
    assert vectors[0].metadata["provider"] == "FlagEmbedding"
