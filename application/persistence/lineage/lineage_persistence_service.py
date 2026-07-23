from __future__ import annotations

from collections.abc import Sequence

from application.persistence.query_result_helpers import (
    build_common_query,
    build_list_result,
)
from core.storage.persistence.lineage import (
    DEFAULT_LINEAGE_TRAVERSAL_DEPTH,
    DEFAULT_LINEAGE_TRAVERSAL_EDGE_LIMIT,
    PersistenceLineageLinkRecord,
    PersistenceLineageLinkRepository,
    PersistenceLineageTraversalRequest,
    PersistenceLineageTraversalResult,
    PersistenceRecordIdentity,
)
from core.storage.persistence.query import PersistenceListResult


class LineagePersistenceService:
    """
    Application service for tracing durable persisted-record lineage.

    This service remains a thin typed boundary over the lineage repository
    contract. Traversal stays PostgreSQL/relational through the repository;
    this service does not introduce graph, vector, or RAG abstractions.
    """

    def __init__(
        self,
        repository: PersistenceLineageLinkRepository,
    ) -> None:
        self._repository = repository

    async def trace_lineage(
        self,
        request: PersistenceLineageTraversalRequest,
    ) -> PersistenceLineageTraversalResult:
        return await self._repository.traverse_lineage(
            request,
        )

    async def trace_upstream_lineage(
        self,
        root_record: PersistenceRecordIdentity,
        *,
        max_depth: int = DEFAULT_LINEAGE_TRAVERSAL_DEPTH,
        max_edges: int = DEFAULT_LINEAGE_TRAVERSAL_EDGE_LIMIT,
        relationship_types: tuple[str, ...] = (),
    ) -> PersistenceLineageTraversalResult:
        return await self._repository.traverse_upstream_lineage(
            root_record,
            max_depth=max_depth,
            max_edges=max_edges,
            relationship_types=relationship_types,
        )

    async def trace_downstream_lineage(
        self,
        root_record: PersistenceRecordIdentity,
        *,
        max_depth: int = DEFAULT_LINEAGE_TRAVERSAL_DEPTH,
        max_edges: int = DEFAULT_LINEAGE_TRAVERSAL_EDGE_LIMIT,
        relationship_types: tuple[str, ...] = (),
    ) -> PersistenceLineageTraversalResult:
        return await self._repository.traverse_downstream_lineage(
            root_record,
            max_depth=max_depth,
            max_edges=max_edges,
            relationship_types=relationship_types,
        )

    async def list_links_for_source(
        self,
        source_record: PersistenceRecordIdentity,
    ) -> Sequence[PersistenceLineageLinkRecord]:
        result = await self.list_links_for_source_result(
            source_record,
        )
        return result.records

    async def list_links_for_source_result(
        self,
        source_record: PersistenceRecordIdentity,
    ) -> PersistenceListResult[PersistenceLineageLinkRecord]:
        records = await self._repository.list_links_for_source(
            source_record,
        )
        query = build_common_query(
            record_type="persistence_lineage_link",
            metadata={
                "lineage_query_direction": "downstream",
                "source_record_type": source_record.record_type,
                "source_record_id": source_record.record_id,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_links_for_target(
        self,
        target_record: PersistenceRecordIdentity,
    ) -> Sequence[PersistenceLineageLinkRecord]:
        result = await self.list_links_for_target_result(
            target_record,
        )
        return result.records

    async def list_links_for_target_result(
        self,
        target_record: PersistenceRecordIdentity,
    ) -> PersistenceListResult[PersistenceLineageLinkRecord]:
        records = await self._repository.list_links_for_target(
            target_record,
        )
        query = build_common_query(
            record_type="persistence_lineage_link",
            metadata={
                "lineage_query_direction": "upstream",
                "target_record_type": target_record.record_type,
                "target_record_id": target_record.record_id,
            },
        )
        return build_list_result(
            records,
            query=query,
        )
