"""add rag query answer and graph projection tables

Revision ID: c3d4e5f6a7b8
Revises: b7c2d4e6f8a1
Create Date: 2026-06-15 09:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b7c2d4e6f8a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rag_graph_jobs",
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("chunk_id", sa.String(), nullable=True),
        sa.Column("target_store", sa.String(), nullable=False),
        sa.Column("graph_model", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["rag_chunks.chunk_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["rag_documents.document_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index(
        op.f("ix_rag_graph_jobs_chunk_id"),
        "rag_graph_jobs",
        ["chunk_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_graph_jobs_document_id"),
        "rag_graph_jobs",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_graph_jobs_graph_model"),
        "rag_graph_jobs",
        ["graph_model"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_graph_jobs_queued_at"),
        "rag_graph_jobs",
        ["queued_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_graph_jobs_status"),
        "rag_graph_jobs",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_graph_jobs_target_store"),
        "rag_graph_jobs",
        ["target_store"],
        unique=False,
    )
    op.create_index(
        "idx_rag_graph_jobs_document_status",
        "rag_graph_jobs",
        ["document_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_rag_graph_jobs_status_queued",
        "rag_graph_jobs",
        ["status", "queued_at"],
        unique=False,
    )

    op.create_table(
        "rag_query_logs",
        sa.Column("query_id", sa.String(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("normalized_query", sa.Text(), nullable=True),
        sa.Column("requester", sa.String(), nullable=True),
        sa.Column("workflow_name", sa.String(), nullable=True),
        sa.Column("execution_id", sa.String(), nullable=True),
        sa.Column("retrieval_route", sa.String(), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("query_id"),
    )
    op.create_index(
        op.f("ix_rag_query_logs_execution_id"),
        "rag_query_logs",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_query_logs_requester"),
        "rag_query_logs",
        ["requester"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_query_logs_retrieval_route"),
        "rag_query_logs",
        ["retrieval_route"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_query_logs_started_at"),
        "rag_query_logs",
        ["started_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_query_logs_status"),
        "rag_query_logs",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_query_logs_workflow_name"),
        "rag_query_logs",
        ["workflow_name"],
        unique=False,
    )
    op.create_index(
        "idx_rag_query_logs_status_started_at",
        "rag_query_logs",
        ["status", "started_at"],
        unique=False,
    )
    op.create_index(
        "idx_rag_query_logs_workflow_execution",
        "rag_query_logs",
        ["workflow_name", "execution_id"],
        unique=False,
    )

    op.create_table(
        "rag_answer_logs",
        sa.Column("answer_id", sa.String(), nullable=False),
        sa.Column("query_id", sa.String(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("answer_hash", sa.String(), nullable=True),
        sa.Column("generation_model", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("citations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0.0 AND confidence_score <= 1.0)",
            name="ck_rag_answer_logs_confidence_score_range",
        ),
        sa.ForeignKeyConstraint(
            ["query_id"],
            ["rag_query_logs.query_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("answer_id"),
    )
    op.create_index(
        op.f("ix_rag_answer_logs_answer_hash"),
        "rag_answer_logs",
        ["answer_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_answer_logs_completed_at"),
        "rag_answer_logs",
        ["completed_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_answer_logs_generation_model"),
        "rag_answer_logs",
        ["generation_model"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_answer_logs_query_id"),
        "rag_answer_logs",
        ["query_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_answer_logs_status"),
        "rag_answer_logs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "idx_rag_answer_logs_query_status",
        "rag_answer_logs",
        ["query_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_rag_answer_logs_query_status", table_name="rag_answer_logs")
    op.drop_index(op.f("ix_rag_answer_logs_status"), table_name="rag_answer_logs")
    op.drop_index(op.f("ix_rag_answer_logs_query_id"), table_name="rag_answer_logs")
    op.drop_index(
        op.f("ix_rag_answer_logs_generation_model"),
        table_name="rag_answer_logs",
    )
    op.drop_index(
        op.f("ix_rag_answer_logs_completed_at"),
        table_name="rag_answer_logs",
    )
    op.drop_index(
        op.f("ix_rag_answer_logs_answer_hash"),
        table_name="rag_answer_logs",
    )
    op.drop_table("rag_answer_logs")

    op.drop_index(
        "idx_rag_query_logs_workflow_execution",
        table_name="rag_query_logs",
    )
    op.drop_index(
        "idx_rag_query_logs_status_started_at",
        table_name="rag_query_logs",
    )
    op.drop_index(
        op.f("ix_rag_query_logs_workflow_name"),
        table_name="rag_query_logs",
    )
    op.drop_index(op.f("ix_rag_query_logs_status"), table_name="rag_query_logs")
    op.drop_index(
        op.f("ix_rag_query_logs_started_at"),
        table_name="rag_query_logs",
    )
    op.drop_index(
        op.f("ix_rag_query_logs_retrieval_route"),
        table_name="rag_query_logs",
    )
    op.drop_index(op.f("ix_rag_query_logs_requester"), table_name="rag_query_logs")
    op.drop_index(
        op.f("ix_rag_query_logs_execution_id"),
        table_name="rag_query_logs",
    )
    op.drop_table("rag_query_logs")

    op.drop_index("idx_rag_graph_jobs_status_queued", table_name="rag_graph_jobs")
    op.drop_index("idx_rag_graph_jobs_document_status", table_name="rag_graph_jobs")
    op.drop_index(
        op.f("ix_rag_graph_jobs_target_store"),
        table_name="rag_graph_jobs",
    )
    op.drop_index(op.f("ix_rag_graph_jobs_status"), table_name="rag_graph_jobs")
    op.drop_index(op.f("ix_rag_graph_jobs_queued_at"), table_name="rag_graph_jobs")
    op.drop_index(
        op.f("ix_rag_graph_jobs_graph_model"),
        table_name="rag_graph_jobs",
    )
    op.drop_index(
        op.f("ix_rag_graph_jobs_document_id"),
        table_name="rag_graph_jobs",
    )
    op.drop_index(op.f("ix_rag_graph_jobs_chunk_id"), table_name="rag_graph_jobs")
    op.drop_table("rag_graph_jobs")
