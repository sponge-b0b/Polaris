from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from application.presentation.governed_result import GovernedPresentationProjection
from mcp_server.contracts.models import RagCitation
from mcp_server.contracts.structured_outputs import StructuredMcpCustomerAgentResponse


def _projection(
    *,
    disposition: str = "eligible",
    may_present: bool = True,
) -> GovernedPresentationProjection:
    return GovernedPresentationProjection(
        disposition=disposition,
        may_present=may_present,
        authority_metadata={
            "intended_sink": "mcp_tool_response",
            "risk_tier": "enhanced",
        },
        gate_failure_mode="none",
        risk_tier="enhanced",
        gate_profile="enhanced_provenance",
        limitations=("Educational decision-support only.",),
        provenance_record_ids=("provenance-1",),
        decision_evidence_packet_ids=("packet-1",),
        governance_approval_states=("not_required",),
    )


def test_mcp_customer_agent_structured_response_maps_to_rag_response() -> None:
    citation = RagCitation(
        source_table="curated_rag_documents",
        source_id="doc-1",
        source_type="morning_report",
        document_id="rag-doc-1",
        title="Morning Report",
        chunk_id="chunk-1",
    )
    structured = StructuredMcpCustomerAgentResponse(
        answer_text="Risk is elevated but still manageable with smaller sizing.",
        status="succeeded",
        route="customer_agent",
        confidence_score=0.82,
        grounding_score=0.91,
        utility_score=0.86,
        citations=(citation,),
        safety_notes=("Educational decision-support only.",),
    )

    response = structured.to_rag_ask_response(
        query_id="query-1",
        generated_at=datetime(2026, 7, 15, tzinfo=UTC),
        projection=_projection(),
    )

    assert response.query_id == "query-1"
    assert response.answer_text == structured.answer_text
    assert response.presentation_disposition == "eligible"
    assert response.presentation_may_present is True
    assert response.presentation_gate_profile == "enhanced_provenance"
    assert response.provenance_record_ids == ("provenance-1",)
    assert response.citations == (citation,)
    assert response.contexts is None
    assert response.corrective_actions == ("Educational decision-support only.",)
    assert response.injection_detected is False


def test_mcp_customer_agent_refusal_requires_reason() -> None:
    with pytest.raises(ValidationError, match="refusal_reason"):
        StructuredMcpCustomerAgentResponse(
            answer_text="I cannot comply with that request.",
            status="refused",
        )


def test_mcp_customer_agent_structured_response_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs"):
        StructuredMcpCustomerAgentResponse.model_validate(
            {
                "answer_text": "Safe response.",
                "unreviewed_payload": {"raw": "data"},
            }
        )


def test_mcp_customer_agent_response_strips_reasoning_before_mapping() -> None:
    structured = StructuredMcpCustomerAgentResponse(
        answer_text="<think>private deliberation</think>\nUse smaller sizing.",
        safety_notes=(
            (
                "```reasoning\nhidden safety trace\n```\n"
                "Educational decision-support only."
            ),
        ),
        corrective_actions=(
            "Chain of thought: private action analysis.\n"
            "Final answer: Cite curated evidence.",
        ),
    )

    response = structured.to_rag_ask_response(
        query_id="query-safe",
        generated_at=datetime(2026, 7, 15, tzinfo=UTC),
        projection=_projection(),
    )

    assert structured.answer_text == "Use smaller sizing."
    assert response.answer_text == "Use smaller sizing."
    assert response.corrective_actions == (
        "Educational decision-support only.",
        "Cite curated evidence.",
    )
    assert "private deliberation" not in response.model_dump_json()
    assert "hidden safety trace" not in response.model_dump_json()
    assert "private action analysis" not in response.model_dump_json()


def test_mcp_customer_agent_response_rejects_unsafe_reasoning_trace() -> None:
    with pytest.raises(ValidationError, match="mcp.customer_agent.answer_text"):
        StructuredMcpCustomerAgentResponse(
            answer_text="<think>private deliberation without a closing tag",
        )


def test_mcp_customer_agent_mapper_rejects_non_presentable_claim_payload() -> None:
    structured = StructuredMcpCustomerAgentResponse(
        answer_text="Risk is elevated but manageable.",
        status="succeeded",
        confidence_score=0.82,
    )

    with pytest.raises(ValidationError, match="successful claim-bearing status"):
        structured.to_rag_ask_response(
            query_id="query-blocked",
            generated_at=datetime(2026, 7, 15, tzinfo=UTC),
            projection=_projection(disposition="blocked", may_present=False),
        )
