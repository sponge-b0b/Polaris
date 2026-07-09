"""correct telemetry trace lifecycle

Revision ID: b8c9d0e1f2a3
Revises: d9649abf672c
Create Date: 2026-07-02 12:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "d9649abf672c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "telemetry_traces",
        sa.Column("terminal_event_id", sa.String(), nullable=True),
    )
    op.add_column(
        "telemetry_traces",
        sa.Column("exception_type", sa.String(), nullable=True),
    )
    op.add_column(
        "telemetry_traces",
        sa.Column("exception_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "telemetry_traces",
        sa.Column("exception_stack_trace", sa.Text(), nullable=True),
    )
    op.add_column(
        "telemetry_traces",
        sa.Column(
            "exception_stack_trace_truncated",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_telemetry_traces_terminal_event_id"),
        "telemetry_traces",
        ["terminal_event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_telemetry_traces_exception_type"),
        "telemetry_traces",
        ["exception_type"],
        unique=False,
    )

    op.execute(
        """
        UPDATE telemetry_traces
        SET
            ended_at = started_at,
            started_at = started_at - make_interval(secs => duration_seconds)
        WHERE ended_at IS NOT NULL
          AND duration_seconds IS NOT NULL
          AND operation_name IN (
              'runtime.workflow.completed',
              'runtime.workflow.failed',
              'runtime.node.completed',
              'runtime.node.failed',
              'runtime.node.skipped',
              'application.service.completed',
              'application.service.failed',
              'application.service.configuration_failed',
              'application.service.cancelled',
              'application.rag.operation.completed',
              'application.rag.operation.failed'
          )
        """
    )
    op.execute(
        """
        UPDATE telemetry_traces
        SET operation_name = CASE
            WHEN operation_name LIKE 'runtime.workflow.%' THEN 'runtime.workflow'
            WHEN operation_name LIKE 'runtime.node.%' THEN 'runtime.node'
            WHEN operation_name LIKE 'application.service.%' THEN 'application.service'
            WHEN operation_name LIKE 'application.rag.operation.%'
                THEN 'application.rag.operation'
            WHEN operation_name LIKE 'integration.provider.%'
                THEN 'integration.provider.call'
            ELSE operation_name
        END
        """
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT
                trace_record_id,
                row_number() OVER (
                    PARTITION BY trace_id, span_id
                    ORDER BY
                        CASE status
                            WHEN 'failed' THEN 4
                            WHEN 'cancelled' THEN 3
                            WHEN 'succeeded' THEN 2
                            WHEN 'running' THEN 1
                            ELSE 0
                        END DESC,
                        ended_at DESC NULLS LAST,
                        started_at ASC,
                        row_updated_at DESC,
                        trace_record_id
                ) AS duplicate_rank
            FROM telemetry_traces
        )
        DELETE FROM telemetry_traces
        WHERE trace_record_id IN (
            SELECT trace_record_id
            FROM ranked
            WHERE duplicate_rank > 1
        )
        """
    )

    op.drop_index(
        "idx_telemetry_traces_trace_span",
        table_name="telemetry_traces",
    )
    op.create_unique_constraint(
        "uq_telemetry_traces_trace_span",
        "telemetry_traces",
        ["trace_id", "span_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_telemetry_traces_trace_span",
        "telemetry_traces",
        type_="unique",
    )
    op.create_index(
        "idx_telemetry_traces_trace_span",
        "telemetry_traces",
        ["trace_id", "span_id"],
        unique=False,
    )
    op.drop_index(
        op.f("ix_telemetry_traces_exception_type"),
        table_name="telemetry_traces",
    )
    op.drop_index(
        op.f("ix_telemetry_traces_terminal_event_id"),
        table_name="telemetry_traces",
    )
    op.drop_column("telemetry_traces", "exception_stack_trace_truncated")
    op.drop_column("telemetry_traces", "exception_stack_trace")
    op.drop_column("telemetry_traces", "exception_message")
    op.drop_column("telemetry_traces", "exception_type")
    op.drop_column("telemetry_traces", "terminal_event_id")
