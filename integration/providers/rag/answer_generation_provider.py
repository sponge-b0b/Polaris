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
class RagAnswerGenerationRequest:
    """
    Provider-bound request for generating a RAG answer from isolated context.

    Retrieved context remains a separate payload so provider implementations can
    keep untrusted source text out of system/developer instructions.
    """

    request_id: str
    query: str
    policy_instructions: str
    user_prompt: str
    context_payload: str
    citation_ids: tuple[str, ...]
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "request_id",
            "query",
            "policy_instructions",
            "user_prompt",
            "context_payload",
        ):
            _require_non_empty(
                getattr(
                    self,
                    field_name,
                ),
                field_name,
            )
        if not self.citation_ids:
            raise ValueError("citation_ids cannot be empty.")


@dataclass(
    frozen=True,
    slots=True,
)
class RagAnswerGenerationResult:
    """
    Provider-bound response from a RAG answer model.
    """

    answer_text: str
    model: str | None = None
    provider_name: str | None = None
    confidence_score: float | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.answer_text,
            "answer_text",
        )
        if (
            self.confidence_score is not None
            and not 0.0 <= self.confidence_score <= 1.0
        ):
            raise ValueError("confidence_score must be between 0.0 and 1.0.")


@runtime_checkable
class RagAnswerGenerationProvider(Protocol):
    """
    Canonical async provider interface for RAG answer generation.
    """

    async def generate_answer(
        self,
        request: RagAnswerGenerationRequest,
    ) -> RagAnswerGenerationResult: ...


def _require_non_empty(
    value: str | None,
    field_name: str,
) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
