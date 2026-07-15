from __future__ import annotations

from datetime import UTC
from datetime import datetime

import pytest
from pydantic import ValidationError

from mcp_server.contracts.models import RagCitation
from mcp_server.contracts.structured_outputs import StructuredMcpCustomerAgentResponse


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
    )

    assert response.query_id == "query-1"
    assert response.answer_text == structured.answer_text
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
