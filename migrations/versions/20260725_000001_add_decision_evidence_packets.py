"""add_decision_evidence_packets

Revision ID: a65d90e0190
Revises: 9d1e2f3a4b5c
Create Date: 2026-07-25 00:00:01.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a65d90e0190"
down_revision: str | None = "9d1e2f3a4b5c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decision_evidence_packets",
        sa.Column("packet_id", sa.String(), nullable=False),
        sa.Column("output_id", sa.String(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("risk_tier", sa.String(), nullable=False),
        sa.Column(
            "authority_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "retention_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "reconstruction_reference_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "claim_audit",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "evidence_references",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "reconstruction_references",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "constraints",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "uncertainties",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "limitations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
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
            "risk_tier IN ('enhanced', 'vigilant')",
            name="ck_decision_evidence_packets_risk_tier",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(authority_metadata) = 'object'",
            name="ck_decision_evidence_packets_authority_metadata_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(retention_metadata) = 'object'",
            name="ck_decision_evidence_packets_retention_metadata_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(reconstruction_reference_ids) = 'array'",
            name="ck_decision_evidence_packets_reconstruction_ids_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(claim_audit) = 'array'",
            name="ck_decision_evidence_packets_claim_audit_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(evidence_references) = 'array'",
            name="ck_decision_evidence_packets_evidence_refs_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(reconstruction_references) = 'array'",
            name="ck_decision_evidence_packets_reconstruction_refs_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(constraints) = 'array'",
            name="ck_decision_evidence_packets_constraints_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(uncertainties) = 'array'",
            name="ck_decision_evidence_packets_uncertainties_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(limitations) = 'array'",
            name="ck_decision_evidence_packets_limitations_array",
        ),
        sa.PrimaryKeyConstraint("packet_id"),
    )
    op.create_index(
        "idx_decision_evidence_packets_output_id",
        "decision_evidence_packets",
        ["output_id"],
        unique=False,
    )
    op.create_index(
        "idx_decision_evidence_packets_risk_tier",
        "decision_evidence_packets",
        ["risk_tier"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_decision_evidence_packets_risk_tier",
        table_name="decision_evidence_packets",
    )
    op.drop_index(
        "idx_decision_evidence_packets_output_id",
        table_name="decision_evidence_packets",
    )
    op.drop_table("decision_evidence_packets")
