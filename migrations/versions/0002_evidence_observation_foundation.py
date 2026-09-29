"""Add durable Evidence observation persistence.

Revision ID: 0002_evidence_observations
Revises: 0001_decision_persistence
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_evidence_observations"
down_revision: str | None = "0001_decision_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_observations",
        sa.Column("row_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("observation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_identity", sa.Text(), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=False),
        sa.Column("source_authority", sa.Text(), nullable=False),
        sa.Column("subject_identity", sa.Text(), nullable=False),
        sa.Column("subject_reference", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retained_representation", sa.Text(), nullable=True),
        sa.Column("verification_reference", sa.Text(), nullable=True),
        sa.Column(
            "supersedes_observation_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "btrim(source_identity) <> ''",
            name="ck_evidence_observations_source_identity_nonempty",
        ),
        sa.CheckConstraint(
            "btrim(source_reference) <> ''",
            name="ck_evidence_observations_source_reference_nonempty",
        ),
        sa.CheckConstraint(
            "btrim(source_authority) <> ''",
            name="ck_evidence_observations_source_authority_nonempty",
        ),
        sa.CheckConstraint(
            "btrim(subject_identity) <> ''",
            name="ck_evidence_observations_subject_identity_nonempty",
        ),
        sa.CheckConstraint(
            "btrim(subject_reference) <> ''",
            name="ck_evidence_observations_subject_reference_nonempty",
        ),
        sa.CheckConstraint(
            "retained_representation IS NOT NULL OR verification_reference IS NOT NULL",
            name="ck_evidence_observations_reconstructable_material",
        ),
        sa.CheckConstraint(
            "retained_representation IS NULL OR btrim(retained_representation) <> ''",
            name="ck_evidence_observations_retained_representation_nonempty",
        ),
        sa.CheckConstraint(
            "verification_reference IS NULL OR btrim(verification_reference) <> ''",
            name="ck_evidence_observations_verification_reference_nonempty",
        ),
        sa.CheckConstraint(
            "supersedes_observation_id IS NULL "
            "OR supersedes_observation_id <> observation_id",
            name="ck_evidence_observations_supersedes_distinct",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_observation_id"],
            ["evidence_observations.observation_id"],
            name="fk_evidence_observation_supersedes",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("row_id", name="pk_evidence_observations"),
        sa.UniqueConstraint(
            "observation_id",
            name="uq_evidence_observations_observation_id",
        ),
    )

    op.create_table(
        "evidence_observation_command_receipts",
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
            name="ck_evidence_observation_receipts_fingerprint_sha256",
        ),
        sa.PrimaryKeyConstraint(
            "row_id",
            name="pk_evidence_observation_command_receipts",
        ),
        sa.UniqueConstraint(
            "operation_id",
            name="uq_evidence_observation_command_receipts_operation_id",
        ),
    )

    op.execute(
        """
        CREATE FUNCTION polaris_reject_immutable_evidence_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'immutable Evidence facts cannot be changed';
        END;
        $$
        """
    )
    for table_name in (
        "evidence_observations",
        "evidence_observation_command_receipts",
    ):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table_name}_immutable
            BEFORE UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION polaris_reject_immutable_evidence_mutation()
            """
        )


def downgrade() -> None:
    for table_name in (
        "evidence_observation_command_receipts",
        "evidence_observations",
    ):
        op.execute(f"DROP TRIGGER trg_{table_name}_immutable ON {table_name}")
    op.execute("DROP FUNCTION polaris_reject_immutable_evidence_mutation()")
    op.drop_table("evidence_observation_command_receipts")
    op.drop_table("evidence_observations")
