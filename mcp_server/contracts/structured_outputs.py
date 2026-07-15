from __future__ import annotations

from datetime import datetime

from pydantic import model_validator

from mcp_server.contracts.models import McpBoundaryModel
from mcp_server.contracts.models import NonEmptyString
from mcp_server.contracts.models import RagAskResponse
from mcp_server.contracts.models import RagCitation
from mcp_server.contracts.models import Score


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
