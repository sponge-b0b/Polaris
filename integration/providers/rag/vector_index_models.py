from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from core.storage.persistence.rag import JsonObject
from core.storage.persistence.rag import RagChunkRecord
from integration.providers.rag.embedding_provider import SparseEmbeddingVector


@dataclass(
    frozen=True,
    slots=True,
)
class VectorIndexPoint:
    """
    Provider-facing vector projection point for a persisted RAG chunk.
    """

    point_id: str
    dense_vector: tuple[float, ...]
    sparse_vector: SparseEmbeddingVector
    payload: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.point_id,
            "point_id",
        )
        if not self.dense_vector:
            raise ValueError("dense_vector cannot be empty.")

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "point_id": self.point_id,
            "dense_vector": list(self.dense_vector),
            "sparse_vector": {
                "indices": list(self.sparse_vector.indices),
                "values": list(self.sparse_vector.values),
            },
            "payload": deepcopy(
                dict(self.payload),
            ),
        }


@dataclass(
    frozen=True,
    slots=True,
)
class VectorSearchQuery:
    """
    Provider-facing vector search query.
    """

    dense_vector: tuple[float, ...]
    sparse_vector: SparseEmbeddingVector
    top_k: int
    filters: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        if not self.dense_vector:
            raise ValueError("dense_vector cannot be empty.")
        if self.top_k <= 0:
            raise ValueError("top_k must be positive.")


@dataclass(
    frozen=True,
    slots=True,
)
class VectorSearchResult:
    """
    Provider-facing vector search result.
    """

    point_id: str
    score: float
    payload: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.point_id,
            "point_id",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class VectorCollectionReadiness:
    """Non-mutating provider view of vector projection readiness."""

    collection_name: str
    exists: bool
    status: str | None
    healthy: bool
    dense_vector_present: bool
    sparse_vector_present: bool
    configured_vector_size: int
    actual_vector_size: int | None
    vector_size_compatible: bool
    points_count: int = 0

    def __post_init__(self) -> None:
        _require_non_empty(self.collection_name, "collection_name")
        if self.configured_vector_size <= 0:
            raise ValueError("configured_vector_size must be positive.")
        if self.actual_vector_size is not None and self.actual_vector_size <= 0:
            raise ValueError("actual_vector_size must be positive when present.")
        if self.points_count < 0:
            raise ValueError("points_count cannot be negative.")


@dataclass(
    frozen=True,
    slots=True,
)
class VectorCollectionStatus:
    """Provider-facing health state for a vector projection collection."""

    collection_name: str
    vector_size: int
    status: str
    healthy: bool
    points_count: int = 0
    created: bool = False

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.collection_name,
            "collection_name",
        )
        _require_non_empty(
            self.status,
            "status",
        )
        if self.vector_size <= 0:
            raise ValueError("vector_size must be positive.")
        if self.points_count < 0:
            raise ValueError("points_count cannot be negative.")


def vector_point_from_chunk(
    chunk: RagChunkRecord,
    *,
    dense_vector: tuple[float, ...],
    sparse_vector: SparseEmbeddingVector,
) -> VectorIndexPoint:
    payload = {
        **dict(chunk.metadata),
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "chunk_index": chunk.chunk_index,
        "chunk_text": chunk.chunk_text,
        "token_count": chunk.token_count,
        "content_hash": chunk.content_hash,
    }
    return VectorIndexPoint(
        point_id=chunk.chunk_id,
        dense_vector=dense_vector,
        sparse_vector=sparse_vector,
        payload=payload,
    )


def _require_non_empty(
    value: str | None,
    field_name: str,
) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
