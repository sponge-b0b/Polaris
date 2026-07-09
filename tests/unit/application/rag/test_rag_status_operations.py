from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import cast

import pytest

from application.rag.contracts.rag_operation_models import RagProjectionReadinessConfig
from application.rag.contracts.rag_operation_models import RagStatusOperationRequest
from application.rag.operations.rag_status_operations import RagStatusOperationsService
from core.storage.persistence.rag import RagCanonicalRecordCounts
from core.storage.persistence.rag import RagEmbeddingJobRecord
from core.storage.persistence.rag import RagPersistenceRepository
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from core.telemetry.events.telemetry_event import TelemetryEventLevel
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from integration.providers.rag.embedding_provider import EmbeddingProvider
from integration.providers.rag.embedding_provider import EmbeddingRequest
from integration.providers.rag.embedding_provider import EmbeddingVector
from integration.providers.rag.embedding_provider import SparseEmbeddingVector
from integration.providers.rag.graph_projection_models import GraphStoreStatus
from integration.providers.rag.graph_projection_provider import GraphProjectionProvider
from integration.providers.rag.reranking_provider import RerankingProvider
from integration.providers.rag.reranking_provider import RerankRequest
from integration.providers.rag.reranking_provider import RerankResult
from integration.providers.rag.vector_index_models import VectorCollectionReadiness
from integration.providers.rag.vector_index_provider import (
    VectorCollectionLifecycleProvider,
)


class FakeRepository:
    async def get_canonical_record_counts(self) -> RagCanonicalRecordCounts:
        return RagCanonicalRecordCounts(3, 8, 5, 2)

    async def list_embedding_jobs(
        self, *, status: str | None = None
    ) -> tuple[RagEmbeddingJobRecord, ...]:
        jobs = (
            _job("queued-new", "queued", attempts=0),
            _job("queued-retry", "queued", attempts=1),
            _job("processing", "processing", attempts=1),
            _job("failed", "failed", attempts=3),
            _job("completed", "completed", attempts=1),
        )
        return tuple(job for job in jobs if status is None or job.status == status)


class FakeVectorProvider:
    async def inspect_collection(
        self, *, collection_name: str, vector_size: int
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
            points_count=8,
        )


class FakeGraphProvider:
    async def status(self) -> GraphStoreStatus:
        return GraphStoreStatus(healthy=True, entity_count=12)


class FakeEmbeddingProvider:
    async def embed_texts(
        self, request: EmbeddingRequest
    ) -> tuple[EmbeddingVector, ...]:
        return (
            EmbeddingVector(
                text_id=request.inputs[0].text_id,
                dense_vector=(0.1, 0.2, 0.3),
                sparse_vector=SparseEmbeddingVector(indices=(1,), values=(0.5,)),
                model=request.model,
            ),
        )


class FakeRerankingProvider:
    async def rerank(self, request: RerankRequest) -> tuple[RerankResult, ...]:
        return (
            RerankResult(
                candidate_id=request.candidates[0].candidate_id,
                score=0.9,
                rank=1,
            ),
        )


@pytest.mark.asyncio
async def test_status_returns_typed_projection_readiness() -> None:
    service = RagStatusOperationsService(
        rag_repository=cast(RagPersistenceRepository, FakeRepository()),
        vector_provider=cast(VectorCollectionLifecycleProvider, FakeVectorProvider()),
        graph_provider=cast(GraphProjectionProvider, FakeGraphProvider()),
        embedding_provider=cast(EmbeddingProvider, FakeEmbeddingProvider()),
        reranking_provider=cast(RerankingProvider, FakeRerankingProvider()),
        config=RagProjectionReadinessConfig(
            collection_name="test_chunks",
            vector_size=3,
            embedding_model="bge-m3",
            reranker_model="bge-reranker-large",
        ),
    )

    result = await service.status(RagStatusOperationRequest())

    assert result.ready is True
    assert result.canonical.document_count == 3
    assert result.canonical.chunk_count == 8
    assert result.canonical.pending_embedding_jobs == 3
    assert result.canonical.retryable_embedding_jobs == 1
    assert result.canonical.failed_embedding_jobs == 1
    assert result.vector.points_count == 8
    assert result.graph.entity_count == 12
    assert result.embedding.dimensions == 3


class FailingVectorProvider(FakeVectorProvider):
    async def inspect_collection(
        self, *, collection_name: str, vector_size: int
    ) -> VectorCollectionReadiness:
        raise RuntimeError("qdrant unavailable")


@pytest.mark.asyncio
async def test_status_preserves_partial_diagnostics_when_projection_is_unavailable() -> (
    None
):
    service = RagStatusOperationsService(
        rag_repository=cast(RagPersistenceRepository, FakeRepository()),
        vector_provider=cast(
            VectorCollectionLifecycleProvider, FailingVectorProvider()
        ),
        graph_provider=cast(GraphProjectionProvider, FakeGraphProvider()),
        embedding_provider=cast(EmbeddingProvider, FakeEmbeddingProvider()),
        reranking_provider=cast(RerankingProvider, FakeRerankingProvider()),
        config=RagProjectionReadinessConfig(
            collection_name="test_chunks",
            vector_size=3,
            embedding_model="bge-m3",
            reranker_model="bge-reranker-large",
        ),
    )

    result = await service.status(RagStatusOperationRequest())

    assert result.ready is False
    assert result.status == "degraded"
    assert result.canonical.available is True
    assert result.vector.error == "qdrant unavailable"
    assert result.graph.ready is True


def _job(job_id: str, status: str, *, attempts: int) -> RagEmbeddingJobRecord:
    return RagEmbeddingJobRecord(
        job_id=job_id,
        document_id="document-1",
        chunk_id=f"chunk-{job_id}",
        target_store="qdrant",
        embedding_model="bge-m3",
        status=status,
        queued_at=datetime(2026, 1, 1, tzinfo=UTC),
        attempts=attempts,
    )


@pytest.mark.asyncio
async def test_status_emits_canonical_degradation_for_failed_dependency() -> None:
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    service = RagStatusOperationsService(
        rag_repository=cast(RagPersistenceRepository, FakeRepository()),
        vector_provider=cast(
            VectorCollectionLifecycleProvider, FailingVectorProvider()
        ),
        graph_provider=cast(GraphProjectionProvider, FakeGraphProvider()),
        embedding_provider=cast(EmbeddingProvider, FakeEmbeddingProvider()),
        reranking_provider=cast(RerankingProvider, FakeRerankingProvider()),
        config=RagProjectionReadinessConfig(
            collection_name="test_chunks",
            vector_size=3,
            embedding_model="bge-m3",
            reranker_model="bge-reranker-large",
        ),
        telemetry=ApplicationRagTelemetry(observability),
    )

    result = await service.status(RagStatusOperationRequest())

    assert result.status == "degraded"
    assert [event.attributes["operation"] for event in sink.events] == [
        "rag.status",
        "rag.status.qdrant",
        "rag.status",
    ]
    assert sink.events[1].level == TelemetryEventLevel.WARNING
    assert sink.events[1].exception_details is not None
    assert sink.events[1].exception_details.message == "qdrant unavailable"
    assert sink.events[2].event_type == "application.rag.operation.degraded"
    assert sink.events[2].level == TelemetryEventLevel.WARNING
