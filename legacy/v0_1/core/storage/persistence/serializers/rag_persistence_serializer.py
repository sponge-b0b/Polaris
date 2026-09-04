from __future__ import annotations

from typing import Any, cast

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
    RagAnswerLogRecord,
    RagChunkRecord,
    RagDocumentRecord,
    RagEmbeddingJobRecord,
    RagGraphJobRecord,
    RagQueryLogRecord,
    RagQueryModelExecutionRecord,
    RagQueryReflectionScores,
    RagSourceEligibilityRecord,
)


class RagPersistenceSerializer:
    """
    Serializer between typed RAG source records and SQLAlchemy models.

    JSON dictionaries are introduced here because this module is the database
    persistence boundary. RAG builders should operate on typed records and only
    serialize when crossing into Postgres.
    """

    @staticmethod
    def document_values(
        record: RagDocumentRecord,
    ) -> dict[str, Any]:
        return {
            "document_id": record.document_id,
            "source_table": record.source_table,
            "source_id": record.source_id,
            "source_type": record.source_type,
            "title": record.title,
            "content_text": record.content_text,
            "content_hash": record.content_hash,
            "workflow_name": record.workflow_name,
            "execution_id": record.execution_id,
            "generated_at": record.generated_at,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def chunk_values(
        record: RagChunkRecord,
    ) -> dict[str, Any]:
        return {
            "chunk_id": record.chunk_id,
            "document_id": record.document_id,
            "chunk_index": record.chunk_index,
            "chunk_text": record.chunk_text,
            "token_count": record.token_count,
            "content_hash": record.content_hash,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def embedding_job_values(
        record: RagEmbeddingJobRecord,
    ) -> dict[str, Any]:
        return {
            "job_id": record.job_id,
            "document_id": record.document_id,
            "chunk_id": record.chunk_id,
            "target_store": record.target_store,
            "embedding_model": record.embedding_model,
            "status": record.status,
            "queued_at": record.queued_at,
            "started_at": record.started_at,
            "completed_at": record.completed_at,
            "attempts": record.attempts,
            "error": record.error,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def graph_job_values(
        record: RagGraphJobRecord,
    ) -> dict[str, Any]:
        return {
            "job_id": record.job_id,
            "document_id": record.document_id,
            "chunk_id": record.chunk_id,
            "target_store": record.target_store,
            "graph_model": record.graph_model,
            "status": record.status,
            "queued_at": record.queued_at,
            "started_at": record.started_at,
            "completed_at": record.completed_at,
            "attempts": record.attempts,
            "error": record.error,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def query_log_values(
        record: RagQueryLogRecord,
    ) -> dict[str, Any]:
        return {
            "query_id": record.query_id,
            "query_text": record.query_text,
            "normalized_query": record.normalized_query,
            "requester": record.requester,
            "workflow_name": record.workflow_name,
            "execution_id": record.execution_id,
            "retrieval_route": record.retrieval_route,
            "top_k": record.top_k,
            "filters_payload": dict(record.filters),
            "model_executions_payload": [
                execution.as_dict() for execution in record.model_executions
            ],
            "context_count": record.context_count,
            "citation_count": record.citation_count,
            "grounding_score": record.grounding_score,
            "utility_score": record.utility_score,
            "injection_detected": record.injection_detected,
            "reflection_scores_payload": (
                {}
                if record.reflection_scores is None
                else record.reflection_scores.as_dict()
            ),
            "corrective_actions_payload": list(record.corrective_actions),
            "status": record.status,
            "started_at": record.started_at,
            "completed_at": record.completed_at,
            "duration_ms": record.duration_ms,
            "error": record.error,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def answer_log_values(
        record: RagAnswerLogRecord,
    ) -> dict[str, Any]:
        return {
            "answer_id": record.answer_id,
            "query_id": record.query_id,
            "answer_text": record.answer_text,
            "answer_hash": record.answer_hash,
            "generation_model": record.generation_model,
            "status": record.status,
            "confidence_score": record.confidence_score,
            "source_count": record.source_count,
            "citations_payload": dict(record.citations),
            "sources_payload": dict(record.sources),
            "completed_at": record.completed_at,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def source_eligibility_values(
        record: RagSourceEligibilityRecord,
    ) -> dict[str, Any]:
        return {
            "eligibility_id": record.eligibility_id,
            "source_table": record.source_table,
            "source_id": record.source_id,
            "source_type": record.source_type,
            "eligible": record.eligible,
            "reason": record.reason,
            "quality_score": record.quality_score,
            "reviewed_timestamp": record.reviewed_timestamp,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def document_from_model(
        model: RagDocumentModel,
    ) -> RagDocumentRecord:
        return RagDocumentRecord(
            document_id=model.document_id,
            source_table=model.source_table,
            source_id=model.source_id,
            source_type=model.source_type,
            title=model.title,
            content_text=model.content_text,
            content_hash=model.content_hash,
            workflow_name=model.workflow_name,
            execution_id=model.execution_id,
            generated_at=model.generated_at,
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
        )

    @staticmethod
    def chunk_from_model(
        model: RagChunkModel,
    ) -> RagChunkRecord:
        return RagChunkRecord(
            chunk_id=model.chunk_id,
            document_id=model.document_id,
            chunk_index=model.chunk_index,
            chunk_text=model.chunk_text,
            token_count=model.token_count,
            content_hash=model.content_hash,
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
        )

    @staticmethod
    def embedding_job_from_model(
        model: RagEmbeddingJobModel,
    ) -> RagEmbeddingJobRecord:
        return RagEmbeddingJobRecord(
            job_id=model.job_id,
            document_id=model.document_id,
            chunk_id=model.chunk_id,
            target_store=model.target_store,
            embedding_model=model.embedding_model,
            status=model.status,
            queued_at=model.queued_at,
            started_at=model.started_at,
            completed_at=model.completed_at,
            attempts=model.attempts,
            error=model.error,
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
        )

    @staticmethod
    def graph_job_from_model(
        model: RagGraphJobModel,
    ) -> RagGraphJobRecord:
        return RagGraphJobRecord(
            job_id=model.job_id,
            document_id=model.document_id,
            chunk_id=model.chunk_id,
            target_store=model.target_store,
            graph_model=model.graph_model,
            status=model.status,
            queued_at=model.queued_at,
            started_at=model.started_at,
            completed_at=model.completed_at,
            attempts=model.attempts,
            error=model.error,
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
        )

    @staticmethod
    def query_log_from_model(
        model: RagQueryLogModel,
    ) -> RagQueryLogRecord:
        return RagQueryLogRecord(
            query_id=model.query_id,
            query_text=model.query_text,
            normalized_query=model.normalized_query,
            requester=model.requester,
            workflow_name=model.workflow_name,
            execution_id=model.execution_id,
            retrieval_route=model.retrieval_route,
            top_k=model.top_k,
            filters=cast(
                JsonObject,
                model.filters_payload,
            ),
            model_executions=tuple(
                RagQueryModelExecutionRecord.from_mapping(payload)
                for payload in model.model_executions_payload
            ),
            context_count=model.context_count,
            citation_count=model.citation_count,
            grounding_score=model.grounding_score,
            utility_score=model.utility_score,
            injection_detected=model.injection_detected,
            reflection_scores=(
                None
                if not model.reflection_scores_payload
                else RagQueryReflectionScores.from_mapping(
                    model.reflection_scores_payload
                )
            ),
            corrective_actions=tuple(model.corrective_actions_payload),
            status=model.status,
            started_at=model.started_at,
            completed_at=model.completed_at,
            duration_ms=model.duration_ms,
            error=model.error,
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
        )

    @staticmethod
    def answer_log_from_model(
        model: RagAnswerLogModel,
    ) -> RagAnswerLogRecord:
        return RagAnswerLogRecord(
            answer_id=model.answer_id,
            query_id=model.query_id,
            answer_text=model.answer_text,
            answer_hash=model.answer_hash,
            generation_model=model.generation_model,
            status=model.status,
            confidence_score=model.confidence_score,
            source_count=model.source_count,
            citations=cast(
                JsonObject,
                model.citations_payload,
            ),
            sources=cast(
                JsonObject,
                model.sources_payload,
            ),
            completed_at=model.completed_at,
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
        )

    @staticmethod
    def source_eligibility_from_model(
        model: RagSourceEligibilityModel,
    ) -> RagSourceEligibilityRecord:
        return RagSourceEligibilityRecord(
            eligibility_id=model.eligibility_id,
            source_table=model.source_table,
            source_id=model.source_id,
            source_type=model.source_type,
            eligible=model.eligible,
            reason=model.reason,
            quality_score=model.quality_score,
            reviewed_timestamp=model.reviewed_timestamp,
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
        )
