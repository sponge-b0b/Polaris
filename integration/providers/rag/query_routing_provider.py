from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import StrEnum
from typing import Protocol
from typing import runtime_checkable

from core.storage.persistence.rag import JsonObject


class RagQueryModelOperation(StrEnum):
    REWRITE = "rewrite"
    ADAPTIVE_TRIAGE = "adaptive_triage"
    ROUTE_SELECTION = "route_selection"
    HYDE = "hyde"


@dataclass(
    frozen=True,
    slots=True,
)
class RagQueryModelConfig:
    query_rewrite_model: str
    adaptive_triage_model: str
    route_selection_model: str
    hyde_model: str
    structured_max_tokens: int = 512
    hyde_max_tokens: int = 768

    def __post_init__(self) -> None:
        for field_name in (
            "query_rewrite_model",
            "adaptive_triage_model",
            "route_selection_model",
            "hyde_model",
        ):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} cannot be empty.")
        for field_name in ("structured_max_tokens", "hyde_max_tokens"):
            if getattr(self, field_name) <= 0:
                raise ValueError(f"{field_name} must be greater than 0.")

    def model_for(self, operation: RagQueryModelOperation) -> str:
        match operation:
            case RagQueryModelOperation.REWRITE:
                return self.query_rewrite_model
            case RagQueryModelOperation.ADAPTIVE_TRIAGE:
                return self.adaptive_triage_model
            case RagQueryModelOperation.ROUTE_SELECTION:
                return self.route_selection_model
            case RagQueryModelOperation.HYDE:
                return self.hyde_model

    def max_tokens_for(self, operation: RagQueryModelOperation) -> int:
        if operation is RagQueryModelOperation.HYDE:
            return self.hyde_max_tokens
        return self.structured_max_tokens


@dataclass(
    frozen=True,
    slots=True,
)
class RagQueryModelRequest:
    request_id: str
    operation: RagQueryModelOperation
    system_prompt: str
    user_prompt: str
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("request_id", "system_prompt", "user_prompt"):
            value = getattr(self, field_name)
            if not value.strip():
                raise ValueError(f"{field_name} cannot be empty.")


@dataclass(
    frozen=True,
    slots=True,
)
class RagQueryModelResult:
    operation: RagQueryModelOperation
    payload: JsonObject
    model: str
    provider_name: str
    duration_ms: float
    success: bool

    def __post_init__(self) -> None:
        for field_name in ("model", "provider_name"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} cannot be empty.")
        if self.duration_ms < 0.0:
            raise ValueError("duration_ms cannot be negative.")


@runtime_checkable
class RagQueryModelProvider(Protocol):
    async def generate_structured(
        self,
        request: RagQueryModelRequest,
    ) -> RagQueryModelResult: ...
