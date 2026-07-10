"""add strategy persistence records

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-07-10 12:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f2a3b4c5d6e7"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _jsonb() -> postgresql.JSONB:
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "strategy_hypotheses",
        sa.Column("hypothesis_id", sa.String(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("perspective", sa.String(), nullable=False),
        sa.Column("thesis", sa.Text(), nullable=False),
        sa.Column("directional_bias", sa.Float(), nullable=False),
        sa.Column("hypothesis_strength", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_fingerprint", sa.String(), nullable=False),
        sa.Column("invalidated", sa.Boolean(), nullable=False),
        sa.Column("horizon", sa.String(), nullable=True),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workflow_name", sa.String(), nullable=True),
        sa.Column("execution_id", sa.String(), nullable=True),
        sa.Column("runtime_id", sa.String(), nullable=True),
        sa.Column("node_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supporting_evidence", _jsonb(), nullable=False),
        sa.Column("contradicting_evidence", _jsonb(), nullable=False),
        sa.Column("key_assumptions", _jsonb(), nullable=False),
        sa.Column("invalidation_conditions", _jsonb(), nullable=False),
        sa.Column("risks", _jsonb(), nullable=False),
        sa.Column("recommendations", _jsonb(), nullable=False),
        sa.Column("data_quality_flags", _jsonb(), nullable=False),
        sa.Column("metadata", _jsonb(), nullable=False),
        sa.Column(
            "row_created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "row_updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("hypothesis_id"),
    )
    op.create_index(
        op.f("ix_strategy_hypotheses_as_of"),
        "strategy_hypotheses",
        ["as_of"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypotheses_created_at"),
        "strategy_hypotheses",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypotheses_evidence_fingerprint"),
        "strategy_hypotheses",
        ["evidence_fingerprint"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypotheses_execution_id"),
        "strategy_hypotheses",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypotheses_horizon"),
        "strategy_hypotheses",
        ["horizon"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypotheses_invalidated"),
        "strategy_hypotheses",
        ["invalidated"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypotheses_node_name"),
        "strategy_hypotheses",
        ["node_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypotheses_perspective"),
        "strategy_hypotheses",
        ["perspective"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypotheses_runtime_id"),
        "strategy_hypotheses",
        ["runtime_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypotheses_symbol"),
        "strategy_hypotheses",
        ["symbol"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypotheses_workflow_name"),
        "strategy_hypotheses",
        ["workflow_name"],
        unique=False,
    )
    op.create_index(
        "idx_strategy_hypotheses_execution_node",
        "strategy_hypotheses",
        ["execution_id", "node_name"],
        unique=False,
    )
    op.create_index(
        "idx_strategy_hypotheses_perspective_fingerprint",
        "strategy_hypotheses",
        ["perspective", "evidence_fingerprint"],
        unique=False,
    )
    op.create_index(
        "idx_strategy_hypotheses_symbol_horizon_as_of",
        "strategy_hypotheses",
        ["symbol", "horizon", "as_of"],
        unique=False,
    )

    op.create_table(
        "strategy_synthesis_decisions",
        sa.Column("decision_id", sa.String(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("selected_perspective", sa.String(), nullable=True),
        sa.Column("selection_status", sa.String(), nullable=False),
        sa.Column("directional_score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("regime", sa.String(), nullable=False),
        sa.Column("uncertainty", sa.Float(), nullable=False),
        sa.Column("thesis", sa.Text(), nullable=False),
        sa.Column("evidence_fingerprint", sa.String(), nullable=False),
        sa.Column("horizon", sa.String(), nullable=True),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workflow_name", sa.String(), nullable=True),
        sa.Column("execution_id", sa.String(), nullable=True),
        sa.Column("runtime_id", sa.String(), nullable=True),
        sa.Column("node_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("signals", _jsonb(), nullable=False),
        sa.Column("risks", _jsonb(), nullable=False),
        sa.Column("recommendations", _jsonb(), nullable=False),
        sa.Column("degraded_reasons", _jsonb(), nullable=False),
        sa.Column("metadata", _jsonb(), nullable=False),
        sa.Column(
            "row_created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "row_updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("decision_id"),
    )
    op.create_index(
        op.f("ix_strategy_synthesis_decisions_as_of"),
        "strategy_synthesis_decisions",
        ["as_of"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_synthesis_decisions_created_at"),
        "strategy_synthesis_decisions",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_synthesis_decisions_evidence_fingerprint"),
        "strategy_synthesis_decisions",
        ["evidence_fingerprint"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_synthesis_decisions_execution_id"),
        "strategy_synthesis_decisions",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_synthesis_decisions_horizon"),
        "strategy_synthesis_decisions",
        ["horizon"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_synthesis_decisions_node_name"),
        "strategy_synthesis_decisions",
        ["node_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_synthesis_decisions_regime"),
        "strategy_synthesis_decisions",
        ["regime"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_synthesis_decisions_runtime_id"),
        "strategy_synthesis_decisions",
        ["runtime_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_synthesis_decisions_selected_perspective"),
        "strategy_synthesis_decisions",
        ["selected_perspective"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_synthesis_decisions_selection_status"),
        "strategy_synthesis_decisions",
        ["selection_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_synthesis_decisions_symbol"),
        "strategy_synthesis_decisions",
        ["symbol"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_synthesis_decisions_workflow_name"),
        "strategy_synthesis_decisions",
        ["workflow_name"],
        unique=False,
    )
    op.create_index(
        "idx_strategy_decisions_execution_node",
        "strategy_synthesis_decisions",
        ["execution_id", "node_name"],
        unique=False,
    )
    op.create_index(
        "idx_strategy_decisions_status_confidence",
        "strategy_synthesis_decisions",
        ["selection_status", "confidence"],
        unique=False,
    )
    op.create_index(
        "idx_strategy_decisions_symbol_horizon_as_of",
        "strategy_synthesis_decisions",
        ["symbol", "horizon", "as_of"],
        unique=False,
    )

    op.create_table(
        "strategy_hypothesis_evaluations",
        sa.Column("evaluation_id", sa.String(), nullable=False),
        sa.Column("decision_id", sa.String(), nullable=False),
        sa.Column("hypothesis_id", sa.String(), nullable=True),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("perspective", sa.String(), nullable=False),
        sa.Column("perspective_weight", sa.Float(), nullable=False),
        sa.Column("contradiction_burden", sa.Float(), nullable=False),
        sa.Column("assumption_support", sa.Float(), nullable=False),
        sa.Column("invalidated", sa.Boolean(), nullable=False),
        sa.Column("candidate_score", sa.Float(), nullable=False),
        sa.Column("posterior_weight", sa.Float(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("selection_status", sa.String(), nullable=False),
        sa.Column("evidence_fingerprint", sa.String(), nullable=False),
        sa.Column("horizon", sa.String(), nullable=True),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workflow_name", sa.String(), nullable=True),
        sa.Column("execution_id", sa.String(), nullable=True),
        sa.Column("runtime_id", sa.String(), nullable=True),
        sa.Column("node_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("degraded_reasons", _jsonb(), nullable=False),
        sa.Column("metadata", _jsonb(), nullable=False),
        sa.Column(
            "row_created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "row_updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["decision_id"],
            ["strategy_synthesis_decisions.decision_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["hypothesis_id"],
            ["strategy_hypotheses.hypothesis_id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("evaluation_id"),
    )
    op.create_index(
        op.f("ix_strategy_hypothesis_evaluations_as_of"),
        "strategy_hypothesis_evaluations",
        ["as_of"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypothesis_evaluations_created_at"),
        "strategy_hypothesis_evaluations",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypothesis_evaluations_decision_id"),
        "strategy_hypothesis_evaluations",
        ["decision_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypothesis_evaluations_evidence_fingerprint"),
        "strategy_hypothesis_evaluations",
        ["evidence_fingerprint"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypothesis_evaluations_execution_id"),
        "strategy_hypothesis_evaluations",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypothesis_evaluations_horizon"),
        "strategy_hypothesis_evaluations",
        ["horizon"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypothesis_evaluations_hypothesis_id"),
        "strategy_hypothesis_evaluations",
        ["hypothesis_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypothesis_evaluations_invalidated"),
        "strategy_hypothesis_evaluations",
        ["invalidated"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypothesis_evaluations_node_name"),
        "strategy_hypothesis_evaluations",
        ["node_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypothesis_evaluations_perspective"),
        "strategy_hypothesis_evaluations",
        ["perspective"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypothesis_evaluations_rank"),
        "strategy_hypothesis_evaluations",
        ["rank"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypothesis_evaluations_runtime_id"),
        "strategy_hypothesis_evaluations",
        ["runtime_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypothesis_evaluations_selection_status"),
        "strategy_hypothesis_evaluations",
        ["selection_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypothesis_evaluations_symbol"),
        "strategy_hypothesis_evaluations",
        ["symbol"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strategy_hypothesis_evaluations_workflow_name"),
        "strategy_hypothesis_evaluations",
        ["workflow_name"],
        unique=False,
    )
    op.create_index(
        "idx_strategy_evaluations_decision_perspective",
        "strategy_hypothesis_evaluations",
        ["decision_id", "perspective"],
        unique=False,
    )
    op.create_index(
        "idx_strategy_evaluations_execution_node",
        "strategy_hypothesis_evaluations",
        ["execution_id", "node_name"],
        unique=False,
    )
    op.create_index(
        "idx_strategy_evaluations_symbol_rank",
        "strategy_hypothesis_evaluations",
        ["symbol", "rank"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_strategy_evaluations_symbol_rank",
        table_name="strategy_hypothesis_evaluations",
    )
    op.drop_index(
        "idx_strategy_evaluations_execution_node",
        table_name="strategy_hypothesis_evaluations",
    )
    op.drop_index(
        "idx_strategy_evaluations_decision_perspective",
        table_name="strategy_hypothesis_evaluations",
    )
    op.drop_index(
        op.f("ix_strategy_hypothesis_evaluations_workflow_name"),
        table_name="strategy_hypothesis_evaluations",
    )
    op.drop_index(
        op.f("ix_strategy_hypothesis_evaluations_symbol"),
        table_name="strategy_hypothesis_evaluations",
    )
    op.drop_index(
        op.f("ix_strategy_hypothesis_evaluations_selection_status"),
        table_name="strategy_hypothesis_evaluations",
    )
    op.drop_index(
        op.f("ix_strategy_hypothesis_evaluations_runtime_id"),
        table_name="strategy_hypothesis_evaluations",
    )
    op.drop_index(
        op.f("ix_strategy_hypothesis_evaluations_rank"),
        table_name="strategy_hypothesis_evaluations",
    )
    op.drop_index(
        op.f("ix_strategy_hypothesis_evaluations_perspective"),
        table_name="strategy_hypothesis_evaluations",
    )
    op.drop_index(
        op.f("ix_strategy_hypothesis_evaluations_node_name"),
        table_name="strategy_hypothesis_evaluations",
    )
    op.drop_index(
        op.f("ix_strategy_hypothesis_evaluations_invalidated"),
        table_name="strategy_hypothesis_evaluations",
    )
    op.drop_index(
        op.f("ix_strategy_hypothesis_evaluations_hypothesis_id"),
        table_name="strategy_hypothesis_evaluations",
    )
    op.drop_index(
        op.f("ix_strategy_hypothesis_evaluations_horizon"),
        table_name="strategy_hypothesis_evaluations",
    )
    op.drop_index(
        op.f("ix_strategy_hypothesis_evaluations_execution_id"),
        table_name="strategy_hypothesis_evaluations",
    )
    op.drop_index(
        op.f("ix_strategy_hypothesis_evaluations_evidence_fingerprint"),
        table_name="strategy_hypothesis_evaluations",
    )
    op.drop_index(
        op.f("ix_strategy_hypothesis_evaluations_decision_id"),
        table_name="strategy_hypothesis_evaluations",
    )
    op.drop_index(
        op.f("ix_strategy_hypothesis_evaluations_created_at"),
        table_name="strategy_hypothesis_evaluations",
    )
    op.drop_index(
        op.f("ix_strategy_hypothesis_evaluations_as_of"),
        table_name="strategy_hypothesis_evaluations",
    )
    op.drop_table("strategy_hypothesis_evaluations")

    op.drop_index(
        "idx_strategy_decisions_symbol_horizon_as_of",
        table_name="strategy_synthesis_decisions",
    )
    op.drop_index(
        "idx_strategy_decisions_status_confidence",
        table_name="strategy_synthesis_decisions",
    )
    op.drop_index(
        "idx_strategy_decisions_execution_node",
        table_name="strategy_synthesis_decisions",
    )
    op.drop_index(
        op.f("ix_strategy_synthesis_decisions_workflow_name"),
        table_name="strategy_synthesis_decisions",
    )
    op.drop_index(
        op.f("ix_strategy_synthesis_decisions_symbol"),
        table_name="strategy_synthesis_decisions",
    )
    op.drop_index(
        op.f("ix_strategy_synthesis_decisions_selection_status"),
        table_name="strategy_synthesis_decisions",
    )
    op.drop_index(
        op.f("ix_strategy_synthesis_decisions_selected_perspective"),
        table_name="strategy_synthesis_decisions",
    )
    op.drop_index(
        op.f("ix_strategy_synthesis_decisions_runtime_id"),
        table_name="strategy_synthesis_decisions",
    )
    op.drop_index(
        op.f("ix_strategy_synthesis_decisions_regime"),
        table_name="strategy_synthesis_decisions",
    )
    op.drop_index(
        op.f("ix_strategy_synthesis_decisions_node_name"),
        table_name="strategy_synthesis_decisions",
    )
    op.drop_index(
        op.f("ix_strategy_synthesis_decisions_horizon"),
        table_name="strategy_synthesis_decisions",
    )
    op.drop_index(
        op.f("ix_strategy_synthesis_decisions_execution_id"),
        table_name="strategy_synthesis_decisions",
    )
    op.drop_index(
        op.f("ix_strategy_synthesis_decisions_evidence_fingerprint"),
        table_name="strategy_synthesis_decisions",
    )
    op.drop_index(
        op.f("ix_strategy_synthesis_decisions_created_at"),
        table_name="strategy_synthesis_decisions",
    )
    op.drop_index(
        op.f("ix_strategy_synthesis_decisions_as_of"),
        table_name="strategy_synthesis_decisions",
    )
    op.drop_table("strategy_synthesis_decisions")

    op.drop_index(
        "idx_strategy_hypotheses_symbol_horizon_as_of",
        table_name="strategy_hypotheses",
    )
    op.drop_index(
        "idx_strategy_hypotheses_perspective_fingerprint",
        table_name="strategy_hypotheses",
    )
    op.drop_index(
        "idx_strategy_hypotheses_execution_node",
        table_name="strategy_hypotheses",
    )
    op.drop_index(
        op.f("ix_strategy_hypotheses_workflow_name"),
        table_name="strategy_hypotheses",
    )
    op.drop_index(
        op.f("ix_strategy_hypotheses_symbol"),
        table_name="strategy_hypotheses",
    )
    op.drop_index(
        op.f("ix_strategy_hypotheses_runtime_id"),
        table_name="strategy_hypotheses",
    )
    op.drop_index(
        op.f("ix_strategy_hypotheses_perspective"),
        table_name="strategy_hypotheses",
    )
    op.drop_index(
        op.f("ix_strategy_hypotheses_node_name"),
        table_name="strategy_hypotheses",
    )
    op.drop_index(
        op.f("ix_strategy_hypotheses_invalidated"),
        table_name="strategy_hypotheses",
    )
    op.drop_index(
        op.f("ix_strategy_hypotheses_horizon"),
        table_name="strategy_hypotheses",
    )
    op.drop_index(
        op.f("ix_strategy_hypotheses_execution_id"),
        table_name="strategy_hypotheses",
    )
    op.drop_index(
        op.f("ix_strategy_hypotheses_evidence_fingerprint"),
        table_name="strategy_hypotheses",
    )
    op.drop_index(
        op.f("ix_strategy_hypotheses_created_at"),
        table_name="strategy_hypotheses",
    )
    op.drop_index(
        op.f("ix_strategy_hypotheses_as_of"),
        table_name="strategy_hypotheses",
    )
    op.drop_table("strategy_hypotheses")
