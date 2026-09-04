from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from core.database.models.rag import (
    RagAnswerLogModel,
    RagChunkModel,
    RagDocumentModel,
    RagEmbeddingJobModel,
    RagGraphJobModel,
    RagQueryLogModel,
    RagSourceEligibilityModel,
)
from core.storage.persistence.rag.rag_persistence_models import (
    JsonObject,
    JsonScalar,
    RagAnswerLogRecord,
    RagCanonicalRecordCounts,
    RagChunkRecord,
    RagDocumentRecord,
    RagEmbeddingJobRecord,
    RagGraphJobRecord,
    RagPersistenceResult,
    RagQueryLogRecord,
    RagRecordPersistenceResult,
    RagSourceEligibilityRecord,
    RagSourceEligibilityResult,
    new_rag_source_eligibility_id,
)
from core.storage.persistence.rag.rag_persistence_repository import (
    RagPersistenceRepository,
)
from core.storage.persistence.serializers.rag_persistence_serializer import (
    RagPersistenceSerializer,
)


class PostgresRagPersistenceRepository(RagPersistenceRepository):
    """
    PostgreSQL adapter for durable curated RAG source persistence.

    Documents, chunks, and embedding jobs are canonical Postgres records. Vector
    stores should be populated from these records, not from raw runtime dumps.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def persist_document(
        self,
        document: RagDocumentRecord,
        *,
        chunks: Sequence[RagChunkRecord] = (),
        embedding_jobs: Sequence[RagEmbeddingJobRecord] = (),
    ) -> RagPersistenceResult:
        try:
            await self._session.execute(
                _upsert_document_statement(
                    document,
                )
            )
            for chunk in chunks:
                await self._session.execute(
                    _upsert_chunk_statement(
                        chunk,
                    )
                )
            for job in embedding_jobs:
                await self._session.execute(
                    _upsert_embedding_job_statement(
                        job,
                    )
                )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return RagPersistenceResult.failed(
                str(exc),
            )

        return RagPersistenceResult.succeeded(
            document_id=document.document_id,
            records_persisted=1
            + len(
                chunks,
            )
            + len(
                embedding_jobs,
            ),
        )

    async def get_canonical_record_counts(
        self,
    ) -> RagCanonicalRecordCounts:
        counts = []
        for model in (
            RagDocumentModel,
            RagChunkModel,
            RagEmbeddingJobModel,
            RagGraphJobModel,
        ):
            result = await self._session.execute(
                select(func.count()).select_from(model)
            )
            counts.append(int(result.scalar_one()))
        return RagCanonicalRecordCounts(
            document_count=counts[0],
            chunk_count=counts[1],
            embedding_job_count=counts[2],
            graph_job_count=counts[3],
        )

    async def get_document(
        self,
        document_id: str,
    ) -> RagDocumentRecord | None:
        stmt = select(RagDocumentModel).where(
            RagDocumentModel.document_id == document_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return RagPersistenceSerializer.document_from_model(
            model,
        )

    async def list_chunks(
        self,
        document_id: str,
    ) -> Sequence[RagChunkRecord]:
        stmt = (
            select(RagChunkModel)
            .where(
                RagChunkModel.document_id == document_id,
            )
            .order_by(
                RagChunkModel.chunk_index,
                RagChunkModel.chunk_id,
            )
        )
        result = await self._session.execute(stmt)

        return tuple(
            RagPersistenceSerializer.chunk_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def get_chunk(
        self,
        chunk_id: str,
    ) -> RagChunkRecord | None:
        stmt = select(RagChunkModel).where(
            RagChunkModel.chunk_id == chunk_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return RagPersistenceSerializer.chunk_from_model(
            model,
        )

    async def list_chunks_by_metadata(
        self,
        *,
        metadata_filters: JsonObject,
        limit: int | None = None,
    ) -> Sequence[RagChunkRecord]:
        if limit is not None and limit <= 0:
            return ()

        stmt = select(RagChunkModel)
        for key, value in metadata_filters.items():
            if not _is_json_scalar(value):
                continue
            condition = cast(
                ColumnElement[bool],
                RagChunkModel.metadata_payload.op("->>")(key)
                == _metadata_filter_text(cast(JsonScalar, value)),
            )
            stmt = stmt.where(
                condition,
            )
        stmt = stmt.order_by(
            RagChunkModel.document_id,
            RagChunkModel.chunk_index,
            RagChunkModel.chunk_id,
        )
        if limit is not None:
            stmt = stmt.limit(
                limit,
            )
        result = await self._session.execute(stmt)

        return tuple(
            RagPersistenceSerializer.chunk_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_embedding_jobs(
        self,
        *,
        status: str | None = None,
    ) -> Sequence[RagEmbeddingJobRecord]:
        stmt = select(RagEmbeddingJobModel)
        if status is not None:
            stmt = stmt.where(
                RagEmbeddingJobModel.status == status,
            )
        stmt = stmt.order_by(
            RagEmbeddingJobModel.queued_at,
            RagEmbeddingJobModel.job_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            RagPersistenceSerializer.embedding_job_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def persist_embedding_job(
        self,
        job: RagEmbeddingJobRecord,
    ) -> RagRecordPersistenceResult:
        try:
            await self._session.execute(
                _upsert_embedding_job_statement(
                    job,
                )
            )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return RagRecordPersistenceResult.failed(
                str(exc),
            )

        return RagRecordPersistenceResult.succeeded(
            record_id=job.job_id,
        )

    async def persist_graph_job(
        self,
        job: RagGraphJobRecord,
    ) -> RagRecordPersistenceResult:
        try:
            await self._session.execute(
                _upsert_graph_job_statement(
                    job,
                )
            )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return RagRecordPersistenceResult.failed(
                str(exc),
            )

        return RagRecordPersistenceResult.succeeded(
            record_id=job.job_id,
        )

    async def list_graph_jobs(
        self,
        *,
        status: str | None = None,
    ) -> Sequence[RagGraphJobRecord]:
        stmt = select(RagGraphJobModel)
        if status is not None:
            stmt = stmt.where(
                RagGraphJobModel.status == status,
            )
        stmt = stmt.order_by(
            RagGraphJobModel.queued_at,
            RagGraphJobModel.job_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            RagPersistenceSerializer.graph_job_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def persist_query_log(
        self,
        query: RagQueryLogRecord,
    ) -> RagRecordPersistenceResult:
        try:
            await self._session.execute(
                _upsert_query_log_statement(
                    query,
                )
            )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return RagRecordPersistenceResult.failed(
                str(exc),
            )

        return RagRecordPersistenceResult.succeeded(
            record_id=query.query_id,
        )

    async def get_query_log(
        self,
        query_id: str,
    ) -> RagQueryLogRecord | None:
        stmt = select(RagQueryLogModel).where(
            RagQueryLogModel.query_id == query_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return RagPersistenceSerializer.query_log_from_model(
            model,
        )

    async def persist_answer_log(
        self,
        answer: RagAnswerLogRecord,
    ) -> RagRecordPersistenceResult:
        try:
            await self._session.execute(
                _upsert_answer_log_statement(
                    answer,
                )
            )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return RagRecordPersistenceResult.failed(
                str(exc),
            )

        return RagRecordPersistenceResult.succeeded(
            record_id=answer.answer_id,
        )

    async def list_answer_logs(
        self,
        *,
        query_id: str | None = None,
    ) -> Sequence[RagAnswerLogRecord]:
        stmt = select(RagAnswerLogModel)
        if query_id is not None:
            stmt = stmt.where(
                RagAnswerLogModel.query_id == query_id,
            )
        stmt = stmt.order_by(
            RagAnswerLogModel.completed_at,
            RagAnswerLogModel.answer_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            RagPersistenceSerializer.answer_log_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def mark_source_eligibility(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> RagSourceEligibilityResult:
        try:
            await self._session.execute(
                _upsert_source_eligibility_statement(
                    eligibility,
                )
            )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return RagSourceEligibilityResult.failed(
                str(exc),
            )

        return RagSourceEligibilityResult.succeeded(
            eligibility_id=eligibility.eligibility_id,
        )

    async def unmark_source_eligibility(
        self,
        *,
        source_table: str,
        source_id: str,
        source_type: str,
    ) -> RagSourceEligibilityResult:
        eligibility_id = new_rag_source_eligibility_id(
            source_table=source_table,
            source_id=source_id,
            source_type=source_type,
        )
        try:
            result = await self._session.execute(
                delete(RagSourceEligibilityModel).where(
                    RagSourceEligibilityModel.source_table == source_table.strip(),
                    RagSourceEligibilityModel.source_id == source_id.strip(),
                    RagSourceEligibilityModel.source_type == source_type.strip(),
                )
            )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return RagSourceEligibilityResult.failed(
                str(exc),
            )

        deleted_count = getattr(
            result,
            "rowcount",
            0,
        )
        if not isinstance(
            deleted_count,
            int,
        ):
            deleted_count = 0

        return RagSourceEligibilityResult.succeeded(
            eligibility_id=eligibility_id,
            records_persisted=deleted_count,
        )

    async def get_source_eligibility(
        self,
        *,
        source_table: str,
        source_id: str,
        source_type: str,
    ) -> RagSourceEligibilityRecord | None:
        stmt = select(RagSourceEligibilityModel).where(
            RagSourceEligibilityModel.source_table == source_table.strip(),
            RagSourceEligibilityModel.source_id == source_id.strip(),
            RagSourceEligibilityModel.source_type == source_type.strip(),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return RagPersistenceSerializer.source_eligibility_from_model(
            model,
        )

    async def list_source_eligibility(
        self,
        *,
        source_table: str | None = None,
        source_id: str | None = None,
        source_type: str | None = None,
        eligible: bool | None = None,
    ) -> Sequence[RagSourceEligibilityRecord]:
        stmt = select(RagSourceEligibilityModel)
        if source_table is not None:
            stmt = stmt.where(
                RagSourceEligibilityModel.source_table == source_table.strip(),
            )
        if source_id is not None:
            stmt = stmt.where(
                RagSourceEligibilityModel.source_id == source_id.strip(),
            )
        if source_type is not None:
            stmt = stmt.where(
                RagSourceEligibilityModel.source_type == source_type.strip(),
            )
        if eligible is not None:
            stmt = stmt.where(
                RagSourceEligibilityModel.eligible == eligible,
            )
        stmt = stmt.order_by(
            RagSourceEligibilityModel.source_table,
            RagSourceEligibilityModel.source_type,
            RagSourceEligibilityModel.source_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            RagPersistenceSerializer.source_eligibility_from_model(
                model,
            )
            for model in result.scalars().all()
        )


def _is_json_scalar(
    value: object,
) -> bool:
    return value is None or isinstance(
        value,
        str | int | float | bool,
    )


def _metadata_filter_text(
    value: JsonScalar,
) -> str:
    if isinstance(
        value,
        bool,
    ):
        return str(value).lower()
    return str(value)


def _upsert_document_statement(
    document: RagDocumentRecord,
) -> Any:
    values = RagPersistenceSerializer.document_values(
        document,
    )
    stmt = insert(RagDocumentModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=[
            "document_id",
        ],
        set_={
            "source_table": excluded.source_table,
            "source_id": excluded.source_id,
            "source_type": excluded.source_type,
            "title": excluded.title,
            "content_text": excluded.content_text,
            "content_hash": excluded.content_hash,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "generated_at": excluded.generated_at,
            "metadata": excluded.metadata,
            "updated_at": func.now(),
        },
    )


def _upsert_chunk_statement(
    chunk: RagChunkRecord,
) -> Any:
    values = RagPersistenceSerializer.chunk_values(
        chunk,
    )
    stmt = insert(RagChunkModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=[
            "chunk_id",
        ],
        set_={
            "document_id": excluded.document_id,
            "chunk_index": excluded.chunk_index,
            "chunk_text": excluded.chunk_text,
            "token_count": excluded.token_count,
            "content_hash": excluded.content_hash,
            "metadata": excluded.metadata,
            "updated_at": func.now(),
        },
    )


def _upsert_embedding_job_statement(
    job: RagEmbeddingJobRecord,
) -> Any:
    values = RagPersistenceSerializer.embedding_job_values(
        job,
    )
    stmt = insert(RagEmbeddingJobModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=[
            "job_id",
        ],
        set_={
            "document_id": excluded.document_id,
            "chunk_id": excluded.chunk_id,
            "target_store": excluded.target_store,
            "embedding_model": excluded.embedding_model,
            "status": excluded.status,
            "queued_at": excluded.queued_at,
            "started_at": excluded.started_at,
            "completed_at": excluded.completed_at,
            "attempts": excluded.attempts,
            "error": excluded.error,
            "metadata": excluded.metadata,
            "updated_at": func.now(),
        },
    )


def _upsert_graph_job_statement(
    job: RagGraphJobRecord,
) -> Any:
    values = RagPersistenceSerializer.graph_job_values(
        job,
    )
    stmt = insert(RagGraphJobModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=[
            "job_id",
        ],
        set_={
            "document_id": excluded.document_id,
            "chunk_id": excluded.chunk_id,
            "target_store": excluded.target_store,
            "graph_model": excluded.graph_model,
            "status": excluded.status,
            "queued_at": excluded.queued_at,
            "started_at": excluded.started_at,
            "completed_at": excluded.completed_at,
            "attempts": excluded.attempts,
            "error": excluded.error,
            "metadata": excluded.metadata,
            "updated_at": func.now(),
        },
    )


def _upsert_query_log_statement(
    query: RagQueryLogRecord,
) -> Any:
    values = RagPersistenceSerializer.query_log_values(
        query,
    )
    stmt = insert(RagQueryLogModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=[
            "query_id",
        ],
        set_={
            "query_text": excluded.query_text,
            "normalized_query": excluded.normalized_query,
            "requester": excluded.requester,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "retrieval_route": excluded.retrieval_route,
            "top_k": excluded.top_k,
            "filters": excluded.filters,
            "model_executions": excluded.model_executions,
            "context_count": excluded.context_count,
            "citation_count": excluded.citation_count,
            "grounding_score": excluded.grounding_score,
            "utility_score": excluded.utility_score,
            "injection_detected": excluded.injection_detected,
            "reflection_scores": excluded.reflection_scores,
            "corrective_actions": excluded.corrective_actions,
            "status": excluded.status,
            "started_at": excluded.started_at,
            "completed_at": excluded.completed_at,
            "duration_ms": excluded.duration_ms,
            "error": excluded.error,
            "metadata": excluded.metadata,
            "updated_at": func.now(),
        },
    )


def _upsert_answer_log_statement(
    answer: RagAnswerLogRecord,
) -> Any:
    values = RagPersistenceSerializer.answer_log_values(
        answer,
    )
    stmt = insert(RagAnswerLogModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=[
            "answer_id",
        ],
        set_={
            "query_id": excluded.query_id,
            "answer_text": excluded.answer_text,
            "answer_hash": excluded.answer_hash,
            "generation_model": excluded.generation_model,
            "status": excluded.status,
            "confidence_score": excluded.confidence_score,
            "source_count": excluded.source_count,
            "citations": excluded.citations,
            "sources": excluded.sources,
            "completed_at": excluded.completed_at,
            "metadata": excluded.metadata,
            "updated_at": func.now(),
        },
    )


def _upsert_source_eligibility_statement(
    eligibility: RagSourceEligibilityRecord,
) -> Any:
    values = RagPersistenceSerializer.source_eligibility_values(
        eligibility,
    )
    stmt = insert(RagSourceEligibilityModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=[
            "source_table",
            "source_id",
            "source_type",
        ],
        set_={
            "eligibility_id": excluded.eligibility_id,
            "eligible": excluded.eligible,
            "reason": excluded.reason,
            "quality_score": excluded.quality_score,
            "reviewed_timestamp": excluded.reviewed_timestamp,
            "metadata": excluded.metadata,
            "updated_at": func.now(),
        },
    )
