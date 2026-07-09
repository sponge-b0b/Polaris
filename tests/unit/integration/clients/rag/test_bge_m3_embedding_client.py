from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pytest

from integration.clients.rag.bge_m3_embedding_client import BgeM3EmbeddingClient


class FakeBgeM3Encoder:
    def __init__(self, result: Mapping[str, object]) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def encode(
        self,
        sentences: list[str],
        *,
        return_dense: bool,
        return_sparse: bool,
        return_colbert_vecs: bool,
    ) -> Mapping[str, object]:
        self.calls.append(
            {
                "sentences": sentences,
                "return_dense": return_dense,
                "return_sparse": return_sparse,
                "return_colbert_vecs": return_colbert_vecs,
            }
        )
        return self.result


@pytest.mark.asyncio
async def test_bge_m3_client_returns_dense_and_learned_sparse_vectors() -> None:
    encoder = FakeBgeM3Encoder(
        {
            "dense_vecs": np.array([[0.1, 0.2], [0.3, 0.4]]),
            "lexical_weights": [{"9": 0.3, "2": 0.8}, {"4": 0.6}],
        }
    )
    client = BgeM3EmbeddingClient(model_name="BAAI/bge-m3", encoder=encoder)

    embeddings = await client.embed_texts(("first", "second"))

    assert embeddings[0].dense_vector == pytest.approx((0.1, 0.2))
    assert embeddings[0].sparse_indices == (2, 9)
    assert embeddings[0].sparse_values == pytest.approx((0.8, 0.3))
    assert embeddings[1].sparse_indices == (4,)
    assert encoder.calls == [
        {
            "sentences": ["first", "second"],
            "return_dense": True,
            "return_sparse": True,
            "return_colbert_vecs": False,
        }
    ]


@pytest.mark.asyncio
async def test_bge_m3_client_rejects_missing_learned_sparse_output() -> None:
    client = BgeM3EmbeddingClient(
        model_name="BAAI/bge-m3",
        encoder=FakeBgeM3Encoder(
            {"dense_vecs": np.array([[0.1, 0.2]]), "lexical_weights": []}
        ),
    )

    with pytest.raises(ValueError, match="invalid sparse vector batch"):
        await client.embed_texts(("text",))
