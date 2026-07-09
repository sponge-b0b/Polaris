"""add first-class RAG query audit fields

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-25 14:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rag_query_logs",
        sa.Column(
            "model_executions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "rag_query_logs",
        sa.Column(
            "context_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "rag_query_logs",
        sa.Column(
            "citation_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "rag_query_logs",
        sa.Column("grounding_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "rag_query_logs",
        sa.Column("utility_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "rag_query_logs",
        sa.Column(
            "injection_detected",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "rag_query_logs",
        sa.Column(
            "reflection_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "rag_query_logs",
        sa.Column(
            "corrective_actions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )

    op.execute(
        """
        UPDATE rag_query_logs
        SET
            model_executions = CASE
                WHEN jsonb_typeof(metadata -> 'model_executions') = 'array'
                THEN (
                    SELECT COALESCE(
                        jsonb_agg(item.value ORDER BY item.ordinality),
                        '[]'::jsonb
                    )
                    FROM jsonb_array_elements(metadata -> 'model_executions')
                        WITH ORDINALITY AS item(value, ordinality)
                    WHERE item.ordinality <= 32
                )
                ELSE '[]'::jsonb
            END,
            context_count = CASE
                WHEN jsonb_typeof(metadata -> 'context_count') = 'number'
                 AND (metadata ->> 'context_count')::numeric >= 0
                 AND trunc((metadata ->> 'context_count')::numeric)
                     = (metadata ->> 'context_count')::numeric
                 AND (metadata ->> 'context_count')::numeric <= 2147483647
                THEN (metadata ->> 'context_count')::integer
                ELSE 0
            END,
            citation_count = CASE
                WHEN jsonb_typeof(metadata -> 'citation_count') = 'number'
                 AND (metadata ->> 'citation_count')::numeric >= 0
                 AND trunc((metadata ->> 'citation_count')::numeric)
                     = (metadata ->> 'citation_count')::numeric
                 AND (metadata ->> 'citation_count')::numeric <= 2147483647
                THEN (metadata ->> 'citation_count')::integer
                ELSE 0
            END,
            grounding_score = CASE
                WHEN jsonb_typeof(metadata -> 'grounding_score') = 'number'
                 AND (metadata ->> 'grounding_score')::double precision
                     BETWEEN 0.0 AND 1.0
                THEN (metadata ->> 'grounding_score')::double precision
            END,
            utility_score = CASE
                WHEN jsonb_typeof(metadata -> 'utility_score') = 'number'
                 AND (metadata ->> 'utility_score')::double precision
                     BETWEEN 0.0 AND 1.0
                THEN (metadata ->> 'utility_score')::double precision
            END,
            injection_detected = CASE
                WHEN jsonb_typeof(metadata -> 'injection_detected') = 'boolean'
                THEN (metadata ->> 'injection_detected')::boolean
                ELSE false
            END,
            reflection_scores = CASE
                WHEN jsonb_typeof(metadata -> 'reflection_scores') = 'object'
                THEN metadata -> 'reflection_scores'
                ELSE '{}'::jsonb
            END,
            corrective_actions = CASE
                WHEN jsonb_typeof(metadata -> 'corrective_actions') = 'array'
                THEN metadata -> 'corrective_actions'
                ELSE '[]'::jsonb
            END,
            metadata = metadata - ARRAY[
                'model_executions',
                'context_count',
                'citation_count',
                'grounding_score',
                'utility_score',
                'injection_detected',
                'reflection_scores',
                'corrective_actions'
            ]::text[]
        """
    )

    op.create_check_constraint(
        "ck_rag_query_logs_model_executions_array",
        "rag_query_logs",
        "jsonb_typeof(model_executions) = 'array' "
        "AND jsonb_array_length(model_executions) <= 32",
    )
    op.create_check_constraint(
        "ck_rag_query_logs_context_count_non_negative",
        "rag_query_logs",
        "context_count >= 0",
    )
    op.create_check_constraint(
        "ck_rag_query_logs_citation_count_non_negative",
        "rag_query_logs",
        "citation_count >= 0",
    )
    op.create_check_constraint(
        "ck_rag_query_logs_grounding_score_range",
        "rag_query_logs",
        "grounding_score IS NULL OR "
        "(grounding_score >= 0.0 AND grounding_score <= 1.0)",
    )
    op.create_check_constraint(
        "ck_rag_query_logs_utility_score_range",
        "rag_query_logs",
        "utility_score IS NULL OR (utility_score >= 0.0 AND utility_score <= 1.0)",
    )
    op.create_check_constraint(
        "ck_rag_query_logs_reflection_scores_object",
        "rag_query_logs",
        "jsonb_typeof(reflection_scores) = 'object'",
    )
    op.create_check_constraint(
        "ck_rag_query_logs_corrective_actions_array",
        "rag_query_logs",
        "jsonb_typeof(corrective_actions) = 'array'",
    )

    op.create_index(
        "idx_rag_query_logs_injection_detected_true",
        "rag_query_logs",
        ["injection_detected"],
        unique=False,
        postgresql_where=sa.text("injection_detected IS true"),
    )
    op.create_index(
        "idx_rag_query_logs_grounding_score",
        "rag_query_logs",
        ["grounding_score"],
        unique=False,
        postgresql_where=sa.text("grounding_score IS NOT NULL"),
    )
    op.create_index(
        "idx_rag_query_logs_utility_score",
        "rag_query_logs",
        ["utility_score"],
        unique=False,
        postgresql_where=sa.text("utility_score IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "idx_rag_query_logs_utility_score",
        table_name="rag_query_logs",
    )
    op.drop_index(
        "idx_rag_query_logs_grounding_score",
        table_name="rag_query_logs",
    )
    op.drop_index(
        "idx_rag_query_logs_injection_detected_true",
        table_name="rag_query_logs",
    )

    op.drop_constraint(
        "ck_rag_query_logs_corrective_actions_array",
        "rag_query_logs",
        type_="check",
    )
    op.drop_constraint(
        "ck_rag_query_logs_reflection_scores_object",
        "rag_query_logs",
        type_="check",
    )
    op.drop_constraint(
        "ck_rag_query_logs_utility_score_range",
        "rag_query_logs",
        type_="check",
    )
    op.drop_constraint(
        "ck_rag_query_logs_grounding_score_range",
        "rag_query_logs",
        type_="check",
    )
    op.drop_constraint(
        "ck_rag_query_logs_citation_count_non_negative",
        "rag_query_logs",
        type_="check",
    )
    op.drop_constraint(
        "ck_rag_query_logs_context_count_non_negative",
        "rag_query_logs",
        type_="check",
    )
    op.drop_constraint(
        "ck_rag_query_logs_model_executions_array",
        "rag_query_logs",
        type_="check",
    )

    op.drop_column("rag_query_logs", "corrective_actions")
    op.drop_column("rag_query_logs", "reflection_scores")
    op.drop_column("rag_query_logs", "injection_detected")
    op.drop_column("rag_query_logs", "utility_score")
    op.drop_column("rag_query_logs", "grounding_score")
    op.drop_column("rag_query_logs", "citation_count")
    op.drop_column("rag_query_logs", "context_count")
    op.drop_column("rag_query_logs", "model_executions")
