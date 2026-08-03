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
        "automated_policy_audit_records",
        sa.Column("audit_record_id", sa.String(), nullable=False),
        sa.Column("subject_type", sa.String(), nullable=False),
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column("risk_tier", sa.String(), nullable=False),
        sa.Column(
            "authority_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("evidence_packet_id", sa.String(), nullable=True),
        sa.Column("evidence_packet_version", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("policy_name", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
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
        sa.CheckConstraint(
            "outcome IN ('allow', 'warn', 'deny', 'skip')",
            name="ck_automated_policy_audit_records_outcome",
        ),
        sa.CheckConstraint(
            "risk_tier IN ('baseline', 'enhanced', 'vigilant', "
            "'prohibited_outside_authority')",
            name="ck_automated_policy_audit_records_risk_tier",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(authority_metadata) = 'object'",
            name="ck_automated_policy_audit_records_authority_metadata_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(metadata) = 'object'",
            name="ck_automated_policy_audit_records_metadata_object",
        ),
        sa.PrimaryKeyConstraint("audit_record_id"),
    )
    op.create_index(
        "ix_automated_policy_audit_records_subject_type",
        "automated_policy_audit_records",
        ["subject_type"],
        unique=False,
    )
    op.create_index(
        "ix_automated_policy_audit_records_subject_id",
        "automated_policy_audit_records",
        ["subject_id"],
        unique=False,
    )
    op.create_index(
        "ix_automated_policy_audit_records_risk_tier",
        "automated_policy_audit_records",
        ["risk_tier"],
        unique=False,
    )
    op.create_index(
        "ix_automated_policy_audit_records_evidence_packet_id",
        "automated_policy_audit_records",
        ["evidence_packet_id"],
        unique=False,
    )
    op.create_index(
        "ix_automated_policy_audit_records_outcome",
        "automated_policy_audit_records",
        ["outcome"],
        unique=False,
    )
    op.create_index(
        "ix_automated_policy_audit_records_policy_name",
        "automated_policy_audit_records",
        ["policy_name"],
        unique=False,
    )
    op.create_index(
        "ix_automated_policy_audit_records_timestamp",
        "automated_policy_audit_records",
        ["timestamp"],
        unique=False,
    )
    op.create_index(
        "idx_automated_policy_audit_subject_outcome",
        "automated_policy_audit_records",
        ["subject_type", "subject_id", "outcome"],
        unique=False,
    )
    op.create_index(
        "idx_automated_policy_audit_evidence_outcome",
        "automated_policy_audit_records",
        ["evidence_packet_id", "outcome"],
        unique=False,
    )

    op.create_table(
        "automated_governance_audit_records",
        sa.Column("audit_record_id", sa.String(), nullable=False),
        sa.Column("subject_type", sa.String(), nullable=False),
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column("risk_tier", sa.String(), nullable=False),
        sa.Column(
            "authority_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("evidence_packet_id", sa.String(), nullable=True),
        sa.Column("evidence_packet_version", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("rule_name", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
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
        sa.CheckConstraint(
            "outcome IN ('allow', 'warn', 'deny', 'require_approval', 'skip')",
            name="ck_automated_governance_audit_records_outcome",
        ),
        sa.CheckConstraint(
            "risk_tier IN ('baseline', 'enhanced', 'vigilant', "
            "'prohibited_outside_authority')",
            name="ck_automated_governance_audit_records_risk_tier",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(authority_metadata) = 'object'",
            name="ck_automated_governance_audit_records_authority_metadata_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(metadata) = 'object'",
            name="ck_automated_governance_audit_records_metadata_object",
        ),
        sa.PrimaryKeyConstraint("audit_record_id"),
    )
    op.create_index(
        "ix_automated_governance_audit_records_subject_type",
        "automated_governance_audit_records",
        ["subject_type"],
        unique=False,
    )
    op.create_index(
        "ix_automated_governance_audit_records_subject_id",
        "automated_governance_audit_records",
        ["subject_id"],
        unique=False,
    )
    op.create_index(
        "ix_automated_governance_audit_records_risk_tier",
        "automated_governance_audit_records",
        ["risk_tier"],
        unique=False,
    )
    op.create_index(
        "ix_automated_governance_audit_records_evidence_packet_id",
        "automated_governance_audit_records",
        ["evidence_packet_id"],
        unique=False,
    )
    op.create_index(
        "ix_automated_governance_audit_records_outcome",
        "automated_governance_audit_records",
        ["outcome"],
        unique=False,
    )
    op.create_index(
        "ix_automated_governance_audit_records_rule_name",
        "automated_governance_audit_records",
        ["rule_name"],
        unique=False,
    )
    op.create_index(
        "ix_automated_governance_audit_records_timestamp",
        "automated_governance_audit_records",
        ["timestamp"],
        unique=False,
    )
    op.create_index(
        "idx_automated_governance_audit_subject_outcome",
        "automated_governance_audit_records",
        ["subject_type", "subject_id", "outcome"],
        unique=False,
    )
    op.create_index(
        "idx_automated_governance_audit_evidence_outcome",
        "automated_governance_audit_records",
        ["evidence_packet_id", "outcome"],
        unique=False,
    )

    op.create_table(
        "governance_review_tasks",
        sa.Column("review_task_id", sa.String(), nullable=False),
        sa.Column("automated_governance_audit_record_id", sa.String(), nullable=False),
        sa.Column("subject_type", sa.String(), nullable=False),
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column("risk_tier", sa.String(), nullable=False),
        sa.Column(
            "authority_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("review_scope", sa.String(), nullable=False),
        sa.Column("intended_sink", sa.String(), nullable=False),
        sa.Column("requested_action", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("evidence_packet_id", sa.String(), nullable=False),
        sa.Column("evidence_packet_version", sa.Integer(), nullable=False),
        sa.Column(
            "evidence_references",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.CheckConstraint(
            "risk_tier IN ('baseline', 'enhanced', 'vigilant', "
            "'prohibited_outside_authority')",
            name="ck_governance_review_tasks_risk_tier",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'in_review', 'approved', 'denied', "
            "'changes_requested', 'cancelled')",
            name="ck_governance_review_tasks_status",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(authority_metadata) = 'object'",
            name="ck_governance_review_tasks_authority_metadata_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(evidence_references) = 'object'",
            name="ck_governance_review_tasks_evidence_references_object",
        ),
        sa.ForeignKeyConstraint(
            ["automated_governance_audit_record_id"],
            ["automated_governance_audit_records.audit_record_id"],
        ),
        sa.PrimaryKeyConstraint("review_task_id"),
        sa.UniqueConstraint(
            "subject_type",
            "subject_id",
            "evidence_packet_id",
            "evidence_packet_version",
            "review_scope",
            "requested_action",
            name="uq_governance_review_tasks_scoped_evidence_action",
        ),
    )
    op.create_index(
        "ix_governance_review_tasks_automated_governance_audit_record_id",
        "governance_review_tasks",
        ["automated_governance_audit_record_id"],
        unique=False,
    )
    op.create_index(
        "ix_governance_review_tasks_subject_type",
        "governance_review_tasks",
        ["subject_type"],
        unique=False,
    )
    op.create_index(
        "ix_governance_review_tasks_subject_id",
        "governance_review_tasks",
        ["subject_id"],
        unique=False,
    )
    op.create_index(
        "ix_governance_review_tasks_risk_tier",
        "governance_review_tasks",
        ["risk_tier"],
        unique=False,
    )
    op.create_index(
        "ix_governance_review_tasks_review_scope",
        "governance_review_tasks",
        ["review_scope"],
        unique=False,
    )
    op.create_index(
        "ix_governance_review_tasks_intended_sink",
        "governance_review_tasks",
        ["intended_sink"],
        unique=False,
    )
    op.create_index(
        "ix_governance_review_tasks_requested_action",
        "governance_review_tasks",
        ["requested_action"],
        unique=False,
    )
    op.create_index(
        "ix_governance_review_tasks_status",
        "governance_review_tasks",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_governance_review_tasks_evidence_packet_id",
        "governance_review_tasks",
        ["evidence_packet_id"],
        unique=False,
    )
    op.create_index(
        "ix_governance_review_tasks_created_at",
        "governance_review_tasks",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_governance_review_tasks_updated_at",
        "governance_review_tasks",
        ["updated_at"],
        unique=False,
    )
    op.create_index(
        "idx_governance_review_tasks_subject_status",
        "governance_review_tasks",
        ["subject_type", "subject_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_governance_review_tasks_evidence_status",
        "governance_review_tasks",
        ["evidence_packet_id", "evidence_packet_version", "status"],
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
        "idx_governance_review_tasks_evidence_status",
        table_name="governance_review_tasks",
    )
    op.drop_index(
        "idx_governance_review_tasks_subject_status",
        table_name="governance_review_tasks",
    )
    op.drop_index(
        "ix_governance_review_tasks_updated_at",
        table_name="governance_review_tasks",
    )
    op.drop_index(
        "ix_governance_review_tasks_created_at",
        table_name="governance_review_tasks",
    )
    op.drop_index(
        "ix_governance_review_tasks_evidence_packet_id",
        table_name="governance_review_tasks",
    )
    op.drop_index(
        "ix_governance_review_tasks_status",
        table_name="governance_review_tasks",
    )
    op.drop_index(
        "ix_governance_review_tasks_requested_action",
        table_name="governance_review_tasks",
    )
    op.drop_index(
        "ix_governance_review_tasks_intended_sink",
        table_name="governance_review_tasks",
    )
    op.drop_index(
        "ix_governance_review_tasks_review_scope",
        table_name="governance_review_tasks",
    )
    op.drop_index(
        "ix_governance_review_tasks_risk_tier",
        table_name="governance_review_tasks",
    )
    op.drop_index(
        "ix_governance_review_tasks_subject_id",
        table_name="governance_review_tasks",
    )
    op.drop_index(
        "ix_governance_review_tasks_subject_type",
        table_name="governance_review_tasks",
    )
    op.drop_index(
        "ix_governance_review_tasks_automated_governance_audit_record_id",
        table_name="governance_review_tasks",
    )
    op.drop_table("governance_review_tasks")

    op.drop_index(
        "idx_automated_governance_audit_evidence_outcome",
        table_name="automated_governance_audit_records",
    )
    op.drop_index(
        "idx_automated_governance_audit_subject_outcome",
        table_name="automated_governance_audit_records",
    )
    op.drop_index(
        "ix_automated_governance_audit_records_timestamp",
        table_name="automated_governance_audit_records",
    )
    op.drop_index(
        "ix_automated_governance_audit_records_rule_name",
        table_name="automated_governance_audit_records",
    )
    op.drop_index(
        "ix_automated_governance_audit_records_outcome",
        table_name="automated_governance_audit_records",
    )
    op.drop_index(
        "ix_automated_governance_audit_records_evidence_packet_id",
        table_name="automated_governance_audit_records",
    )
    op.drop_index(
        "ix_automated_governance_audit_records_risk_tier",
        table_name="automated_governance_audit_records",
    )
    op.drop_index(
        "ix_automated_governance_audit_records_subject_id",
        table_name="automated_governance_audit_records",
    )
    op.drop_index(
        "ix_automated_governance_audit_records_subject_type",
        table_name="automated_governance_audit_records",
    )
    op.drop_table("automated_governance_audit_records")

    op.drop_index(
        "idx_automated_policy_audit_evidence_outcome",
        table_name="automated_policy_audit_records",
    )
    op.drop_index(
        "idx_automated_policy_audit_subject_outcome",
        table_name="automated_policy_audit_records",
    )
    op.drop_index(
        "ix_automated_policy_audit_records_timestamp",
        table_name="automated_policy_audit_records",
    )
    op.drop_index(
        "ix_automated_policy_audit_records_policy_name",
        table_name="automated_policy_audit_records",
    )
    op.drop_index(
        "ix_automated_policy_audit_records_outcome",
        table_name="automated_policy_audit_records",
    )
    op.drop_index(
        "ix_automated_policy_audit_records_evidence_packet_id",
        table_name="automated_policy_audit_records",
    )
    op.drop_index(
        "ix_automated_policy_audit_records_risk_tier",
        table_name="automated_policy_audit_records",
    )
    op.drop_index(
        "ix_automated_policy_audit_records_subject_id",
        table_name="automated_policy_audit_records",
    )
    op.drop_index(
        "ix_automated_policy_audit_records_subject_type",
        table_name="automated_policy_audit_records",
    )
    op.drop_table("automated_policy_audit_records")
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
