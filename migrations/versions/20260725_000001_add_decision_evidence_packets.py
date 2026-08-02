"""add_decision_evidence_packets_and_claim_evidence_links

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

    op.create_table(
        "report_claim_evidence_links",
        sa.Column("link_id", sa.String(), nullable=False),
        sa.Column("report_id", sa.String(), nullable=False),
        sa.Column("section_id", sa.String(), nullable=True),
        sa.Column("claim_target_id", sa.String(), nullable=False),
        sa.Column("packet_id", sa.String(), nullable=False),
        sa.Column("packet_claim_id", sa.String(), nullable=False),
        sa.Column("risk_tier", sa.String(), nullable=False),
        sa.Column(
            "material",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "supporting_evidence_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "reconstruction_reference_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "uncertainty_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "limitation_ids",
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
        sa.ForeignKeyConstraint(
            ["packet_id"],
            ["decision_evidence_packets.packet_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["reports.report_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["report_sections.section_id"],
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "risk_tier IN ('enhanced', 'vigilant')",
            name="ck_report_claim_evidence_links_risk_tier",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(supporting_evidence_ids) = 'array'",
            name="ck_report_claim_evidence_links_supporting_ids_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(reconstruction_reference_ids) = 'array'",
            name="ck_report_claim_evidence_links_reconstruction_ids_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(uncertainty_ids) = 'array'",
            name="ck_report_claim_evidence_links_uncertainty_ids_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(limitation_ids) = 'array'",
            name="ck_report_claim_evidence_links_limitation_ids_array",
        ),
        sa.CheckConstraint(
            "NOT (material AND (jsonb_array_length(supporting_evidence_ids) = 0 "
            "OR jsonb_array_length(reconstruction_reference_ids) = 0))",
            name="ck_report_claim_evidence_links_material_has_support",
        ),
        sa.PrimaryKeyConstraint("link_id"),
    )
    op.create_index(
        "ix_report_claim_evidence_links_claim_target_id",
        "report_claim_evidence_links",
        ["claim_target_id"],
        unique=False,
    )
    op.create_index(
        "ix_report_claim_evidence_links_packet_claim_id",
        "report_claim_evidence_links",
        ["packet_claim_id"],
        unique=False,
    )
    op.create_index(
        "ix_report_claim_evidence_links_packet_id",
        "report_claim_evidence_links",
        ["packet_id"],
        unique=False,
    )
    op.create_index(
        "ix_report_claim_evidence_links_report_id",
        "report_claim_evidence_links",
        ["report_id"],
        unique=False,
    )
    op.create_index(
        "ix_report_claim_evidence_links_risk_tier",
        "report_claim_evidence_links",
        ["risk_tier"],
        unique=False,
    )
    op.create_index(
        "ix_report_claim_evidence_links_section_id",
        "report_claim_evidence_links",
        ["section_id"],
        unique=False,
    )
    op.create_index(
        "idx_report_claim_evidence_links_packet_claim",
        "report_claim_evidence_links",
        ["packet_id", "packet_claim_id"],
        unique=False,
    )
    op.create_index(
        "idx_report_claim_evidence_links_report_claim",
        "report_claim_evidence_links",
        ["report_id", "claim_target_id"],
        unique=False,
    )

    op.create_table(
        "recommendation_claim_evidence_links",
        sa.Column("link_id", sa.String(), nullable=False),
        sa.Column("recommendation_id", sa.String(), nullable=False),
        sa.Column("rationale_id", sa.String(), nullable=True),
        sa.Column("claim_target_id", sa.String(), nullable=False),
        sa.Column("packet_id", sa.String(), nullable=False),
        sa.Column("packet_claim_id", sa.String(), nullable=False),
        sa.Column("risk_tier", sa.String(), nullable=False),
        sa.Column(
            "material",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "supporting_evidence_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "reconstruction_reference_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "uncertainty_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "limitation_ids",
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
        sa.ForeignKeyConstraint(
            ["packet_id"],
            ["decision_evidence_packets.packet_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_id"],
            ["recommendations.recommendation_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["rationale_id"],
            ["recommendation_rationales.rationale_id"],
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "risk_tier IN ('enhanced', 'vigilant')",
            name="ck_recommendation_claim_evidence_links_risk_tier",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(supporting_evidence_ids) = 'array'",
            name="ck_recommendation_claim_evidence_links_supporting_ids_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(reconstruction_reference_ids) = 'array'",
            name="ck_recommendation_claim_evidence_links_reconstruction_ids_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(uncertainty_ids) = 'array'",
            name="ck_recommendation_claim_evidence_links_uncertainty_ids_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(limitation_ids) = 'array'",
            name="ck_recommendation_claim_evidence_links_limitation_ids_array",
        ),
        sa.CheckConstraint(
            "NOT (material AND (jsonb_array_length(supporting_evidence_ids) = 0 "
            "OR jsonb_array_length(reconstruction_reference_ids) = 0))",
            name="ck_recommendation_claim_evidence_links_material_has_support",
        ),
        sa.PrimaryKeyConstraint("link_id"),
    )
    op.create_index(
        "ix_recommendation_claim_evidence_links_claim_target_id",
        "recommendation_claim_evidence_links",
        ["claim_target_id"],
        unique=False,
    )
    op.create_index(
        "ix_recommendation_claim_evidence_links_packet_claim_id",
        "recommendation_claim_evidence_links",
        ["packet_claim_id"],
        unique=False,
    )
    op.create_index(
        "ix_recommendation_claim_evidence_links_packet_id",
        "recommendation_claim_evidence_links",
        ["packet_id"],
        unique=False,
    )
    op.create_index(
        "ix_recommendation_claim_evidence_links_rationale_id",
        "recommendation_claim_evidence_links",
        ["rationale_id"],
        unique=False,
    )
    op.create_index(
        "ix_recommendation_claim_evidence_links_recommendation_id",
        "recommendation_claim_evidence_links",
        ["recommendation_id"],
        unique=False,
    )
    op.create_index(
        "ix_recommendation_claim_evidence_links_risk_tier",
        "recommendation_claim_evidence_links",
        ["risk_tier"],
        unique=False,
    )
    op.create_index(
        "idx_recommendation_claim_evidence_links_packet_claim",
        "recommendation_claim_evidence_links",
        ["packet_id", "packet_claim_id"],
        unique=False,
    )
    op.create_index(
        "idx_recommendation_claim_evidence_links_recommendation_claim",
        "recommendation_claim_evidence_links",
        ["recommendation_id", "claim_target_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_recommendation_claim_evidence_links_recommendation_claim",
        table_name="recommendation_claim_evidence_links",
    )
    op.drop_index(
        "idx_recommendation_claim_evidence_links_packet_claim",
        table_name="recommendation_claim_evidence_links",
    )
    op.drop_index(
        "ix_recommendation_claim_evidence_links_risk_tier",
        table_name="recommendation_claim_evidence_links",
    )
    op.drop_index(
        "ix_recommendation_claim_evidence_links_recommendation_id",
        table_name="recommendation_claim_evidence_links",
    )
    op.drop_index(
        "ix_recommendation_claim_evidence_links_rationale_id",
        table_name="recommendation_claim_evidence_links",
    )
    op.drop_index(
        "ix_recommendation_claim_evidence_links_packet_id",
        table_name="recommendation_claim_evidence_links",
    )
    op.drop_index(
        "ix_recommendation_claim_evidence_links_packet_claim_id",
        table_name="recommendation_claim_evidence_links",
    )
    op.drop_index(
        "ix_recommendation_claim_evidence_links_claim_target_id",
        table_name="recommendation_claim_evidence_links",
    )
    op.drop_table("recommendation_claim_evidence_links")

    op.drop_index(
        "idx_report_claim_evidence_links_report_claim",
        table_name="report_claim_evidence_links",
    )
    op.drop_index(
        "idx_report_claim_evidence_links_packet_claim",
        table_name="report_claim_evidence_links",
    )
    op.drop_index(
        "ix_report_claim_evidence_links_section_id",
        table_name="report_claim_evidence_links",
    )
    op.drop_index(
        "ix_report_claim_evidence_links_risk_tier",
        table_name="report_claim_evidence_links",
    )
    op.drop_index(
        "ix_report_claim_evidence_links_report_id",
        table_name="report_claim_evidence_links",
    )
    op.drop_index(
        "ix_report_claim_evidence_links_packet_id",
        table_name="report_claim_evidence_links",
    )
    op.drop_index(
        "ix_report_claim_evidence_links_packet_claim_id",
        table_name="report_claim_evidence_links",
    )
    op.drop_index(
        "ix_report_claim_evidence_links_claim_target_id",
        table_name="report_claim_evidence_links",
    )
    op.drop_table("report_claim_evidence_links")

    op.drop_index(
        "idx_decision_evidence_packets_risk_tier",
        table_name="decision_evidence_packets",
    )
    op.drop_index(
        "idx_decision_evidence_packets_output_id",
        table_name="decision_evidence_packets",
    )
    op.drop_table("decision_evidence_packets")
