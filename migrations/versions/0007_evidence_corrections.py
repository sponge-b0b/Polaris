"""Persist typed Evidence correction lineage and immutable command receipts.

Revision ID: 0007_evidence_corrections
Revises: 0006_sufficiency_assessments
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_evidence_corrections"
down_revision: str | None = "0006_sufficiency_assessments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_correction_table(
    table_name: str,
    root_table_name: str,
    root_column_name: str,
) -> None:
    # duplicate-code: this migration is a frozen historical schema snapshot;
    # sharing DDL with current schema code or older revisions would couple time.
    # arid: disable
    op.create_table(
        table_name,
        sa.Column("row_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("correction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("root_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_root_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_correction_id", postgresql.UUID(as_uuid=True)),
        sa.Column("effect", sa.String(length=16), nullable=False),
        sa.Column(
            "replacement",
            postgresql.JSONB(astext_type=sa.Text()),
        ),
        sa.Column("actor_attribution_kind", sa.String(length=16), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "actor_candidate_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
        ),
        sa.Column("basis_reference", sa.Text(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "actor_attribution_kind IN ('known', 'unknown', 'contested')",
            name=op.f(f"ck_{table_name}_actor_attribution_kind"),
        ),
        sa.CheckConstraint(
            "(actor_attribution_kind = 'known' AND actor_id IS NOT NULL "
            "AND actor_candidate_ids IS NULL) OR "
            "(actor_attribution_kind = 'unknown' AND actor_id IS NULL "
            "AND actor_candidate_ids IS NULL) OR "
            "(actor_attribution_kind = 'contested' AND actor_id IS NULL "
            "AND cardinality(actor_candidate_ids) > 0)",
            name=op.f(f"ck_{table_name}_actor_attribution_shape"),
        ),
        sa.CheckConstraint(
            "btrim(basis_reference) <> ''",
            name=op.f(f"ck_{table_name}_basis_nonempty"),
        ),
        sa.CheckConstraint(
            "(effect = 'revise' AND replacement IS NOT NULL) OR "
            "(effect = 'retract' AND replacement IS NULL)",
            name=op.f(f"ck_{table_name}_effect_shape"),
        ),
        sa.CheckConstraint(
            "(target_root_id IS NOT NULL AND target_correction_id IS NULL "
            "AND target_root_id = root_id) OR "
            "(target_root_id IS NULL AND target_correction_id IS NOT NULL)",
            name=op.f(f"ck_{table_name}_target_shape"),
        ),
        sa.ForeignKeyConstraint(
            ["correction_id"],
            ["evidence_correction_identities.correction_id"],
            name=op.f(f"fk_{table_name}_correction_identity"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["root_id"],
            [f"{root_table_name}.{root_column_name}"],
            name=op.f(f"fk_{table_name}_root"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_root_id"],
            [f"{root_table_name}.{root_column_name}"],
            name=op.f(f"fk_{table_name}_target_root"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_correction_id", "root_id"],
            [f"{table_name}.correction_id", f"{table_name}.root_id"],
            name=op.f(f"fk_{table_name}_target_correction_lineage"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("row_id", name=op.f(f"pk_{table_name}")),
        sa.UniqueConstraint(
            "correction_id",
            name=op.f(f"uq_{table_name}_correction_id"),
        ),
        sa.UniqueConstraint(
            "correction_id",
            "root_id",
            name=op.f(f"uq_{table_name}_correction_root"),
        ),
    )
    # arid: enable


def upgrade() -> None:
    # duplicate-code: registry and receipt DDL is self-contained migration
    # history and must not import mutable current schema declarations.
    # arid: disable
    op.create_table(
        "evidence_correction_identities",
        sa.Column("row_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("correction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("family", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "family IN ('observation', 'binding', 'assessment')",
            name=op.f("ck_evidence_correction_identities_family"),
        ),
        sa.PrimaryKeyConstraint(
            "row_id",
            name=op.f("pk_evidence_correction_identities"),
        ),
        sa.UniqueConstraint(
            "correction_id",
            name=op.f("uq_evidence_correction_identities_correction_id"),
        ),
    )
    op.alter_column(
        "evidence_support_versions",
        "binding_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "evidence_support_versions",
        sa.Column("correction_id", postgresql.UUID(as_uuid=True)),
    )
    op.create_foreign_key(
        op.f("fk_evidence_support_version_correction"),
        "evidence_support_versions",
        "evidence_correction_identities",
        ["correction_id"],
        ["correction_id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        op.f("ck_evidence_support_versions_support_event_source"),
        "evidence_support_versions",
        "(binding_id IS NOT NULL AND correction_id IS NULL) OR "
        "(binding_id IS NULL AND correction_id IS NOT NULL)",
    )
    op.create_index(
        "uq_evidence_support_versions_scope_correction",
        "evidence_support_versions",
        [
            "target_family",
            "target_id",
            "scope_kind",
            "claim_id",
            "evidence_use",
            "correction_id",
        ],
        unique=True,
        postgresql_where=sa.text("correction_id IS NOT NULL"),
        postgresql_nulls_not_distinct=True,
    )
    _create_correction_table(
        "evidence_observation_corrections",
        "evidence_observations",
        "observation_id",
    )
    _create_correction_table(
        "evidence_binding_corrections",
        "evidence_bindings",
        "binding_id",
    )
    _create_correction_table(
        "evidence_assessment_corrections",
        "evidence_sufficiency_assessments",
        "assessment_id",
    )
    op.create_table(
        "evidence_correction_command_receipts",
        sa.Column("row_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("family", sa.String(length=32), nullable=False),
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
            name=op.f("ck_evidence_correction_command_receipts_fingerprint_sha256"),
        ),
        sa.CheckConstraint(
            "family IN ('observation', 'binding', 'assessment')",
            name=op.f("ck_evidence_correction_command_receipts_family"),
        ),
        sa.PrimaryKeyConstraint(
            "row_id",
            name=op.f("pk_evidence_correction_command_receipts"),
        ),
        sa.UniqueConstraint(
            "operation_id",
            name=op.f("uq_evidence_correction_command_receipts_operation_id"),
        ),
    )
    op.execute(
        """
        CREATE FUNCTION polaris_reject_immutable_evidence_correction_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'immutable Evidence correction facts cannot be changed';
        END;
        $$
        """
    )
    for table_name in (
        "evidence_observation_corrections",
        "evidence_binding_corrections",
        "evidence_assessment_corrections",
        "evidence_correction_command_receipts",
        "evidence_correction_identities",
    ):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table_name}_immutable
            BEFORE UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION
            polaris_reject_immutable_evidence_correction_mutation()
            """
        )
    # arid: enable


def downgrade() -> None:
    for table_name in (
        "evidence_correction_command_receipts",
        "evidence_binding_corrections",
        "evidence_assessment_corrections",
        "evidence_observation_corrections",
        "evidence_correction_identities",
    ):
        op.execute(f"DROP TRIGGER trg_{table_name}_immutable ON {table_name}")
    op.execute("DELETE FROM evidence_support_versions WHERE correction_id IS NOT NULL")
    op.drop_index(
        "uq_evidence_support_versions_scope_correction",
        table_name="evidence_support_versions",
    )
    op.drop_constraint(
        op.f("ck_evidence_support_versions_support_event_source"),
        "evidence_support_versions",
        type_="check",
    )
    op.drop_constraint(
        op.f("fk_evidence_support_version_correction"),
        "evidence_support_versions",
        type_="foreignkey",
    )
    op.drop_column("evidence_support_versions", "correction_id")
    op.alter_column(
        "evidence_support_versions",
        "binding_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.execute("DROP FUNCTION polaris_reject_immutable_evidence_correction_mutation()")
    op.drop_table("evidence_correction_command_receipts")
    op.drop_table("evidence_binding_corrections")
    op.drop_table("evidence_assessment_corrections")
    op.drop_table("evidence_observation_corrections")
    op.drop_table("evidence_correction_identities")
