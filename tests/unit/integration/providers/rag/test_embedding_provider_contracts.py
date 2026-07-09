from __future__ import annotations

import pytest
from collections.abc import Callable

from integration.providers.rag.embedding_provider import EmbeddingInput
from integration.providers.rag.embedding_provider import EmbeddingRequest
from integration.providers.rag.embedding_provider import EmbeddingVector
from integration.providers.rag.embedding_provider import SparseEmbeddingVector


def test_embedding_contracts_validate_and_expose_dimensions() -> None:
    request = EmbeddingRequest(
        inputs=(
            EmbeddingInput(
                text_id="chunk-1",
                text="SPY breadth improved.",
                metadata={"symbol": "SPY"},
            ),
        ),
        model="bge-m3",
    )
    vector = EmbeddingVector(
        text_id="chunk-1",
        dense_vector=(0.1, 0.2, 0.3),
        sparse_vector=SparseEmbeddingVector(indices=(1, 4), values=(0.7, 0.2)),
        model=request.model,
    )

    assert request.inputs[0].text_id == "chunk-1"
    assert vector.dimensions == 3


@pytest.mark.parametrize(
    "record",
    [
        lambda: EmbeddingInput(text_id=" ", text="valid"),
        lambda: EmbeddingInput(text_id="chunk-1", text=" "),
        lambda: EmbeddingRequest(inputs=(), model="bge-m3"),
        lambda: EmbeddingRequest(
            inputs=(EmbeddingInput(text_id="chunk-1", text="valid"),), model=" "
        ),
        lambda: EmbeddingVector(
            text_id="chunk-1",
            dense_vector=(),
            sparse_vector=SparseEmbeddingVector(indices=(1,), values=(1.0,)),
            model="bge-m3",
        ),
    ],
)
def test_embedding_contracts_reject_invalid_records(
    record: Callable[[], object],
) -> None:
    with pytest.raises(ValueError):
        record()
