"""Greenfield PostgreSQL schema for durable Investment Decision truth."""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _row_id() -> Column[int]:
    return Column("row_id", BigInteger, Identity(), primary_key=True)


def _uuid_array() -> ARRAY:
    return ARRAY(UUID(as_uuid=True))


def _command_provenance_columns() -> tuple[Column[object], ...]:
    return (
        Column("operation_id", UUID(as_uuid=True), nullable=False),
        Column("actor_attribution_kind", String(16), nullable=False),
        Column("actor_id", UUID(as_uuid=True)),
        Column("actor_candidate_ids", _uuid_array()),
        Column("trigger_kind", String(32), nullable=False),
        Column("trigger_reference", Text, nullable=False),
        Column(
            "technical_provenance",
            JSONB,
            nullable=False,
            server_default=text("'[]'::jsonb"),
        ),
    )


def _actor_attribution_constraints() -> tuple[CheckConstraint, ...]:
    return (
        CheckConstraint(
            "actor_attribution_kind IN ('known', 'unknown', 'contested')",
            name="actor_attribution_kind",
        ),
        CheckConstraint(
            "(actor_attribution_kind = 'known' AND actor_id IS NOT NULL "
            "AND actor_candidate_ids IS NULL) OR "
            "(actor_attribution_kind = 'unknown' AND actor_id IS NULL "
            "AND actor_candidate_ids IS NULL) OR "
            "(actor_attribution_kind = 'contested' AND actor_id IS NULL "
            "AND cardinality(actor_candidate_ids) > 0)",
            name="actor_attribution_shape",
        ),
    )


decision_needs = Table(
    "decision_needs",
    metadata,
    _row_id(),
    Column("need_id", UUID(as_uuid=True), nullable=False, unique=True),
    Column("statement", Text, nullable=False),
    Column("effective_at", DateTime(timezone=True), nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
    *_command_provenance_columns(),
    CheckConstraint("btrim(statement) <> ''", name="statement_nonempty"),
    *_actor_attribution_constraints(),
    CheckConstraint(
        "btrim(trigger_reference) <> ''", name="trigger_reference_nonempty"
    ),
)

investment_decisions = Table(
    "investment_decisions",
    metadata,
    _row_id(),
    Column("decision_id", UUID(as_uuid=True), nullable=False, unique=True),
    Column(
        "need_id",
        UUID(as_uuid=True),
        ForeignKey("decision_needs.need_id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    ),
    Column("subject_statement", Text, nullable=False),
    Column("scope_completeness", String(16), nullable=False),
    Column(
        "scope_portfolio_ids",
        _uuid_array(),
        nullable=False,
        server_default=text("'{}'::uuid[]"),
    ),
    Column("lifecycle_interpretation_kind", String(24), nullable=False),
    Column("lifecycle_disposition", String(32)),
    Column("lifecycle_effective_at", DateTime(timezone=True), nullable=False),
    Column("lifecycle_known_at", DateTime(timezone=True), nullable=False),
    Column(
        "lifecycle_support_fact_ids",
        _uuid_array(),
        nullable=False,
        server_default=text("'{}'::uuid[]"),
    ),
    Column("work_posture", String(16)),
    Column("applicability", String(20), nullable=False),
    Column("decision_version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("rebuild_required", Boolean, nullable=False, server_default=text("false")),
    CheckConstraint("btrim(subject_statement) <> ''", name="subject_nonempty"),
    CheckConstraint(
        "scope_completeness IN ('unresolved', 'established')",
        name="scope_completeness",
    ),
    CheckConstraint(
        "scope_completeness <> 'established' OR cardinality(scope_portfolio_ids) > 0",
        name="established_scope_nonempty",
    ),
    CheckConstraint("decision_version >= 1", name="decision_version_positive"),
    CheckConstraint(
        "lifecycle_interpretation_kind IN "
        "('NOT_YET_EFFECTIVE', 'DETERMINATE', 'CONTESTED')",
        name="lifecycle_interpretation_kind",
    ),
    CheckConstraint(
        "applicability IN ('operative', 'non_operative', 'contested')",
        name="applicability",
    ),
)

Index(
    "ix_investment_decisions_continuity_candidates",
    investment_decisions.c.lifecycle_disposition,
    investment_decisions.c.applicability,
)

investment_decision_lifecycle_facts = Table(
    "investment_decision_lifecycle_facts",
    metadata,
    _row_id(),
    Column("fact_id", UUID(as_uuid=True), nullable=False, unique=True),
    Column(
        "decision_id",
        UUID(as_uuid=True),
        ForeignKey(
            "investment_decisions.decision_id",
            name="fk_lifecycle_fact_decision",
            ondelete="RESTRICT",
        ),
        nullable=False,
    ),
    Column("lifecycle_sequence", Integer, nullable=False),
    Column("decision_version", Integer, nullable=False),
    Column("fact_kind", String(48), nullable=False),
    *_command_provenance_columns(),
    Column("effective_at", DateTime(timezone=True), nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
    Column(
        "need_id",
        UUID(as_uuid=True),
        ForeignKey("decision_needs.need_id", name="fk_lifecycle_fact_need"),
    ),
    Column("subject_statement", Text),
    Column("scope_completeness", String(16)),
    Column("scope_portfolio_ids", _uuid_array()),
    Column("continuity_determination", String(32)),
    Column("continuity_candidate_ids", _uuid_array()),
    Column("continuity_known_at", DateTime(timezone=True)),
    Column("continuity_rationale", Text),
    Column("human_decision_reference", Text),
    Column("human_decision_effect", String(32)),
    Column("work_control_reference", Text),
    Column("external_resolution_reference", Text),
    Column(
        "correction_target_fact_id",
        UUID(as_uuid=True),
        ForeignKey(
            "investment_decision_lifecycle_facts.fact_id",
            name="fk_lifecycle_fact_correction_target",
        ),
    ),
    Column("correction_effect", String(16)),
    Column("correction_basis_reference", Text),
    Column("replacement_disposition", String(32)),
    Column("replacement_basis_kind", String(40)),
    Column("replacement_basis_reference", Text),
    UniqueConstraint(
        "decision_id",
        "lifecycle_sequence",
        name="uq_lifecycle_facts_decision_sequence",
    ),
    CheckConstraint("lifecycle_sequence >= 1", name="sequence_positive"),
    CheckConstraint("decision_version >= 1", name="version_positive"),
    *_actor_attribution_constraints(),
    CheckConstraint("btrim(trigger_reference) <> ''", name="trigger_nonempty"),
    CheckConstraint(
        "scope_completeness IS NULL OR "
        "scope_completeness IN ('unresolved', 'established')",
        name="scope_completeness",
    ),
    CheckConstraint(
        "scope_completeness IS DISTINCT FROM 'established' "
        "OR cardinality(scope_portfolio_ids) > 0",
        name="scope_nonempty",
    ),
)

Index(
    "ix_lifecycle_facts_decision_recorded",
    investment_decision_lifecycle_facts.c.decision_id,
    investment_decision_lifecycle_facts.c.recorded_at,
)

investment_decision_relationships = Table(
    "investment_decision_relationships",
    metadata,
    _row_id(),
    Column("relationship_fact_id", UUID(as_uuid=True), nullable=False, unique=True),
    Column(
        "source_decision_id",
        UUID(as_uuid=True),
        ForeignKey(
            "investment_decisions.decision_id",
            name="fk_relationship_source_decision",
            ondelete="RESTRICT",
        ),
        nullable=False,
    ),
    Column(
        "target_decision_id",
        UUID(as_uuid=True),
        ForeignKey(
            "investment_decisions.decision_id",
            name="fk_relationship_target_decision",
            ondelete="RESTRICT",
        ),
        nullable=False,
    ),
    Column("relationship_type", String(32), nullable=False),
    Column("fact_kind", String(24), nullable=False),
    Column(
        "target_relationship_fact_id",
        UUID(as_uuid=True),
        ForeignKey(
            "investment_decision_relationships.relationship_fact_id",
            name="fk_relationship_correction_target",
        ),
    ),
    *_command_provenance_columns(),
    Column("effective_at", DateTime(timezone=True), nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
    Column("correction_effect", String(16)),
    Column("positive_claim_effective_at", DateTime(timezone=True)),
    Column("positive_basis", JSONB),
    Column("correction_basis", JSONB),
    Column("admission_evidence", JSONB),
    CheckConstraint(
        "source_decision_id <> target_decision_id", name="distinct_endpoints"
    ),
    *_actor_attribution_constraints(),
    CheckConstraint(
        "btrim(trigger_reference) <> ''", name="trigger_reference_nonempty"
    ),
    CheckConstraint(
        "relationship_type IN ('renewed_from', 'supersedes')",
        name="relationship_type",
    ),
    CheckConstraint("fact_kind IN ('base', 'correction')", name="fact_kind"),
)

Index(
    "ix_relationships_source_type",
    investment_decision_relationships.c.source_decision_id,
    investment_decision_relationships.c.relationship_type,
)
Index(
    "ix_relationships_target_type",
    investment_decision_relationships.c.target_decision_id,
    investment_decision_relationships.c.relationship_type,
)

investment_decision_command_receipts = Table(
    "investment_decision_command_receipts",
    metadata,
    _row_id(),
    Column("operation_id", UUID(as_uuid=True), nullable=False, unique=True),
    Column("command_kind", String(48), nullable=False),
    Column("request_fingerprint", String(64), nullable=False),
    Column("request_payload", JSONB, nullable=False),
    Column("result_payload", JSONB, nullable=False),
    Column("committed_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "char_length(request_fingerprint) = 64",
        name="fingerprint_sha256",
    ),
)

DECISION_TABLE_NAMES = frozenset(table.name for table in metadata.sorted_tables)
