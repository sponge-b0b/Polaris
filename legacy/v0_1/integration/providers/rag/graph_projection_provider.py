from __future__ import annotations

from typing import Protocol

from integration.providers.rag.graph_projection_models import (
    GraphProjection,
    GraphSearchQuery,
    GraphSearchResult,
    GraphStoreStatus,
)


class GraphProjectionProvider(Protocol):
    async def upsert_projection(self, projection: GraphProjection) -> None: ...

    async def search(
        self,
        query: GraphSearchQuery,
    ) -> tuple[GraphSearchResult, ...]: ...

    async def clear_projection(self) -> int: ...

    async def status(self) -> GraphStoreStatus: ...
