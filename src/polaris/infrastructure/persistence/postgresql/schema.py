"""Greenfield PostgreSQL schema for durable Polaris business truth."""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
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


def _command_provenance_columns() -> tuple[Column[Any], ...]:
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

evidence_observations = Table(
    "evidence_observations",
    metadata,
    _row_id(),
    Column("observation_id", UUID(as_uuid=True), nullable=False, unique=True),
    Column("source_identity", Text, nullable=False),
    Column("source_reference", Text, nullable=False),
    Column("source_authority", Text, nullable=False),
    Column("subject_identity", Text, nullable=False),
    Column("subject_reference", Text, nullable=False),
    Column("observed_at", DateTime(timezone=True), nullable=False),
    Column("acquired_at", DateTime(timezone=True), nullable=False),
    Column("effective_at", DateTime(timezone=True)),
    Column("retained_representation", Text),
    Column("verification_reference", Text),
    Column(
        "supersedes_observation_id",
        UUID(as_uuid=True),
        ForeignKey(
            "evidence_observations.observation_id",
            name="fk_evidence_observation_supersedes",
            ondelete="RESTRICT",
        ),
    ),
    CheckConstraint("btrim(source_identity) <> ''", name="source_identity_nonempty"),
    CheckConstraint("btrim(source_reference) <> ''", name="source_reference_nonempty"),
    CheckConstraint("btrim(source_authority) <> ''", name="source_authority_nonempty"),
    CheckConstraint("btrim(subject_identity) <> ''", name="subject_identity_nonempty"),
    CheckConstraint(
        "btrim(subject_reference) <> ''", name="subject_reference_nonempty"
    ),
    CheckConstraint(
        "retained_representation IS NOT NULL OR verification_reference IS NOT NULL",
        name="reconstructable_material",
    ),
    CheckConstraint(
        "retained_representation IS NULL OR btrim(retained_representation) <> ''",
        name="retained_representation_nonempty",
    ),
    CheckConstraint(
        "verification_reference IS NULL OR btrim(verification_reference) <> ''",
        name="verification_reference_nonempty",
    ),
    CheckConstraint(
        "supersedes_observation_id IS NULL "
        "OR supersedes_observation_id <> observation_id",
        name="supersedes_distinct",
    ),
)

# duplicate-code: Decision and Evidence receipts are separate domain-owned
# idempotency records and may evolve independently; a shared table factory would
# make physical similarity an architectural coupling.
# arid: disable
evidence_observation_command_receipts = Table(
    "evidence_observation_command_receipts",
    metadata,
    _row_id(),
    Column("operation_id", UUID(as_uuid=True), nullable=False, unique=True),
    Column("request_fingerprint", String(64), nullable=False),
    Column("request_payload", JSONB, nullable=False),
    Column("result_payload", JSONB, nullable=False),
    Column("committed_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "char_length(request_fingerprint) = 64",
        name="fingerprint_sha256",
    ),
)
# arid: enable

evidence_requirement_set_versions = Table(
    "evidence_requirement_set_versions",
    metadata,
    _row_id(),
    Column("set_id", UUID(as_uuid=True), nullable=False),
    Column("version_id", UUID(as_uuid=True), nullable=False, unique=True),
    Column("authority_identity", Text, nullable=False),
    Column("source_reference", Text, nullable=False),
    Column("effective_at", DateTime(timezone=True), nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
    Column("applicability", JSONB, nullable=False),
    Column(
        "predecessor_version_id",
        UUID(as_uuid=True),
        ForeignKey(
            "evidence_requirement_set_versions.version_id",
            name="fk_evidence_requirement_version_predecessor",
            ondelete="RESTRICT",
        ),
    ),
    Column("predecessor_effect", String(16)),
    UniqueConstraint(
        "set_id",
        "version_id",
        name="uq_evidence_requirement_versions_set_version",
    ),
    CheckConstraint(
        "btrim(authority_identity) <> ''", name="authority_identity_nonempty"
    ),
    CheckConstraint("btrim(source_reference) <> ''", name="source_reference_nonempty"),
    CheckConstraint(
        "(predecessor_version_id IS NULL AND predecessor_effect IS NULL) OR "
        "(predecessor_version_id IS NOT NULL AND predecessor_effect IS NOT NULL)",
        name="predecessor_complete",
    ),
    CheckConstraint(
        "predecessor_effect IS NULL OR "
        "predecessor_effect IN ('corrects', 'supersedes')",
        name="predecessor_effect",
    ),
    CheckConstraint(
        "predecessor_version_id IS NULL OR predecessor_version_id <> version_id",
        name="predecessor_distinct",
    ),
)

evidence_requirement_definitions = Table(
    "evidence_requirement_definitions",
    metadata,
    _row_id(),
    Column("set_id", UUID(as_uuid=True), nullable=False),
    Column("version_id", UUID(as_uuid=True), nullable=False),
    Column("requirement_id", UUID(as_uuid=True), nullable=False),
    Column("position", Integer, nullable=False),
    Column("requirement_kind", String(16), nullable=False),
    Column("definition", JSONB, nullable=False),
    ForeignKeyConstraint(
        ["set_id", "version_id"],
        [
            "evidence_requirement_set_versions.set_id",
            "evidence_requirement_set_versions.version_id",
        ],
        name="fk_evidence_requirement_definition_version",
        ondelete="RESTRICT",
    ),
    UniqueConstraint(
        "set_id",
        "version_id",
        "requirement_id",
        name="uq_evidence_requirement_definitions_identity",
    ),
    UniqueConstraint(
        "version_id",
        "position",
        name="uq_evidence_requirement_definitions_position",
    ),
    CheckConstraint("position >= 0", name="position_nonnegative"),
    CheckConstraint(
        "requirement_kind IN ('freshness', 'sufficiency')",
        name="requirement_kind",
    ),
)

evidence_bindings = Table(
    "evidence_bindings",
    metadata,
    _row_id(),
    Column("binding_id", UUID(as_uuid=True), nullable=False, unique=True),
    Column(
        "observation_id",
        UUID(as_uuid=True),
        ForeignKey(
            "evidence_observations.observation_id",
            name="fk_evidence_binding_observation",
            ondelete="RESTRICT",
        ),
        nullable=False,
    ),
    Column("target_family", String(48), nullable=False),
    Column("target_id", UUID(as_uuid=True), nullable=False),
    Column("scope_kind", String(24), nullable=False),
    Column("claim_id", UUID(as_uuid=True)),
    Column("evidence_use", String(40), nullable=False),
    Column("role", String(24), nullable=False),
    Column("availability", String(16), nullable=False),
    Column("materially_used", Boolean, nullable=False),
    Column("effective_at", DateTime(timezone=True), nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
    Column("material_qualification", Text),
    Column("freshness_set_id", UUID(as_uuid=True)),
    Column("freshness_version_id", UUID(as_uuid=True)),
    Column("freshness_requirement_id", UUID(as_uuid=True)),
    Column("freshness_basis_reference", Text),
    ForeignKeyConstraint(
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
    CheckConstraint(
        "target_family IN ("
        "'investment_hypothesis', 'investment_view', "
        "'meaningful_challenge_result', 'projected_portfolio_consequence', "
        "'portfolio_risk_assessment', 'investment_recommendation', "
        "'recommendation_withholding_judgment', 'human_investment_decision', "
        "'decision_evaluation', 'lesson'"
        ")",
        name="target_family",
    ),
    CheckConstraint(
        "(scope_kind = 'judgment_wide' AND claim_id IS NULL) OR "
        "(scope_kind = 'claim_specific' AND claim_id IS NOT NULL)",
        name="scope_kind",
    ),
    CheckConstraint(
        "evidence_use IN ("
        "'judgment_basis', 'challenge_basis', 'current_support_check', "
        "'retrospective_later_evidence', 'reconstruction_only'"
        ")",
        name="evidence_use",
    ),
    CheckConstraint(
        "role IN ("
        "'supporting', 'conflicting', 'constraining', "
        "'qualifying', 'contextual', 'reconstruction'"
        ")",
        name="role",
    ),
    CheckConstraint(
        "availability IN ('available', 'unavailable', 'unknown')",
        name="availability",
    ),
    CheckConstraint(
        "NOT materially_used OR availability = 'available'",
        name="material_use_requires_available",
    ),
    CheckConstraint(
        "material_qualification IS NULL OR btrim(material_qualification) <> ''",
        name="material_qualification_nonempty",
    ),
    CheckConstraint(
        "("
        "freshness_set_id IS NULL AND freshness_version_id IS NULL AND "
        "freshness_requirement_id IS NULL AND freshness_basis_reference IS NULL"
        ") OR ("
        "freshness_set_id IS NOT NULL AND freshness_version_id IS NOT NULL AND "
        "freshness_requirement_id IS NOT NULL AND freshness_basis_reference IS NOT NULL"
        ")",
        name="freshness_reference_complete",
    ),
    CheckConstraint(
        "freshness_basis_reference IS NULL OR btrim(freshness_basis_reference) <> ''",
        name="freshness_basis_reference_nonempty",
    ),
)

# duplicate-code: Evidence observation and binding receipts are independently
# evolvable operation contracts; sharing one table factory would couple them.
# arid: disable
evidence_binding_command_receipts = Table(
    "evidence_binding_command_receipts",
    metadata,
    _row_id(),
    Column("operation_id", UUID(as_uuid=True), nullable=False, unique=True),
    Column("request_fingerprint", String(64), nullable=False),
    Column("request_payload", JSONB, nullable=False),
    Column("result_payload", JSONB, nullable=False),
    Column("committed_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "char_length(request_fingerprint) = 64",
        name="fingerprint_sha256",
    ),
)
# arid: enable


DECISION_TABLE_NAMES = frozenset(
    {
        "decision_needs",
        "investment_decisions",
        "investment_decision_lifecycle_facts",
        "investment_decision_relationships",
        "investment_decision_command_receipts",
    }
)
EVIDENCE_TABLE_NAMES = frozenset(
    {
        "evidence_observations",
        "evidence_observation_command_receipts",
        "evidence_bindings",
        "evidence_binding_command_receipts",
    }
)
CONFIGURATION_TABLE_NAMES = frozenset(
    {
        "evidence_requirement_set_versions",
        "evidence_requirement_definitions",
    }
)
POLARIS_TABLE_NAMES = (
    DECISION_TABLE_NAMES | EVIDENCE_TABLE_NAMES | CONFIGURATION_TABLE_NAMES
)
