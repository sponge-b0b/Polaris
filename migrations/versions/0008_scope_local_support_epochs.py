"""Track assessment and observation-succession support events.

Revision ID: 0008_support_epochs
Revises: 0007_evidence_corrections
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_support_epochs"
down_revision: str | None = "0007_evidence_corrections"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "evidence_support_versions",
        sa.Column("observation_id", postgresql.UUID(as_uuid=True)),
    )
    op.add_column(
        "evidence_support_versions",
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True)),
    )
    op.create_foreign_key(
        op.f("fk_evidence_support_version_observation"),
        "evidence_support_versions",
        "evidence_observations",
        ["observation_id"],
        ["observation_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_evidence_support_version_assessment"),
        "evidence_support_versions",
        "evidence_sufficiency_assessments",
        ["assessment_id"],
        ["assessment_id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        op.f("uq_evidence_support_versions_assessment_id"),
        "evidence_support_versions",
        ["assessment_id"],
    )
    # duplicate-code: this revision freezes its own scope index; sharing the
    # column list with revision 0006 would make historical migrations mutable.
    # arid: disable
    op.create_index(
        "uq_evidence_support_versions_scope_observation",
        "evidence_support_versions",
        [
            "target_family",
            "target_id",
            "scope_kind",
            "claim_id",
            "evidence_use",
            "observation_id",
        ],
        unique=True,
        postgresql_nulls_not_distinct=True,
        postgresql_where=sa.text("observation_id IS NOT NULL"),
    )
    # arid: enable
    # duplicate-code: upgrade and downgrade independently restore the exact
    # historical check at their respective schema boundaries.
    # arid: disable
    op.drop_constraint(
        op.f("ck_evidence_support_versions_support_event_source"),
        "evidence_support_versions",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_evidence_support_versions_support_event_source"),
        "evidence_support_versions",
        "num_nonnulls(binding_id, correction_id, observation_id, assessment_id) = 1",
    )
    # arid: enable


def downgrade() -> None:
    op.execute(
        "DELETE FROM evidence_support_versions "
        "WHERE observation_id IS NOT NULL OR assessment_id IS NOT NULL"
    )
    # duplicate-code: the reverse check transition is a frozen migration
    # snapshot, not a reusable runtime constraint implementation.
    # arid: disable
    op.drop_constraint(
        op.f("ck_evidence_support_versions_support_event_source"),
        "evidence_support_versions",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_evidence_support_versions_support_event_source"),
        "evidence_support_versions",
        "(binding_id IS NOT NULL AND correction_id IS NULL) OR "
        "(binding_id IS NULL AND correction_id IS NOT NULL)",
    )
    # arid: enable
    op.drop_index(
        "uq_evidence_support_versions_scope_observation",
        table_name="evidence_support_versions",
    )
    op.drop_constraint(
        op.f("uq_evidence_support_versions_assessment_id"),
        "evidence_support_versions",
        type_="unique",
    )
    op.drop_constraint(
        op.f("fk_evidence_support_version_assessment"),
        "evidence_support_versions",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_evidence_support_version_observation"),
        "evidence_support_versions",
        type_="foreignkey",
    )
    op.drop_column("evidence_support_versions", "assessment_id")
    op.drop_column("evidence_support_versions", "observation_id")
