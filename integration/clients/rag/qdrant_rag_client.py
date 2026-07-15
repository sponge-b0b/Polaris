from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Protocol
from typing import cast
from uuid import NAMESPACE_URL
from uuid import uuid5

from qdrant_client import AsyncQdrantClient
from qdrant_client import models

from config.settings import Settings
from core.storage.persistence.rag import JsonObject

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"


@dataclass(
    frozen=True,
    slots=True,
)
class QdrantUpsertPoint:
    point_id: str
    dense_vector: tuple[float, ...]
    sparse_indices: tuple[int, ...]
    sparse_values: tuple[float, ...]
    payload: JsonObject


@dataclass(
    frozen=True,
    slots=True,
)
class QdrantSearchQuery:
    dense_vector: tuple[float, ...]
    sparse_indices: tuple[int, ...]
    sparse_values: tuple[float, ...]
    limit: int
    filters: JsonObject


@dataclass(
    frozen=True,
    slots=True,
)
class QdrantSearchHit:
    point_id: str
    score: float
    payload: JsonObject


@dataclass(
    frozen=True,
    slots=True,
)
class QdrantCollectionReadiness:
    collection_name: str
    exists: bool
    status: str | None
    healthy: bool
    dense_vector_present: bool
    sparse_vector_present: bool
    configured_vector_size: int
    actual_vector_size: int | None
    vector_size_compatible: bool
    points_count: int = 0


@dataclass(
    frozen=True,
    slots=True,
)
class QdrantCollectionStatus:
    collection_name: str
    vector_size: int
    status: str
    healthy: bool
    points_count: int = 0
    created: bool = False


class QdrantClientProtocol(Protocol):
    async def collection_exists(
        self,
        collection_name: str,
    ) -> bool: ...

    async def create_collection(
        self,
        collection_name: str,
        vectors_config: dict[str, models.VectorParams],
        sparse_vectors_config: dict[str, models.SparseVectorParams],
    ) -> bool: ...

    async def delete_collection(
        self,
        collection_name: str,
    ) -> bool: ...

    async def get_collection(
        self,
        collection_name: str,
    ) -> object: ...

    async def upsert(
        self,
        *,
        collection_name: str,
        points: list[models.PointStruct],
    ) -> object: ...

    async def query_points(
        self,
        *,
        collection_name: str,
        prefetch: list[models.Prefetch],
        query: models.FusionQuery,
        limit: int,
        query_filter: models.Filter | None = None,
        with_payload: bool = True,
    ) -> object: ...

    async def close(
        self,
    ) -> None: ...


class QdrantRagClient:
    """
    Vendor-specific Qdrant client wrapper for RAG vector projections.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        client: QdrantClientProtocol | None = None,
    ) -> None:
        self._client: QdrantClientProtocol = client or cast(
            QdrantClientProtocol,
            AsyncQdrantClient(
                url=settings.qdrant_url,
            ),
        )

    async def inspect_collection(
        self,
        *,
        collection_name: str,
        vector_size: int,
    ) -> QdrantCollectionReadiness:
        _validate_collection_request(
            collection_name=collection_name,
            vector_size=vector_size,
        )
        if not await self._client.collection_exists(collection_name):
            return QdrantCollectionReadiness(
                collection_name=collection_name,
                exists=False,
                status=None,
                healthy=False,
                dense_vector_present=False,
                sparse_vector_present=False,
                configured_vector_size=vector_size,
                actual_vector_size=None,
                vector_size_compatible=False,
            )
        collection = await self._client.get_collection(collection_name)
        dense_present, sparse_present, actual_size = _collection_schema(collection)
        status = _collection_status(collection)
        return QdrantCollectionReadiness(
            collection_name=collection_name,
            exists=True,
            status=status,
            healthy=status == models.CollectionStatus.GREEN.value,
            dense_vector_present=dense_present,
            sparse_vector_present=sparse_present,
            configured_vector_size=vector_size,
            actual_vector_size=actual_size,
            vector_size_compatible=actual_size == vector_size,
            points_count=_collection_points_count(collection),
        )

    async def ensure_collection(
        self,
        *,
        collection_name: str,
        vector_size: int,
    ) -> QdrantCollectionStatus:
        _validate_collection_request(
            collection_name=collection_name,
            vector_size=vector_size,
        )
        created = False
        if not await self._client.collection_exists(collection_name):
            await self._client.create_collection(
                collection_name,
                vectors_config={
                    DENSE_VECTOR_NAME: models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE,
                    )
                },
                sparse_vectors_config={SPARSE_VECTOR_NAME: models.SparseVectorParams()},
            )
            created = True
        return await self._validated_collection_status(
            collection_name=collection_name,
            expected_vector_size=vector_size,
            created=created,
        )

    async def recreate_collection(
        self,
        *,
        collection_name: str,
        vector_size: int,
    ) -> QdrantCollectionStatus:
        _validate_collection_request(
            collection_name=collection_name,
            vector_size=vector_size,
        )
        if await self._client.collection_exists(collection_name):
            await self._client.delete_collection(collection_name)
        await self._client.create_collection(
            collection_name,
            vectors_config={
                DENSE_VECTOR_NAME: models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE,
                )
            },
            sparse_vectors_config={SPARSE_VECTOR_NAME: models.SparseVectorParams()},
        )
        return await self._validated_collection_status(
            collection_name=collection_name,
            expected_vector_size=vector_size,
            created=True,
        )

    async def _validated_collection_status(
        self,
        *,
        collection_name: str,
        expected_vector_size: int,
        created: bool,
    ) -> QdrantCollectionStatus:
        collection = await self._client.get_collection(collection_name)
        actual_vector_size = _collection_vector_size(collection)
        if actual_vector_size != expected_vector_size:
            raise ValueError(
                f"Qdrant collection '{collection_name}' vector size "
                f"{actual_vector_size} does not match expected size "
                f"{expected_vector_size}."
            )
        status = _collection_status(collection)
        healthy = status == models.CollectionStatus.GREEN.value
        if not healthy:
            raise RuntimeError(
                f"Qdrant collection '{collection_name}' is not healthy: {status}."
            )
        return QdrantCollectionStatus(
            collection_name=collection_name,
            vector_size=actual_vector_size,
            status=status,
            healthy=True,
            points_count=_collection_points_count(collection),
            created=created,
        )

    async def upsert_points(
        self,
        *,
        collection_name: str,
        points: tuple[QdrantUpsertPoint, ...],
    ) -> int:
        if not points:
            return 0

        await self._client.upsert(
            collection_name=collection_name,
            points=[
                models.PointStruct(
                    id=_qdrant_point_id(point.point_id),
                    vector={
                        DENSE_VECTOR_NAME: list(point.dense_vector),
                        SPARSE_VECTOR_NAME: models.SparseVector(
                            indices=list(point.sparse_indices),
                            values=list(point.sparse_values),
                        ),
                    },
                    payload=_upsert_payload(point),
                )
                for point in points
            ],
        )
        return len(
            points,
        )

    async def close(
        self,
    ) -> None:
        await self._client.close()

    async def search(
        self,
        *,
        collection_name: str,
        query: QdrantSearchQuery,
    ) -> tuple[QdrantSearchHit, ...]:
        response = await self._client.query_points(
            collection_name=collection_name,
            prefetch=[
                models.Prefetch(
                    query=list(query.dense_vector),
                    using=DENSE_VECTOR_NAME,
                    limit=query.limit,
                ),
                models.Prefetch(
                    query=models.SparseVector(
                        indices=list(query.sparse_indices),
                        values=list(query.sparse_values),
                    ),
                    using=SPARSE_VECTOR_NAME,
                    limit=query.limit,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=query.limit,
            query_filter=_build_filter(
                query.filters,
            ),
            with_payload=True,
        )
        hits = getattr(response, "points", ())
        return tuple(_search_hit_from_qdrant(hit) for hit in hits)


def _build_filter(
    filters: JsonObject,
) -> models.Filter | None:
    must: list[models.FieldCondition] = []
    for key, value in filters.items():
        if value is None:
            continue
        must.append(
            models.FieldCondition(
                key=key,
                match=models.MatchValue(
                    value=cast(
                        Any,
                        value,
                    ),
                ),
            )
        )

    if not must:
        return None

    return models.Filter(
        must=cast(
            Any,
            must,
        ),
    )


def _search_hit_from_qdrant(
    hit: object,
) -> QdrantSearchHit:
    payload = _payload_from_qdrant(
        getattr(
            hit,
            "payload",
            {},
        )
    )
    return QdrantSearchHit(
        point_id=_canonical_point_id(
            qdrant_point_id=str(
                getattr(
                    hit,
                    "id",
                )
            ),
            payload=payload,
        ),
        score=float(
            getattr(
                hit,
                "score",
            )
        ),
        payload=payload,
    )


def _qdrant_point_id(
    canonical_point_id: str,
) -> str:
    return str(
        uuid5(
            NAMESPACE_URL,
            f"polaris:qdrant-point:{canonical_point_id}",
        )
    )


def _upsert_payload(
    point: QdrantUpsertPoint,
) -> dict[str, Any]:
    payload = dict(point.payload)
    payload.setdefault(
        "point_id",
        point.point_id,
    )
    payload.setdefault(
        "chunk_id",
        point.point_id,
    )
    return payload


def _canonical_point_id(
    *,
    qdrant_point_id: str,
    payload: JsonObject,
) -> str:
    for key in (
        "chunk_id",
        "point_id",
    ):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return qdrant_point_id


def _payload_from_qdrant(
    value: object,
) -> JsonObject:
    if not isinstance(
        value,
        dict,
    ):
        return {}
    return value


def _validate_collection_request(
    *,
    collection_name: str,
    vector_size: int,
) -> None:
    if not collection_name.strip():
        raise ValueError("collection_name cannot be empty.")
    if vector_size <= 0:
        raise ValueError("vector_size must be positive.")


def _collection_vector_size(
    collection: object,
) -> int:
    dense_present, sparse_present, size = _collection_schema(collection)
    if not dense_present:
        raise TypeError(
            "Qdrant collection is missing its named dense vector. "
            "Explicit projection rebuild is required."
        )
    if not sparse_present:
        raise TypeError(
            "Qdrant collection is missing its named sparse vector. "
            "Explicit projection rebuild is required."
        )
    if size is None:
        raise TypeError("Qdrant dense vector size is missing.")
    return size


def _collection_schema(
    collection: object,
) -> tuple[bool, bool, int | None]:
    config = getattr(collection, "config", None)
    params = getattr(config, "params", None)
    vectors = getattr(params, "vectors", None)
    sparse_vectors = getattr(params, "sparse_vectors", None)
    dense_present = isinstance(vectors, dict) and DENSE_VECTOR_NAME in vectors
    sparse_present = (
        isinstance(sparse_vectors, dict) and SPARSE_VECTOR_NAME in sparse_vectors
    )
    size = None
    if dense_present:
        candidate = getattr(vectors[DENSE_VECTOR_NAME], "size", None)
        if isinstance(candidate, int):
            size = candidate
    return dense_present, sparse_present, size


def _collection_status(
    collection: object,
) -> str:
    status = getattr(collection, "status", None)
    value = getattr(status, "value", status)
    if not isinstance(value, str) or not value:
        raise TypeError("Qdrant collection status is missing.")
    return value


def _collection_points_count(
    collection: object,
) -> int:
    value = getattr(collection, "points_count", 0)
    return value if isinstance(value, int) else 0
