from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from time import perf_counter

from config.settings import DEFAULT_QDRANT_COLLECTION, DEFAULT_VECTOR_SIZE
from core.storage.persistence.rag import (
    RagChunkRecord,
    RagEmbeddingJobRecord,
    RagPersistenceRepository,
)
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from integration.providers.rag.embedding_provider import (
    EmbeddingInput,
    EmbeddingProvider,
    EmbeddingRequest,
    EmbeddingVector,
)
from integration.providers.rag.vector_index_models import vector_point_from_chunk
from integration.providers.rag.vector_index_provider import (
    VectorCollectionLifecycleProvider,
    VectorIndexProvider,
)

logger = logging.getLogger(__name__)

QUEUED_STATUS = "queued"
PROCESSING_STATUS = "processing"
COMPLETED_STATUS = "completed"
FAILED_STATUS = "failed"


@dataclass(
    frozen=True,
    slots=True,
)
class EmbeddingJobProcessorConfig:
    """
    Runtime controls for projecting queued RAG chunks into a vector index.
    """

    collection_name: str = DEFAULT_QDRANT_COLLECTION
    vector_size: int = DEFAULT_VECTOR_SIZE
    batch_size: int = 25
    max_attempts: int = 3

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.collection_name,
            "collection_name",
        )
        if self.vector_size <= 0:
            raise ValueError("vector_size must be positive.")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive.")
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be positive.")


@dataclass(
    frozen=True,
    slots=True,
)
class EmbeddingJobProcessingOutcome:
    """
    Typed outcome for one embedding projection job.
    """

    job_id: str
    status: str
    attempts: int
    chunk_id: str | None = None
    vector_dimensions: int | None = None
    upserted_points: int = 0
    error: str | None = None

    @property
    def completed(
        self,
    ) -> bool:
        return self.status == COMPLETED_STATUS

    @property
    def retryable_failure(
        self,
    ) -> bool:
        return self.status == QUEUED_STATUS and self.error is not None

    @property
    def terminal_failure(
        self,
    ) -> bool:
        return self.status == FAILED_STATUS


@dataclass(
    frozen=True,
    slots=True,
)
class EmbeddingJobProcessorResult:
    """
    Typed batch result returned by the embedding job processor.
    """

    outcomes: tuple[EmbeddingJobProcessingOutcome, ...]

    @property
    def processed_count(
        self,
    ) -> int:
        return len(
            self.outcomes,
        )

    @property
    def completed_count(
        self,
    ) -> int:
        return sum(1 for outcome in self.outcomes if outcome.completed)

    @property
    def retryable_failure_count(
        self,
    ) -> int:
        return sum(1 for outcome in self.outcomes if outcome.retryable_failure)

    @property
    def terminal_failure_count(
        self,
    ) -> int:
        return sum(1 for outcome in self.outcomes if outcome.terminal_failure)

    @property
    def retryable_job_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            outcome.job_id for outcome in self.outcomes if outcome.retryable_failure
        )

    @property
    def terminal_failure_job_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            outcome.job_id for outcome in self.outcomes if outcome.terminal_failure
        )

    @property
    def failure_summaries(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            f"{outcome.job_id}: {outcome.error}"
            for outcome in self.outcomes
            if outcome.error is not None
        )


class EmbeddingJobProcessor:
    """
    Processes queued PostgreSQL RAG embedding jobs into Qdrant projections.

    PostgreSQL remains the system-of-record. This processor reads queued jobs and
    persisted chunk text from PostgreSQL, requests embeddings through the
    platform embedding provider, writes vectors through the vector index provider,
    and records lifecycle state back to PostgreSQL.
    """

    def __init__(
        self,
        *,
        repository: RagPersistenceRepository,
        embedding_provider: EmbeddingProvider,
        vector_index_provider: VectorIndexProvider,
        collection_lifecycle_provider: VectorCollectionLifecycleProvider | None = None,
        telemetry: ApplicationRagTelemetry | None = None,
        config: EmbeddingJobProcessorConfig | None = None,
    ) -> None:
        self._repository = repository
        self._embedding_provider = embedding_provider
        self._vector_index_provider = vector_index_provider
        self._collection_lifecycle_provider = collection_lifecycle_provider
        self._telemetry = telemetry
        self._config = config or EmbeddingJobProcessorConfig()

    async def process_queued_jobs(
        self,
        *,
        batch_size: int | None = None,
    ) -> EmbeddingJobProcessorResult:
        effective_batch_size = batch_size or self._config.batch_size
        if effective_batch_size <= 0:
            raise ValueError("batch_size must be positive.")
        started_at = perf_counter()
        await self._emit_started(
            batch_size=effective_batch_size,
        )
        try:
            jobs = tuple(
                await self._repository.list_embedding_jobs(
                    status=QUEUED_STATUS,
                )
            )[:effective_batch_size]
            if jobs and self._collection_lifecycle_provider is not None:
                await self._collection_lifecycle_provider.ensure_collection(
                    collection_name=self._config.collection_name,
                    vector_size=self._config.vector_size,
                )
            outcomes = tuple([await self.process_job(job) for job in jobs])
        except Exception as exc:
            await self._emit_failed(
                error=exc,
                duration_seconds=perf_counter() - started_at,
            )
            raise

        result = EmbeddingJobProcessorResult(
            outcomes=outcomes,
        )
        await self._emit_completed(
            result=result,
            duration_seconds=perf_counter() - started_at,
        )
        return result

    async def process_job(
        self,
        job: RagEmbeddingJobRecord,
    ) -> EmbeddingJobProcessingOutcome:
        started_at = perf_counter()
        await self._emit_job_started(
            job,
        )
        started_job = replace(
            job,
            status=PROCESSING_STATUS,
            started_at=_utc_now(),
            completed_at=None,
            attempts=job.attempts + 1,
            error=None,
        )
        persist_result = await self._repository.persist_embedding_job(
            started_job,
        )
        if not persist_result.success:
            raise RuntimeError(
                persist_result.error or "Failed to mark embedding job as processing."
            )

        try:
            chunk = await self._load_chunk(
                started_job,
            )
            embedding = await self._embed_chunk(
                job=started_job,
                chunk=chunk,
            )
            if embedding.dimensions != self._config.vector_size:
                raise ValueError(
                    f"Embedding vector size {embedding.dimensions} does not match "
                    f"configured size {self._config.vector_size}."
                )
            point = vector_point_from_chunk(
                chunk,
                dense_vector=embedding.dense_vector,
                sparse_vector=embedding.sparse_vector,
            )
            upserted_points = await self._vector_index_provider.upsert_points(
                collection_name=self._config.collection_name,
                points=(point,),
            )
        except Exception as exc:
            outcome = await self._record_failure(
                job=started_job,
                error=exc,
            )
            await self._emit_job_failed(
                outcome=outcome,
                error=exc,
                duration_seconds=perf_counter() - started_at,
            )
            return outcome

        completed_job = replace(
            started_job,
            status=COMPLETED_STATUS,
            completed_at=_utc_now(),
            error=None,
            metadata={
                **dict(started_job.metadata),
                "collection_name": self._config.collection_name,
                "dense_vector_dimensions": embedding.dimensions,
                "sparse_vector_dimensions": len(embedding.sparse_vector.indices),
                "upserted_points": upserted_points,
            },
        )
        await self._persist_job_or_raise(
            completed_job,
        )
        logger.info(
            "RAG embedding job completed: %s",
            completed_job.job_id,
        )
        outcome = EmbeddingJobProcessingOutcome(
            job_id=completed_job.job_id,
            chunk_id=completed_job.chunk_id,
            status=completed_job.status,
            attempts=completed_job.attempts,
            vector_dimensions=embedding.dimensions,
            upserted_points=upserted_points,
        )
        await self._emit_job_completed(
            outcome=outcome,
            duration_seconds=perf_counter() - started_at,
        )
        return outcome

    async def _load_chunk(
        self,
        job: RagEmbeddingJobRecord,
    ) -> RagChunkRecord:
        if job.chunk_id is None:
            raise ValueError("embedding job chunk_id cannot be empty.")

        chunk = await self._repository.get_chunk(
            job.chunk_id,
        )
        if chunk is None:
            raise LookupError(f"RAG chunk not found for embedding job: {job.chunk_id}")

        return chunk

    async def _embed_chunk(
        self,
        *,
        job: RagEmbeddingJobRecord,
        chunk: RagChunkRecord,
    ) -> EmbeddingVector:
        embeddings = await self._embedding_provider.embed_texts(
            EmbeddingRequest(
                model=job.embedding_model,
                inputs=(
                    EmbeddingInput(
                        text_id=chunk.chunk_id,
                        text=chunk.chunk_text,
                        metadata=chunk.metadata,
                    ),
                ),
            )
        )
        for embedding in embeddings:
            if embedding.text_id == chunk.chunk_id:
                return embedding

        raise LookupError(
            f"Embedding provider did not return vector for {chunk.chunk_id}."
        )

    async def _record_failure(
        self,
        *,
        job: RagEmbeddingJobRecord,
        error: Exception,
    ) -> EmbeddingJobProcessingOutcome:
        terminal = job.attempts >= self._config.max_attempts
        status = FAILED_STATUS if terminal else QUEUED_STATUS
        failed_job = replace(
            job,
            status=status,
            completed_at=_utc_now() if terminal else None,
            error=str(error),
            metadata={
                **dict(job.metadata),
                "collection_name": self._config.collection_name,
                "last_failure_type": type(error).__name__,
            },
        )
        await self._persist_job_or_raise(
            failed_job,
        )
        return EmbeddingJobProcessingOutcome(
            job_id=failed_job.job_id,
            chunk_id=failed_job.chunk_id,
            status=failed_job.status,
            attempts=failed_job.attempts,
            error=failed_job.error,
        )

    async def _persist_job_or_raise(
        self,
        job: RagEmbeddingJobRecord,
    ) -> None:
        persist_result = await self._repository.persist_embedding_job(
            job,
        )
        if not persist_result.success:
            raise RuntimeError(
                persist_result.error or "Failed to persist embedding job state."
            )

    async def _emit_started(
        self,
        *,
        batch_size: int,
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_started(
            "EmbeddingJobProcessor",
            "rag.embedding_jobs.process",
            attributes={
                "collection_name": self._config.collection_name,
                "vector_size": self._config.vector_size,
                "batch_size": batch_size,
                "max_attempts": self._config.max_attempts,
            },
        )

    async def _emit_completed(
        self,
        *,
        result: EmbeddingJobProcessorResult,
        duration_seconds: float,
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_completed(
            "EmbeddingJobProcessor",
            "rag.embedding_jobs.process",
            duration_seconds=duration_seconds,
            attributes={
                "processed_count": result.processed_count,
                "completed_count": result.completed_count,
                "retryable_failure_count": result.retryable_failure_count,
                "terminal_failure_count": result.terminal_failure_count,
                "retryable_job_ids": ",".join(result.retryable_job_ids),
                "terminal_failure_job_ids": ",".join(result.terminal_failure_job_ids),
                "failure_summaries": " | ".join(result.failure_summaries),
            },
        )

    async def _emit_failed(
        self,
        *,
        error: Exception,
        duration_seconds: float,
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_failed(
            "EmbeddingJobProcessor",
            "rag.embedding_jobs.process",
            error=error,
            duration_seconds=duration_seconds,
        )

    async def _emit_job_started(
        self,
        job: RagEmbeddingJobRecord,
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_started(
            "EmbeddingJobProcessor",
            "rag.embedding.job",
            correlation_id=job.job_id,
            attributes={
                "job_id": job.job_id,
                "chunk_id": job.chunk_id,
                "document_id": job.document_id,
                "target_store": job.target_store,
                "embedding_model": job.embedding_model,
                "attempts": job.attempts,
                "collection_name": self._config.collection_name,
            },
        )

    async def _emit_job_completed(
        self,
        *,
        outcome: EmbeddingJobProcessingOutcome,
        duration_seconds: float,
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_completed(
            "EmbeddingJobProcessor",
            "rag.embedding.job",
            duration_seconds=duration_seconds,
            correlation_id=outcome.job_id,
            attributes={
                "job_id": outcome.job_id,
                "chunk_id": outcome.chunk_id,
                "status": outcome.status,
                "attempts": outcome.attempts,
                "vector_dimensions": outcome.vector_dimensions,
                "upserted_points": outcome.upserted_points,
                "collection_name": self._config.collection_name,
            },
        )

    async def _emit_job_failed(
        self,
        *,
        outcome: EmbeddingJobProcessingOutcome,
        error: Exception,
        duration_seconds: float,
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_failed(
            "EmbeddingJobProcessor",
            "rag.embedding.job",
            error=error,
            duration_seconds=duration_seconds,
            correlation_id=outcome.job_id,
            attributes={
                "job_id": outcome.job_id,
                "chunk_id": outcome.chunk_id,
                "status": outcome.status,
                "attempts": outcome.attempts,
                "retryable_failure": outcome.retryable_failure,
                "terminal_failure": outcome.terminal_failure,
                "collection_name": self._config.collection_name,
            },
        )


def _utc_now() -> datetime:
    return datetime.now(
        UTC,
    )


def _require_non_empty(
    value: str | None,
    field_name: str,
) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
