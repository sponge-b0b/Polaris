from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import StrEnum
from typing import Protocol
from typing import runtime_checkable

from core.storage.persistence.rag import JsonObject


class RagQualityModelOperation(StrEnum):
    CRAG_GRADE = "crag_grade"
    CRAG_QUERY_REWRITE = "crag_query_rewrite"
    SELF_REFLECTION = "self_reflection"


@dataclass(frozen=True, slots=True)
class RagQualityModelConfig:
    crag_grader_model: str
    crag_query_rewrite_model: str
    self_reflection_model: str

    def __post_init__(self) -> None:
        for field_name in (
            "crag_grader_model",
            "crag_query_rewrite_model",
            "self_reflection_model",
        ):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} cannot be empty.")

    def model_for(self, operation: RagQualityModelOperation) -> str:
        match operation:
            case RagQualityModelOperation.CRAG_GRADE:
                return self.crag_grader_model
            case RagQualityModelOperation.CRAG_QUERY_REWRITE:
                return self.crag_query_rewrite_model
            case RagQualityModelOperation.SELF_REFLECTION:
                return self.self_reflection_model


@dataclass(frozen=True, slots=True)
class RagQualityModelRequest:
    request_id: str
    operation: RagQualityModelOperation
    system_prompt: str
    user_prompt: str
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("request_id", "system_prompt", "user_prompt"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} cannot be empty.")


@dataclass(frozen=True, slots=True)
class RagQualityModelResult:
    operation: RagQualityModelOperation
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
class RagQualityModelProvider(Protocol):
    async def generate_structured(
        self,
        request: RagQualityModelRequest,
    ) -> RagQualityModelResult: ...
