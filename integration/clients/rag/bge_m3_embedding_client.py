from __future__ import annotations

import asyncio

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from typing import cast

import numpy as np
from FlagEmbedding import BGEM3FlagModel


class BgeM3EncoderProtocol(Protocol):
    def encode(
        self,
        sentences: list[str],
        *,
        return_dense: bool,
        return_sparse: bool,
        return_colbert_vecs: bool,
    ) -> Mapping[str, object]: ...


@dataclass(
    frozen=True,
    slots=True,
)
class BgeM3Embedding:
    dense_vector: tuple[float, ...]
    sparse_indices: tuple[int, ...]
    sparse_values: tuple[float, ...]


class BgeM3EmbeddingClient:
    """Vendor-specific client for native BGE-M3 dense and lexical embeddings."""

    def __init__(
        self,
        *,
        model_name: str,
        encoder: BgeM3EncoderProtocol | None = None,
    ) -> None:
        if not model_name.strip():
            raise ValueError("model_name cannot be empty.")
        self._model_name = model_name
        self._encoder = encoder or cast(
            BgeM3EncoderProtocol,
            BGEM3FlagModel(
                model_name,
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=False,
            ),
        )

    async def embed_texts(
        self,
        texts: tuple[str, ...],
    ) -> tuple[BgeM3Embedding, ...]:
        if not texts:
            raise ValueError("texts cannot be empty.")
        encoded = await asyncio.to_thread(
            self._encoder.encode,
            list(texts),
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
        )
        return _embeddings_from_encoded(encoded, expected_count=len(texts))


def _embeddings_from_encoded(
    encoded: Mapping[str, object],
    *,
    expected_count: int,
) -> tuple[BgeM3Embedding, ...]:
    dense_vectors = np.asarray(encoded.get("dense_vecs"), dtype=float)
    lexical_weights = encoded.get("lexical_weights")
    if dense_vectors.ndim != 2 or len(dense_vectors) != expected_count:
        raise ValueError("BGE-M3 returned an invalid dense vector batch.")
    if not isinstance(lexical_weights, list) or len(lexical_weights) != expected_count:
        raise ValueError("BGE-M3 returned an invalid sparse vector batch.")

    embeddings: list[BgeM3Embedding] = []
    for dense_vector, sparse_weights in zip(
        dense_vectors,
        lexical_weights,
        strict=True,
    ):
        if not isinstance(sparse_weights, Mapping):
            raise TypeError("BGE-M3 sparse vector must be a token-weight mapping.")
        sparse_items = sorted(
            (int(token_id), float(weight))
            for token_id, weight in sparse_weights.items()
            if float(weight) != 0.0
        )
        if not sparse_items:
            raise ValueError("BGE-M3 returned an empty sparse vector.")
        embeddings.append(
            BgeM3Embedding(
                dense_vector=tuple(float(value) for value in dense_vector),
                sparse_indices=tuple(index for index, _ in sparse_items),
                sparse_values=tuple(value for _, value in sparse_items),
            )
        )
    return tuple(embeddings)
