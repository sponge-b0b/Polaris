from __future__ import annotations

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.clients.rag.qdrant_rag_client import (
    QdrantRagClient,
    QdrantSearchQuery,
    QdrantUpsertPoint,
)
from integration.providers.provider_telemetry import record_provider_call
from integration.providers.rag.vector_index_models import (
    VectorCollectionReadiness,
    VectorCollectionStatus,
    VectorIndexPoint,
    VectorSearchQuery,
    VectorSearchResult,
)
from integration.providers.rag.vector_index_provider import VectorIndexProvider


class QdrantVectorIndexProvider(VectorIndexProvider):
    """
    Platform-facing vector index provider backed by Qdrant.
    """

    def __init__(
        self,
        client: QdrantRagClient,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:
        self._client = client
        self._telemetry = telemetry

    async def inspect_collection(
        self,
        *,
        collection_name: str,
        vector_size: int,
    ) -> VectorCollectionReadiness:
        status = await record_provider_call(
            self._telemetry,
            self.__class__.__name__,
            "inspect_collection",
            lambda: self._client.inspect_collection(
                collection_name=collection_name,
                vector_size=vector_size,
            ),
        )
        return VectorCollectionReadiness(
            collection_name=status.collection_name,
            exists=status.exists,
            status=status.status,
            healthy=status.healthy,
            dense_vector_present=status.dense_vector_present,
            sparse_vector_present=status.sparse_vector_present,
            configured_vector_size=status.configured_vector_size,
            actual_vector_size=status.actual_vector_size,
            vector_size_compatible=status.vector_size_compatible,
            points_count=status.points_count,
        )

    async def ensure_collection(
        self,
        *,
        collection_name: str,
        vector_size: int,
    ) -> VectorCollectionStatus:
        status = await record_provider_call(
            self._telemetry,
            self.__class__.__name__,
            "ensure_collection",
            lambda: self._client.ensure_collection(
                collection_name=collection_name,
                vector_size=vector_size,
            ),
        )
        return VectorCollectionStatus(
            collection_name=status.collection_name,
            vector_size=status.vector_size,
            status=status.status,
            healthy=status.healthy,
            points_count=status.points_count,
            created=status.created,
        )

    async def recreate_collection(
        self,
        *,
        collection_name: str,
        vector_size: int,
    ) -> VectorCollectionStatus:
        status = await record_provider_call(
            self._telemetry,
            self.__class__.__name__,
            "recreate_collection",
            lambda: self._client.recreate_collection(
                collection_name=collection_name,
                vector_size=vector_size,
            ),
        )
        return VectorCollectionStatus(
            collection_name=status.collection_name,
            vector_size=status.vector_size,
            status=status.status,
            healthy=status.healthy,
            points_count=status.points_count,
            created=status.created,
        )

    async def upsert_points(
        self,
        *,
        collection_name: str,
        points: tuple[VectorIndexPoint, ...],
    ) -> int:
        return await record_provider_call(
            self._telemetry,
            self.__class__.__name__,
            "upsert_points",
            lambda: self._client.upsert_points(
                collection_name=collection_name,
                points=tuple(
                    QdrantUpsertPoint(
                        point_id=point.point_id,
                        dense_vector=point.dense_vector,
                        sparse_indices=point.sparse_vector.indices,
                        sparse_values=point.sparse_vector.values,
                        payload=point.payload,
                    )
                    for point in points
                ),
            ),
        )

    async def search(
        self,
        *,
        collection_name: str,
        query: VectorSearchQuery,
    ) -> tuple[VectorSearchResult, ...]:
        hits = await record_provider_call(
            self._telemetry,
            self.__class__.__name__,
            "search",
            lambda: self._client.search(
                collection_name=collection_name,
                query=QdrantSearchQuery(
                    dense_vector=query.dense_vector,
                    sparse_indices=query.sparse_vector.indices,
                    sparse_values=query.sparse_vector.values,
                    limit=query.top_k,
                    filters=query.filters,
                ),
            ),
        )
        return tuple(
            VectorSearchResult(
                point_id=hit.point_id,
                score=hit.score,
                payload=hit.payload,
            )
            for hit in hits
        )
