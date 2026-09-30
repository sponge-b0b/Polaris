"""Add immutable Configuration-owned Evidence requirement versions.

Revision ID: 0003_evidence_requirements
Revises: 0002_evidence_observations
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_evidence_requirements"
down_revision: str | None = "0002_evidence_observations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_requirement_set_versions",
        sa.Column("row_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("authority_identity", sa.Text(), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "applicability",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "predecessor_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("predecessor_effect", sa.String(length=16), nullable=True),
        sa.CheckConstraint(
            "btrim(authority_identity) <> ''",
            name="ck_evidence_requirement_set_versions_authority_identity_nonempty",
        ),
        sa.CheckConstraint(
            "btrim(source_reference) <> ''",
            name="ck_evidence_requirement_set_versions_source_reference_nonempty",
        ),
        sa.CheckConstraint(
            "(predecessor_version_id IS NULL AND predecessor_effect IS NULL) OR "
            "(predecessor_version_id IS NOT NULL AND predecessor_effect IS NOT NULL)",
            name="ck_evidence_requirement_set_versions_predecessor_complete",
        ),
        sa.CheckConstraint(
            "predecessor_effect IS NULL OR "
            "predecessor_effect IN ('corrects', 'supersedes')",
            name="ck_evidence_requirement_set_versions_predecessor_effect",
        ),
        sa.CheckConstraint(
            "predecessor_version_id IS NULL OR predecessor_version_id <> version_id",
            name="ck_evidence_requirement_set_versions_predecessor_distinct",
        ),
        sa.ForeignKeyConstraint(
            ["predecessor_version_id"],
            ["evidence_requirement_set_versions.version_id"],
            name="fk_evidence_requirement_version_predecessor",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("row_id", name="pk_evidence_requirement_set_versions"),
        sa.UniqueConstraint(
            "version_id",
            name="uq_evidence_requirement_set_versions_version_id",
        ),
        sa.UniqueConstraint(
            "set_id",
            "version_id",
            name="uq_evidence_requirement_versions_set_version",
        ),
    )
    op.create_table(
        "evidence_requirement_definitions",
        sa.Column("row_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("requirement_kind", sa.String(length=16), nullable=False),
        sa.Column(
            "definition",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.CheckConstraint(
            "position >= 0",
            name="ck_evidence_requirement_definitions_position_nonnegative",
        ),
        sa.CheckConstraint(
            "requirement_kind IN ('freshness', 'sufficiency')",
            name="ck_evidence_requirement_definitions_requirement_kind",
        ),
        # duplicate-code: an immutable Alembic revision must preserve its own
        # schema snapshot; importing live metadata would make history mutable.
        # arid: disable
        sa.ForeignKeyConstraint(
            ["set_id", "version_id"],
            [
                "evidence_requirement_set_versions.set_id",
                "evidence_requirement_set_versions.version_id",
            ],
            name="fk_evidence_requirement_definition_version",
            ondelete="RESTRICT",
        ),
        # arid: enable
        sa.PrimaryKeyConstraint("row_id", name="pk_evidence_requirement_definitions"),
        # duplicate-code: migration-local constraint declarations are frozen
        # history and must not depend on the evolving live schema module.
        # arid: disable
        sa.UniqueConstraint(
            "set_id",
            "version_id",
            "requirement_id",
            name="uq_evidence_requirement_definitions_identity",
        ),
        # arid: enable
        sa.UniqueConstraint(
            "version_id",
            "position",
            name="uq_evidence_requirement_definitions_position",
        ),
    )

    # duplicate-code: each immutable migration owns its historical trigger DDL;
    # sharing it with another revision would couple independently frozen history.
    # arid: disable
    op.execute(
        """
        CREATE FUNCTION polaris_reject_immutable_requirement_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'immutable requirement facts cannot be changed';
        END;
        $$
        """
    )
    for table_name in (
        "evidence_requirement_set_versions",
        "evidence_requirement_definitions",
    ):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table_name}_immutable
            BEFORE UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION
            polaris_reject_immutable_requirement_mutation()
            """
        )
    # arid: enable


def downgrade() -> None:
    for table_name in (
        "evidence_requirement_definitions",
        "evidence_requirement_set_versions",
    ):
        op.execute(f"DROP TRIGGER trg_{table_name}_immutable ON {table_name}")
    op.execute("DROP FUNCTION polaris_reject_immutable_requirement_mutation()")
    op.drop_table("evidence_requirement_definitions")
    op.drop_table("evidence_requirement_set_versions")
