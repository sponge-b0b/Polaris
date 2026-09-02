from __future__ import annotations

from typing import TYPE_CHECKING

from mcp_server.contracts.models import RagAskResponse

if TYPE_CHECKING:
    from application.presentation.governed_result import GovernedPresentationProjection


def governed_projection_response_fields(
    projection: GovernedPresentationProjection,
) -> dict[str, object]:
    """Project application-owned presentation facts into the MCP response contract."""

    return {
        "authority_metadata": dict(projection.authority_metadata),
        "presentation_disposition": projection.disposition,
        "presentation_may_present": projection.may_present,
        "presentation_limitations": projection.limitations,
        "presentation_gate_failure_mode": projection.gate_failure_mode,
        "presentation_risk_tier": projection.risk_tier,
        "presentation_gate_profile": projection.gate_profile,
        "provenance_record_ids": projection.provenance_record_ids,
        "decision_evidence_packet_ids": projection.decision_evidence_packet_ids,
        "governance_approval_states": projection.governance_approval_states,
    }


__all__ = ["RagAskResponse", "governed_projection_response_fields"]
