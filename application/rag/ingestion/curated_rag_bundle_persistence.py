from __future__ import annotations

from core.storage.persistence.rag import RagPersistenceBundle
from core.storage.persistence.rag import RagPersistenceRepository
from core.storage.persistence.rag import RagPersistenceResult


class CuratedRagBundlePersister:
    """Passes a complete typed ingestion bundle to one repository transaction."""

    def __init__(
        self,
        repository: RagPersistenceRepository,
    ) -> None:
        self._repository = repository

    async def persist(
        self,
        bundle: RagPersistenceBundle,
    ) -> RagPersistenceResult:
        return await self._repository.persist_document(
            bundle.document,
            chunks=bundle.chunks,
            embedding_jobs=bundle.embedding_jobs,
        )
