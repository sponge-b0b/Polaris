from __future__ import annotations

from pydantic import ValidationInfo, field_validator

from mcp_server.contracts.models import (
    NonEmptyString,
    _sanitize_mcp_text_sequence,
    _sanitize_optional_mcp_text,
)
from mcp_server.contracts.models import (
    RagAskResponse as BaseRagAskResponse,
)


class RagAskResponse(BaseRagAskResponse):
    """RAG response extended with the application-owned presentation projection."""

    presentation_gate_failure_mode: NonEmptyString | None = None
    presentation_risk_tier: NonEmptyString | None = None
    presentation_gate_profile: NonEmptyString | None = None
    provenance_record_ids: tuple[NonEmptyString, ...] = ()
    decision_evidence_packet_ids: tuple[NonEmptyString, ...] = ()
    governance_approval_states: tuple[NonEmptyString, ...] = ()

    @field_validator(
        "presentation_gate_failure_mode",
        "presentation_risk_tier",
        "presentation_gate_profile",
        mode="before",
    )
    @classmethod
    def sanitize_presentation_gate_text(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        return _sanitize_optional_mcp_text(
            value,
            boundary_name=f"mcp.rag_response.{info.field_name}",
        )

    @field_validator(
        "provenance_record_ids",
        "decision_evidence_packet_ids",
        "governance_approval_states",
        mode="before",
    )
    @classmethod
    def sanitize_presentation_references(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        return _sanitize_mcp_text_sequence(
            value,
            boundary_name=f"mcp.rag_response.{info.field_name}",
        )


__all__ = ["RagAskResponse"]
