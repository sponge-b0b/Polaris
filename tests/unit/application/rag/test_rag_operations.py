from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from types import SimpleNamespace

from application.rag.operations.rag_embedding_operations import (
    RagEmbeddingJobOperationsService,
)
from application.rag.operations.rag_ingestion_operations import (
    RagIngestionOperationsService,
)
from application.rag.contracts.rag_operation_models import RagIngestOperationRequest
from application.rag.contracts.rag_operation_models import (
    RagProcessEmbeddingsOperationRequest,
)
from application.rag.contracts.rag_operation_models import (
    RagProcessGraphOperationRequest,
)
from application.rag.contracts.rag_operation_models import RagProjectionConfig
from application.rag.contracts.rag_operation_models import (
    RagRebuildProjectionOperationRequest,
)
from application.rag.operations.rag_projection_operations import (
    RagProjectionOperationsService,
)
from application.rag.ingestion.rag_source_loaders import CuratedRagSourceLoaderRegistry
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
from core.storage.persistence.rag.rag_persistence_models import JsonObject
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from integration.providers.rag.vector_index_models import VectorCollectionReadiness
from integration.providers.rag.vector_index_models import VectorCollectionStatus


class FakeRagRepository:
    def __init__(
        self,
        *,
        eligibility: tuple[RagSourceEligibilityRecord, ...] = (),
        embedding_jobs: tuple[RagEmbeddingJobRecord, ...] = (),
        graph_jobs: tuple[RagGraphJobRecord, ...] = (),
        document_count: int | None = None,
        chunk_count: int | None = None,
        mutate_chunk_after_requeue: bool = False,
    ) -> None:
        self._eligibility = eligibility
        self._embedding_jobs = embedding_jobs
        self._graph_jobs = graph_jobs
        self._document_count = document_count
        self._chunk_count = chunk_count
        self._mutate_chunk_after_requeue = mutate_chunk_after_requeue
        self.persisted_embedding_jobs: tuple[RagEmbeddingJobRecord, ...] = ()

    async def persist_document(
        self,
        document: RagDocumentRecord,
        *,
        chunks: Sequence[RagChunkRecord] = (),
        embedding_jobs: Sequence[RagEmbeddingJobRecord] = (),
    ) -> RagPersistenceResult:
        return RagPersistenceResult.succeeded(
            document_id=document.document_id,
            records_persisted=1,
        )

    async def get_document(
        self,
        document_id: str,
    ) -> RagDocumentRecord | None:
        if any(job.document_id == document_id for job in self._embedding_jobs):
            return RagDocumentRecord(
                document_id=document_id,
                source_table="reports",
                source_id="report-1",
                source_type="morning_report",
                title="Canonical report",
                content_text="Canonical document text.",
                generated_at=datetime(2026, 1, 1, tzinfo=UTC),
                content_hash=f"hash-{document_id}",
            )
        return None

    async def get_canonical_record_counts(self) -> RagCanonicalRecordCounts:
        chunk_ids = {
            job.chunk_id for job in self._embedding_jobs if job.chunk_id is not None
        }
        return RagCanonicalRecordCounts(
            self._document_count if self._document_count is not None else 0,
            self._chunk_count if self._chunk_count is not None else len(chunk_ids),
            len(self._embedding_jobs),
            len(self._graph_jobs),
        )

    async def list_chunks(
        self,
        document_id: str,
    ) -> Sequence[RagChunkRecord]:
        return ()

    async def get_chunk(
        self,
        chunk_id: str,
    ) -> RagChunkRecord | None:
        if any(job.chunk_id == chunk_id for job in self._embedding_jobs):
            return RagChunkRecord(
                chunk_id=chunk_id,
                document_id="document-1",
                chunk_index=0,
                chunk_text=(
                    "Changed canonical chunk text."
                    if self._mutate_chunk_after_requeue
                    and self.persisted_embedding_jobs
                    else "Canonical chunk text."
                ),
                token_count=3,
                content_hash=f"hash-{chunk_id}",
            )
        return None

    async def list_chunks_by_metadata(
        self,
        *,
        metadata_filters: JsonObject,
        limit: int | None = None,
    ) -> Sequence[RagChunkRecord]:
        return ()

    async def list_embedding_jobs(
        self,
        *,
        status: str | None = None,
    ) -> Sequence[RagEmbeddingJobRecord]:
        if status is None:
            return self._embedding_jobs
        return tuple(job for job in self._embedding_jobs if job.status == status)

    async def persist_embedding_job(
        self,
        job: RagEmbeddingJobRecord,
    ) -> RagRecordPersistenceResult:
        self.persisted_embedding_jobs = self.persisted_embedding_jobs + (job,)
        self._embedding_jobs = tuple(
            existing
            for existing in self._embedding_jobs
            if existing.job_id != job.job_id
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
        if status is None:
            return self._graph_jobs
        return tuple(job for job in self._graph_jobs if job.status == status)

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
            eligibility_id="eligibility-1",
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
        records = self._eligibility
        if source_table is not None:
            records = tuple(
                record for record in records if record.source_table == source_table
            )
        if source_id is not None:
            records = tuple(
                record for record in records if record.source_id == source_id
            )
        if source_type is not None:
            records = tuple(
                record for record in records if record.source_type == source_type
            )
        if eligible is not None:
            records = tuple(record for record in records if record.eligible is eligible)
        return records


class FakeVectorCollectionProvider:
    def __init__(
        self,
        *,
        exists: bool = True,
        dense_vector_present: bool = True,
        sparse_vector_present: bool = True,
        actual_vector_size: int | None = 3,
        points_count: int = 0,
    ) -> None:
        self.exists = exists
        self.dense_vector_present = dense_vector_present
        self.sparse_vector_present = sparse_vector_present
        self.actual_vector_size = actual_vector_size
        self.points_count = points_count
        self.recreate_calls: tuple[tuple[str, int], ...] = ()

    async def inspect_collection(
        self,
        *,
        collection_name: str,
        vector_size: int,
    ) -> VectorCollectionReadiness:
        return VectorCollectionReadiness(
            collection_name=collection_name,
            exists=self.exists,
            status="green" if self.exists else None,
            healthy=self.exists,
            dense_vector_present=self.dense_vector_present,
            sparse_vector_present=self.sparse_vector_present,
            configured_vector_size=vector_size,
            actual_vector_size=self.actual_vector_size,
            vector_size_compatible=self.actual_vector_size == vector_size,
            points_count=self.points_count,
        )

    async def ensure_collection(
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
            points_count=self.points_count,
        )

    async def recreate_collection(
        self,
        *,
        collection_name: str,
        vector_size: int,
    ) -> VectorCollectionStatus:
        self.recreate_calls = self.recreate_calls + ((collection_name, vector_size),)
        self.exists = True
        self.dense_vector_present = True
        self.sparse_vector_present = True
        self.actual_vector_size = vector_size
        self.points_count = 0
        return VectorCollectionStatus(
            collection_name=collection_name,
            vector_size=vector_size,
            status="green",
            healthy=True,
            points_count=0,
            created=True,
        )


class FakeRebuildEmbeddingProcessor:
    def __init__(
        self,
        provider: FakeVectorCollectionProvider,
        *,
        completed: bool = True,
    ) -> None:
        self._provider = provider
        self._completed = completed
        self.processed_jobs: tuple[RagEmbeddingJobRecord, ...] = ()

    async def process_job(self, job: RagEmbeddingJobRecord) -> object:
        self.processed_jobs = self.processed_jobs + (job,)
        if self._completed:
            self._provider.points_count += 1
        return SimpleNamespace(completed=self._completed)


class FakeEmbeddingProcessorResult:
    processed_count = 2
    completed_count = 1
    retryable_failure_count = 1
    terminal_failure_count = 0
    retryable_job_ids = ("job-retry",)
    terminal_failure_job_ids: tuple[str, ...] = ()
    failure_summaries = ("job-retry: provider timeout",)


class FakeEmbeddingProcessor:
    def __init__(
        self,
    ) -> None:
        self.called = False
        self.batch_size: int | None = None

    async def process_queued_jobs(
        self,
        *,
        batch_size: int | None = None,
    ) -> FakeEmbeddingProcessorResult:
        self.called = True
        self.batch_size = batch_size
        return FakeEmbeddingProcessorResult()


def test_rag_ingest_reports_dry_run_counts_eligible_sources() -> None:
    service = RagIngestionOperationsService(
        source_loader_registry=CuratedRagSourceLoaderRegistry(()),
        rag_repository=FakeRagRepository(
            eligibility=(
                _eligibility("reports", "report-1", eligible=True),
                _eligibility("reports", "report-2", eligible=True),
            ),
        ),
    )

    result = _run(
        service.ingest(
            RagIngestOperationRequest(
                source="reports",
                limit=1,
                dry_run=True,
            )
        )
    )

    assert result.success is True
    assert result.dry_run is True
    assert result.records_processed == 1
    assert result.details[0].value == "reports"


def test_rag_ingest_market_dry_run_counts_all_curated_market_tables() -> None:
    service = RagIngestionOperationsService(
        source_loader_registry=CuratedRagSourceLoaderRegistry(()),
        rag_repository=FakeRagRepository(
            eligibility=(
                _eligibility(
                    "technical_analysis_snapshots", "technical-1", eligible=True
                ),
                _eligibility("market_context_snapshots", "context-1", eligible=True),
                _eligibility("market_breadth_snapshots", "breadth-1", eligible=True),
                _eligibility("market_ohlcv", "raw-1", eligible=True),
            ),
        ),
    )

    result = _run(
        service.ingest(
            RagIngestOperationRequest(
                source="market",
                dry_run=True,
            )
        )
    )

    details = {detail.name: detail.value for detail in result.details}
    assert result.success is True
    assert result.dry_run is True
    assert result.records_processed == 3
    assert details["source"] == "market"
    assert details["source_tables"] == (
        "technical_analysis_snapshots,market_context_snapshots,market_breadth_snapshots"
    )
    assert details["eligible_sources"] == "3"


def test_rag_ingest_unsupported_source_fails_explicitly() -> None:
    service = RagIngestionOperationsService(
        source_loader_registry=CuratedRagSourceLoaderRegistry(()),
        rag_repository=FakeRagRepository(),
    )

    result = _run(
        service.ingest(
            RagIngestOperationRequest(
                source="bad-source",
            )
        )
    )

    assert result.success is False
    assert "Unsupported RAG ingestion source" in result.message


def test_rag_ingest_emits_source_selection_for_supported_and_rejected_sources() -> None:
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    service = RagIngestionOperationsService(
        source_loader_registry=CuratedRagSourceLoaderRegistry(()),
        rag_repository=FakeRagRepository(),
        telemetry=ApplicationRagTelemetry(observability),
    )

    supported = _run(
        service.ingest(
            RagIngestOperationRequest(source="reports", dry_run=True),
        )
    )
    rejected = _run(
        service.ingest(
            RagIngestOperationRequest(source="raw-provider-payloads"),
        )
    )

    assert supported.success is True
    assert rejected.success is False
    selection_events = [
        event
        for event in sink.events
        if event.attributes.get("operation") == "rag.ingestion.source_selection"
    ]
    assert [event.attributes["supported"] for event in selection_events] == [
        True,
        False,
    ]
    assert selection_events[-1].attributes["source"] == "raw-provider-payloads"


def test_rag_process_embeddings_dry_run_counts_queued_jobs() -> None:
    service = RagEmbeddingJobOperationsService(
        rag_repository=FakeRagRepository(
            embedding_jobs=(
                _embedding_job("job-1", "queued"),
                _embedding_job("job-2", "queued"),
            ),
        ),
    )

    result = _run(
        service.process_embeddings(
            RagProcessEmbeddingsOperationRequest(
                batch_size=1,
                dry_run=True,
            )
        )
    )

    assert result.success is True
    assert result.dry_run is True
    assert result.records_processed == 1


def test_rag_process_embeddings_delegates_to_processor() -> None:
    processor = FakeEmbeddingProcessor()
    service = RagEmbeddingJobOperationsService(
        rag_repository=FakeRagRepository(),
        embedding_job_processor=processor,
    )

    result = _run(
        service.process_embeddings(
            RagProcessEmbeddingsOperationRequest(batch_size=7),
        )
    )

    assert result.success is True
    assert processor.called is True
    assert processor.batch_size == 7
    assert result.records_processed == 2
    details = {detail.name: detail.value for detail in result.details}
    assert details["retryable_job_ids"] == "job-retry"
    assert details["terminal_failure_job_ids"] == ""
    assert details["failure_summaries"] == "job-retry: provider timeout"


def test_rag_process_graph_is_dry_run_until_graph_processor_exists() -> None:
    service = RagProjectionOperationsService(
        rag_repository=FakeRagRepository(
            graph_jobs=(_graph_job("graph-job-1", "queued"),),
        ),
    )

    result = _run(
        service.process_graph(
            RagProcessGraphOperationRequest(),
        )
    )

    assert result.success is True
    assert result.dry_run is True
    assert result.records_processed == 1


def test_rag_rebuild_projection_is_dry_run_without_confirmation() -> None:
    provider = FakeVectorCollectionProvider()
    service = RagProjectionOperationsService(
        rag_repository=FakeRagRepository(),
        vector_collection_provider=provider,
        embedding_job_processor=FakeRebuildEmbeddingProcessor(provider),
        projection_config=RagProjectionConfig(
            collection_name="test_chunks",
            vector_size=3,
            embedding_model="bge-m3",
        ),
    )

    result = _run(
        service.rebuild(
            RagRebuildProjectionOperationRequest(
                projection="qdrant",
            )
        )
    )

    assert result.success is True
    assert result.dry_run is True
    assert "PostgreSQL" in result.message or result.details[-1].value == "postgresql"


def test_rag_rebuild_qdrant_dry_run_detects_legacy_schema() -> None:
    repository = FakeRagRepository(
        embedding_jobs=(_embedding_job("legacy-job-1", "completed"),),
        document_count=1,
    )
    provider = FakeVectorCollectionProvider(
        dense_vector_present=False,
        sparse_vector_present=False,
        actual_vector_size=None,
        points_count=1,
    )
    service = RagProjectionOperationsService(
        rag_repository=repository,
        vector_collection_provider=provider,
        embedding_job_processor=FakeRebuildEmbeddingProcessor(provider),
        projection_config=RagProjectionConfig(
            collection_name="test_chunks",
            vector_size=3,
            embedding_model="bge-m3",
        ),
    )

    result = _run(
        service.rebuild(RagRebuildProjectionOperationRequest(projection="qdrant"))
    )

    assert result.success is True
    assert result.dry_run is True
    assert "legacy or incomplete vector schema" in result.message
    assert provider.recreate_calls == ()


def test_rag_rebuild_qdrant_blocks_before_delete_when_job_coverage_is_incomplete() -> (
    None
):
    repository = FakeRagRepository(
        embedding_jobs=(_embedding_job("legacy-job-1", "completed"),),
        document_count=1,
        chunk_count=2,
    )
    provider = FakeVectorCollectionProvider(points_count=2)
    service = RagProjectionOperationsService(
        rag_repository=repository,
        vector_collection_provider=provider,
        embedding_job_processor=FakeRebuildEmbeddingProcessor(provider),
        projection_config=RagProjectionConfig(
            collection_name="test_chunks",
            vector_size=3,
            embedding_model="bge-m3",
        ),
    )

    result = _run(
        service.rebuild(
            RagRebuildProjectionOperationRequest(
                projection="qdrant",
                dry_run=False,
                confirm_delete=True,
            )
        )
    )

    assert result.success is False
    assert "blocked before deletion" in result.message
    assert provider.recreate_calls == ()


def test_rag_rebuild_qdrant_recreates_repopulates_and_verifies() -> None:
    repository = FakeRagRepository(
        embedding_jobs=(
            _embedding_job("legacy-job-1", "completed"),
            _embedding_job("legacy-job-2", "failed"),
        ),
        document_count=1,
    )
    provider = FakeVectorCollectionProvider(points_count=2)
    processor = FakeRebuildEmbeddingProcessor(provider)
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    service = RagProjectionOperationsService(
        rag_repository=repository,
        vector_collection_provider=provider,
        embedding_job_processor=processor,
        projection_config=RagProjectionConfig(
            collection_name="test_chunks",
            vector_size=3,
            embedding_model="bge-m3",
        ),
        telemetry=ApplicationRagTelemetry(observability),
    )
    request = RagRebuildProjectionOperationRequest(
        projection="qdrant",
        dry_run=False,
        confirm_delete=True,
    )

    result = _run(service.rebuild(request))

    details = {detail.name: detail.value for detail in result.details}
    assert result.success is True
    assert result.records_processed == 2
    assert provider.recreate_calls == (("test_chunks", 3),)
    assert len(processor.processed_jobs) == 2
    assert details["documents_before"] == details["documents_after"] == "1"
    assert details["chunks_before"] == details["chunks_after"] == "2"
    assert details["expected_point_count"] == details["actual_point_count"] == "2"
    assert details["named_dense_vector"] == "True"
    assert details["named_sparse_vector"] == "True"
    assert details["vector_size_compatible"] == "True"
    current_model_jobs = tuple(
        job for job in repository._embedding_jobs if job.embedding_model == "bge-m3"
    )
    assert len(current_model_jobs) == 2
    assert all(job.metadata["rebuild_requeued"] is True for job in current_model_jobs)
    completed_events = [
        event
        for event in sink.events
        if event.event_type == "application.rag.operation.completed"
        and event.attributes.get("operation") == "rag.rebuild_projection"
    ]
    assert len(completed_events) == 1
    assert completed_events[0].attributes["expected_point_count"] == "2"
    assert completed_events[0].attributes["actual_point_count"] == "2"
    assert completed_events[0].duration_seconds is not None


def test_rag_rebuild_qdrant_fails_if_canonical_chunk_changes() -> None:
    repository = FakeRagRepository(
        embedding_jobs=(_embedding_job("legacy-job-1", "completed"),),
        document_count=1,
        mutate_chunk_after_requeue=True,
    )
    provider = FakeVectorCollectionProvider(points_count=1)
    service = RagProjectionOperationsService(
        rag_repository=repository,
        vector_collection_provider=provider,
        embedding_job_processor=FakeRebuildEmbeddingProcessor(provider),
        projection_config=RagProjectionConfig(
            collection_name="test_chunks",
            vector_size=3,
            embedding_model="bge-m3",
        ),
    )

    result = _run(
        service.rebuild(
            RagRebuildProjectionOperationRequest(
                projection="qdrant",
                dry_run=False,
                confirm_delete=True,
            )
        )
    )

    assert result.success is False
    assert "chunk content changed" in result.message


def test_rag_rebuild_qdrant_fails_when_projection_does_not_reach_expected_count() -> (
    None
):
    repository = FakeRagRepository(
        embedding_jobs=(_embedding_job("legacy-job-1", "completed"),),
        document_count=1,
    )
    provider = FakeVectorCollectionProvider(points_count=1)
    service = RagProjectionOperationsService(
        rag_repository=repository,
        vector_collection_provider=provider,
        embedding_job_processor=FakeRebuildEmbeddingProcessor(
            provider,
            completed=False,
        ),
        projection_config=RagProjectionConfig(
            collection_name="test_chunks",
            vector_size=3,
            embedding_model="bge-m3",
        ),
    )

    result = _run(
        service.rebuild(
            RagRebuildProjectionOperationRequest(
                projection="qdrant",
                dry_run=False,
                confirm_delete=True,
            )
        )
    )

    assert result.success is False
    assert "did not complete all canonical embedding jobs" in result.message


def _eligibility(
    source_table: str,
    source_id: str,
    *,
    eligible: bool,
) -> RagSourceEligibilityRecord:
    return RagSourceEligibilityRecord(
        eligibility_id=f"eligibility-{source_id}",
        source_table=source_table,
        source_id=source_id,
        source_type="morning_report",
        eligible=eligible,
        reason="test",
        quality_score=0.9,
        reviewed_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _embedding_job(
    job_id: str,
    status: str,
) -> RagEmbeddingJobRecord:
    return RagEmbeddingJobRecord(
        job_id=job_id,
        document_id="document-1",
        chunk_id=f"chunk-{job_id}",
        target_store="qdrant",
        embedding_model="nomic-embed-text",
        status=status,
        queued_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _graph_job(
    job_id: str,
    status: str,
) -> RagGraphJobRecord:
    return RagGraphJobRecord(
        job_id=job_id,
        document_id="document-1",
        chunk_id=f"chunk-{job_id}",
        target_store="neo4j",
        graph_model="rag-graph-v1",
        status=status,
        queued_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _run(
    awaitable,
):
    import asyncio

    return asyncio.run(
        awaitable,
    )
