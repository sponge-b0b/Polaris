from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Protocol
from typing import runtime_checkable

from core.storage.persistence.rag import JsonObject


@dataclass(
    frozen=True,
    slots=True,
)
class EmbeddingInput:
    text_id: str
    text: str
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.text_id,
            "text_id",
        )
        _require_non_empty(
            self.text,
            "text",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class EmbeddingRequest:
    inputs: tuple[EmbeddingInput, ...]
    model: str

    def __post_init__(
        self,
    ) -> None:
        if not self.inputs:
            raise ValueError("inputs cannot be empty.")
        _require_non_empty(
            self.model,
            "model",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SparseEmbeddingVector:
    indices: tuple[int, ...]
    values: tuple[float, ...]

    def __post_init__(
        self,
    ) -> None:
        if not self.indices:
            raise ValueError("sparse indices cannot be empty.")
        if len(self.indices) != len(self.values):
            raise ValueError("sparse indices and values must have equal length.")
        if any(index < 0 for index in self.indices):
            raise ValueError("sparse indices cannot be negative.")
        if tuple(sorted(set(self.indices))) != self.indices:
            raise ValueError("sparse indices must be unique and sorted.")


@dataclass(
    frozen=True,
    slots=True,
)
class EmbeddingVector:
    text_id: str
    dense_vector: tuple[float, ...]
    sparse_vector: SparseEmbeddingVector
    model: str
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.text_id,
            "text_id",
        )
        _require_non_empty(
            self.model,
            "model",
        )
        if not self.dense_vector:
            raise ValueError("dense_vector cannot be empty.")

    @property
    def dimensions(
        self,
    ) -> int:
        return len(
            self.dense_vector,
        )


@runtime_checkable
class EmbeddingProvider(Protocol):
    """
    Canonical provider interface for text embeddings.
    """

    async def embed_texts(
        self,
        request: EmbeddingRequest,
    ) -> tuple[EmbeddingVector, ...]: ...


def _require_non_empty(
    value: str | None,
    field_name: str,
) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
