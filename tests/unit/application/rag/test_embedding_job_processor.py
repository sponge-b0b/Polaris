from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from datetime import timezone

import pytest

from application.rag.operations.embedding_job_processor import EmbeddingJobProcessor
from application.rag.operations.embedding_job_processor import (
    EmbeddingJobProcessorConfig,
)
from core.storage.persistence.rag import JsonObject
from core.storage.persistence.rag import RagAnswerLogRecord
from core.storage.persistence.rag import RagCanonicalRecordCounts
from core.storage.persistence.rag import RagChunkRecord
from core.storage.persistence.rag import RagDocumentRecord
from core.storage.persistence.rag import RagEmbeddingJobRecord
from core.storage.persistence.rag import RagGraphJobRecord
from core.storage.persistence.rag import RagPersistenceResult
from core.storage.persistence.rag import RagQueryLogRecord
from core.storage.persistence.rag import RagRecordPersistenceResult
from core.storage.persistence.rag import RagSourceEligibilityRecord
from core.storage.persistence.rag import RagSourceEligibilityResult
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from integration.providers.rag.embedding_provider import EmbeddingRequest
from integration.providers.rag.embedding_provider import EmbeddingVector
from integration.providers.rag.embedding_provider import SparseEmbeddingVector
from integration.providers.rag.vector_index_models import VectorCollectionReadiness
from integration.providers.rag.vector_index_models import VectorCollectionStatus
from integration.providers.rag.vector_index_models import VectorIndexPoint
from integration.providers.rag.vector_index_models import VectorSearchQuery
from integration.providers.rag.vector_index_models import VectorSearchResult


@pytest.mark.asyncio
async def test_embedding_job_processor_completes_queued_job() -> None:
    telemetry, sink, observability = _telemetry()
    repository = FakeRagPersistenceRepository(
        chunks=(_chunk(),),
        jobs=(_job(),),
    )
    embedding_provider = FakeEmbeddingProvider(
        vectors=(
            EmbeddingVector(
                text_id=_chunk().chunk_id,
                dense_vector=(0.1, 0.2, 0.3),
                sparse_vector=SparseEmbeddingVector(indices=(1, 4), values=(0.7, 0.2)),
                model="bge-large",
            ),
        )
    )
    vector_provider = FakeVectorIndexProvider()
    processor = EmbeddingJobProcessor(
        repository=repository,
        embedding_provider=embedding_provider,
        vector_index_provider=vector_provider,
        telemetry=telemetry,
        collection_lifecycle_provider=vector_provider,
        config=EmbeddingJobProcessorConfig(
            collection_name="polaris_rag_chunks",
            vector_size=3,
        ),
    )

    result = await processor.process_queued_jobs()

    assert result.processed_count == 1
    assert result.completed_count == 1
    assert result.retryable_failure_count == 0
    assert result.terminal_failure_count == 0
    assert repository.persisted_jobs[-2].status == "processing"
    assert repository.persisted_jobs[-2].attempts == 1
    assert repository.persisted_jobs[-1].status == "completed"
    assert repository.persisted_jobs[-1].completed_at is not None
    assert repository.persisted_jobs[-1].metadata["dense_vector_dimensions"] == 3
    assert embedding_provider.requests[0].model == "bge-large"
    assert (
        embedding_provider.requests[0].inputs[0].text
        == "# Market context\n\nRisk is elevated."
    )
    assert vector_provider.ensure_calls == (("polaris_rag_chunks", 3),)
    assert vector_provider.upserts == (
        (
            "polaris_rag_chunks",
            (
                VectorIndexPoint(
                    point_id=_chunk().chunk_id,
                    dense_vector=(0.1, 0.2, 0.3),
                    sparse_vector=SparseEmbeddingVector(
                        indices=(1, 4), values=(0.7, 0.2)
                    ),
                    payload={
                        "section_name": "market_context",
                        "chunk_id": _chunk().chunk_id,
                        "document_id": _chunk().document_id,
                        "chunk_index": 0,
                        "chunk_text": _chunk().chunk_text,
                        "token_count": 5,
                        "content_hash": "chunk-hash-1",
                    },
                ),
            ),
        ),
    )
    operations = _operations(
        sink,
    )
    assert "rag.embedding_jobs.process" in operations
    assert operations.count("rag.embedding.job") == 2
    assert any(
        point.name == "application.rag.operations.total"
        for point in observability.metrics_store.points()
    )


@pytest.mark.asyncio
async def test_embedding_job_processor_requeues_retryable_failure() -> None:
    repository = FakeRagPersistenceRepository(
        chunks=(_chunk(),),
        jobs=(_job(),),
    )
    embedding_provider = FakeEmbeddingProvider(error=RuntimeError("provider timeout"))
    vector_provider = FakeVectorIndexProvider()
    processor = EmbeddingJobProcessor(
        repository=repository,
        embedding_provider=embedding_provider,
        vector_index_provider=vector_provider,
        config=EmbeddingJobProcessorConfig(max_attempts=3),
    )

    result = await processor.process_queued_jobs()

    assert result.processed_count == 1
    assert result.completed_count == 0
    assert result.retryable_failure_count == 1
    assert result.terminal_failure_count == 0
    assert repository.persisted_jobs[-1].status == "queued"
    assert repository.persisted_jobs[-1].attempts == 1
    assert repository.persisted_jobs[-1].completed_at is None
    assert repository.persisted_jobs[-1].error == "provider timeout"
    assert result.retryable_job_ids == ("job-1",)
    assert result.terminal_failure_job_ids == ()
    assert result.failure_summaries == ("job-1: provider timeout",)
    assert vector_provider.upserts == ()


@pytest.mark.asyncio
async def test_embedding_job_processor_records_terminal_failure() -> None:
    repository = FakeRagPersistenceRepository(
        chunks=(_chunk(),),
        jobs=(
            _job(
                attempts=2,
            ),
        ),
    )
    embedding_provider = FakeEmbeddingProvider(error=RuntimeError("bad vector"))
    vector_provider = FakeVectorIndexProvider()
    processor = EmbeddingJobProcessor(
        repository=repository,
        embedding_provider=embedding_provider,
        vector_index_provider=vector_provider,
        config=EmbeddingJobProcessorConfig(max_attempts=3),
    )

    result = await processor.process_queued_jobs()

    assert result.processed_count == 1
    assert result.completed_count == 0
    assert result.retryable_failure_count == 0
    assert result.terminal_failure_count == 1
    assert repository.persisted_jobs[-1].status == "failed"
    assert repository.persisted_jobs[-1].attempts == 3
    assert repository.persisted_jobs[-1].completed_at is not None
    assert repository.persisted_jobs[-1].error == "bad vector"
    assert result.retryable_job_ids == ()
    assert result.terminal_failure_job_ids == ("job-1",)
    assert result.failure_summaries == ("job-1: bad vector",)


class FakeEmbeddingProvider:
    def __init__(
        self,
        *,
        vectors: tuple[EmbeddingVector, ...] = (),
        error: Exception | None = None,
    ) -> None:
        self.vectors = vectors
        self.error = error
        self.requests: list[EmbeddingRequest] = []

    async def embed_texts(
        self,
        request: EmbeddingRequest,
    ) -> tuple[EmbeddingVector, ...]:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.vectors


class FakeVectorIndexProvider:
    def __init__(
        self,
    ) -> None:
        self.ensure_calls: tuple[tuple[str, int], ...] = ()
        self.upserts: tuple[tuple[str, tuple[VectorIndexPoint, ...]], ...] = ()

    async def inspect_collection(
        self,
        *,
        collection_name: str,
        vector_size: int,
    ) -> VectorCollectionReadiness:
        return VectorCollectionReadiness(
            collection_name=collection_name,
            exists=True,
            status="green",
            healthy=True,
            dense_vector_present=True,
            sparse_vector_present=True,
            configured_vector_size=vector_size,
            actual_vector_size=vector_size,
            vector_size_compatible=True,
        )

    async def ensure_collection(
        self,
        *,
        collection_name: str,
        vector_size: int,
    ) -> VectorCollectionStatus:
        self.ensure_calls = self.ensure_calls + ((collection_name, vector_size),)
        return VectorCollectionStatus(
            collection_name=collection_name,
            vector_size=vector_size,
            status="green",
            healthy=True,
        )

    async def recreate_collection(
        self,
        *,
        collection_name: str,
        vector_size: int,
    ) -> VectorCollectionStatus:
        return VectorCollectionStatus(
            collection_name=collection_name,
            vector_size=vector_size,
            status="green",
            healthy=True,
            created=True,
        )

    async def upsert_points(
        self,
        *,
        collection_name: str,
        points: tuple[VectorIndexPoint, ...],
    ) -> int:
        self.upserts = self.upserts + ((collection_name, points),)
        return len(points)

    async def search(
        self,
        *,
        collection_name: str,
        query: VectorSearchQuery,
    ) -> tuple[VectorSearchResult, ...]:
        return ()


class FakeRagPersistenceRepository:
    def __init__(
        self,
        *,
        chunks: Sequence[RagChunkRecord] = (),
        jobs: Sequence[RagEmbeddingJobRecord] = (),
    ) -> None:
        self.chunks = tuple(chunks)
        self.jobs = tuple(jobs)
        self.persisted_jobs: tuple[RagEmbeddingJobRecord, ...] = ()

    async def persist_document(
        self,
        document: RagDocumentRecord,
        *,
        chunks: Sequence[RagChunkRecord] = (),
        embedding_jobs: Sequence[RagEmbeddingJobRecord] = (),
    ) -> RagPersistenceResult:
        return RagPersistenceResult.succeeded(
            document_id=document.document_id,
            records_persisted=1 + len(chunks) + len(embedding_jobs),
        )

    async def get_document(
        self,
        document_id: str,
    ) -> RagDocumentRecord | None:
        return None

    async def get_canonical_record_counts(self) -> RagCanonicalRecordCounts:
        return RagCanonicalRecordCounts(0, 0, 0, 0)

    async def list_chunks(
        self,
        document_id: str,
    ) -> Sequence[RagChunkRecord]:
        return tuple(chunk for chunk in self.chunks if chunk.document_id == document_id)

    async def get_chunk(
        self,
        chunk_id: str,
    ) -> RagChunkRecord | None:
        for chunk in self.chunks:
            if chunk.chunk_id == chunk_id:
                return chunk
        return None

    async def list_chunks_by_metadata(
        self,
        *,
        metadata_filters: JsonObject,
        limit: int | None = None,
    ) -> Sequence[RagChunkRecord]:
        chunks = tuple(
            chunk
            for chunk in self.chunks
            if all(
                chunk.metadata.get(key) == value
                for key, value in metadata_filters.items()
            )
        )
        if limit is not None:
            return chunks[:limit]
        return chunks

    async def list_embedding_jobs(
        self,
        *,
        status: str | None = None,
    ) -> Sequence[RagEmbeddingJobRecord]:
        if status is None:
            return self.jobs
        return tuple(job for job in self.jobs if job.status == status)

    async def persist_embedding_job(
        self,
        job: RagEmbeddingJobRecord,
    ) -> RagRecordPersistenceResult:
        self.persisted_jobs = self.persisted_jobs + (job,)
        self.jobs = tuple(
            existing for existing in self.jobs if existing.job_id != job.job_id
        ) + (job,)
        return RagRecordPersistenceResult.succeeded(
            record_id=job.job_id,
        )

    async def persist_graph_job(
        self,
        job: RagGraphJobRecord,
    ) -> RagRecordPersistenceResult:
        return RagRecordPersistenceResult.succeeded(
            record_id=job.job_id,
        )

    async def list_graph_jobs(
        self,
        *,
        status: str | None = None,
    ) -> Sequence[RagGraphJobRecord]:
        return ()

    async def persist_query_log(
        self,
        query: RagQueryLogRecord,
    ) -> RagRecordPersistenceResult:
        return RagRecordPersistenceResult.succeeded(
            record_id=query.query_id,
        )

    async def get_query_log(
        self,
        query_id: str,
    ) -> RagQueryLogRecord | None:
        return None

    async def persist_answer_log(
        self,
        answer: RagAnswerLogRecord,
    ) -> RagRecordPersistenceResult:
        return RagRecordPersistenceResult.succeeded(
            record_id=answer.answer_id,
        )

    async def list_answer_logs(
        self,
        *,
        query_id: str | None = None,
    ) -> Sequence[RagAnswerLogRecord]:
        return ()

    async def mark_source_eligibility(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> RagSourceEligibilityResult:
        return RagSourceEligibilityResult.succeeded(
            eligibility_id=eligibility.eligibility_id,
        )

    async def unmark_source_eligibility(
        self,
        *,
        source_table: str,
        source_id: str,
        source_type: str,
    ) -> RagSourceEligibilityResult:
        return RagSourceEligibilityResult.succeeded(
            eligibility_id=f"{source_table}:{source_type}:{source_id}",
        )

    async def get_source_eligibility(
        self,
        *,
        source_table: str,
        source_id: str,
        source_type: str,
    ) -> RagSourceEligibilityRecord | None:
        return None

    async def list_source_eligibility(
        self,
        *,
        source_table: str | None = None,
        source_id: str | None = None,
        source_type: str | None = None,
        eligible: bool | None = None,
    ) -> Sequence[RagSourceEligibilityRecord]:
        return ()


def _chunk() -> RagChunkRecord:
    return RagChunkRecord(
        chunk_id="chunk-1",
        document_id="document-1",
        chunk_index=0,
        chunk_text="# Market context\n\nRisk is elevated.",
        token_count=5,
        content_hash="chunk-hash-1",
        metadata={"section_name": "market_context"},
    )


def _job(
    *,
    attempts: int = 0,
) -> RagEmbeddingJobRecord:
    return RagEmbeddingJobRecord(
        job_id="job-1",
        document_id="document-1",
        chunk_id="chunk-1",
        target_store="qdrant",
        embedding_model="bge-large",
        status="queued",
        queued_at=datetime(2026, 5, 30, tzinfo=timezone.utc),
        attempts=attempts,
        metadata={"source_type": "morning_report"},
    )


def _telemetry() -> tuple[
    ApplicationRagTelemetry,
    InMemoryTelemetrySink,
    ObservabilityManager,
]:
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(
        sink,
    )
    return (
        ApplicationRagTelemetry(
            observability_manager=observability,
        ),
        sink,
        observability,
    )


def _operations(
    sink: InMemoryTelemetrySink,
) -> list[object]:
    return [event.attributes.get("operation") for event in sink.events]
