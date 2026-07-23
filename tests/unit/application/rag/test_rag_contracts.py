from __future__ import annotations

from datetime import UTC, datetime

import pytest

from application.rag.contracts.rag_context import (
    RagRetrievalFilters,
    RagRetrievedContext,
    RagSource,
)
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult


def test_rag_request_normalizes_query_and_serializes_filters() -> None:
    request = RagRequest(
        query="  What changed   in SPY breadth?  ",
        filters=RagRetrievalFilters(
            source_tables=("rag_chunks", " ", "reports"),
            symbols=("SPY",),
            workflow_name="morning_report",
            as_of_start=datetime(2026, 6, 1, tzinfo=UTC),
            as_of_end=datetime(2026, 6, 15, tzinfo=UTC),
            metadata={"source": "unit-test"},
        ),
        route="hybrid",
        top_k=5,
        allow_web=True,
        requester="cli",
        request_id="rag_query:test",
    )

    payload = request.to_dict()
    restored = RagRequest.from_dict(
        payload,
    )

    assert request.normalized_query == "What changed in SPY breadth?"
    assert restored == request
    assert payload["filters"]["source_tables"] == ["rag_chunks", "reports"]
    assert payload["filters"]["symbols"] == ["SPY"]
    assert payload["allow_web"] is True
    assert payload["filters"]["as_of_start"] == "2026-06-01T00:00:00+00:00"


def test_rag_request_rejects_non_boolean_allow_web_payload() -> None:
    with pytest.raises(TypeError, match="allow_web must be a boolean"):
        RagRequest.from_dict(
            {
                "query": "SPY breadth",
                "allow_web": "false",
            }
        )


def test_rag_request_validates_required_fields() -> None:
    with pytest.raises(ValueError, match="query"):
        RagRequest(
            query=" ",
        )

    with pytest.raises(ValueError, match="top_k"):
        RagRequest(
            query="valid query",
            top_k=0,
        )

    with pytest.raises(ValueError, match="as_of_start"):
        RagRetrievalFilters(
            as_of_start=datetime(2026, 6, 15, tzinfo=UTC),
            as_of_end=datetime(2026, 6, 1, tzinfo=UTC),
        )


def test_retrieved_context_round_trips_with_source_lineage() -> None:
    source = _source()
    context = RagRetrievedContext(
        context_id="chunk-1",
        text="SPY breadth improved with broad participation.",
        source=source,
        score=0.91,
        rank=0,
        retrieval_route="hybrid",
        metadata={"section_name": "breadth_snapshot"},
    )

    restored = RagRetrievedContext.from_dict(
        context.to_dict(),
    )

    assert restored == context
    assert restored.source.source_table == "reports"
    assert restored.source.chunk_id == "chunk-1"
    assert restored.metadata["section_name"] == "breadth_snapshot"


def test_rag_result_builds_unique_citations_and_round_trips() -> None:
    request = RagRequest(
        query="Summarize SPY breadth.",
        request_id="rag_query:test",
    )
    source = _source()
    contexts = (
        RagRetrievedContext(
            context_id="ctx-1",
            text="Breadth improved.",
            source=source,
            score=0.9,
            rank=0,
            retrieval_route="hybrid",
        ),
        RagRetrievedContext(
            context_id="ctx-2",
            text="Breadth improved again.",
            source=source,
            score=0.8,
            rank=1,
            retrieval_route="hybrid",
        ),
    )

    result = RagResult.answered(
        request=request,
        answer_text="SPY breadth improved.",
        contexts=contexts,
        confidence_score=0.84,
    )
    restored = RagResult.from_dict(
        result.to_dict(),
    )

    assert result.query_id == request.request_id
    assert result.status == "answered"
    assert len(result.citations) == 1
    assert restored == result


def test_rag_result_failed_requires_error() -> None:
    request = RagRequest(
        query="Valid query",
        request_id="rag_query:test",
    )

    result = RagResult.failed(
        request=request,
        error="retriever unavailable",
    )

    assert result.status == "failed"
    assert result.error == "retriever unavailable"
    assert result.answer_text == "RAG request failed: retriever unavailable"

    with pytest.raises(ValueError, match="error"):
        RagResult(
            query_id="rag_query:test",
            request=request,
            answer_text="failed",
            status="failed",
            route="hybrid",
        )


def _source() -> RagSource:
    return RagSource(
        source_table="reports",
        source_id="morning_report:exec-1",
        source_type="morning_report",
        document_id="rag_document:reports:morning_report:exec-1",
        title="Morning Report",
        chunk_id="chunk-1",
        section_name="breadth_snapshot",
        generated_at=datetime(2026, 6, 15, tzinfo=UTC),
        workflow_name="morning_report",
        execution_id="exec-1",
        metadata={"symbol": "SPY"},
    )
