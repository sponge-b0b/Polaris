from __future__ import annotations

from typing import Protocol
from typing import Sequence

from core.storage.persistence.rag.rag_persistence_models import JsonObject

from core.storage.persistence.rag.rag_persistence_models import RagAnswerLogRecord
from core.storage.persistence.rag.rag_persistence_models import RagCanonicalRecordCounts
from core.storage.persistence.rag.rag_persistence_models import RagChunkRecord
from core.storage.persistence.rag.rag_persistence_models import RagDocumentRecord
from core.storage.persistence.rag.rag_persistence_models import RagEmbeddingJobRecord
from core.storage.persistence.rag.rag_persistence_models import RagGraphJobRecord
from core.storage.persistence.rag.rag_persistence_models import RagPersistenceResult
from core.storage.persistence.rag.rag_persistence_models import RagQueryLogRecord
from core.storage.persistence.rag.rag_persistence_models import (
    RagRecordPersistenceResult,
)
from core.storage.persistence.rag.rag_persistence_models import (
    RagSourceEligibilityRecord,
)
from core.storage.persistence.rag.rag_persistence_models import (
    RagSourceEligibilityResult,
)


class RagPersistenceRepository(Protocol):
    """
    Async repository contract for durable curated RAG source persistence.
    """

    async def persist_document(
        self,
        document: RagDocumentRecord,
        *,
        chunks: Sequence[RagChunkRecord] = (),
        embedding_jobs: Sequence[RagEmbeddingJobRecord] = (),
    ) -> RagPersistenceResult: ...

    async def get_document(
        self,
        document_id: str,
    ) -> RagDocumentRecord | None: ...

    async def get_canonical_record_counts(
        self,
    ) -> RagCanonicalRecordCounts: ...

    async def list_chunks(
        self,
        document_id: str,
    ) -> Sequence[RagChunkRecord]: ...

    async def get_chunk(
        self,
        chunk_id: str,
    ) -> RagChunkRecord | None: ...

    async def list_chunks_by_metadata(
        self,
        *,
        metadata_filters: JsonObject,
        limit: int | None = None,
    ) -> Sequence[RagChunkRecord]: ...

    async def list_embedding_jobs(
        self,
        *,
        status: str | None = None,
    ) -> Sequence[RagEmbeddingJobRecord]: ...

    async def persist_embedding_job(
        self,
        job: RagEmbeddingJobRecord,
    ) -> RagRecordPersistenceResult: ...

    async def persist_graph_job(
        self,
        job: RagGraphJobRecord,
    ) -> RagRecordPersistenceResult: ...

    async def list_graph_jobs(
        self,
        *,
        status: str | None = None,
    ) -> Sequence[RagGraphJobRecord]: ...

    async def persist_query_log(
        self,
        query: RagQueryLogRecord,
    ) -> RagRecordPersistenceResult: ...

    async def get_query_log(
        self,
        query_id: str,
    ) -> RagQueryLogRecord | None: ...

    async def persist_answer_log(
        self,
        answer: RagAnswerLogRecord,
    ) -> RagRecordPersistenceResult: ...

    async def list_answer_logs(
        self,
        *,
        query_id: str | None = None,
    ) -> Sequence[RagAnswerLogRecord]: ...

    async def mark_source_eligibility(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> RagSourceEligibilityResult: ...

    async def unmark_source_eligibility(
        self,
        *,
        source_table: str,
        source_id: str,
        source_type: str,
    ) -> RagSourceEligibilityResult: ...

    async def get_source_eligibility(
        self,
        *,
        source_table: str,
        source_id: str,
        source_type: str,
    ) -> RagSourceEligibilityRecord | None: ...

    async def list_source_eligibility(
        self,
        *,
        source_table: str | None = None,
        source_id: str | None = None,
        source_type: str | None = None,
        eligible: bool | None = None,
    ) -> Sequence[RagSourceEligibilityRecord]: ...
