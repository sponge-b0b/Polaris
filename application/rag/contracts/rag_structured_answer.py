from __future__ import annotations

import ast
import json

from pydantic import BaseModel, ConfigDict, Field, field_validator

from application.rag.contracts.rag_generated_claims import RagGeneratedClaim
from domain.decision_evidence import ClaimMaterialityTier


class RagStructuredCitation(BaseModel):
    """One model-declared citation reference in a structured RAG answer."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    citation_id: str = Field(min_length=1)
    claim_summary: str = Field(min_length=1)

    @field_validator("citation_id", "claim_summary")
    @classmethod
    def _strip_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("structured RAG citation fields cannot be empty.")
        return stripped


class RagStructuredGeneratedClaim(BaseModel):
    """One typed claim generated before RAG answer presentation rendering."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    citation_ids: tuple[str, ...] = ()
    supporting_citation_ids: tuple[str, ...] = ()
    materiality: ClaimMaterialityTier = ClaimMaterialityTier.READINESS_GATING
    sanitized_context_ids: tuple[str, ...] = ()
    rejected_context_ids: tuple[str, ...] = ()

    @field_validator("claim_id", "text")
    @classmethod
    def _strip_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("structured RAG generated claim fields cannot be empty.")
        return stripped

    @field_validator(
        "citation_ids",
        "supporting_citation_ids",
        "sanitized_context_ids",
        "rejected_context_ids",
        mode="before",
    )
    @classmethod
    def _coerce_string_tuple(cls, value: object) -> tuple[str, ...]:
        return _coerce_string_tuple(value)

    def to_generated_claim(self) -> RagGeneratedClaim:
        return RagGeneratedClaim(
            claim_id=self.claim_id,
            text=self.text,
            citation_ids=self.citation_ids,
            supporting_citation_ids=self.supporting_citation_ids,
            materiality=self.materiality,
            sanitized_context_ids=self.sanitized_context_ids,
            rejected_context_ids=self.rejected_context_ids,
        )


class RagStructuredAnswerQuality(BaseModel):
    """Model-declared quality metadata for a structured RAG answer."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    confidence_score: float = Field(ge=0.0, le=1.0)
    grounding_summary: str = Field(min_length=1)
    limitations: tuple[str, ...] = ()
    refusal_reason: str | None = None

    @field_validator("grounding_summary")
    @classmethod
    def _strip_grounding_summary(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("grounding_summary cannot be empty.")
        return stripped

    @field_validator("limitations", mode="before")
    @classmethod
    def _coerce_limitations(cls, value: object) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            stripped = value.strip()
            return (stripped,) if stripped else ()
        if not isinstance(value, (list, tuple)):
            raise TypeError("limitations must be a sequence of strings.")
        limitations: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise TypeError("limitations must contain only strings.")
            stripped = item.strip()
            if stripped:
                limitations.append(stripped)
        return tuple(limitations)

    @field_validator("refusal_reason")
    @classmethod
    def _strip_refusal_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


def _coerce_string_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        stripped = value.strip()
        return (stripped,) if stripped else ()
    if not isinstance(value, (list, tuple)):
        raise TypeError("value must be a sequence of strings.")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise TypeError("value must contain only strings.")
        stripped = item.strip()
        if stripped:
            items.append(stripped)
    return tuple(dict.fromkeys(items))


def _parse_nested_structured_value(value: object, field_name: str) -> object:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return value
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(stripped)
        except (SyntaxError, ValueError):
            return value
    if not isinstance(parsed, (dict, list, tuple)):
        raise TypeError(f"{field_name} must decode to a structured value.")
    return parsed


def _coerce_citation_sequence(value: object) -> object:
    parsed = _parse_nested_structured_value(value, "citations")
    if not isinstance(parsed, (list, tuple)):
        return parsed

    citations: list[object] = []
    for item in parsed:
        if isinstance(item, tuple) and len(item) == 2:
            citation_id, claim_summary = item
            citations.append(
                {
                    "citation_id": citation_id,
                    "claim_summary": claim_summary,
                }
            )
            continue
        citations.append(item)
    return tuple(citations)


class RagStructuredAnswer(BaseModel):
    """Schema-enforced RAG answer generated by the configured LLM provider."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    answer_text: str = Field(min_length=1)
    citations: tuple[RagStructuredCitation, ...] = ()
    generated_claims: tuple[RagStructuredGeneratedClaim, ...] = ()
    quality: RagStructuredAnswerQuality

    @field_validator("citations", mode="before")
    @classmethod
    def _coerce_citations(cls, value: object) -> object:
        return _coerce_citation_sequence(value)

    @field_validator("generated_claims", mode="before")
    @classmethod
    def _coerce_generated_claims(cls, value: object) -> object:
        return _parse_nested_structured_value(value, "generated_claims")

    @field_validator("quality", mode="before")
    @classmethod
    def _coerce_quality(cls, value: object) -> object:
        return _parse_nested_structured_value(value, "quality")

    @field_validator("answer_text")
    @classmethod
    def _strip_answer_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("answer_text cannot be empty.")
        return stripped
