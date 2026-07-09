from __future__ import annotations

from typing import cast

from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import JSONB

from core.database.base import Base
from core.database.models.rag import RagAnswerLogModel
from core.database.models.rag import RagChunkModel
from core.database.models.rag import RagDocumentModel
from core.database.models.rag import RagEmbeddingJobModel
from core.database.models.rag import RagGraphJobModel
from core.database.models.rag import RagQueryLogModel
from core.database.models.rag import RagSourceEligibilityModel


def test_rag_models_are_imported_into_base_metadata() -> None:
    assert "rag_documents" in Base.metadata.tables
    assert "rag_chunks" in Base.metadata.tables
    assert "rag_embedding_jobs" in Base.metadata.tables
    assert "rag_source_eligibility" in Base.metadata.tables
    assert "rag_graph_jobs" in Base.metadata.tables
    assert "rag_query_logs" in Base.metadata.tables
    assert "rag_answer_logs" in Base.metadata.tables


def test_rag_source_eligibility_model_links_canonical_postgres_sources() -> None:
    table = cast(Table, RagSourceEligibilityModel.__table__)
    columns = table.c
    primary_keys = {column.name for column in table.primary_key}
    unique_constraints = {constraint.name for constraint in table.constraints}
    check_constraints = {constraint.name for constraint in table.constraints}

    assert primary_keys == {"eligibility_id"}
    assert columns.source_table.nullable is False
    assert columns.source_id.nullable is False
    assert columns.source_type.nullable is False
    assert columns.eligible.nullable is False
    assert columns.reason.nullable is False
    assert columns.quality_score.nullable is False
    assert columns.reviewed_timestamp.nullable is False
    assert columns.created_at.server_default is not None
    assert columns.updated_at.server_default is not None
    assert "uq_rag_source_eligibility_source" in unique_constraints
    assert "ck_rag_source_eligibility_quality_score_range" in check_constraints


def test_rag_source_eligibility_model_has_source_lookup_indexes() -> None:
    table = cast(Table, RagSourceEligibilityModel.__table__)
    index_columns = {
        str(index.name): tuple(column.name for column in index.columns)
        for index in table.indexes
    }

    assert index_columns["idx_rag_source_eligibility_source"] == (
        "source_table",
        "source_id",
        "source_type",
    )
    assert index_columns["idx_rag_source_eligibility_source_eligible"] == (
        "source_table",
        "source_type",
        "eligible",
    )
    assert index_columns["ix_rag_source_eligibility_eligible"] == ("eligible",)
    assert index_columns["ix_rag_source_eligibility_quality_score"] == (
        "quality_score",
    )


def test_rag_document_model_preserves_source_lineage() -> None:
    columns = RagDocumentModel.__table__.c
    primary_keys = {column.name for column in RagDocumentModel.__table__.primary_key}

    assert primary_keys == {"document_id"}
    assert columns.source_table.nullable is False
    assert columns.source_id.nullable is False
    assert columns.source_type.nullable is False
    assert columns.title.nullable is False
    assert columns.content_text.nullable is False
    assert columns.generated_at.nullable is False
    assert columns.workflow_name.nullable is True
    assert columns.execution_id.nullable is True
    assert columns.created_at.server_default is not None
    assert columns.updated_at.server_default is not None


def test_rag_chunk_model_persists_ordered_chunk_text() -> None:
    columns = RagChunkModel.__table__.c
    primary_keys = {column.name for column in RagChunkModel.__table__.primary_key}
    foreign_keys = {
        foreign_key.target_fullname for foreign_key in columns.document_id.foreign_keys
    }

    assert primary_keys == {"chunk_id"}
    assert columns.document_id.nullable is False
    assert columns.chunk_index.nullable is False
    assert columns.chunk_text.nullable is False
    assert columns.token_count.nullable is True
    assert foreign_keys == {"rag_documents.document_id"}


def test_rag_embedding_job_model_tracks_projection_queue() -> None:
    columns = RagEmbeddingJobModel.__table__.c
    primary_keys = {
        column.name for column in RagEmbeddingJobModel.__table__.primary_key
    }
    document_foreign_keys = {
        foreign_key.target_fullname for foreign_key in columns.document_id.foreign_keys
    }
    chunk_foreign_keys = {
        foreign_key.target_fullname for foreign_key in columns.chunk_id.foreign_keys
    }

    assert primary_keys == {"job_id"}
    assert columns.document_id.nullable is False
    assert columns.chunk_id.nullable is True
    assert columns.target_store.nullable is False
    assert columns.embedding_model.nullable is False
    assert columns.status.nullable is False
    assert columns.queued_at.nullable is False
    assert columns.error.nullable is True
    assert document_foreign_keys == {"rag_documents.document_id"}
    assert chunk_foreign_keys == {"rag_chunks.chunk_id"}


def test_rag_graph_job_model_tracks_graph_projection_queue() -> None:
    table = cast(Table, RagGraphJobModel.__table__)
    columns = table.c
    primary_keys = {column.name for column in table.primary_key}
    document_foreign_keys = {
        foreign_key.target_fullname for foreign_key in columns.document_id.foreign_keys
    }
    chunk_foreign_keys = {
        foreign_key.target_fullname for foreign_key in columns.chunk_id.foreign_keys
    }
    index_columns = {
        str(index.name): tuple(column.name for column in index.columns)
        for index in table.indexes
    }

    assert primary_keys == {"job_id"}
    assert columns.document_id.nullable is False
    assert columns.chunk_id.nullable is True
    assert columns.target_store.nullable is False
    assert columns.graph_model.nullable is False
    assert columns.status.nullable is False
    assert columns.queued_at.nullable is False
    assert columns.error.nullable is True
    assert document_foreign_keys == {"rag_documents.document_id"}
    assert chunk_foreign_keys == {"rag_chunks.chunk_id"}
    assert index_columns["idx_rag_graph_jobs_status_queued"] == (
        "status",
        "queued_at",
    )
    assert index_columns["idx_rag_graph_jobs_document_status"] == (
        "document_id",
        "status",
    )


def test_rag_query_log_model_tracks_retrieval_requests() -> None:
    table = cast(Table, RagQueryLogModel.__table__)
    columns = table.c
    primary_keys = {column.name for column in table.primary_key}
    index_columns = {
        str(index.name): tuple(column.name for column in index.columns)
        for index in table.indexes
    }
    check_constraints = {constraint.name for constraint in table.constraints}

    assert primary_keys == {"query_id"}
    assert columns.query_text.nullable is False
    assert columns.normalized_query.nullable is True
    assert columns.retrieval_route.nullable is False
    assert columns.top_k.nullable is False
    assert columns.model_executions.nullable is False
    assert columns.model_executions.server_default is not None
    assert columns.context_count.nullable is False
    assert columns.context_count.server_default is not None
    assert columns.citation_count.nullable is False
    assert columns.citation_count.server_default is not None
    assert columns.grounding_score.nullable is True
    assert columns.utility_score.nullable is True
    assert columns.injection_detected.nullable is False
    assert columns.injection_detected.server_default is not None
    assert columns.reflection_scores.nullable is False
    assert columns.reflection_scores.server_default is not None
    assert columns.corrective_actions.nullable is False
    assert columns.corrective_actions.server_default is not None
    assert columns.status.nullable is False
    assert columns.started_at.nullable is False
    assert columns.completed_at.nullable is True
    assert columns.duration_ms.nullable is True
    assert columns.error.nullable is True
    assert {
        "ck_rag_query_logs_model_executions_array",
        "ck_rag_query_logs_context_count_non_negative",
        "ck_rag_query_logs_citation_count_non_negative",
        "ck_rag_query_logs_grounding_score_range",
        "ck_rag_query_logs_utility_score_range",
        "ck_rag_query_logs_reflection_scores_object",
        "ck_rag_query_logs_corrective_actions_array",
    } <= check_constraints
    assert index_columns["idx_rag_query_logs_workflow_execution"] == (
        "workflow_name",
        "execution_id",
    )
    assert index_columns["idx_rag_query_logs_status_started_at"] == (
        "status",
        "started_at",
    )
    assert index_columns["idx_rag_query_logs_injection_detected_true"] == (
        "injection_detected",
    )
    assert index_columns["idx_rag_query_logs_grounding_score"] == ("grounding_score",)
    assert index_columns["idx_rag_query_logs_utility_score"] == ("utility_score",)


def test_rag_answer_log_model_tracks_generated_answers_and_citations() -> None:
    table = cast(Table, RagAnswerLogModel.__table__)
    columns = table.c
    primary_keys = {column.name for column in table.primary_key}
    foreign_keys = {
        foreign_key.target_fullname for foreign_key in columns.query_id.foreign_keys
    }
    check_constraints = {constraint.name for constraint in table.constraints}
    index_columns = {
        str(index.name): tuple(column.name for column in index.columns)
        for index in table.indexes
    }

    assert primary_keys == {"answer_id"}
    assert columns.query_id.nullable is False
    assert columns.answer_text.nullable is False
    assert columns.answer_hash.nullable is True
    assert columns.generation_model.nullable is True
    assert columns.status.nullable is False
    assert columns.confidence_score.nullable is True
    assert columns.source_count.nullable is False
    assert columns.completed_at.nullable is False
    assert foreign_keys == {"rag_query_logs.query_id"}
    assert "ck_rag_answer_logs_confidence_score_range" in check_constraints
    assert index_columns["idx_rag_answer_logs_query_status"] == (
        "query_id",
        "status",
    )


def test_rag_models_use_jsonb_at_persistence_boundaries() -> None:
    assert isinstance(RagDocumentModel.__table__.c.metadata.type, JSONB)
    assert isinstance(RagChunkModel.__table__.c.metadata.type, JSONB)
    assert isinstance(RagEmbeddingJobModel.__table__.c.metadata.type, JSONB)
    assert isinstance(RagGraphJobModel.__table__.c.metadata.type, JSONB)
    assert isinstance(RagQueryLogModel.__table__.c.filters.type, JSONB)
    assert isinstance(RagQueryLogModel.__table__.c.model_executions.type, JSONB)
    assert isinstance(RagQueryLogModel.__table__.c.reflection_scores.type, JSONB)
    assert isinstance(RagQueryLogModel.__table__.c.corrective_actions.type, JSONB)
    assert isinstance(RagQueryLogModel.__table__.c.metadata.type, JSONB)
    assert isinstance(RagAnswerLogModel.__table__.c.citations.type, JSONB)
    assert isinstance(RagAnswerLogModel.__table__.c.sources.type, JSONB)
    assert isinstance(RagAnswerLogModel.__table__.c.metadata.type, JSONB)
    assert isinstance(RagSourceEligibilityModel.__table__.c.metadata.type, JSONB)
