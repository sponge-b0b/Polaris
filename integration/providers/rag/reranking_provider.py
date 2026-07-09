from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from typing import runtime_checkable


@dataclass(
    frozen=True,
    slots=True,
)
class RerankCandidate:
    candidate_id: str
    text: str

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(self.candidate_id, "candidate_id")
        _require_non_empty(self.text, "text")


@dataclass(
    frozen=True,
    slots=True,
)
class RerankRequest:
    query: str
    candidates: tuple[RerankCandidate, ...]
    top_k: int

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(self.query, "query")
        if not self.candidates:
            raise ValueError("candidates cannot be empty.")
        if self.top_k <= 0:
            raise ValueError("top_k must be positive.")


@dataclass(
    frozen=True,
    slots=True,
)
class RerankResult:
    candidate_id: str
    score: float
    rank: int

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(self.candidate_id, "candidate_id")
        if self.rank <= 0:
            raise ValueError("rank must be positive.")


@runtime_checkable
class RerankingProvider(Protocol):
    """Canonical async provider contract for cross-encoder reranking."""

    async def rerank(
        self,
        request: RerankRequest,
    ) -> tuple[RerankResult, ...]: ...


def _require_non_empty(
    value: str,
    field_name: str,
) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
