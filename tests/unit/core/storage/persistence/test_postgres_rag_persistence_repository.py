from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

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
from core.storage.persistence.repositories.postgres_rag_persistence_repository import (
    PostgresRagPersistenceRepository,
)
from core.storage.persistence.serializers.rag_persistence_serializer import (
    RagPersistenceSerializer,
)


class FakeScalarResult:
    def __init__(self, rows: Sequence[object]) -> None:
        self._rows = list(rows)

    def all(self) -> list[object]:
        return self._rows


class FakeExecuteResult:
    def __init__(
        self,
        rows: Sequence[object] | None = None,
        *,
        rowcount: int = 0,
    ) -> None:
        self._rows = list(rows or [])
        self.rowcount = rowcount

    def scalar_one_or_none(self) -> object | None:
        if not self._rows:
            return None
        return self._rows[0]

    def scalar_one(self) -> object:
        if not self._rows:
            raise ValueError("No scalar row available.")
        return self._rows[0]

    def scalars(self) -> FakeScalarResult:
        return FakeScalarResult(self._rows)


class FakeAsyncSession:
    def __init__(
        self,
        result: FakeExecuteResult | None = None,
        error: SQLAlchemyError | None = None,
        fail_on_execute_call: int | None = None,
    ) -> None:
        self.result = result or FakeExecuteResult()
        self.error = error
        self.fail_on_execute_call = fail_on_execute_call
        self.executed: list[Any] = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, statement: Any) -> FakeExecuteResult:
        self.executed.append(statement)
        if self.error is not None and (
            self.fail_on_execute_call is None
            or len(self.executed) == self.fail_on_execute_call
        ):
            raise self.error
        return self.result

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_persist_document_bundle_uses_idempotent_upserts() -> None:
    session = FakeAsyncSession()
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    result = await repository.persist_document(
        _document(),
        chunks=(_chunk(),),
        embedding_jobs=(_job(),),
    )

    compiled = [
        str(statement.compile(dialect=postgresql.dialect()))
        for statement in session.executed
    ]

    assert result.success is True
    assert result.records_persisted == 3
    assert session.commits == 1
    assert len(session.executed) == 3
    assert all("ON CONFLICT" in statement for statement in compiled)
    assert "document_id" in compiled[0]
    assert "chunk_id" in compiled[1]
    assert "job_id" in compiled[2]


@pytest.mark.asyncio
async def test_persist_document_bundle_rolls_back_on_sqlalchemy_error() -> None:
    session = FakeAsyncSession(
        error=SQLAlchemyError("chunk write failed"),
        fail_on_execute_call=2,
    )
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    result = await repository.persist_document(
        _document(),
        chunks=(_chunk(),),
        embedding_jobs=(_job(),),
    )

    assert result.success is False
    assert result.error == "chunk write failed"
    assert len(session.executed) == 2
    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_get_canonical_record_counts_queries_all_rag_record_types() -> None:
    class CountSession(FakeAsyncSession):
        async def execute(self, statement: Any) -> FakeExecuteResult:
            self.executed.append(statement)
            return FakeExecuteResult([len(self.executed)])

    session = CountSession()
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    counts = await repository.get_canonical_record_counts()

    assert counts.document_count == 1
    assert counts.chunk_count == 2
    assert counts.embedding_job_count == 3
    assert counts.graph_job_count == 4
    assert len(session.executed) == 4


@pytest.mark.asyncio
async def test_get_document_round_trips_model_to_record() -> None:
    model = RagDocumentModel(**RagPersistenceSerializer.document_values(_document()))
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    record = await repository.get_document(
        "rag_document:reports:morning_report:report-1"
    )

    assert record is not None
    assert record.source_table == "reports"
    assert record.content_text == "# Full curated report"


@pytest.mark.asyncio
async def test_list_chunks_returns_typed_records() -> None:
    model = RagChunkModel(**RagPersistenceSerializer.chunk_values(_chunk()))
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    records = await repository.list_chunks(
        "rag_document:reports:morning_report:report-1"
    )

    assert len(records) == 1
    assert records[0].chunk_index == 0
    assert records[0].chunk_text == "# Full curated report"


@pytest.mark.asyncio
async def test_get_chunk_round_trips_model_to_record() -> None:
    model = RagChunkModel(**RagPersistenceSerializer.chunk_values(_chunk()))
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    record = await repository.get_chunk(
        "rag_document:reports:morning_report:report-1:chunk:0"
    )

    assert record is not None
    assert record.chunk_id == "rag_document:reports:morning_report:report-1:chunk:0"
    assert record.chunk_text == "# Full curated report"


@pytest.mark.asyncio
async def test_list_chunks_by_metadata_filters_jsonb_payload() -> None:
    model = RagChunkModel(**RagPersistenceSerializer.chunk_values(_chunk()))
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    records = await repository.list_chunks_by_metadata(
        metadata_filters={
            "source_type": "morning_report",
            "symbol": "SPY",
        },
        limit=25,
    )

    compiled = str(session.executed[0].compile(dialect=postgresql.dialect()))

    assert len(records) == 1
    assert records[0].chunk_id == "rag_document:reports:morning_report:report-1:chunk:0"
    assert "rag_chunks" in compiled
    assert "->>" in compiled
    assert "ORDER BY" in compiled
    assert "LIMIT" in compiled


@pytest.mark.asyncio
async def test_list_chunks_by_metadata_returns_empty_for_nonpositive_limit() -> None:
    session = FakeAsyncSession()
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    records = await repository.list_chunks_by_metadata(
        metadata_filters={"source_type": "morning_report"},
        limit=0,
    )

    assert records == ()
    assert session.executed == []


@pytest.mark.asyncio
async def test_list_embedding_jobs_returns_typed_records() -> None:
    model = RagEmbeddingJobModel(
        **RagPersistenceSerializer.embedding_job_values(_job())
    )
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    records = await repository.list_embedding_jobs(status="queued")

    assert len(records) == 1
    assert records[0].status == "queued"
    assert records[0].target_store == "qdrant"


@pytest.mark.asyncio
async def test_persist_embedding_job_uses_idempotent_upsert() -> None:
    session = FakeAsyncSession()
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    result = await repository.persist_embedding_job(_job())

    compiled = str(session.executed[0].compile(dialect=postgresql.dialect()))

    assert result.success is True
    assert result.record_id == "job-1"
    assert session.commits == 1
    assert "rag_embedding_jobs" in compiled
    assert "ON CONFLICT" in compiled
    assert "embedding_model" in compiled


@pytest.mark.asyncio
async def test_mark_source_eligibility_uses_metadata_only_upsert() -> None:
    session = FakeAsyncSession()
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    result = await repository.mark_source_eligibility(_eligibility())

    compiled = str(session.executed[0].compile(dialect=postgresql.dialect()))

    assert result.success is True
    assert result.eligibility_id == (
        "rag_source_eligibility:reports:morning_report:report-1"
    )
    assert session.commits == 1
    assert "rag_source_eligibility" in compiled
    assert "ON CONFLICT" in compiled
    assert "source_table" in compiled
    assert "quality_score" in compiled
    assert "rag_documents" not in compiled
    assert "rag_embedding_jobs" not in compiled


@pytest.mark.asyncio
async def test_mark_source_eligibility_rolls_back_on_sqlalchemy_error() -> None:
    session = FakeAsyncSession(error=SQLAlchemyError("database unavailable"))
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    result = await repository.mark_source_eligibility(_eligibility())

    assert result.success is False
    assert result.error is not None
    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_unmark_source_eligibility_deletes_metadata_marker() -> None:
    session = FakeAsyncSession(result=FakeExecuteResult(rowcount=1))
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    result = await repository.unmark_source_eligibility(
        source_table=" reports ",
        source_id=" report-1 ",
        source_type=" morning_report ",
    )

    compiled = str(session.executed[0].compile(dialect=postgresql.dialect()))

    assert result.success is True
    assert result.records_persisted == 1
    assert result.eligibility_id == (
        "rag_source_eligibility:reports:morning_report:report-1"
    )
    assert session.commits == 1
    assert "DELETE FROM rag_source_eligibility" in compiled


@pytest.mark.asyncio
async def test_get_source_eligibility_round_trips_model_to_record() -> None:
    model = RagSourceEligibilityModel(
        **RagPersistenceSerializer.source_eligibility_values(_eligibility())
    )
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    record = await repository.get_source_eligibility(
        source_table="reports",
        source_id="report-1",
        source_type="morning_report",
    )

    assert record is not None
    assert record.source_key == ("reports", "morning_report", "report-1")
    assert record.eligible is True
    assert record.metadata == {"reviewer": "default_rules"}


@pytest.mark.asyncio
async def test_list_source_eligibility_returns_filtered_typed_records() -> None:
    model = RagSourceEligibilityModel(
        **RagPersistenceSerializer.source_eligibility_values(_eligibility())
    )
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    records = await repository.list_source_eligibility(
        source_table="reports",
        source_type="morning_report",
        eligible=True,
    )

    compiled = str(session.executed[0].compile(dialect=postgresql.dialect()))

    assert len(records) == 1
    assert records[0].source_id == "report-1"
    assert records[0].quality_score == 0.91
    assert "rag_source_eligibility" in compiled
    assert "ORDER BY" in compiled


@pytest.mark.asyncio
async def test_persist_graph_job_uses_idempotent_upsert() -> None:
    session = FakeAsyncSession()
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    result = await repository.persist_graph_job(_graph_job())

    compiled = str(session.executed[0].compile(dialect=postgresql.dialect()))

    assert result.success is True
    assert result.record_id == "graph-job-1"
    assert session.commits == 1
    assert "rag_graph_jobs" in compiled
    assert "ON CONFLICT" in compiled
    assert "graph_model" in compiled


@pytest.mark.asyncio
async def test_list_graph_jobs_returns_filtered_typed_records() -> None:
    model = RagGraphJobModel(**RagPersistenceSerializer.graph_job_values(_graph_job()))
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    records = await repository.list_graph_jobs(status="queued")

    compiled = str(session.executed[0].compile(dialect=postgresql.dialect()))

    assert len(records) == 1
    assert records[0].graph_model == "neo4j-v1"
    assert "rag_graph_jobs" in compiled
    assert "ORDER BY" in compiled


@pytest.mark.asyncio
async def test_persist_query_log_uses_idempotent_upsert() -> None:
    session = FakeAsyncSession()
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    result = await repository.persist_query_log(_query_log())

    compiled = str(session.executed[0].compile(dialect=postgresql.dialect()))

    assert result.success is True
    assert result.record_id == "query-1"
    assert session.commits == 1
    assert "rag_query_logs" in compiled
    assert "ON CONFLICT" in compiled
    assert "retrieval_route" in compiled


@pytest.mark.asyncio
async def test_get_query_log_round_trips_model_to_record() -> None:
    model = RagQueryLogModel(**RagPersistenceSerializer.query_log_values(_query_log()))
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    record = await repository.get_query_log("query-1")

    assert record is not None
    assert record.query_text.startswith("What does")
    assert record.filters == {"source_type": "morning_report"}


@pytest.mark.asyncio
async def test_persist_answer_log_uses_idempotent_upsert() -> None:
    session = FakeAsyncSession()
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    result = await repository.persist_answer_log(_answer_log())

    compiled = str(session.executed[0].compile(dialect=postgresql.dialect()))

    assert result.success is True
    assert result.record_id == "answer-1"
    assert session.commits == 1
    assert "rag_answer_logs" in compiled
    assert "ON CONFLICT" in compiled
    assert "confidence_score" in compiled


@pytest.mark.asyncio
async def test_list_answer_logs_returns_filtered_typed_records() -> None:
    model = RagAnswerLogModel(
        **RagPersistenceSerializer.answer_log_values(_answer_log())
    )
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresRagPersistenceRepository(cast(AsyncSession, session))

    records = await repository.list_answer_logs(query_id="query-1")

    compiled = str(session.executed[0].compile(dialect=postgresql.dialect()))

    assert len(records) == 1
    assert records[0].source_count == 2
    assert records[0].citations == {"items": ["chunk-1"]}
    assert "rag_answer_logs" in compiled
    assert "ORDER BY" in compiled


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
        metadata={
            "section": "summary",
            "source_type": "morning_report",
            "symbol": "SPY",
        },
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
