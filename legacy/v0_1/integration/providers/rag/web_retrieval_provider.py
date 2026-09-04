from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from application.rag.contracts.rag_context import RagRetrievedContext


@dataclass(frozen=True, slots=True)
class WebRetrievalRequest:
    request_id: str
    query: str
    top_k: int

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id cannot be empty.")
        if not self.query.strip():
            raise ValueError("query cannot be empty.")
        if self.top_k <= 0:
            raise ValueError("top_k must be positive.")


@runtime_checkable
class WebRetrievalProvider(Protocol):
    """Optional transient web retrieval provider for corrective RAG."""

    async def retrieve(
        self,
        request: WebRetrievalRequest,
    ) -> tuple[RagRetrievedContext, ...]: ...
