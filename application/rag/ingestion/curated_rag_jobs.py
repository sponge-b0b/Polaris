from __future__ import annotations

from application.rag.ingestion.curated_rag_models import CuratedRagBuildOptions
from core.storage.persistence.rag import (
    RagChunkRecord,
    RagDocumentRecord,
    RagEmbeddingJobRecord,
    new_rag_embedding_job_id,
)


def build_embedding_jobs(
    *,
    document: RagDocumentRecord,
    chunks: tuple[RagChunkRecord, ...],
    options: CuratedRagBuildOptions,
) -> tuple[RagEmbeddingJobRecord, ...]:
    if not options.queue_embedding_jobs:
        return ()

    queued_at = document.generated_at
    return tuple(
        RagEmbeddingJobRecord(
            job_id=new_rag_embedding_job_id(
                document_id=document.document_id,
                chunk_id=chunk.chunk_id,
                target_store=options.target_store,
                embedding_model=options.embedding_model,
            ),
            document_id=document.document_id,
            chunk_id=chunk.chunk_id,
            target_store=options.target_store,
            embedding_model=options.embedding_model,
            status="queued",
            queued_at=queued_at,
            metadata={
                "source_table": document.source_table,
                "source_id": document.source_id,
                "source_type": document.source_type,
                "rag_builder_version": "1",
            },
        )
        for chunk in chunks
    )
