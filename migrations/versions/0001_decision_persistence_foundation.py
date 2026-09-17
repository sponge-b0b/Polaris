"""Establish the greenfield Decision persistence foundation.

Revision ID: 0001_decision_persistence
Revises: None
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_decision_persistence"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decision_needs",
        sa.Column("row_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("need_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_attribution_kind", sa.String(length=16), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "actor_candidate_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=True,
        ),
        sa.Column("trigger_kind", sa.String(length=32), nullable=False),
        sa.Column("trigger_reference", sa.Text(), nullable=False),
        sa.Column(
            "technical_provenance",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "actor_attribution_kind IN ('known', 'unknown', 'contested')",
            name="ck_decision_needs_actor_attribution_kind",
        ),
        sa.CheckConstraint(
            "(actor_attribution_kind = 'known' AND actor_id IS NOT NULL "
            "AND actor_candidate_ids IS NULL) OR "
            "(actor_attribution_kind = 'unknown' AND actor_id IS NULL "
            "AND actor_candidate_ids IS NULL) OR "
            "(actor_attribution_kind = 'contested' AND actor_id IS NULL "
            "AND cardinality(actor_candidate_ids) > 0)",
            name="ck_decision_needs_actor_attribution_shape",
        ),
        sa.CheckConstraint(
            "btrim(statement) <> ''", name="ck_decision_needs_statement_nonempty"
        ),
        sa.CheckConstraint(
            "btrim(trigger_reference) <> ''",
            name="ck_decision_needs_trigger_reference_nonempty",
        ),
        sa.PrimaryKeyConstraint("row_id", name="pk_decision_needs"),
        sa.UniqueConstraint("need_id", name="uq_decision_needs_need_id"),
    )

    op.create_table(
        "investment_decisions",
        sa.Column("row_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("need_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_statement", sa.Text(), nullable=False),
        sa.Column("scope_completeness", sa.String(length=16), nullable=False),
        sa.Column(
            "scope_portfolio_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            server_default=sa.text("'{}'::uuid[]"),
            nullable=False,
        ),
        sa.Column(
            "lifecycle_interpretation_kind",
            sa.String(length=24),
            nullable=False,
        ),
        sa.Column("lifecycle_disposition", sa.String(length=32), nullable=True),
        sa.Column("lifecycle_effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lifecycle_known_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "lifecycle_support_fact_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            server_default=sa.text("'{}'::uuid[]"),
            nullable=False,
        ),
        sa.Column("work_posture", sa.String(length=16), nullable=True),
        sa.Column("applicability", sa.String(length=20), nullable=False),
        sa.Column("decision_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "rebuild_required",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "applicability IN ('operative', 'non_operative', 'contested')",
            name="ck_investment_decisions_applicability",
        ),
        sa.CheckConstraint(
            "decision_version >= 1",
            name="ck_investment_decisions_decision_version_positive",
        ),
        sa.CheckConstraint(
            "scope_completeness <> 'established' "
            "OR cardinality(scope_portfolio_ids) > 0",
            name="ck_investment_decisions_established_scope_nonempty",
        ),
        sa.CheckConstraint(
            "lifecycle_interpretation_kind IN "
            "('NOT_YET_EFFECTIVE', 'DETERMINATE', 'CONTESTED')",
            name="ck_investment_decisions_lifecycle_interpretation_kind",
        ),
        sa.CheckConstraint(
            "scope_completeness IN ('unresolved', 'established')",
            name="ck_investment_decisions_scope_completeness",
        ),
        sa.CheckConstraint(
            "btrim(subject_statement) <> ''",
            name="ck_investment_decisions_subject_nonempty",
        ),
        sa.ForeignKeyConstraint(
            ["need_id"],
            ["decision_needs.need_id"],
            name="fk_investment_decisions_need_id_decision_needs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("row_id", name="pk_investment_decisions"),
        sa.UniqueConstraint("decision_id", name="uq_investment_decisions_decision_id"),
        sa.UniqueConstraint("need_id", name="uq_investment_decisions_need_id"),
    )
    op.create_index(
        "ix_investment_decisions_continuity_candidates",
        "investment_decisions",
        ["lifecycle_disposition", "applicability"],
        unique=False,
    )

    op.create_table(
        "investment_decision_lifecycle_facts",
        sa.Column("row_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("fact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lifecycle_sequence", sa.Integer(), nullable=False),
        sa.Column("decision_version", sa.Integer(), nullable=False),
        sa.Column("fact_kind", sa.String(length=48), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_attribution_kind", sa.String(length=16), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "actor_candidate_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=True,
        ),
        sa.Column("trigger_kind", sa.String(length=32), nullable=False),
        sa.Column("trigger_reference", sa.Text(), nullable=False),
        sa.Column(
            "technical_provenance",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("need_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject_statement", sa.Text(), nullable=True),
        sa.Column("scope_completeness", sa.String(length=16), nullable=True),
        sa.Column(
            "scope_portfolio_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=True,
        ),
        sa.Column("continuity_determination", sa.String(length=32), nullable=True),
        sa.Column(
            "continuity_candidate_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=True,
        ),
        sa.Column("continuity_known_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("continuity_rationale", sa.Text(), nullable=True),
        sa.Column("human_decision_reference", sa.Text(), nullable=True),
        sa.Column("human_decision_effect", sa.String(length=32), nullable=True),
        sa.Column("work_control_reference", sa.Text(), nullable=True),
        sa.Column("external_resolution_reference", sa.Text(), nullable=True),
        sa.Column(
            "correction_target_fact_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("correction_effect", sa.String(length=16), nullable=True),
        sa.Column("correction_basis_reference", sa.Text(), nullable=True),
        sa.Column("replacement_disposition", sa.String(length=32), nullable=True),
        sa.Column("replacement_basis_kind", sa.String(length=40), nullable=True),
        sa.Column("replacement_basis_reference", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "actor_attribution_kind IN ('known', 'unknown', 'contested')",
            name="ck_investment_decision_lifecycle_facts_actor_attribution_kind",
        ),
        sa.CheckConstraint(
            "(actor_attribution_kind = 'known' AND actor_id IS NOT NULL "
            "AND actor_candidate_ids IS NULL) OR "
            "(actor_attribution_kind = 'unknown' AND actor_id IS NULL "
            "AND actor_candidate_ids IS NULL) OR "
            "(actor_attribution_kind = 'contested' AND actor_id IS NULL "
            "AND cardinality(actor_candidate_ids) > 0)",
            name="ck_investment_decision_lifecycle_facts_actor_shape",
        ),
        sa.CheckConstraint(
            "decision_version >= 1",
            name="ck_investment_decision_lifecycle_facts_version_positive",
        ),
        sa.CheckConstraint(
            "scope_completeness IS DISTINCT FROM 'established' "
            "OR cardinality(scope_portfolio_ids) > 0",
            name="ck_investment_decision_lifecycle_facts_scope_nonempty",
        ),
        sa.CheckConstraint(
            "lifecycle_sequence >= 1",
            name="ck_investment_decision_lifecycle_facts_sequence_positive",
        ),
        sa.CheckConstraint(
            "scope_completeness IS NULL OR "
            "scope_completeness IN ('unresolved', 'established')",
            name="ck_investment_decision_lifecycle_facts_scope_completeness",
        ),
        sa.CheckConstraint(
            "btrim(trigger_reference) <> ''",
            name="ck_investment_decision_lifecycle_facts_trigger_nonempty",
        ),
        sa.ForeignKeyConstraint(
            ["correction_target_fact_id"],
            ["investment_decision_lifecycle_facts.fact_id"],
            name="fk_lifecycle_fact_correction_target",
        ),
        sa.ForeignKeyConstraint(
            ["decision_id"],
            ["investment_decisions.decision_id"],
            name="fk_lifecycle_fact_decision",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["need_id"],
            ["decision_needs.need_id"],
            name="fk_lifecycle_fact_need",
        ),
        sa.PrimaryKeyConstraint(
            "row_id", name="pk_investment_decision_lifecycle_facts"
        ),
        sa.UniqueConstraint(
            "decision_id",
            "lifecycle_sequence",
            name="uq_lifecycle_facts_decision_sequence",
        ),
        sa.UniqueConstraint(
            "fact_id", name="uq_investment_decision_lifecycle_facts_fact_id"
        ),
    )
    op.create_index(
        "ix_lifecycle_facts_decision_recorded",
        "investment_decision_lifecycle_facts",
        ["decision_id", "recorded_at"],
        unique=False,
    )

    op.create_table(
        "investment_decision_relationships",
        sa.Column("row_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column(
            "relationship_fact_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("source_decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_type", sa.String(length=32), nullable=False),
        sa.Column("fact_kind", sa.String(length=24), nullable=False),
        sa.Column(
            "target_relationship_fact_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_attribution_kind", sa.String(length=16), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "actor_candidate_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=True,
        ),
        sa.Column("trigger_kind", sa.String(length=32), nullable=False),
        sa.Column("trigger_reference", sa.Text(), nullable=False),
        sa.Column(
            "technical_provenance",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correction_effect", sa.String(length=16), nullable=True),
        sa.Column(
            "positive_claim_effective_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "positive_basis",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "correction_basis",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "admission_evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.CheckConstraint(
            "actor_attribution_kind IN ('known', 'unknown', 'contested')",
            name="ck_investment_decision_relationships_actor_kind",
        ),
        sa.CheckConstraint(
            "(actor_attribution_kind = 'known' AND actor_id IS NOT NULL "
            "AND actor_candidate_ids IS NULL) OR "
            "(actor_attribution_kind = 'unknown' AND actor_id IS NULL "
            "AND actor_candidate_ids IS NULL) OR "
            "(actor_attribution_kind = 'contested' AND actor_id IS NULL "
            "AND cardinality(actor_candidate_ids) > 0)",
            name="ck_investment_decision_relationships_actor_shape",
        ),
        sa.CheckConstraint(
            "source_decision_id <> target_decision_id",
            name="ck_investment_decision_relationships_distinct_endpoints",
        ),
        sa.CheckConstraint(
            "fact_kind IN ('base', 'correction')",
            name="ck_investment_decision_relationships_fact_kind",
        ),
        sa.CheckConstraint(
            "relationship_type IN ('renewed_from', 'supersedes')",
            name="ck_investment_decision_relationships_relationship_type",
        ),
        sa.CheckConstraint(
            "btrim(trigger_reference) <> ''",
            name="ck_investment_decision_relationships_trigger_nonempty",
        ),
        sa.ForeignKeyConstraint(
            ["source_decision_id"],
            ["investment_decisions.decision_id"],
            name="fk_relationship_source_decision",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_decision_id"],
            ["investment_decisions.decision_id"],
            name="fk_relationship_target_decision",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_relationship_fact_id"],
            ["investment_decision_relationships.relationship_fact_id"],
            name="fk_relationship_correction_target",
        ),
        sa.PrimaryKeyConstraint("row_id", name="pk_investment_decision_relationships"),
        sa.UniqueConstraint(
            "relationship_fact_id",
            name="uq_investment_decision_relationships_relationship_fact_id",
        ),
    )
    op.create_index(
        "ix_relationships_source_type",
        "investment_decision_relationships",
        ["source_decision_id", "relationship_type"],
        unique=False,
    )
    op.create_index(
        "ix_relationships_target_type",
        "investment_decision_relationships",
        ["target_decision_id", "relationship_type"],
        unique=False,
    )

    op.create_table(
        "investment_decision_command_receipts",
        sa.Column("row_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("command_kind", sa.String(length=48), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "request_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "result_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "char_length(request_fingerprint) = 64",
            name="ck_investment_decision_command_receipts_fingerprint_sha256",
        ),
        sa.PrimaryKeyConstraint(
            "row_id", name="pk_investment_decision_command_receipts"
        ),
        sa.UniqueConstraint(
            "operation_id",
            name="uq_investment_decision_command_receipts_operation_id",
        ),
    )

    op.execute(
        """
        CREATE FUNCTION polaris_reject_immutable_fact_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'immutable Decision facts cannot be changed';
        END;
        $$
        """
    )
    for table_name in (
        "decision_needs",
        "investment_decision_lifecycle_facts",
        "investment_decision_relationships",
        "investment_decision_command_receipts",
    ):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table_name}_immutable
            BEFORE UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION polaris_reject_immutable_fact_mutation()
            """
        )


def downgrade() -> None:
    for table_name in (
        "investment_decision_command_receipts",
        "investment_decision_relationships",
        "investment_decision_lifecycle_facts",
        "decision_needs",
    ):
        op.execute(f"DROP TRIGGER trg_{table_name}_immutable ON {table_name}")
    op.execute("DROP FUNCTION polaris_reject_immutable_fact_mutation()")
    op.drop_table("investment_decision_command_receipts")
    op.drop_index(
        "ix_relationships_target_type",
        table_name="investment_decision_relationships",
    )
    op.drop_index(
        "ix_relationships_source_type",
        table_name="investment_decision_relationships",
    )
    op.drop_table("investment_decision_relationships")
    op.drop_index(
        "ix_lifecycle_facts_decision_recorded",
        table_name="investment_decision_lifecycle_facts",
    )
    op.drop_table("investment_decision_lifecycle_facts")
    op.drop_index(
        "ix_investment_decisions_continuity_candidates",
        table_name="investment_decisions",
    )
    op.drop_table("investment_decisions")
    op.drop_table("decision_needs")
