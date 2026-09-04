from __future__ import annotations

from typing import Protocol, runtime_checkable

from integration.providers.rag.vector_index_models import (
    VectorCollectionReadiness,
    VectorCollectionStatus,
    VectorIndexPoint,
    VectorSearchQuery,
    VectorSearchResult,
)


@runtime_checkable
class VectorIndexProvider(Protocol):
    """
    Canonical provider interface for vector-store projections.
    """

    async def upsert_points(
        self,
        *,
        collection_name: str,
        points: tuple[VectorIndexPoint, ...],
    ) -> int: ...

    async def search(
        self,
        *,
        collection_name: str,
        query: VectorSearchQuery,
    ) -> tuple[VectorSearchResult, ...]: ...


@runtime_checkable
class VectorCollectionLifecycleProvider(Protocol):
    """Lifecycle and non-mutating inspection contract for vector projections."""

    async def inspect_collection(
        self,
        *,
        collection_name: str,
        vector_size: int,
    ) -> VectorCollectionReadiness: ...

    async def ensure_collection(
        self,
        *,
        collection_name: str,
        vector_size: int,
    ) -> VectorCollectionStatus: ...

    async def recreate_collection(
        self,
        *,
        collection_name: str,
        vector_size: int,
    ) -> VectorCollectionStatus: ...
