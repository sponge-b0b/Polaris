"""Add durable judgment-relative Evidence bindings.

Revision ID: 0004_evidence_bindings
Revises: 0003_evidence_requirements
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_evidence_bindings"
down_revision: str | None = "0003_evidence_requirements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_bindings",
        sa.Column("row_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("binding_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("observation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_family", sa.String(length=48), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_kind", sa.String(length=24), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evidence_use", sa.String(length=40), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False),
        sa.Column("availability", sa.String(length=16), nullable=False),
        sa.Column("materially_used", sa.Boolean(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("material_qualification", sa.Text(), nullable=True),
        sa.Column("freshness_state", sa.String(length=24), nullable=False),
        sa.Column("freshness_set_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "freshness_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "freshness_requirement_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("freshness_basis_reference", sa.Text(), nullable=False),
        sa.Column(
            "freshness_basis_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "freshness_applicability",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("freshness_result", sa.String(length=16), nullable=True),
        sa.Column("freshness_failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "freshness_contested_version_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=True,
        ),
        # duplicate-code: immutable migration snapshots must retain their exact
        # historical constraint text instead of importing mutable live schema.
        # arid: disable
        sa.CheckConstraint(
            "target_family IN ("
            "'investment_hypothesis', 'investment_view', "
            "'meaningful_challenge_result', 'projected_portfolio_consequence', "
            "'portfolio_risk_assessment', 'investment_recommendation', "
            "'recommendation_withholding_judgment', 'human_investment_decision', "
            "'decision_evaluation', 'lesson'"
            ")",
            name=op.f("ck_evidence_bindings_target_family"),
        ),
        # arid: enable
        sa.CheckConstraint(
            "(scope_kind = 'judgment_wide' AND claim_id IS NULL) OR "
            "(scope_kind = 'claim_specific' AND claim_id IS NOT NULL)",
            name=op.f("ck_evidence_bindings_scope_kind"),
        ),
        sa.CheckConstraint(
            "evidence_use IN ("
            "'judgment_basis', 'challenge_basis', 'current_support_check', "
            "'retrospective_later_evidence', 'reconstruction_only'"
            ")",
            name=op.f("ck_evidence_bindings_evidence_use"),
        ),
        sa.CheckConstraint(
            "role IN ("
            "'supporting', 'conflicting', 'constraining', "
            "'qualifying', 'contextual', 'reconstruction'"
            ")",
            name=op.f("ck_evidence_bindings_role"),
        ),
        sa.CheckConstraint(
            "availability IN ('available', 'unavailable', 'unknown')",
            name=op.f("ck_evidence_bindings_availability"),
        ),
        sa.CheckConstraint(
            "NOT materially_used OR availability = 'available'",
            name=op.f("ck_evidence_bindings_material_use_requires_available"),
        ),
        sa.CheckConstraint(
            "material_qualification IS NULL OR btrim(material_qualification) <> ''",
            name=op.f("ck_evidence_bindings_material_qualification_nonempty"),
        ),
        # duplicate-code: immutable migration snapshots must retain their exact
        # historical constraint text instead of importing mutable live schema.
        # arid: disable
        sa.CheckConstraint(
            "freshness_state IN ("
            "'applicable', 'not_applicable', 'missing_authority', "
            "'unavailable_authority', 'contested_authority', 'invalid_authority'"
            ")",
            name=op.f("ck_evidence_bindings_freshness_state"),
        ),
        sa.CheckConstraint(
            "freshness_result IS NULL OR "
            "freshness_result IN ('fresh', 'stale', 'indeterminate')",
            name=op.f("ck_evidence_bindings_freshness_result"),
        ),
        # arid: enable
        sa.CheckConstraint(
            "btrim(freshness_basis_reference) <> ''",
            name=op.f("ck_evidence_bindings_freshness_basis_reference_nonempty"),
        ),
        sa.CheckConstraint(
            "freshness_failure_reason IS NULL OR "
            "btrim(freshness_failure_reason) <> ''",
            name=op.f("ck_evidence_bindings_freshness_failure_reason_nonempty"),
        ),
        # duplicate-code: frozen migration shape must mirror the live binding
        # contract without importing mutable schema construction.
        # arid: disable
        sa.CheckConstraint(
            "("
            "freshness_state = 'applicable' AND "
            "freshness_set_id IS NOT NULL AND freshness_version_id IS NOT NULL AND "
            "freshness_requirement_id IS NOT NULL AND "
            "freshness_result IN ('fresh', 'stale', 'indeterminate') AND "
            "freshness_failure_reason IS NULL AND "
            "freshness_contested_version_ids IS NULL"
            ") OR ("
            "freshness_state = 'not_applicable' AND "
            "freshness_set_id IS NOT NULL AND freshness_version_id IS NOT NULL AND "
            "freshness_requirement_id IS NULL AND freshness_result IS NULL AND "
            "freshness_failure_reason IS NULL AND "
            "freshness_contested_version_ids IS NULL"
            ") OR ("
            "freshness_state = 'missing_authority' AND "
            "freshness_set_id IS NULL AND freshness_version_id IS NULL AND "
            "freshness_requirement_id IS NULL AND "
            "freshness_result = 'indeterminate' AND "
            "freshness_failure_reason IS NULL AND "
            "freshness_contested_version_ids IS NULL"
            ") OR ("
            "freshness_state = 'unavailable_authority' AND "
            "freshness_set_id IS NULL AND freshness_version_id IS NULL AND "
            "freshness_requirement_id IS NULL AND "
            "freshness_result = 'indeterminate' AND "
            "freshness_failure_reason IS NOT NULL AND "
            "freshness_contested_version_ids IS NULL"
            ") OR ("
            "freshness_state = 'contested_authority' AND "
            "freshness_set_id IS NULL AND freshness_version_id IS NULL AND "
            "freshness_requirement_id IS NULL AND "
            "freshness_result = 'indeterminate' AND "
            "freshness_failure_reason IS NULL AND "
            "cardinality(freshness_contested_version_ids) > 1"
            ") OR ("
            "freshness_state = 'invalid_authority' AND "
            "freshness_set_id IS NULL AND freshness_version_id IS NULL AND "
            "freshness_requirement_id IS NULL AND freshness_result IS NULL AND "
            "freshness_failure_reason IS NOT NULL AND "
            "freshness_contested_version_ids IS NULL"
            ")",
            name=op.f("ck_evidence_bindings_freshness_shape"),
        ),
        # arid: enable
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["evidence_observations.observation_id"],
            name="fk_evidence_binding_observation",
            ondelete="RESTRICT",
        ),
        # duplicate-code: this mutable pre-1.0 migration must preserve its own
        # historical DDL rather than importing the live SQLAlchemy schema.
        # arid: disable
        sa.ForeignKeyConstraint(
            ["freshness_set_id", "freshness_version_id"],
            [
                "evidence_requirement_set_versions.set_id",
                "evidence_requirement_set_versions.version_id",
            ],
            name="fk_evidence_binding_freshness_version",
            ondelete="RESTRICT",
        ),
        # arid: enable
        # duplicate-code: migration FK declarations are frozen historical DDL;
        # sharing live schema construction would make old revisions mutable.
        # arid: disable
        sa.ForeignKeyConstraint(
            [
                "freshness_set_id",
                "freshness_version_id",
                "freshness_requirement_id",
            ],
            [
                "evidence_requirement_definitions.set_id",
                "evidence_requirement_definitions.version_id",
                "evidence_requirement_definitions.requirement_id",
            ],
            name="fk_evidence_binding_freshness_requirement",
            ondelete="RESTRICT",
        ),
        # arid: enable
        sa.PrimaryKeyConstraint("row_id", name="pk_evidence_bindings"),
        sa.UniqueConstraint(
            "binding_id",
            name="uq_evidence_bindings_binding_id",
        ),
    )

    # duplicate-code: each immutable Alembic revision owns its receipt-table
    # snapshot; sharing a mutable migration helper would rewrite history.
    # arid: disable
    op.create_table(
        "evidence_binding_command_receipts",
        sa.Column("row_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
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
            name=op.f("ck_evidence_binding_command_receipts_fingerprint_sha256"),
        ),
        sa.PrimaryKeyConstraint(
            "row_id",
            name="pk_evidence_binding_command_receipts",
        ),
        sa.UniqueConstraint(
            "operation_id",
            name="uq_evidence_binding_command_receipts_operation_id",
        ),
    )
    # arid: enable

    # duplicate-code: immutable Alembic revisions own their trigger DDL so
    # historical behavior never depends on mutable shared migration helpers.
    # arid: disable
    op.execute(
        """
        CREATE FUNCTION polaris_reject_immutable_evidence_binding_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'immutable Evidence binding facts cannot be changed';
        END;
        $$
        """
    )
    for table_name in (
        "evidence_bindings",
        "evidence_binding_command_receipts",
    ):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table_name}_immutable
            BEFORE UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION
            polaris_reject_immutable_evidence_binding_mutation()
            """
        )
    # arid: enable


def downgrade() -> None:
    for table_name in (
        "evidence_binding_command_receipts",
        "evidence_bindings",
    ):
        op.execute(f"DROP TRIGGER trg_{table_name}_immutable ON {table_name}")
    op.execute("DROP FUNCTION polaris_reject_immutable_evidence_binding_mutation()")
    op.drop_table("evidence_binding_command_receipts")
    op.drop_table("evidence_bindings")
