from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import StrEnum

from core.storage.persistence.rag import JsonObject


class RagConversationRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class RagQueryComplexity(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class RagRetrievalRoute(StrEnum):
    DIRECT_ANSWER = "direct_answer"
    RETRIEVAL = "retrieval"
    DEEP_RESEARCH = "deep_research"


@dataclass(
    frozen=True,
    slots=True,
)
class RagQueryModelExecution:
    operation: str
    configured_model: str
    provider_name: str
    duration_ms: float
    success: bool

    def __post_init__(self) -> None:
        for field_name in ("operation", "configured_model", "provider_name"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} cannot be empty.")
        if self.duration_ms < 0.0:
            raise ValueError("duration_ms cannot be negative.")

    def to_dict(self) -> JsonObject:
        return {
            "operation": self.operation,
            "configured_model": self.configured_model,
            "provider_name": self.provider_name,
            "duration_ms": self.duration_ms,
            "success": self.success,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class RagConversationTurn:
    role: RagConversationRole
    content: str

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("content cannot be empty.")


@dataclass(
    frozen=True,
    slots=True,
)
class RagConversationMemory:
    turns: tuple[RagConversationTurn, ...] = field(default_factory=tuple)

    @property
    def is_empty(self) -> bool:
        return not self.turns


@dataclass(
    frozen=True,
    slots=True,
)
class RagQueryContext:
    request_id: str
    query: str
    memory: RagConversationMemory = field(default_factory=RagConversationMemory)

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id cannot be empty.")
        if not self.query.strip():
            raise ValueError("query cannot be empty.")


@dataclass(
    frozen=True,
    slots=True,
)
class RagStandaloneQueryRewrite:
    original_query: str
    standalone_query: str
    rewritten: bool

    def __post_init__(self) -> None:
        if not self.original_query.strip():
            raise ValueError("original_query cannot be empty.")
        if not self.standalone_query.strip():
            raise ValueError("standalone_query cannot be empty.")


@dataclass(
    frozen=True,
    slots=True,
)
class RagAdaptiveTriage:
    complexity: RagQueryComplexity


@dataclass(
    frozen=True,
    slots=True,
)
class RagRouteSelection:
    route: RagRetrievalRoute


@dataclass(
    frozen=True,
    slots=True,
)
class RagHydeExpansion:
    query: str
    hypothetical_document: str

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("query cannot be empty.")
        if not self.hypothetical_document.strip():
            raise ValueError("hypothetical_document cannot be empty.")


@dataclass(
    frozen=True,
    slots=True,
)
class RagQueryRoutingDecision:
    context: RagQueryContext
    rewrite: RagStandaloneQueryRewrite
    triage: RagAdaptiveTriage
    route_selection: RagRouteSelection
    model_executions: tuple[RagQueryModelExecution, ...]
    hyde: RagHydeExpansion | None = None

    def __post_init__(self) -> None:
        requires_hyde = self.route_selection.route is RagRetrievalRoute.DEEP_RESEARCH
        if requires_hyde != (self.hyde is not None):
            raise ValueError("HyDE expansion must be present only for deep research.")
        if not self.model_executions:
            raise ValueError("model_executions cannot be empty.")

    def persistence_metadata(self) -> JsonObject:
        return {
            "model_executions": [
                execution.to_dict() for execution in self.model_executions
            ]
        }
