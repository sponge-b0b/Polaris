from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import replace
from time import perf_counter
from typing import Protocol

from application.rag.operations.rag_embedding_operations import safe_int_attr
from application.rag.contracts.rag_operation_models import RagOperationDetail
from application.rag.contracts.rag_operation_models import RagOperationResult
from application.rag.contracts.rag_operation_models import (
    RagProcessGraphOperationRequest,
)
from application.rag.contracts.rag_operation_models import RagProjectionConfig
from application.rag.contracts.rag_operation_models import (
    RagRebuildProjectionOperationRequest,
)
from application.rag.operations.rag_operation_telemetry import RagOperationTelemetry
from core.storage.persistence.rag import RagCanonicalRecordCounts
from core.storage.persistence.rag import RagChunkRecord
from core.storage.persistence.rag import RagDocumentRecord
from core.storage.persistence.rag import RagEmbeddingJobRecord
from core.storage.persistence.rag import RagPersistenceRepository
from core.storage.persistence.rag import new_rag_embedding_job_id
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from integration.providers.rag.vector_index_models import VectorCollectionReadiness
from integration.providers.rag.vector_index_provider import (
    VectorCollectionLifecycleProvider,
)


RAG_PROJECTION_QDRANT = "qdrant"
RAG_PROJECTION_NEO4J = "neo4j"
SUPPORTED_RAG_PROJECTIONS = (RAG_PROJECTION_QDRANT, RAG_PROJECTION_NEO4J)


class GraphProjectionProcessorPort(Protocol):
    async def queue_document(self, document_id: str) -> bool: ...

    async def process_queued_jobs(
        self,
        *,
        batch_size: int | None = None,
    ) -> object: ...

    async def rebuild(self) -> object: ...


class QdrantEmbeddingJobProcessorPort(Protocol):
    async def process_job(self, job: RagEmbeddingJobRecord) -> object: ...


@dataclass(frozen=True, slots=True)
class _QdrantRebuildPreflight:
    counts: RagCanonicalRecordCounts
    readiness: VectorCollectionReadiness
    documents: tuple[RagDocumentRecord, ...]
    chunks: tuple[RagChunkRecord, ...]
    source_jobs: tuple[RagEmbeddingJobRecord, ...]


@dataclass(frozen=True, slots=True)
class _QdrantRebuildVerification:
    counts_before: RagCanonicalRecordCounts
    counts_after: RagCanonicalRecordCounts
    readiness: VectorCollectionReadiness
    requeued_jobs: tuple[RagEmbeddingJobRecord, ...]
    completed_jobs: int
    failed_jobs: int


class RagProjectionOperationsService:
    """Processes and explicitly rebuilds Qdrant and Neo4j projections."""

    def __init__(
        self,
        *,
        rag_repository: RagPersistenceRepository,
        graph_projection_processor: GraphProjectionProcessorPort | None = None,
        vector_collection_provider: VectorCollectionLifecycleProvider | None = None,
        embedding_job_processor: QdrantEmbeddingJobProcessorPort | None = None,
        projection_config: RagProjectionConfig | None = None,
        telemetry: ApplicationRagTelemetry | None = None,
    ) -> None:
        self._rag_repository = rag_repository
        self._graph_projection_processor = graph_projection_processor
        self._vector_collection_provider = vector_collection_provider
        self._embedding_job_processor = embedding_job_processor
        self._projection_config = projection_config
        self._telemetry = RagOperationTelemetry(self.__class__.__name__, telemetry)

    async def process_graph(
        self,
        request: RagProcessGraphOperationRequest,
    ) -> RagOperationResult:
        operation = "rag.process_graph"
        queued_jobs = await self._rag_repository.list_graph_jobs(status="queued")
        if request.dry_run:
            return RagOperationResult.succeeded(
                operation=operation,
                message="Dry run complete; queued graph jobs were not processed.",
                records_processed=len(queued_jobs),
                dry_run=True,
                details=(
                    RagOperationDetail("queued_graph_jobs", str(len(queued_jobs))),
                ),
            )
        if self._graph_projection_processor is None:
            return RagOperationResult.failed(
                operation=operation,
                error="Graph projection processor is not configured.",
            )

        started_at = perf_counter()
        await self._telemetry.emit_started(
            operation,
            details=(RagOperationDetail("queued_graph_jobs", str(len(queued_jobs))),),
        )
        try:
            processor_result = (
                await self._graph_projection_processor.process_queued_jobs()
            )
        except Exception as exc:
            await self._telemetry.emit_failed(
                operation,
                error=exc,
                duration_seconds=perf_counter() - started_at,
            )
            return RagOperationResult.failed(operation=operation, error=str(exc))

        failed_count = safe_int_attr(processor_result, "failed_count")
        result = (
            RagOperationResult.succeeded(
                operation=operation,
                message="Graph projection job processing complete.",
                records_processed=safe_int_attr(processor_result, "processed_count"),
                details=(
                    RagOperationDetail(
                        "completed_count",
                        str(safe_int_attr(processor_result, "completed_count")),
                    ),
                    RagOperationDetail("failed_count", str(failed_count)),
                ),
            )
            if failed_count == 0
            else RagOperationResult.failed(
                operation=operation,
                error=(
                    "Graph projection processing completed with "
                    f"{failed_count} failure(s)."
                ),
                details=(RagOperationDetail("failed_count", str(failed_count)),),
            )
        )
        await self._telemetry.emit_completed(
            operation,
            result=result,
            duration_seconds=perf_counter() - started_at,
        )
        return result

    async def rebuild(
        self,
        request: RagRebuildProjectionOperationRequest,
    ) -> RagOperationResult:
        operation = "rag.rebuild_projection"
        projection = request.projection.strip().lower()
        if projection not in SUPPORTED_RAG_PROJECTIONS:
            return RagOperationResult.failed(
                operation=operation,
                error=(
                    f"Unsupported RAG projection '{projection}'. Supported projections: "
                    f"{', '.join(SUPPORTED_RAG_PROJECTIONS)}."
                ),
                dry_run=request.dry_run,
            )
        if projection == RAG_PROJECTION_QDRANT:
            return await self._rebuild_qdrant(
                operation,
                execute=not request.dry_run and request.confirm_delete,
            )
        if request.dry_run or not request.confirm_delete:
            return _rebuild_dry_run_result(projection)
        return await self._rebuild_neo4j(operation)

    async def _rebuild_neo4j(self, operation: str) -> RagOperationResult:
        if self._graph_projection_processor is None:
            return RagOperationResult.failed(
                operation=operation,
                error="Neo4j projection lifecycle is not configured.",
            )
        started_at = perf_counter()
        await self._telemetry.emit_started(
            operation,
            details=(RagOperationDetail("projection", RAG_PROJECTION_NEO4J),),
        )
        try:
            processor_result = await self._graph_projection_processor.rebuild()
        except Exception as exc:
            await self._telemetry.emit_failed(
                operation,
                error=exc,
                duration_seconds=perf_counter() - started_at,
            )
            return RagOperationResult.failed(operation=operation, error=str(exc))

        result = RagOperationResult.succeeded(
            operation=operation,
            message="Neo4j projection recreated from PostgreSQL graph jobs.",
            records_processed=safe_int_attr(processor_result, "processed_count"),
            details=(
                RagOperationDetail("projection", RAG_PROJECTION_NEO4J),
                RagOperationDetail(
                    "completed_count",
                    str(safe_int_attr(processor_result, "completed_count")),
                ),
                RagOperationDetail(
                    "failed_count",
                    str(safe_int_attr(processor_result, "failed_count")),
                ),
                RagOperationDetail(
                    "cleared_entity_count",
                    str(safe_int_attr(processor_result, "cleared_entity_count")),
                ),
                RagOperationDetail("source_of_truth", "postgresql"),
            ),
        )
        await self._telemetry.emit_completed(
            operation,
            result=result,
            duration_seconds=perf_counter() - started_at,
        )
        return result

    async def _rebuild_qdrant(
        self,
        operation: str,
        *,
        execute: bool,
    ) -> RagOperationResult:
        if (
            self._vector_collection_provider is None
            or self._embedding_job_processor is None
            or self._projection_config is None
        ):
            return RagOperationResult.failed(
                operation=operation,
                error="Qdrant projection rebuild lifecycle is not fully configured.",
            )

        started_at = perf_counter()
        await self._telemetry.emit_started(
            operation,
            details=(
                RagOperationDetail("projection", RAG_PROJECTION_QDRANT),
                RagOperationDetail(
                    "collection_name",
                    self._projection_config.collection_name,
                ),
                RagOperationDetail("dry_run", str(not execute).lower()),
            ),
        )
        try:
            preflight = await self._qdrant_rebuild_preflight()
        except Exception as exc:
            await self._telemetry.emit_failed(
                operation,
                error=exc,
                duration_seconds=perf_counter() - started_at,
                details=(RagOperationDetail("dry_run", str(not execute).lower()),),
            )
            return RagOperationResult.failed(operation=operation, error=str(exc))

        if not execute:
            return _qdrant_rebuild_dry_run_result(preflight)

        verification: _QdrantRebuildVerification | None = None
        try:
            verification = await self._execute_qdrant_rebuild(preflight)
            _validate_qdrant_rebuild(verification)
        except Exception as exc:
            await self._telemetry.emit_failed(
                operation,
                error=exc,
                duration_seconds=perf_counter() - started_at,
                details=(
                    _qdrant_rebuild_verification_details(verification)
                    if verification is not None
                    else _qdrant_rebuild_details(preflight)
                ),
            )
            return RagOperationResult.failed(
                operation=operation,
                error=str(exc),
                details=(
                    _qdrant_rebuild_verification_details(verification)
                    if verification is not None
                    else _qdrant_rebuild_details(preflight)
                ),
            )

        result = RagOperationResult.succeeded(
            operation=operation,
            message=(
                "Qdrant projection recreated, repopulated from canonical PostgreSQL "
                "chunks, and verified."
            ),
            records_processed=verification.completed_jobs,
            details=_qdrant_rebuild_verification_details(verification),
        )
        await self._telemetry.emit_completed(
            operation,
            result=result,
            duration_seconds=perf_counter() - started_at,
        )
        return result

    async def _qdrant_rebuild_preflight(self) -> _QdrantRebuildPreflight:
        if self._vector_collection_provider is None or self._projection_config is None:
            raise RuntimeError("Qdrant projection lifecycle is not configured.")
        counts = await self._rag_repository.get_canonical_record_counts()
        jobs = await self._rag_repository.list_embedding_jobs()
        source_jobs = _canonical_qdrant_jobs(
            jobs,
            embedding_model=self._projection_config.embedding_model,
        )
        if len(source_jobs) != counts.chunk_count:
            raise RuntimeError(
                "Qdrant rebuild blocked before deletion: canonical PostgreSQL contains "
                f"{counts.chunk_count} chunk(s), but only {len(source_jobs)} unique "
                "Qdrant embedding-job source(s). Restore or regenerate the missing "
                "canonical embedding jobs, then rerun the rebuild dry run."
            )
        documents, chunks = await self._load_canonical_qdrant_records(source_jobs)
        if len(documents) != counts.document_count:
            raise RuntimeError(
                "Qdrant rebuild blocked before deletion: canonical PostgreSQL contains "
                f"{counts.document_count} document(s), but only {len(documents)} "
                "document(s) are reachable from canonical Qdrant embedding jobs. "
                "Restore or regenerate the missing canonical jobs before rebuilding."
            )
        readiness = await self._vector_collection_provider.inspect_collection(
            collection_name=self._projection_config.collection_name,
            vector_size=self._projection_config.vector_size,
        )
        return _QdrantRebuildPreflight(
            counts=counts,
            readiness=readiness,
            documents=documents,
            chunks=chunks,
            source_jobs=source_jobs,
        )

    async def _load_canonical_qdrant_records(
        self,
        source_jobs: Sequence[RagEmbeddingJobRecord],
    ) -> tuple[tuple[RagDocumentRecord, ...], tuple[RagChunkRecord, ...]]:
        documents_by_id: dict[str, RagDocumentRecord] = {}
        chunks: list[RagChunkRecord] = []
        for job in source_jobs:
            if job.chunk_id is None:
                raise RuntimeError(
                    "Canonical Qdrant embedding job is missing chunk ID."
                )
            chunk = await self._rag_repository.get_chunk(job.chunk_id)
            if chunk is None:
                raise RuntimeError(
                    "Qdrant rebuild blocked before deletion: embedding job references "
                    f"missing canonical PostgreSQL chunk '{job.chunk_id}'."
                )
            if chunk.document_id != job.document_id:
                raise RuntimeError(
                    "Qdrant rebuild blocked before deletion: embedding job/chunk "
                    f"document mismatch for chunk '{job.chunk_id}'."
                )
            chunks.append(chunk)
            if chunk.document_id not in documents_by_id:
                document = await self._rag_repository.get_document(chunk.document_id)
                if document is None:
                    raise RuntimeError(
                        "Qdrant rebuild blocked before deletion: chunk references "
                        "missing canonical PostgreSQL document "
                        f"'{chunk.document_id}'."
                    )
                documents_by_id[chunk.document_id] = document
        return (
            tuple(documents_by_id[key] for key in sorted(documents_by_id)),
            tuple(sorted(chunks, key=lambda chunk: chunk.chunk_id)),
        )

    async def _verify_canonical_records_unchanged(
        self,
        preflight: _QdrantRebuildPreflight,
    ) -> None:
        current_documents: list[RagDocumentRecord] = []
        for expected_document in preflight.documents:
            current_document = await self._rag_repository.get_document(
                expected_document.document_id
            )
            if current_document is None:
                raise RuntimeError(
                    "Canonical PostgreSQL document was deleted during Qdrant rebuild: "
                    f"'{expected_document.document_id}'."
                )
            current_documents.append(current_document)
        current_chunks: list[RagChunkRecord] = []
        for expected_chunk in preflight.chunks:
            current_chunk = await self._rag_repository.get_chunk(
                expected_chunk.chunk_id
            )
            if current_chunk is None:
                raise RuntimeError(
                    "Canonical PostgreSQL chunk was deleted during Qdrant rebuild: "
                    f"'{expected_chunk.chunk_id}'."
                )
            current_chunks.append(current_chunk)
        if tuple(current_documents) != preflight.documents:
            raise RuntimeError(
                "Canonical PostgreSQL document content changed during Qdrant rebuild."
            )
        if tuple(current_chunks) != preflight.chunks:
            raise RuntimeError(
                "Canonical PostgreSQL chunk content changed during Qdrant rebuild."
            )

    async def _execute_qdrant_rebuild(
        self,
        preflight: _QdrantRebuildPreflight,
    ) -> _QdrantRebuildVerification:
        if (
            self._vector_collection_provider is None
            or self._embedding_job_processor is None
            or self._projection_config is None
        ):
            raise RuntimeError("Qdrant projection rebuild lifecycle is not configured.")

        counts_at_delete = await self._rag_repository.get_canonical_record_counts()
        if (
            counts_at_delete.document_count,
            counts_at_delete.chunk_count,
        ) != (
            preflight.counts.document_count,
            preflight.counts.chunk_count,
        ):
            raise RuntimeError(
                "Qdrant rebuild blocked before deletion because canonical PostgreSQL "
                "document/chunk counts changed after preflight. Rerun the dry run."
            )
        await self._vector_collection_provider.recreate_collection(
            collection_name=self._projection_config.collection_name,
            vector_size=self._projection_config.vector_size,
        )
        recreated = await self._vector_collection_provider.inspect_collection(
            collection_name=self._projection_config.collection_name,
            vector_size=self._projection_config.vector_size,
        )
        _validate_recreated_qdrant_schema(recreated)

        requeued_jobs = tuple(
            [
                await self._persist_requeued_embedding_job(job)
                for job in preflight.source_jobs
            ]
        )
        outcomes = tuple(
            [
                await self._embedding_job_processor.process_job(job)
                for job in requeued_jobs
            ]
        )
        completed_jobs = sum(
            1 for outcome in outcomes if bool(getattr(outcome, "completed", False))
        )
        failed_jobs = len(outcomes) - completed_jobs
        counts_after = await self._rag_repository.get_canonical_record_counts()
        await self._verify_canonical_records_unchanged(preflight)
        readiness = await self._vector_collection_provider.inspect_collection(
            collection_name=self._projection_config.collection_name,
            vector_size=self._projection_config.vector_size,
        )
        return _QdrantRebuildVerification(
            counts_before=preflight.counts,
            counts_after=counts_after,
            readiness=readiness,
            requeued_jobs=requeued_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
        )

    async def _persist_requeued_embedding_job(
        self,
        job: RagEmbeddingJobRecord,
    ) -> RagEmbeddingJobRecord:
        if self._projection_config is None or job.chunk_id is None:
            raise RuntimeError(
                "Qdrant projection configuration or chunk ID is missing."
            )
        requeued_job = replace(
            job,
            job_id=new_rag_embedding_job_id(
                document_id=job.document_id,
                chunk_id=job.chunk_id,
                target_store=RAG_PROJECTION_QDRANT,
                embedding_model=self._projection_config.embedding_model,
            ),
            target_store=RAG_PROJECTION_QDRANT,
            embedding_model=self._projection_config.embedding_model,
            status="queued",
            started_at=None,
            completed_at=None,
            attempts=0,
            error=None,
            metadata={
                **dict(job.metadata),
                "collection_name": self._projection_config.collection_name,
                "rebuild_requeued": True,
            },
        )
        result = await self._rag_repository.persist_embedding_job(requeued_job)
        if not result.success:
            raise RuntimeError(
                result.error
                or f"Failed to requeue embedding job for chunk {job.chunk_id}."
            )
        return requeued_job


def _canonical_qdrant_jobs(
    jobs: Sequence[RagEmbeddingJobRecord],
    *,
    embedding_model: str,
) -> tuple[RagEmbeddingJobRecord, ...]:
    jobs_by_chunk: dict[str, RagEmbeddingJobRecord] = {}
    for job in jobs:
        if job.target_store != RAG_PROJECTION_QDRANT or job.chunk_id is None:
            continue
        current = jobs_by_chunk.get(job.chunk_id)
        if current is None or (
            job.embedding_model == embedding_model
            and current.embedding_model != embedding_model
        ):
            jobs_by_chunk[job.chunk_id] = job
    return tuple(jobs_by_chunk[chunk_id] for chunk_id in sorted(jobs_by_chunk))


def _validate_recreated_qdrant_schema(readiness: VectorCollectionReadiness) -> None:
    if not readiness.exists:
        raise RuntimeError("Recreated Qdrant collection does not exist.")
    if not readiness.dense_vector_present or not readiness.sparse_vector_present:
        raise RuntimeError(
            "Recreated Qdrant collection is missing the required named dense/sparse "
            "vector schema."
        )
    if not readiness.vector_size_compatible:
        raise RuntimeError(
            "Recreated Qdrant collection vector dimensions do not match configuration."
        )
    if not readiness.healthy:
        raise RuntimeError("Recreated Qdrant collection is not healthy.")
    if readiness.points_count != 0:
        raise RuntimeError(
            "Recreated Qdrant collection was expected to be empty before canonical "
            f"repopulation, but contains {readiness.points_count} point(s)."
        )


def _validate_qdrant_rebuild(verification: _QdrantRebuildVerification) -> None:
    before = verification.counts_before
    after = verification.counts_after
    if (after.document_count, after.chunk_count) != (
        before.document_count,
        before.chunk_count,
    ):
        raise RuntimeError(
            "Canonical PostgreSQL document/chunk counts changed during Qdrant rebuild: "
            f"before={before.document_count}/{before.chunk_count}, "
            f"after={after.document_count}/{after.chunk_count}."
        )
    if verification.failed_jobs:
        raise RuntimeError(
            "Qdrant rebuild did not complete all canonical embedding jobs: "
            f"{verification.failed_jobs} failure(s)."
        )
    readiness = verification.readiness
    if not readiness.exists or not readiness.healthy:
        raise RuntimeError("Rebuilt Qdrant collection is unavailable or unhealthy.")
    if not readiness.dense_vector_present or not readiness.sparse_vector_present:
        raise RuntimeError(
            "Rebuilt Qdrant collection does not use the required named dense/sparse "
            "vector schema."
        )
    if not readiness.vector_size_compatible:
        raise RuntimeError(
            "Rebuilt Qdrant collection vector dimensions do not match configuration."
        )
    expected_points = before.chunk_count
    if readiness.points_count != expected_points:
        raise RuntimeError(
            f"Rebuilt Qdrant collection contains {readiness.points_count} point(s); "
            f"expected {expected_points} canonical chunk point(s)."
        )


def _qdrant_rebuild_details(
    preflight: _QdrantRebuildPreflight,
) -> tuple[RagOperationDetail, ...]:
    readiness = preflight.readiness
    schema_state = (
        "compatible"
        if (
            readiness.exists
            and readiness.healthy
            and readiness.dense_vector_present
            and readiness.sparse_vector_present
            and readiness.vector_size_compatible
        )
        else "missing_or_incompatible"
    )
    return (
        RagOperationDetail("projection", RAG_PROJECTION_QDRANT),
        RagOperationDetail("collection_name", readiness.collection_name),
        RagOperationDetail("collection_exists", str(readiness.exists)),
        RagOperationDetail("schema_state", schema_state),
        RagOperationDetail("documents_before", str(preflight.counts.document_count)),
        RagOperationDetail("chunks_before", str(preflight.counts.chunk_count)),
        RagOperationDetail("expected_point_count", str(preflight.counts.chunk_count)),
        RagOperationDetail("requeue_source_jobs", str(len(preflight.source_jobs))),
        RagOperationDetail("source_of_truth", "postgresql"),
    )


def _qdrant_rebuild_dry_run_result(
    preflight: _QdrantRebuildPreflight,
) -> RagOperationResult:
    readiness = preflight.readiness
    if not readiness.exists:
        remediation = "The configured collection is absent and will be created."
    elif not readiness.dense_vector_present or not readiness.sparse_vector_present:
        remediation = (
            "The collection uses a legacy or incomplete vector schema and requires "
            "explicit projection recreation."
        )
    elif not readiness.vector_size_compatible:
        remediation = (
            "The collection vector dimensions are incompatible and require explicit "
            "projection recreation."
        )
    else:
        remediation = "The existing compatible projection will be explicitly recreated."
    return RagOperationResult.succeeded(
        operation="rag.rebuild_projection",
        message=(
            "Qdrant rebuild preflight complete; no projection data was changed. "
            f"{remediation} Pass --confirm-delete to recreate and repopulate only "
            f"collection '{readiness.collection_name}' from PostgreSQL."
        ),
        dry_run=True,
        details=_qdrant_rebuild_details(preflight),
    )


def _qdrant_rebuild_verification_details(
    verification: _QdrantRebuildVerification,
) -> tuple[RagOperationDetail, ...]:
    before = verification.counts_before
    after = verification.counts_after
    readiness = verification.readiness
    return (
        RagOperationDetail("projection", RAG_PROJECTION_QDRANT),
        RagOperationDetail("collection_name", readiness.collection_name),
        RagOperationDetail("collection_status", readiness.status or "unknown"),
        RagOperationDetail("documents_before", str(before.document_count)),
        RagOperationDetail("documents_after", str(after.document_count)),
        RagOperationDetail("chunks_before", str(before.chunk_count)),
        RagOperationDetail("chunks_after", str(after.chunk_count)),
        RagOperationDetail(
            "requeued_embedding_jobs", str(len(verification.requeued_jobs))
        ),
        RagOperationDetail(
            "completed_embedding_jobs", str(verification.completed_jobs)
        ),
        RagOperationDetail("failed_embedding_jobs", str(verification.failed_jobs)),
        RagOperationDetail("expected_point_count", str(before.chunk_count)),
        RagOperationDetail("actual_point_count", str(readiness.points_count)),
        RagOperationDetail("named_dense_vector", str(readiness.dense_vector_present)),
        RagOperationDetail("named_sparse_vector", str(readiness.sparse_vector_present)),
        RagOperationDetail(
            "vector_size_compatible", str(readiness.vector_size_compatible)
        ),
        RagOperationDetail("source_of_truth", "postgresql"),
    )


def _rebuild_dry_run_result(projection: str) -> RagOperationResult:
    return RagOperationResult.succeeded(
        operation="rag.rebuild_projection",
        message=(
            f"Dry run complete; projection '{projection}' was not deleted or rebuilt. "
            "Pass --confirm-delete to execute destructive projection cleanup."
        ),
        dry_run=True,
        details=(
            RagOperationDetail("projection", projection),
            RagOperationDetail("source_of_truth", "postgresql"),
        ),
    )
