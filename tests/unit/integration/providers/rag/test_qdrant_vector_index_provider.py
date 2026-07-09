from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import cast

import pytest

from core.storage.persistence.rag import RagChunkRecord
from integration.clients.rag.qdrant_rag_client import QdrantCollectionReadiness
from integration.clients.rag.qdrant_rag_client import QdrantCollectionStatus
from integration.clients.rag.qdrant_rag_client import QdrantRagClient
from integration.clients.rag.qdrant_rag_client import QdrantSearchHit
from integration.clients.rag.qdrant_rag_client import QdrantSearchQuery
from integration.clients.rag.qdrant_rag_client import QdrantUpsertPoint
from integration.providers.rag.qdrant_vector_index_provider import (
    QdrantVectorIndexProvider,
)
from integration.providers.rag.embedding_provider import SparseEmbeddingVector
from integration.providers.rag.vector_index_models import VectorIndexPoint
from integration.providers.rag.vector_index_models import VectorSearchQuery
from integration.providers.rag.vector_index_models import vector_point_from_chunk


class FakeQdrantRagClient:
    def __init__(self) -> None:
        self.lifecycle_calls: list[tuple[str, str, int]] = []
        self.upsert_calls: list[tuple[str, tuple[QdrantUpsertPoint, ...]]] = []
        self.search_calls: list[tuple[str, QdrantSearchQuery]] = []

    async def inspect_collection(
        self, *, collection_name: str, vector_size: int
    ) -> QdrantCollectionReadiness:
        self.lifecycle_calls.append(("inspect", collection_name, vector_size))
        return QdrantCollectionReadiness(
            collection_name=collection_name,
            exists=True,
            status="green",
            healthy=True,
            dense_vector_present=True,
            sparse_vector_present=True,
            configured_vector_size=vector_size,
            actual_vector_size=vector_size,
            vector_size_compatible=True,
            points_count=2,
        )

    async def ensure_collection(
        self, *, collection_name: str, vector_size: int
    ) -> QdrantCollectionStatus:
        self.lifecycle_calls.append(("ensure", collection_name, vector_size))
        return QdrantCollectionStatus(
            collection_name=collection_name,
            vector_size=vector_size,
            status="green",
            healthy=True,
        )

    async def recreate_collection(
        self, *, collection_name: str, vector_size: int
    ) -> QdrantCollectionStatus:
        self.lifecycle_calls.append(("recreate", collection_name, vector_size))
        return QdrantCollectionStatus(
            collection_name=collection_name,
            vector_size=vector_size,
            status="green",
            healthy=True,
            created=True,
        )

    async def upsert_points(
        self, *, collection_name: str, points: tuple[QdrantUpsertPoint, ...]
    ) -> int:
        self.upsert_calls.append((collection_name, points))
        return len(points)

    async def search(
        self, *, collection_name: str, query: QdrantSearchQuery
    ) -> tuple[QdrantSearchHit, ...]:
        self.search_calls.append((collection_name, query))
        return (
            QdrantSearchHit(
                point_id="chunk-1",
                score=0.82,
                payload={"chunk_id": "chunk-1", "symbol": "SPY"},
            ),
        )


@pytest.mark.asyncio
async def test_qdrant_vector_provider_exposes_non_mutating_readiness() -> None:
    fake_client = FakeQdrantRagClient()
    provider = QdrantVectorIndexProvider(client=cast(QdrantRagClient, fake_client))

    readiness = await provider.inspect_collection(
        collection_name="test_chunks", vector_size=3
    )

    assert readiness.vector_size_compatible is True
    assert readiness.points_count == 2
    assert fake_client.lifecycle_calls == [("inspect", "test_chunks", 3)]


@pytest.mark.asyncio
async def test_qdrant_vector_provider_exposes_collection_lifecycle() -> None:
    fake_client = FakeQdrantRagClient()
    provider = QdrantVectorIndexProvider(client=cast(QdrantRagClient, fake_client))

    ensured = await provider.ensure_collection(
        collection_name="test_chunks", vector_size=3
    )
    recreated = await provider.recreate_collection(
        collection_name="test_chunks", vector_size=3
    )

    assert ensured.healthy is True
    assert recreated.created is True
    assert fake_client.lifecycle_calls == [
        ("ensure", "test_chunks", 3),
        ("recreate", "test_chunks", 3),
    ]


@pytest.mark.asyncio
async def test_qdrant_vector_provider_upserts_hybrid_platform_points() -> None:
    fake_client = FakeQdrantRagClient()
    provider = QdrantVectorIndexProvider(client=cast(QdrantRagClient, fake_client))
    sparse = SparseEmbeddingVector(indices=(4, 9), values=(0.8, 0.3))

    count = await provider.upsert_points(
        collection_name="polaris_rag_chunks",
        points=(
            VectorIndexPoint(
                point_id="chunk-1",
                dense_vector=(0.1, 0.2),
                sparse_vector=sparse,
                payload={"chunk_id": "chunk-1"},
            ),
        ),
    )

    assert count == 1
    collection_name, points = fake_client.upsert_calls[0]
    assert collection_name == "polaris_rag_chunks"
    assert points[0] == QdrantUpsertPoint(
        point_id="chunk-1",
        dense_vector=(0.1, 0.2),
        sparse_indices=(4, 9),
        sparse_values=(0.8, 0.3),
        payload={"chunk_id": "chunk-1"},
    )


@pytest.mark.asyncio
async def test_qdrant_vector_provider_search_returns_platform_results() -> None:
    fake_client = FakeQdrantRagClient()
    provider = QdrantVectorIndexProvider(client=cast(QdrantRagClient, fake_client))
    sparse = SparseEmbeddingVector(indices=(2, 7), values=(0.9, 0.4))

    results = await provider.search(
        collection_name="polaris_rag_chunks",
        query=VectorSearchQuery(
            dense_vector=(0.7, 0.8),
            sparse_vector=sparse,
            top_k=4,
            filters={"symbol": "SPY"},
        ),
    )

    assert len(results) == 1
    collection_name, query = fake_client.search_calls[0]
    assert collection_name == "polaris_rag_chunks"
    assert query.dense_vector == (0.7, 0.8)
    assert query.sparse_indices == (2, 7)
    assert query.sparse_values == (0.9, 0.4)
    assert query.limit == 4


def test_vector_point_from_chunk_preserves_chunk_payload_and_vectors() -> None:
    chunk = RagChunkRecord(
        chunk_id="chunk-1",
        document_id="doc-1",
        chunk_index=2,
        chunk_text="SPY breadth improved.",
        token_count=3,
        content_hash="hash-1",
        metadata={
            "source_table": "reports",
            "source_record_id": "report-1",
            "symbol": "SPY",
            "created_at": datetime(2026, 6, 15, tzinfo=timezone.utc).isoformat(),
        },
    )
    sparse = SparseEmbeddingVector(indices=(1,), values=(0.7,))

    point = vector_point_from_chunk(
        chunk, dense_vector=(0.1, 0.2, 0.3), sparse_vector=sparse
    )

    assert point.point_id == "chunk-1"
    assert point.dense_vector == (0.1, 0.2, 0.3)
    assert point.sparse_vector == sparse
    assert point.payload["document_id"] == "doc-1"
    assert point.payload["symbol"] == "SPY"
