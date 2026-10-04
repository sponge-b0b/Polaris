"""Persist derived Evidence sufficiency assessments and their proof.

Revision ID: 0006_sufficiency_assessments
Revises: 0005_sufficiency_requirements
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_sufficiency_assessments"
down_revision: str | None = "0005_sufficiency_requirements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # duplicate-code: this revision freezes the support-epoch table's DDL rather
    # than importing mutable current schema or coupling distinct historical tables.
    # arid: disable
    op.create_table(
        "evidence_support_versions",
        sa.Column("row_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("target_family", sa.String(length=48), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_kind", sa.String(length=24), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True)),
        sa.Column("evidence_use", sa.String(length=40), nullable=False),
        sa.Column("binding_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("support_version", sa.BigInteger(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "support_version > 0",
            name=op.f("ck_evidence_support_versions_support_version_positive"),
        ),
        sa.CheckConstraint(
            "(scope_kind = 'judgment_wide' AND claim_id IS NULL) OR "
            "(scope_kind = 'claim_specific' AND claim_id IS NOT NULL)",
            name=op.f("ck_evidence_support_versions_scope_kind"),
        ),
        sa.CheckConstraint(
            "target_family IN ("
            "'investment_hypothesis', 'investment_view', "
            "'meaningful_challenge_result', 'projected_portfolio_consequence', "
            "'portfolio_risk_assessment', 'investment_recommendation', "
            "'recommendation_withholding_judgment', 'human_investment_decision', "
            "'decision_evaluation', 'lesson'"
            ")",
            name=op.f("ck_evidence_support_versions_target_family"),
        ),
        sa.CheckConstraint(
            "evidence_use IN ("
            "'judgment_basis', 'challenge_basis', 'current_support_check', "
            "'retrospective_later_evidence', 'reconstruction_only'"
            ")",
            name=op.f("ck_evidence_support_versions_evidence_use"),
        ),
        sa.ForeignKeyConstraint(
            ["binding_id"],
            ["evidence_bindings.binding_id"],
            name=op.f("fk_evidence_support_version_binding"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "row_id",
            name=op.f("pk_evidence_support_versions"),
        ),
        sa.UniqueConstraint(
            "binding_id",
            name=op.f("uq_evidence_support_versions_binding_id"),
        ),
    )
    # arid: enable
    op.create_index(
        "uq_evidence_support_versions_scope_version",
        "evidence_support_versions",
        [
            "target_family",
            "target_id",
            "scope_kind",
            "claim_id",
            "evidence_use",
            "support_version",
        ],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )
    # duplicate-code: the backfill repeats its target columns in INSERT, SELECT,
    # and partition clauses so the immutable historical transformation stays explicit.
    # arid: disable
    op.execute(
        """
        INSERT INTO evidence_support_versions (
            target_family,
            target_id,
            scope_kind,
            claim_id,
            evidence_use,
            binding_id,
            support_version,
            effective_at,
            recorded_at
        )
        SELECT
            target_family,
            target_id,
            scope_kind,
            claim_id,
            evidence_use,
            binding_id,
            row_number() OVER (
                PARTITION BY
                    target_family,
                    target_id,
                    scope_kind,
                    claim_id,
                    evidence_use
                ORDER BY recorded_at, row_id
            ),
            effective_at,
            recorded_at
        FROM evidence_bindings
        WHERE effective_at <= recorded_at
        """
    )
    # arid: enable
    op.create_table(
        "evidence_sufficiency_assessments",
        sa.Column("row_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_family", sa.String(length=48), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_kind", sa.String(length=24), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True)),
        sa.Column("evidence_use", sa.String(length=40), nullable=False),
        # duplicate-code: this revision freezes its JSONB column shape independently;
        # importing historical migration structure would couple immutable revisions.
        # arid: disable
        sa.Column(
            "applicability",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        # arid: enable
        sa.Column("requirement_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "requirement_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("support_version", sa.BigInteger(), nullable=False),
        sa.Column(
            "binding_guard_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
        ),
        sa.Column(
            "correction_guard_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
        ),
        sa.Column(
            "requirement_authority_guard_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
        ),
        sa.Column("proof", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("actor_attribution_kind", sa.String(length=16), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "actor_candidate_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
        ),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("known_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.Column(
            "reassesses_assessment_id",
            postgresql.UUID(as_uuid=True),
        ),
        sa.CheckConstraint(
            "actor_attribution_kind IN ('known', 'unknown', 'contested')",
            name=op.f("ck_evidence_sufficiency_assessments_actor_attribution_kind"),
        ),
        # duplicate-code: this revision owns its actor-shape constraint snapshot;
        # current schema helpers and earlier revisions must remain independently frozen.
        # arid: disable
        sa.CheckConstraint(
            "(actor_attribution_kind = 'known' AND actor_id IS NOT NULL "
            "AND actor_candidate_ids IS NULL) OR "
            "(actor_attribution_kind = 'unknown' AND actor_id IS NULL "
            "AND actor_candidate_ids IS NULL) OR "
            "(actor_attribution_kind = 'contested' AND actor_id IS NULL "
            "AND cardinality(actor_candidate_ids) > 0)",
            name=op.f("ck_evidence_sufficiency_assessments_actor_attribution_shape"),
        ),
        # arid: enable
        sa.CheckConstraint(
            "known_at <= recorded_at",
            name=op.f("ck_evidence_sufficiency_assessments_known_before_recorded"),
        ),
        sa.CheckConstraint(
            "reassesses_assessment_id IS NULL OR "
            "reassesses_assessment_id <> assessment_id",
            name=op.f("ck_evidence_sufficiency_assessments_reassessment_distinct"),
        ),
        sa.CheckConstraint(
            "result IN ('sufficient', 'insufficient', 'indeterminate')",
            name=op.f("ck_evidence_sufficiency_assessments_result"),
        ),
        sa.CheckConstraint(
            "(scope_kind = 'judgment_wide' AND claim_id IS NULL) OR "
            "(scope_kind = 'claim_specific' AND claim_id IS NOT NULL)",
            name=op.f("ck_evidence_sufficiency_assessments_scope_kind"),
        ),
        sa.CheckConstraint(
            "support_version >= 0",
            name=op.f(
                "ck_evidence_sufficiency_assessments_support_version_nonnegative"
            ),
        ),
        # duplicate-code: applicability enum snapshots belong to this immutable
        # revision and must not depend on mutable current-schema helpers.
        # arid: disable
        sa.CheckConstraint(
            "target_family IN ("
            "'investment_hypothesis', 'investment_view', "
            "'meaningful_challenge_result', 'projected_portfolio_consequence', "
            "'portfolio_risk_assessment', 'investment_recommendation', "
            "'recommendation_withholding_judgment', 'human_investment_decision', "
            "'decision_evaluation', 'lesson'"
            ")",
            name=op.f("ck_evidence_sufficiency_assessments_target_family"),
        ),
        sa.CheckConstraint(
            "evidence_use IN ("
            "'judgment_basis', 'challenge_basis', 'current_support_check', "
            "'retrospective_later_evidence', 'reconstruction_only'"
            ")",
            name=op.f("ck_evidence_sufficiency_assessments_evidence_use"),
        ),
        # arid: enable
        sa.ForeignKeyConstraint(
            ["reassesses_assessment_id"],
            ["evidence_sufficiency_assessments.assessment_id"],
            name=op.f("fk_evidence_sufficiency_reassessment"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_set_id", "requirement_version_id"],
            [
                "evidence_requirement_set_versions.set_id",
                "evidence_requirement_set_versions.version_id",
            ],
            name=op.f("fk_evidence_sufficiency_requirement_version"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "row_id",
            name=op.f("pk_evidence_sufficiency_assessments"),
        ),
        sa.UniqueConstraint(
            "assessment_id",
            name=op.f("uq_evidence_sufficiency_assessments_assessment_id"),
        ),
        sa.UniqueConstraint(
            "assessment_id",
            "requirement_version_id",
            name=op.f("uq_evidence_sufficiency_assessment_requirement_version"),
        ),
    )
    op.create_table(
        "evidence_sufficiency_contributors",
        sa.Column("row_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("binding_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["evidence_sufficiency_assessments.assessment_id"],
            name=op.f("fk_evidence_sufficiency_contributor_assessment"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["binding_id"],
            ["evidence_bindings.binding_id"],
            name=op.f("fk_evidence_sufficiency_contributor_binding"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "row_id",
            name=op.f("pk_evidence_sufficiency_contributors"),
        ),
        sa.UniqueConstraint(
            "assessment_id",
            "binding_id",
            name=op.f("uq_evidence_sufficiency_contributor"),
        ),
    )
    op.create_table(
        "evidence_sufficiency_command_receipts",
        sa.Column("row_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        # duplicate-code: this revision's receipt DDL is an independently frozen
        # historical snapshot, not reusable runtime command-table infrastructure.
        # arid: disable
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
            name=op.f("ck_evidence_sufficiency_command_receipts_fingerprint_sha256"),
        ),
        # arid: enable
        sa.PrimaryKeyConstraint(
            "row_id",
            name=op.f("pk_evidence_sufficiency_command_receipts"),
        ),
        sa.UniqueConstraint(
            "operation_id",
            name=op.f("uq_evidence_sufficiency_command_receipts_operation_id"),
        ),
    )
    # duplicate-code: this immutable revision owns its trigger DDL so historical
    # upgrades never depend on a mutable shared migration helper.
    # arid: disable
    op.execute(
        """
        CREATE FUNCTION polaris_reject_immutable_evidence_sufficiency_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'immutable Evidence sufficiency facts cannot be changed';
        END;
        $$
        """
    )
    for table_name in (
        "evidence_support_versions",
        "evidence_sufficiency_assessments",
        "evidence_sufficiency_contributors",
        "evidence_sufficiency_command_receipts",
    ):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table_name}_immutable
            BEFORE UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION
            polaris_reject_immutable_evidence_sufficiency_mutation()
            """
        )
    # arid: enable


def downgrade() -> None:
    for table_name in (
        "evidence_sufficiency_command_receipts",
        "evidence_sufficiency_contributors",
        "evidence_sufficiency_assessments",
        "evidence_support_versions",
    ):
        op.execute(f"DROP TRIGGER trg_{table_name}_immutable ON {table_name}")
    op.execute("DROP FUNCTION polaris_reject_immutable_evidence_sufficiency_mutation()")
    op.drop_table("evidence_sufficiency_command_receipts")
    op.drop_table("evidence_sufficiency_contributors")
    op.drop_table("evidence_sufficiency_assessments")
    op.drop_index(
        "uq_evidence_support_versions_scope_version",
        table_name="evidence_support_versions",
    )
    op.drop_table("evidence_support_versions")
