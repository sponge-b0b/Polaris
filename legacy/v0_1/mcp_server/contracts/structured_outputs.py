from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from pydantic import ValidationInfo, field_validator, model_validator

from domain.llm import sanitize_reasoning_trace_text_for_boundary
from mcp_server.contracts.models import (
    McpBoundaryModel,
    NonEmptyString,
    RagAskResponse,
    RagCitation,
    Score,
)


class StructuredMcpCustomerAgentResponse(McpBoundaryModel):
    """Instructor target schema for externally safe customer-agent responses."""

    answer_text: NonEmptyString
    status: NonEmptyString = "succeeded"
    route: NonEmptyString = "customer_agent"
    confidence_score: Score | None = None
    grounding_score: Score | None = None
    utility_score: Score | None = None
    citations: tuple[RagCitation, ...] = ()
    safety_notes: tuple[NonEmptyString, ...] = ()
    refusal_reason: NonEmptyString | None = None
    corrective_actions: tuple[NonEmptyString, ...] = ()

    @field_validator("answer_text", "status", "route", "refusal_reason", mode="before")
    @classmethod
    def sanitize_public_text(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if value is None:
            return None
        return sanitize_reasoning_trace_text_for_boundary(
            str(
                value,
            ),
            boundary_name=f"mcp.customer_agent.{info.field_name}",
        )

    @field_validator("safety_notes", "corrective_actions", mode="before")
    @classmethod
    def sanitize_public_text_items(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if value is None:
            return ()

        items: tuple[object, ...]
        if isinstance(value, str):
            items = (value,)
        elif isinstance(value, Sequence) and not isinstance(
            value,
            bytes | bytearray,
        ):
            items = tuple(value)
        else:
            items = (value,)

        return tuple(
            sanitize_reasoning_trace_text_for_boundary(
                str(
                    item,
                ),
                boundary_name=f"mcp.customer_agent.{info.field_name}[]",
            )
            for item in items
        )

    @model_validator(mode="after")
    def validate_refusal_status(self) -> StructuredMcpCustomerAgentResponse:
        if self.status == "refused" and self.refusal_reason is None:
            raise ValueError("refusal_reason is required when status is refused.")
        return self

    def to_rag_ask_response(
        self,
        *,
        query_id: str,
        generated_at: datetime,
        include_contexts: bool = False,
    ) -> RagAskResponse:
        """Map the structured payload into the external MCP RAG response contract."""

        actions = (*self.safety_notes, *self.corrective_actions)
        return RagAskResponse(
            query_id=query_id,
            answer_text=self.answer_text,
            status=self.status,
            route=self.route,
            citations=self.citations,
            contexts=() if include_contexts else None,
            confidence_score=self.confidence_score,
            grounding_score=self.grounding_score,
            utility_score=self.utility_score,
            injection_detected=self.status == "refused",
            corrective_actions=actions,
            error=self.refusal_reason,
            generated_at=generated_at,
        )
