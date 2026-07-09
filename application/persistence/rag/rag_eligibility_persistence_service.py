from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.query import PersistenceListResult
from core.storage.persistence.rag import RagPersistenceRepository
from core.storage.persistence.rag import RagSourceEligibilityRecord
from core.storage.persistence.rag import RagSourceEligibilityResult

from application.persistence.query_result_helpers import build_common_query
from application.persistence.query_result_helpers import build_list_result


@dataclass(
    frozen=True,
    slots=True,
)
class RagEligibilityPersistenceFilters:
    """
    Typed application-layer filters for RAG source eligibility metadata.

    Eligibility records point at canonical PostgreSQL source records by source
    table, source id, and source type. They do not represent RAG ingestion,
    chunking, embedding jobs, vector writes, or graph writes.
    """

    source_table: str | None = None
    source_id: str | None = None
    source_type: str | None = None
    eligible: bool | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "source_table",
            clean_optional_identifier(
                self.source_table,
                "source_table",
            ),
        )
        object.__setattr__(
            self,
            "source_id",
            clean_optional_identifier(
                self.source_id,
                "source_id",
            ),
        )
        object.__setattr__(
            self,
            "source_type",
            clean_optional_identifier(
                self.source_type,
                "source_type",
            ),
        )


class RagEligibilityPersistenceService:
    """
    Application service for metadata-only RAG eligibility persistence.

    This service marks canonical PostgreSQL source records as eligible or
    ineligible for future RAG source building. It intentionally does not build
    RAG documents, chunks, embeddings, vector-store writes, graph-store writes,
    or ingestion jobs.
    """

    def __init__(
        self,
        repository: RagPersistenceRepository,
    ) -> None:
        self._repository = repository

    async def mark_source_eligibility(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> RagSourceEligibilityResult:
        return await self._repository.mark_source_eligibility(
            eligibility,
        )

    async def unmark_source_eligibility(
        self,
        *,
        source_table: str,
        source_id: str,
        source_type: str,
    ) -> RagSourceEligibilityResult:
        return await self._repository.unmark_source_eligibility(
            source_table=source_table,
            source_id=source_id,
            source_type=source_type,
        )

    async def get_source_eligibility(
        self,
        *,
        source_table: str,
        source_id: str,
        source_type: str,
    ) -> RagSourceEligibilityRecord | None:
        return await self._repository.get_source_eligibility(
            source_table=source_table,
            source_id=source_id,
            source_type=source_type,
        )

    async def list_source_eligibility(
        self,
        filters: RagEligibilityPersistenceFilters | None = None,
    ) -> Sequence[RagSourceEligibilityRecord]:
        result = await self.list_source_eligibility_result(
            filters,
        )
        return result.records

    async def list_source_eligibility_result(
        self,
        filters: RagEligibilityPersistenceFilters | None = None,
    ) -> PersistenceListResult[RagSourceEligibilityRecord]:
        active_filters = filters or RagEligibilityPersistenceFilters()
        records = await self._repository.list_source_eligibility(
            source_table=active_filters.source_table,
            source_id=active_filters.source_id,
            source_type=active_filters.source_type,
            eligible=active_filters.eligible,
        )
        query = build_common_query(
            record_type="rag_source_eligibility",
            metadata={
                "source_table": active_filters.source_table,
                "source_id": active_filters.source_id,
                "source_type": active_filters.source_type,
                "eligible": active_filters.eligible,
            },
        )
        return build_list_result(
            records,
            query=query,
        )
