from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from core.storage.persistence.rag import (
    RagAnswerLogRecord,
    RagChunkRecord,
    RagDocumentRecord,
    RagEmbeddingJobRecord,
    RagGraphJobRecord,
    RagPersistenceBundle,
    RagPersistenceResult,
    RagQueryLogRecord,
    RagQueryModelExecutionRecord,
    RagQueryReflectionScores,
    RagRecordPersistenceResult,
    new_rag_answer_log_id,
    new_rag_chunk_id,
    new_rag_document_id,
    new_rag_embedding_job_id,
    new_rag_graph_job_id,
    new_rag_query_log_id,
)


def test_rag_document_record_is_typed_and_immutable() -> None:
    record = _document()

    assert record.source_table == "reports"
    assert record.content_text == "# Full curated report"

    with pytest.raises(FrozenInstanceError):
        record.title = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        ("document_id", {"document_id": " "}),
        ("source_table", {"source_table": ""}),
        ("source_id", {"source_id": " "}),
        ("source_type", {"source_type": ""}),
        ("title", {"title": " "}),
        ("content_text", {"content_text": ""}),
    ],
)
def test_rag_document_record_validates_required_fields(
    field_name: str,
    kwargs: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "document_id": "rag_document:reports:morning_report:report-1",
        "source_table": "reports",
        "source_id": "report-1",
        "source_type": "morning_report",
        "title": "Morning Report",
        "content_text": "Full curated text",
        "generated_at": datetime(2026, 5, 30, tzinfo=UTC),
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        RagDocumentRecord(**values)  # type: ignore[arg-type]


def test_rag_chunk_and_embedding_job_records_validate_state() -> None:
    chunk = _chunk()
    job = _job()

    assert chunk.chunk_index == 0
    assert job.status == "queued"

    with pytest.raises(ValueError, match="chunk_index"):
        RagChunkRecord(
            chunk_id="chunk-1",
            document_id="doc-1",
            chunk_index=-1,
            chunk_text="text",
        )

    with pytest.raises(ValueError, match="attempts"):
        RagEmbeddingJobRecord(
            job_id="job-1",
            document_id="doc-1",
            target_store="qdrant",
            embedding_model="bge-large",
            status="queued",
            queued_at=datetime(2026, 5, 30, tzinfo=UTC),
            attempts=-1,
        )


def test_rag_persistence_bundle_and_result_validate_state() -> None:
    bundle = RagPersistenceBundle(
        document=_document(),
        chunks=(_chunk(),),
        embedding_jobs=(_job(),),
    )
    success = RagPersistenceResult.succeeded(
        document_id=bundle.document.document_id,
        records_persisted=3,
    )
    failure = RagPersistenceResult.failed("database unavailable")

    assert success.success is True
    assert success.records_persisted == 3
    assert failure.success is False

    with pytest.raises(ValueError, match="document_id"):
        RagPersistenceResult(success=True)

    with pytest.raises(ValueError, match="error"):
        RagPersistenceResult.failed(" ")


def test_rag_id_helpers_are_stable_for_curated_sources() -> None:
    document_id = new_rag_document_id(
        source_table="reports",
        source_id="report-1",
        source_type="morning_report",
    )
    chunk_id = new_rag_chunk_id(
        document_id=document_id,
        chunk_index=0,
    )
    job_id = new_rag_embedding_job_id(
        document_id=document_id,
        chunk_id=chunk_id,
        target_store="qdrant",
        embedding_model="bge-large",
    )

    assert document_id == "rag_document:reports:morning_report:report-1"
    assert chunk_id == "rag_document:reports:morning_report:report-1:chunk:0"
    assert job_id == f"rag_embedding_job:qdrant:bge-large:{chunk_id}"


def _document() -> RagDocumentRecord:
    return RagDocumentRecord(
        document_id="rag_document:reports:morning_report:report-1",
        source_table="reports",
        source_id="report-1",
        source_type="morning_report",
        title="Morning Report",
        content_text="# Full curated report",
        content_hash="hash-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        generated_at=datetime(2026, 5, 30, tzinfo=UTC),
        metadata={"audience": "human"},
    )


def _chunk() -> RagChunkRecord:
    return RagChunkRecord(
        chunk_id="rag_document:reports:morning_report:report-1:chunk:0",
        document_id="rag_document:reports:morning_report:report-1",
        chunk_index=0,
        chunk_text="# Full curated report",
        token_count=4,
        metadata={"section": "summary"},
    )


def _job() -> RagEmbeddingJobRecord:
    return RagEmbeddingJobRecord(
        job_id="job-1",
        document_id="rag_document:reports:morning_report:report-1",
        chunk_id="rag_document:reports:morning_report:report-1:chunk:0",
        target_store="qdrant",
        embedding_model="bge-large",
        status="queued",
        queued_at=datetime(2026, 5, 30, tzinfo=UTC),
    )


def test_rag_graph_query_and_answer_records_validate_state() -> None:
    graph_job = _graph_job()
    query_log = _query_log()
    answer_log = _answer_log()

    assert graph_job.graph_model == "neo4j-v1"
    assert query_log.top_k == 5
    assert answer_log.confidence_score == 0.82

    with pytest.raises(ValueError, match="top_k"):
        RagQueryLogRecord(
            query_id="query-1",
            query_text="What changed?",
            retrieval_route="hybrid",
            top_k=0,
            status="started",
            started_at=datetime(2026, 5, 30, tzinfo=UTC),
        )

    with pytest.raises(ValueError, match="duration_ms"):
        RagQueryLogRecord(
            query_id="query-1",
            query_text="What changed?",
            retrieval_route="hybrid",
            top_k=5,
            status="failed",
            started_at=datetime(2026, 5, 30, tzinfo=UTC),
            duration_ms=-1.0,
        )

    with pytest.raises(ValueError, match="confidence_score"):
        RagAnswerLogRecord(
            answer_id="answer-1",
            query_id="query-1",
            answer_text="Answer",
            status="completed",
            completed_at=datetime(2026, 5, 30, tzinfo=UTC),
            confidence_score=1.01,
        )


def test_rag_query_log_validates_first_class_audit_fields() -> None:
    with pytest.raises(ValueError, match="context_count"):
        RagQueryLogRecord(
            query_id="query-1",
            query_text="What changed?",
            retrieval_route="hybrid",
            top_k=5,
            status="completed",
            started_at=datetime(2026, 5, 30, tzinfo=UTC),
            context_count=-1,
        )

    with pytest.raises(ValueError, match="grounding_score"):
        RagQueryLogRecord(
            query_id="query-1",
            query_text="What changed?",
            retrieval_route="hybrid",
            top_k=5,
            status="completed",
            started_at=datetime(2026, 5, 30, tzinfo=UTC),
            grounding_score=1.01,
        )

    with pytest.raises(ValueError, match="model_executions"):
        RagQueryLogRecord(
            query_id="query-1",
            query_text="What changed?",
            retrieval_route="hybrid",
            top_k=5,
            status="completed",
            started_at=datetime(2026, 5, 30, tzinfo=UTC),
            model_executions=tuple(
                RagQueryModelExecutionRecord(
                    operation="route",
                    configured_model="qwen3.5:4b",
                    provider_name="ollama",
                    duration_ms=1.0,
                    success=True,
                )
                for _ in range(33)
            ),
        )


def test_rag_record_persistence_result_validates_state() -> None:
    success = RagRecordPersistenceResult.succeeded(
        record_id="query-1",
    )
    failure = RagRecordPersistenceResult.failed("database unavailable")

    assert success.success is True
    assert success.records_persisted == 1
    assert failure.success is False

    with pytest.raises(ValueError, match="record_id"):
        RagRecordPersistenceResult(success=True)

    with pytest.raises(ValueError, match="error"):
        RagRecordPersistenceResult.failed(" ")


def test_rag_log_and_graph_id_helpers_create_namespaced_ids() -> None:
    graph_job_id = new_rag_graph_job_id(
        document_id="doc-1",
        chunk_id="chunk-1",
        target_store="neo4j",
        graph_model="neo4j-v1",
    )
    query_id = new_rag_query_log_id()
    answer_id = new_rag_answer_log_id(
        query_id=query_id,
    )

    assert graph_job_id == "rag_graph_job:neo4j:neo4j-v1:chunk-1"
    assert query_id.startswith("rag_query_log:")
    assert answer_id.startswith(f"rag_answer_log:{query_id}:")


def _graph_job() -> RagGraphJobRecord:
    return RagGraphJobRecord(
        job_id="graph-job-1",
        document_id="rag_document:reports:morning_report:report-1",
        chunk_id="rag_document:reports:morning_report:report-1:chunk:0",
        target_store="neo4j",
        graph_model="neo4j-v1",
        status="queued",
        queued_at=datetime(2026, 5, 30, tzinfo=UTC),
        metadata={"projection": "entities"},
    )


def _query_log() -> RagQueryLogRecord:
    return RagQueryLogRecord(
        query_id="query-1",
        query_text="What does the morning report say about risk?",
        normalized_query="morning report risk",
        requester="cli",
        workflow_name="morning_report",
        execution_id="exec-1",
        retrieval_route="hybrid",
        top_k=5,
        filters={"source_type": "morning_report"},
        model_executions=(
            RagQueryModelExecutionRecord(
                operation="adaptive_triage",
                configured_model="qwen2.5:7b",
                provider_name="ollama",
                duration_ms=14.25,
                success=True,
            ),
        ),
        context_count=3,
        citation_count=2,
        grounding_score=0.73,
        utility_score=0.81,
        injection_detected=False,
        reflection_scores=RagQueryReflectionScores(
            retrieval_necessity=0.9,
            source_relevance=0.8,
            answer_support=0.73,
            usefulness=0.81,
        ),
        corrective_actions=("rewrite", "proceed"),
        status="completed",
        started_at=datetime(2026, 5, 30, tzinfo=UTC),
        completed_at=datetime(2026, 5, 30, 0, 0, 1, tzinfo=UTC),
        duration_ms=12.5,
        metadata={"trace_id": "trace-1"},
    )


def _answer_log() -> RagAnswerLogRecord:
    return RagAnswerLogRecord(
        answer_id="answer-1",
        query_id="query-1",
        answer_text="Risk is elevated but manageable.",
        answer_hash="answer-hash-1",
        generation_model="gpt-test",
        status="completed",
        confidence_score=0.82,
        source_count=2,
        citations={"items": ["chunk-1"]},
        sources={"chunks": ["chunk-1", "chunk-2"]},
        completed_at=datetime(2026, 5, 30, tzinfo=UTC),
        metadata={"trace_id": "trace-1"},
    )
