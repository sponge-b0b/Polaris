from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from core.storage.persistence.lineage.lineage_persistence_models import (
    PersistenceLineageLinkRecord,
    PersistenceLineageLinkResult,
    PersistenceRecordIdentity,
)
from core.storage.persistence.lineage.lineage_traversal_models import (
    DEFAULT_LINEAGE_TRAVERSAL_DEPTH,
    DEFAULT_LINEAGE_TRAVERSAL_EDGE_LIMIT,
    PersistenceLineageTraversalRequest,
    PersistenceLineageTraversalResult,
)


class PersistenceLineageLinkRepository(Protocol):
    """
    Async repository contract for durable cross-record persistence lineage.
    """

    async def persist_lineage_link(
        self,
        link: PersistenceLineageLinkRecord,
    ) -> PersistenceLineageLinkResult: ...

    async def get_lineage_link(
        self,
        link_id: str,
    ) -> PersistenceLineageLinkRecord | None: ...

    async def list_links_for_source(
        self,
        source_record: PersistenceRecordIdentity,
    ) -> Sequence[PersistenceLineageLinkRecord]: ...

    async def list_links_for_target(
        self,
        target_record: PersistenceRecordIdentity,
    ) -> Sequence[PersistenceLineageLinkRecord]: ...

    async def traverse_lineage(
        self,
        request: PersistenceLineageTraversalRequest,
    ) -> PersistenceLineageTraversalResult: ...

    async def traverse_upstream_lineage(
        self,
        root_record: PersistenceRecordIdentity,
        *,
        max_depth: int = DEFAULT_LINEAGE_TRAVERSAL_DEPTH,
        max_edges: int = DEFAULT_LINEAGE_TRAVERSAL_EDGE_LIMIT,
        relationship_types: tuple[str, ...] = (),
    ) -> PersistenceLineageTraversalResult: ...

    async def traverse_downstream_lineage(
        self,
        root_record: PersistenceRecordIdentity,
        *,
        max_depth: int = DEFAULT_LINEAGE_TRAVERSAL_DEPTH,
        max_edges: int = DEFAULT_LINEAGE_TRAVERSAL_EDGE_LIMIT,
        relationship_types: tuple[str, ...] = (),
    ) -> PersistenceLineageTraversalResult: ...
