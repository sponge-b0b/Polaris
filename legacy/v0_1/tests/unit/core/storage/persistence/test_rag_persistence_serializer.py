from __future__ import annotations

from datetime import UTC, datetime

from core.database.models.rag import (
    RagAnswerLogModel,
    RagChunkModel,
    RagDocumentModel,
    RagEmbeddingJobModel,
    RagGraphJobModel,
    RagQueryLogModel,
    RagSourceEligibilityModel,
)
from core.storage.persistence.rag import (
    RagAnswerLogRecord,
    RagChunkRecord,
    RagDocumentRecord,
    RagEmbeddingJobRecord,
    RagGraphJobRecord,
    RagQueryLogRecord,
    RagQueryModelExecutionRecord,
    RagQueryReflectionScores,
    RagSourceEligibilityRecord,
)
from core.storage.persistence.serializers.rag_persistence_serializer import (
    RagPersistenceSerializer,
)


def test_rag_serializer_preserves_full_document_text_and_lineage() -> None:
    full_text = "# Morning Report\n" + ("Full curated analysis. " * 200)
    document = _document(
        content_text=full_text,
    )

    values = RagPersistenceSerializer.document_values(
        document,
    )

    assert values["source_table"] == "reports"
    assert values["source_id"] == "report-1"
    assert values["source_type"] == "morning_report"
    assert values["content_text"] == full_text
    assert values["metadata_payload"] == {"audience": "human"}


def test_rag_serializer_converts_chunk_and_embedding_job_records() -> None:
    chunk = _chunk()
    job = _job()

    chunk_values = RagPersistenceSerializer.chunk_values(chunk)
    job_values = RagPersistenceSerializer.embedding_job_values(job)

    assert chunk_values["chunk_text"] == "# Full curated report"
    assert chunk_values["metadata_payload"] == {"section": "summary"}
    assert job_values["target_store"] == "qdrant"
    assert job_values["status"] == "queued"


def test_rag_serializer_round_trips_models_to_records() -> None:
    document = _document()
    chunk = _chunk()
    job = _job()

    document_model = RagDocumentModel(
        **RagPersistenceSerializer.document_values(document),
    )
    chunk_model = RagChunkModel(
        **RagPersistenceSerializer.chunk_values(chunk),
    )
    job_model = RagEmbeddingJobModel(
        **RagPersistenceSerializer.embedding_job_values(job),
    )

    round_tripped_document = RagPersistenceSerializer.document_from_model(
        document_model,
    )
    round_tripped_chunk = RagPersistenceSerializer.chunk_from_model(
        chunk_model,
    )
    round_tripped_job = RagPersistenceSerializer.embedding_job_from_model(
        job_model,
    )

    assert round_tripped_document.content_text == document.content_text
    assert round_tripped_document.metadata == {"audience": "human"}
    assert round_tripped_chunk.chunk_text == chunk.chunk_text
    assert round_tripped_job.embedding_model == "bge-large"


def test_rag_serializer_converts_source_eligibility_metadata_only_records() -> None:
    eligibility = _eligibility()

    values = RagPersistenceSerializer.source_eligibility_values(
        eligibility,
    )
    model = RagSourceEligibilityModel(**values)
    round_tripped = RagPersistenceSerializer.source_eligibility_from_model(
        model,
    )

    assert values["source_table"] == "reports"
    assert values["source_id"] == "report-1"
    assert values["source_type"] == "morning_report"
    assert values["eligible"] is True
    assert values["quality_score"] == 0.91
    assert values["metadata_payload"] == {"reviewer": "default_rules"}
    assert "document_id" not in values
    assert "chunk_id" not in values
    assert "job_id" not in values
    assert round_tripped == eligibility


def _document(
    *,
    content_text: str = "# Full curated report",
) -> RagDocumentRecord:
    return RagDocumentRecord(
        document_id="rag_document:reports:morning_report:report-1",
        source_table="reports",
        source_id="report-1",
        source_type="morning_report",
        title="Morning Report",
        content_text=content_text,
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


def _eligibility() -> RagSourceEligibilityRecord:
    return RagSourceEligibilityRecord(
        eligibility_id="rag_source_eligibility:reports:morning_report:report-1",
        source_table="reports",
        source_id="report-1",
        source_type="morning_report",
        eligible=True,
        reason="Curated report is suitable for future RAG source building.",
        quality_score=0.91,
        reviewed_timestamp=datetime(2026, 5, 30, tzinfo=UTC),
        metadata={"reviewer": "default_rules"},
    )


def test_rag_serializer_converts_graph_query_and_answer_records() -> None:
    graph_job = _graph_job()
    query_log = _query_log()
    answer_log = _answer_log()

    graph_values = RagPersistenceSerializer.graph_job_values(graph_job)
    query_values = RagPersistenceSerializer.query_log_values(query_log)
    answer_values = RagPersistenceSerializer.answer_log_values(answer_log)

    assert graph_values["target_store"] == "neo4j"
    assert graph_values["graph_model"] == "neo4j-v1"
    assert query_values["filters_payload"] == {"source_type": "morning_report"}
    assert query_values["model_executions_payload"] == [
        {
            "operation": "adaptive_triage",
            "configured_model": "qwen2.5:7b",
            "provider_name": "ollama",
            "duration_ms": 14.25,
            "success": True,
        }
    ]
    assert query_values["context_count"] == 3
    assert query_values["citation_count"] == 2
    assert query_values["grounding_score"] == 0.73
    assert query_values["utility_score"] == 0.81
    assert query_values["injection_detected"] is False
    assert query_values["reflection_scores_payload"] == {
        "retrieval_necessity": 0.9,
        "source_relevance": 0.8,
        "answer_support": 0.73,
        "usefulness": 0.81,
    }
    assert query_values["corrective_actions_payload"] == ["rewrite", "proceed"]
    assert query_values["metadata_payload"] == {"trace_id": "trace-1"}
    assert answer_values["citations_payload"] == {"items": ["chunk-1"]}
    assert answer_values["sources_payload"] == {"chunks": ["chunk-1", "chunk-2"]}


def test_rag_serializer_round_trips_graph_query_and_answer_models() -> None:
    graph_job = _graph_job()
    query_log = _query_log()
    answer_log = _answer_log()

    graph_model = RagGraphJobModel(
        **RagPersistenceSerializer.graph_job_values(graph_job),
    )
    query_model = RagQueryLogModel(
        **RagPersistenceSerializer.query_log_values(query_log),
    )
    answer_model = RagAnswerLogModel(
        **RagPersistenceSerializer.answer_log_values(answer_log),
    )

    assert RagPersistenceSerializer.graph_job_from_model(graph_model) == graph_job
    assert RagPersistenceSerializer.query_log_from_model(query_model) == query_log
    assert RagPersistenceSerializer.answer_log_from_model(answer_model) == answer_log


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
