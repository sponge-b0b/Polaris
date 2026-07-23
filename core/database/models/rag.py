from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base


class RagSourceEligibilityModel(Base):
    __tablename__ = "rag_source_eligibility"
    __table_args__ = (
        CheckConstraint(
            "quality_score >= 0.0 AND quality_score <= 1.0",
            name="ck_rag_source_eligibility_quality_score_range",
        ),
        UniqueConstraint(
            "source_table",
            "source_id",
            "source_type",
            name="uq_rag_source_eligibility_source",
        ),
    )

    eligibility_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    source_table: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    source_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    eligible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    quality_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        index=True,
    )
    reviewed_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_rag_source_eligibility_source",
    RagSourceEligibilityModel.source_table,
    RagSourceEligibilityModel.source_id,
    RagSourceEligibilityModel.source_type,
)

Index(
    "idx_rag_source_eligibility_source_eligible",
    RagSourceEligibilityModel.source_table,
    RagSourceEligibilityModel.source_type,
    RagSourceEligibilityModel.eligible,
)


class RagDocumentModel(Base):
    __tablename__ = "rag_documents"

    document_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    source_table: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    source_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    content_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    content_hash: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    workflow_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    execution_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_rag_documents_source",
    RagDocumentModel.source_table,
    RagDocumentModel.source_id,
    RagDocumentModel.source_type,
)

Index(
    "idx_rag_documents_workflow_execution",
    RagDocumentModel.workflow_name,
    RagDocumentModel.execution_id,
)


class RagChunkModel(Base):
    __tablename__ = "rag_chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_rag_chunks_document_chunk_index",
        ),
    )

    chunk_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    document_id: Mapped[str] = mapped_column(
        ForeignKey(
            "rag_documents.document_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    chunk_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    content_hash: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_rag_chunks_document_order",
    RagChunkModel.document_id,
    RagChunkModel.chunk_index,
)


class RagEmbeddingJobModel(Base):
    __tablename__ = "rag_embedding_jobs"

    job_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    document_id: Mapped[str] = mapped_column(
        ForeignKey(
            "rag_documents.document_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "rag_chunks.chunk_id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )
    target_store: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    embedding_model: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_rag_embedding_jobs_status_queued",
    RagEmbeddingJobModel.status,
    RagEmbeddingJobModel.queued_at,
)

Index(
    "idx_rag_embedding_jobs_document_status",
    RagEmbeddingJobModel.document_id,
    RagEmbeddingJobModel.status,
)


class RagGraphJobModel(Base):
    __tablename__ = "rag_graph_jobs"

    job_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    document_id: Mapped[str] = mapped_column(
        ForeignKey(
            "rag_documents.document_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "rag_chunks.chunk_id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )
    target_store: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    graph_model: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_rag_graph_jobs_status_queued",
    RagGraphJobModel.status,
    RagGraphJobModel.queued_at,
)

Index(
    "idx_rag_graph_jobs_document_status",
    RagGraphJobModel.document_id,
    RagGraphJobModel.status,
)


class RagQueryLogModel(Base):
    __tablename__ = "rag_query_logs"
    __table_args__ = (
        CheckConstraint(
            "jsonb_typeof(model_executions) = 'array' "
            "AND jsonb_array_length(model_executions) <= 32",
            name="ck_rag_query_logs_model_executions_array",
        ),
        CheckConstraint(
            "context_count >= 0",
            name="ck_rag_query_logs_context_count_non_negative",
        ),
        CheckConstraint(
            "citation_count >= 0",
            name="ck_rag_query_logs_citation_count_non_negative",
        ),
        CheckConstraint(
            "grounding_score IS NULL OR "
            "(grounding_score >= 0.0 AND grounding_score <= 1.0)",
            name="ck_rag_query_logs_grounding_score_range",
        ),
        CheckConstraint(
            "utility_score IS NULL OR (utility_score >= 0.0 AND utility_score <= 1.0)",
            name="ck_rag_query_logs_utility_score_range",
        ),
        CheckConstraint(
            "jsonb_typeof(reflection_scores) = 'object'",
            name="ck_rag_query_logs_reflection_scores_object",
        ),
        CheckConstraint(
            "jsonb_typeof(corrective_actions) = 'array'",
            name="ck_rag_query_logs_corrective_actions_array",
        ),
    )

    query_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    query_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    normalized_query: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    requester: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    workflow_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    execution_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    retrieval_route: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    top_k: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    filters_payload: Mapped[dict[str, Any]] = mapped_column(
        "filters",
        JSONB,
        nullable=False,
        default=dict,
    )
    model_executions_payload: Mapped[list[dict[str, Any]]] = mapped_column(
        "model_executions",
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    context_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    citation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    grounding_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    utility_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    injection_detected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    reflection_scores_payload: Mapped[dict[str, Any]] = mapped_column(
        "reflection_scores",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    corrective_actions_payload: Mapped[list[str]] = mapped_column(
        "corrective_actions",
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_rag_query_logs_workflow_execution",
    RagQueryLogModel.workflow_name,
    RagQueryLogModel.execution_id,
)

Index(
    "idx_rag_query_logs_status_started_at",
    RagQueryLogModel.status,
    RagQueryLogModel.started_at,
)

Index(
    "idx_rag_query_logs_injection_detected_true",
    RagQueryLogModel.injection_detected,
    postgresql_where=RagQueryLogModel.injection_detected.is_(True),
)

Index(
    "idx_rag_query_logs_grounding_score",
    RagQueryLogModel.grounding_score,
    postgresql_where=RagQueryLogModel.grounding_score.is_not(None),
)

Index(
    "idx_rag_query_logs_utility_score",
    RagQueryLogModel.utility_score,
    postgresql_where=RagQueryLogModel.utility_score.is_not(None),
)


class RagAnswerLogModel(Base):
    __tablename__ = "rag_answer_logs"
    __table_args__ = (
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0.0 AND confidence_score <= 1.0)",  # noqa: E501
            name="ck_rag_answer_logs_confidence_score_range",
        ),
    )

    answer_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    query_id: Mapped[str] = mapped_column(
        ForeignKey(
            "rag_query_logs.query_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    answer_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    answer_hash: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    generation_model: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    confidence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    source_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    citations_payload: Mapped[dict[str, Any]] = mapped_column(
        "citations",
        JSONB,
        nullable=False,
        default=dict,
    )
    sources_payload: Mapped[dict[str, Any]] = mapped_column(
        "sources",
        JSONB,
        nullable=False,
        default=dict,
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_rag_answer_logs_query_status",
    RagAnswerLogModel.query_id,
    RagAnswerLogModel.status,
)
