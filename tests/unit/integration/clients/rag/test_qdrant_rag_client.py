from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest
from qdrant_client import models

from config.settings import Settings
from integration.clients.rag.qdrant_rag_client import (
    DENSE_VECTOR_NAME,
    SPARSE_VECTOR_NAME,
    QdrantClientProtocol,
    QdrantRagClient,
    QdrantSearchQuery,
    QdrantUpsertPoint,
)


@dataclass(frozen=True, slots=True)
class FakeQdrantHit:
    id: str
    score: float
    payload: dict[str, object]


class FakeQdrantClient:
    def __init__(self) -> None:
        self.exists = False
        self.vector_size = 3
        self.status = models.CollectionStatus.GREEN
        self.legacy_unnamed_vectors = False
        self.create_calls: list[
            tuple[
                str,
                dict[str, models.VectorParams],
                dict[str, models.SparseVectorParams],
            ]
        ] = []
        self.delete_calls: list[str] = []
        self.upsert_calls: list[dict[str, object]] = []
        self.query_calls: list[dict[str, object]] = []
        self.query_response_points: list[FakeQdrantHit] | None = None
        self.close_calls = 0

    async def collection_exists(self, collection_name: str) -> bool:
        return self.exists

    async def create_collection(
        self,
        collection_name: str,
        vectors_config: dict[str, models.VectorParams],
        sparse_vectors_config: dict[str, models.SparseVectorParams],
    ) -> bool:
        self.create_calls.append(
            (collection_name, vectors_config, sparse_vectors_config)
        )
        self.exists = True
        self.vector_size = int(vectors_config[DENSE_VECTOR_NAME].size)
        return True

    async def delete_collection(self, collection_name: str) -> bool:
        self.delete_calls.append(collection_name)
        self.exists = False
        return True

    async def get_collection(self, collection_name: str) -> object:
        vectors: object = (
            SimpleNamespace(size=self.vector_size)
            if self.legacy_unnamed_vectors
            else {DENSE_VECTOR_NAME: SimpleNamespace(size=self.vector_size)}
        )
        sparse_vectors = (
            {}
            if self.legacy_unnamed_vectors
            else {SPARSE_VECTOR_NAME: SimpleNamespace()}
        )
        return SimpleNamespace(
            config=SimpleNamespace(
                params=SimpleNamespace(
                    vectors=vectors,
                    sparse_vectors=sparse_vectors,
                )
            ),
            status=self.status,
            points_count=7,
        )

    async def upsert(
        self,
        *,
        collection_name: str,
        points: list[Any],
    ) -> object:
        self.upsert_calls.append({"collection_name": collection_name, "points": points})
        return object()

    async def query_points(
        self,
        *,
        collection_name: str,
        prefetch: list[models.Prefetch],
        query: models.FusionQuery,
        limit: int,
        query_filter: models.Filter | None = None,
        with_payload: bool = True,
    ) -> object:
        self.query_calls.append(
            {
                "collection_name": collection_name,
                "prefetch": prefetch,
                "query": query,
                "limit": limit,
                "query_filter": query_filter,
                "with_payload": with_payload,
            }
        )
        return SimpleNamespace(
            points=self.query_response_points
            or [
                FakeQdrantHit(
                    id="chunk-1",
                    score=0.91,
                    payload={"chunk_id": "chunk-1", "symbol": "SPY"},
                )
            ]
        )

    async def close(
        self,
    ) -> None:
        self.close_calls += 1


@pytest.mark.asyncio
async def test_qdrant_client_closes_wrapped_client() -> None:
    fake_client = FakeQdrantClient()
    client = QdrantRagClient(
        settings=Settings(), client=cast(QdrantClientProtocol, fake_client)
    )

    await client.close()

    assert fake_client.close_calls == 1


@pytest.mark.asyncio
async def test_qdrant_client_upsert_translates_named_dense_and_sparse_vectors() -> None:
    fake_client = FakeQdrantClient()
    client = QdrantRagClient(
        settings=Settings(), client=cast(QdrantClientProtocol, fake_client)
    )

    count = await client.upsert_points(
        collection_name="polaris_rag_chunks",
        points=(
            QdrantUpsertPoint(
                point_id="chunk-1",
                dense_vector=(0.1, 0.2, 0.3),
                sparse_indices=(4, 9),
                sparse_values=(0.8, 0.3),
                payload={"chunk_id": "chunk-1", "symbol": "SPY"},
            ),
        ),
    )

    assert count == 1
    points = fake_client.upsert_calls[0]["points"]
    assert isinstance(points, list)
    point = points[0]
    assert UUID(str(point.id))
    assert point.id != "chunk-1"
    assert point.vector[DENSE_VECTOR_NAME] == [0.1, 0.2, 0.3]
    assert point.vector[SPARSE_VECTOR_NAME] == models.SparseVector(
        indices=[4, 9], values=[0.8, 0.3]
    )
    assert point.payload == {
        "chunk_id": "chunk-1",
        "symbol": "SPY",
        "point_id": "chunk-1",
    }


@pytest.mark.asyncio
async def test_qdrant_client_search_falls_back_to_qdrant_id_without_canonical_payload() -> (  # noqa: E501
    None
):
    fake_client = FakeQdrantClient()
    fake_client.query_response_points = [
        FakeQdrantHit(
            id="0bd837a1-8f17-5943-8f41-6bc621e1d8d7",
            score=0.42,
            payload={"symbol": "SPY"},
        )
    ]
    client = QdrantRagClient(
        settings=Settings(), client=cast(QdrantClientProtocol, fake_client)
    )

    hits = await client.search(
        collection_name="polaris_rag_chunks",
        query=QdrantSearchQuery(
            dense_vector=(0.5, 0.6),
            sparse_indices=(2,),
            sparse_values=(0.9,),
            limit=1,
            filters={},
        ),
    )

    assert hits[0].point_id == "0bd837a1-8f17-5943-8f41-6bc621e1d8d7"


@pytest.mark.asyncio
async def test_qdrant_client_search_uses_rrf_fusion_for_hybrid_vectors() -> None:
    fake_client = FakeQdrantClient()
    client = QdrantRagClient(
        settings=Settings(), client=cast(QdrantClientProtocol, fake_client)
    )

    hits = await client.search(
        collection_name="polaris_rag_chunks",
        query=QdrantSearchQuery(
            dense_vector=(0.5, 0.6),
            sparse_indices=(2, 7),
            sparse_values=(0.9, 0.4),
            limit=3,
            filters={"symbol": "SPY", "source_type": "morning_report"},
        ),
    )

    assert len(hits) == 1
    assert hits[0].point_id == "chunk-1"
    call = fake_client.query_calls[0]
    assert call["collection_name"] == "polaris_rag_chunks"
    prefetch = cast(list[models.Prefetch], call["prefetch"])
    assert prefetch[0].using == DENSE_VECTOR_NAME
    assert prefetch[0].query == [0.5, 0.6]
    assert prefetch[1].using == SPARSE_VECTOR_NAME
    assert prefetch[1].query == models.SparseVector(indices=[2, 7], values=[0.9, 0.4])
    assert call["query"] == models.FusionQuery(fusion=models.Fusion.RRF)
    assert call["limit"] == 3
    assert call["query_filter"] is not None


@pytest.mark.asyncio
async def test_qdrant_client_inspects_collection_without_creating_it() -> None:
    fake_client = FakeQdrantClient()
    client = QdrantRagClient(
        settings=Settings(), client=cast(QdrantClientProtocol, fake_client)
    )

    readiness = await client.inspect_collection(
        collection_name="test_chunks", vector_size=3
    )

    assert readiness.exists is False
    assert readiness.healthy is False
    assert fake_client.create_calls == []


@pytest.mark.asyncio
async def test_qdrant_client_reports_hybrid_schema_compatibility() -> None:
    fake_client = FakeQdrantClient()
    fake_client.exists = True
    client = QdrantRagClient(
        settings=Settings(), client=cast(QdrantClientProtocol, fake_client)
    )

    readiness = await client.inspect_collection(
        collection_name="test_chunks", vector_size=3
    )

    assert readiness.exists is True
    assert readiness.dense_vector_present is True
    assert readiness.sparse_vector_present is True
    assert readiness.vector_size_compatible is True
    assert readiness.points_count == 7


@pytest.mark.asyncio
async def test_qdrant_client_ensures_named_hybrid_collection() -> None:
    fake_client = FakeQdrantClient()
    client = QdrantRagClient(
        settings=Settings(), client=cast(QdrantClientProtocol, fake_client)
    )

    status = await client.ensure_collection(
        collection_name="test_chunks", vector_size=3
    )

    assert status.created is True
    assert status.healthy is True
    _, dense_config, sparse_config = fake_client.create_calls[0]
    assert dense_config[DENSE_VECTOR_NAME].size == 3
    assert dense_config[DENSE_VECTOR_NAME].distance == models.Distance.COSINE
    assert SPARSE_VECTOR_NAME in sparse_config


@pytest.mark.asyncio
async def test_qdrant_client_fails_closed_for_legacy_unnamed_vectors() -> None:
    fake_client = FakeQdrantClient()
    fake_client.exists = True
    fake_client.legacy_unnamed_vectors = True
    client = QdrantRagClient(
        settings=Settings(), client=cast(QdrantClientProtocol, fake_client)
    )

    with pytest.raises(TypeError, match="Explicit projection rebuild is required"):
        await client.ensure_collection(collection_name="test_chunks", vector_size=3)

    assert fake_client.delete_calls == []
    assert fake_client.create_calls == []


@pytest.mark.asyncio
async def test_qdrant_client_rejects_collection_vector_size_mismatch() -> None:
    fake_client = FakeQdrantClient()
    fake_client.exists = True
    fake_client.vector_size = 4
    client = QdrantRagClient(
        settings=Settings(), client=cast(QdrantClientProtocol, fake_client)
    )

    with pytest.raises(ValueError, match="does not match expected size"):
        await client.ensure_collection(collection_name="test_chunks", vector_size=3)


@pytest.mark.asyncio
async def test_qdrant_client_rejects_unhealthy_collection() -> None:
    fake_client = FakeQdrantClient()
    fake_client.exists = True
    fake_client.status = models.CollectionStatus.RED
    client = QdrantRagClient(
        settings=Settings(), client=cast(QdrantClientProtocol, fake_client)
    )

    with pytest.raises(RuntimeError, match="is not healthy: red"):
        await client.ensure_collection(collection_name="test_chunks", vector_size=3)


@pytest.mark.asyncio
async def test_qdrant_client_recreates_existing_collection() -> None:
    fake_client = FakeQdrantClient()
    fake_client.exists = True
    client = QdrantRagClient(
        settings=Settings(), client=cast(QdrantClientProtocol, fake_client)
    )

    status = await client.recreate_collection(
        collection_name="test_chunks", vector_size=3
    )

    assert status.created is True
    assert fake_client.delete_calls == ["test_chunks"]
    assert fake_client.create_calls[0][0] == "test_chunks"
