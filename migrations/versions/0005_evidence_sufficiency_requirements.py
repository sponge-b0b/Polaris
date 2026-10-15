"""Constrain executable Evidence sufficiency requirement definitions.

Revision ID: 0005_sufficiency_requirements
Revises: 0004_evidence_bindings
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005_sufficiency_requirements"
down_revision: str | None = "0004_evidence_bindings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINT_NAME = "ck_evidence_requirement_definitions_definition_shape"


def upgrade() -> None:
    op.create_check_constraint(
        op.f(_CONSTRAINT_NAME),
        "evidence_requirement_definitions",
        # duplicate-code: this migration is a frozen historical snapshot; sharing
        # its DDL with mutable current schema would make old upgrades change later.
        # arid: disable
        "COALESCE((requirement_kind = 'freshness' AND "
        "jsonb_typeof(definition -> 'maximum_age_microseconds') = 'number' AND "
        "(definition ->> 'maximum_age_microseconds')::bigint > 0) OR "
        "(requirement_kind = 'sufficiency' AND "
        "jsonb_typeof(definition -> 'minimum_distinct_observations') = 'number' AND "
        "definition ->> 'minimum_distinct_observations' ~ '^[1-9][0-9]*$' AND "
        "jsonb_typeof(definition -> 'qualifying_roles') = 'array' AND "
        "jsonb_array_length(definition -> 'qualifying_roles') > 0 AND "
        "definition -> 'qualifying_roles' <@ "
        '\'["supporting", "conflicting", "constraining", "qualifying"]\'::jsonb '
        "AND definition ->> 'applicability_state' "
        "IN ('required', 'not_applicable') "
        "AND jsonb_typeof(definition -> 'description') = 'string' AND "
        "btrim(definition ->> 'description') <> ''), FALSE)",
        # arid: enable
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f(_CONSTRAINT_NAME),
        "evidence_requirement_definitions",
        type_="check",
    )
