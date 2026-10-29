"""Integrated PostgreSQL schema for the staged R3 provider handoff.

The certified Investment Intelligence foundation is retained byte-for-byte in
``schema_foundation``. This module composes that schema with the independently
certified Portfolio State table from #404 so both sibling ``0009`` migration
branches share one runtime metadata registry without rewriting either migration.
"""

from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from . import schema_foundation as _foundation
from .schema_foundation import *  # noqa: F401,F403


def _portfolio_actor_columns() -> tuple[Column[Any], ...]:
    return (
        Column("actor_attribution_kind", String(16), nullable=False),
        Column("actor_id", UUID(as_uuid=True)),
        Column("actor_candidate_ids", ARRAY(UUID(as_uuid=True))),
    )


def _portfolio_source_fk(name: str) -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        ["source_state_id", "source_as_of"],
        ["portfolio_states.state_id", "portfolio_states.as_of"],
        name=name,
    )


portfolio_states = Table(
    "portfolio_states",
    _foundation.metadata,
    Column("state_id", UUID(as_uuid=True), primary_key=True),
    Column("portfolio_id", UUID(as_uuid=True), nullable=False),
    Column("as_of", DateTime(timezone=True), nullable=False),
    Column("known_at", DateTime(timezone=True), nullable=False),
    Column("source_system", Text, nullable=False),
    Column("source_record_reference", Text, nullable=False),
    Column("source_observed_at", DateTime(timezone=True), nullable=False),
    Column("currency", String(3), nullable=False),
    Column("capital_basis", Numeric, nullable=False),
    Column("cash", Numeric, nullable=False),
    Column("instrument_id", UUID(as_uuid=True), nullable=False),
    Column("position_quantity", Numeric, nullable=False),
    Column("position_value", Numeric, nullable=False),
    Column("exposure_value", Numeric, nullable=False),
    Column("allocation_fraction", Numeric, nullable=False),
    Column("interpretation_basis", Text, nullable=False),
    Column("uncertainty", Text),
    CheckConstraint("capital_basis > 0", name="positive_capital_basis"),
    CheckConstraint("known_at >= source_observed_at", name="known_after_source"),
    UniqueConstraint("state_id", "as_of", name="uq_portfolio_states_state_id"),
    Index("ix_portfolio_states_history", "portfolio_id", "as_of", "known_at"),
)

portfolio_context_commits = Table(
    "portfolio_context_commits",
    _foundation.metadata,
    Column("commit_id", UUID(as_uuid=True), primary_key=True),
    Column("known_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSONB, nullable=False),
    CheckConstraint("jsonb_typeof(payload) = 'object'", name="payload_object"),
    Index("ix_portfolio_context_commits_known_at", "known_at"),
)

projected_portfolio_consequences = Table(
    "projected_portfolio_consequences",
    _foundation.metadata,
    Column("consequence_id", UUID(as_uuid=True), primary_key=True),
    Column("alternative_id", UUID(as_uuid=True), nullable=False),
    Column("alternative_revision", Integer, nullable=False),
    Column("source_state_id", UUID(as_uuid=True), nullable=False),
    Column("source_as_of", DateTime(timezone=True), nullable=False),
    Column("horizon", Text, nullable=False),
    Column("scenario", Text, nullable=False),
    Column("assumptions", ARRAY(Text), nullable=False),
    Column("exposure_change", Numeric),
    Column("exposure_unresolved", Text),
    Column("allocation_change", Numeric),
    Column("allocation_unresolved", Text),
    Column("cash_effect", Numeric),
    Column("cash_unresolved", Text),
    Column("economic_benefits", ARRAY(Text), nullable=False),
    Column("adverse_possibilities", ARRAY(Text), nullable=False),
    Column("material_risk_changes", ARRAY(Text), nullable=False),
    *_portfolio_actor_columns(),
    Column("formed_at", DateTime(timezone=True), nullable=False),
    Column("known_at", DateTime(timezone=True), nullable=False),
    Column("uncertainty", Text, nullable=False),
    CheckConstraint("alternative_revision > 0", name="positive_alternative_revision"),
    CheckConstraint(
        "exposure_change IS NOT NULL OR exposure_unresolved IS NOT NULL OR "
        "allocation_change IS NOT NULL OR allocation_unresolved IS NOT NULL",
        name="material_spy_change",
    ),
    CheckConstraint(
        "NOT (exposure_change IS NOT NULL AND exposure_unresolved IS NOT NULL) AND "
        "NOT (allocation_change IS NOT NULL AND allocation_unresolved IS NOT NULL) AND "
        "NOT (cash_effect IS NOT NULL AND cash_unresolved IS NOT NULL)",
        name="change_resolution",
    ),
    *_foundation._actor_attribution_constraints(),
    _portfolio_source_fk("fk_consequence_source_state_as_of"),
    ForeignKeyConstraint(
        ["alternative_id", "alternative_revision"],
        [
            "decision_alternative_revisions.alternative_id",
            "decision_alternative_revisions.revision",
        ],
        name="fk_projected_portfolio_consequences_alternative_revision",
    ),
    Index("ix_projected_consequence_alternative", "alternative_id", "known_at"),
)

portfolio_risk_assessments = Table(
    "portfolio_risk_assessments",
    _foundation.metadata,
    Column("assessment_id", UUID(as_uuid=True), primary_key=True),
    Column("source_state_id", UUID(as_uuid=True), nullable=False),
    Column("source_as_of", DateTime(timezone=True), nullable=False),
    Column("projected_consequence_id", UUID(as_uuid=True)),
    Column("horizon", Text, nullable=False),
    Column("scenario", Text, nullable=False),
    Column("support_basis", Text, nullable=False),
    Column("evidence_ids", ARRAY(UUID(as_uuid=True)), nullable=False),
    Column("assumptions", ARRAY(Text), nullable=False),
    Column("downside_fraction", Numeric),
    Column("market_volatility_fraction", Numeric),
    Column("objective_shortfall_amount", Numeric),
    Column("dimensions", JSONB, nullable=False),
    Column("support_uncertainty", ARRAY(Text), nullable=False),
    Column("uncertainty", ARRAY(Text), nullable=False),
    *_portfolio_actor_columns(),
    Column("formed_at", DateTime(timezone=True), nullable=False),
    Column("known_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("jsonb_typeof(dimensions) = 'array'", name="dimensions_array"),
    CheckConstraint("jsonb_array_length(dimensions) > 0", name="dimensions_present"),
    *_foundation._actor_attribution_constraints(),
    _portfolio_source_fk("fk_risk_source_state_as_of"),
    ForeignKeyConstraint(
        ["projected_consequence_id"],
        ["projected_portfolio_consequences.consequence_id"],
        name="fk_risk_projected_consequence",
    ),
    Index("ix_portfolio_risk_source_history", "source_state_id", "known_at"),
    Index(
        "ix_portfolio_risk_projection_history", "projected_consequence_id", "known_at"
    ),
)

portfolio_judgment_acts = Table(
    "portfolio_judgment_acts",
    _foundation.metadata,
    Column("act_id", UUID(as_uuid=True), primary_key=True),
    Column("sequence", Integer, nullable=False),
    Column("consequence_id", UUID(as_uuid=True)),
    Column("assessment_id", UUID(as_uuid=True)),
    Column("effective_at", DateTime(timezone=True), nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
    Column("known_at", DateTime(timezone=True), nullable=False),
    Column("judgment_revision", Integer, nullable=False),
    Column("claim_catalog_version", Integer, nullable=False),
    Column("act", JSONB, nullable=False),
    CheckConstraint(
        "(consequence_id IS NULL) <> (assessment_id IS NULL)",
        name="one_portfolio_judgment_root",
    ),
    CheckConstraint("judgment_revision > 0", name="positive_judgment_revision"),
    CheckConstraint("sequence > 0", name="positive_sequence"),
    CheckConstraint("claim_catalog_version > 0", name="positive_catalog_version"),
    CheckConstraint("known_at >= recorded_at", name="known_after_recorded"),
    CheckConstraint("jsonb_typeof(act) = 'object'", name="act_object"),
    ForeignKeyConstraint(
        ["consequence_id"],
        ["projected_portfolio_consequences.consequence_id"],
        name="fk_portfolio_judgment_consequence",
    ),
    ForeignKeyConstraint(
        ["assessment_id"],
        ["portfolio_risk_assessments.assessment_id"],
        name="fk_portfolio_judgment_assessment",
    ),
    UniqueConstraint("consequence_id", "sequence", name="uq_consequence_act_sequence"),
    UniqueConstraint("assessment_id", "sequence", name="uq_risk_act_sequence"),
    Index("ix_portfolio_judgment_consequence_history", "consequence_id", "known_at"),
    Index("ix_portfolio_judgment_risk_history", "assessment_id", "known_at"),
)

investment_intelligence_judgment_acts = Table(
    "investment_intelligence_judgment_acts",
    _foundation.metadata,
    Column("act_id", UUID(as_uuid=True), primary_key=True),
    Column("row_id", BigInteger, Identity(), nullable=False),
    Column("target_family", String(48), nullable=False),
    Column("target_id", UUID(as_uuid=True), nullable=False),
    Column(
        # duplicate-code: Sharing would couple distinct owner tables.
        # arid: disable
        "decision_id",
        UUID(as_uuid=True),
        ForeignKey("investment_decisions.decision_id", ondelete="RESTRICT"),
        nullable=False,
        # arid: enable
    ),
    Column("sequence", Integer, nullable=False),
    Column("effective_at", DateTime(timezone=True), nullable=False),
    Column("draft", JSONB, nullable=False),
    CheckConstraint("sequence > 0", name="positive_sequence"),
    CheckConstraint("jsonb_typeof(draft) = 'object'", name="draft_object"),
    CheckConstraint(
        "target_family IN ('InvestmentHypothesisRef', 'InvestmentViewRef', "
        "'MeaningfulChallengeResultRef', 'InvestmentRecommendationRef', "
        "'RecommendationWithholdingJudgmentRef')",
        name="closed_target_family",
    ),
    UniqueConstraint(
        "target_family", "target_id", "sequence", name="uq_intelligence_act_sequence"
    ),
    UniqueConstraint("row_id", name="uq_intelligence_act_row_id"),
    Index("ix_intelligence_act_history", "target_family", "target_id", "sequence"),
)

investment_intelligence_act_publications = Table(
    "investment_intelligence_act_publications",
    _foundation.metadata,
    Column(
        "act_id",
        UUID(as_uuid=True),
        ForeignKey("investment_intelligence_judgment_acts.act_id", ondelete="RESTRICT"),
        primary_key=True,
    ),
    Column("committed_at", DateTime(timezone=True), nullable=False),
)

investment_intelligence_judgment_bases = Table(
    "investment_intelligence_judgment_bases",
    _foundation.metadata,
    _foundation._row_id(),
    Column(
        "operation_id",
        UUID(as_uuid=True),
        ForeignKey(
            "investment_intelligence_command_receipts.operation_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    ),
    Column("basis_index", Integer, nullable=False),
    Column("basis", JSONB, nullable=False),
    CheckConstraint("basis_index >= 0", name="basis_index_nonnegative"),
    UniqueConstraint("operation_id", "basis_index", name="uq_intelligence_basis"),
)

POLARIS_TABLE_NAMES = _foundation.POLARIS_TABLE_NAMES | frozenset(
    {
        "portfolio_states",
        "projected_portfolio_consequences",
        "portfolio_risk_assessments",
        "portfolio_judgment_acts",
        "portfolio_context_commits",
        "investment_intelligence_judgment_acts",
        "investment_intelligence_act_publications",
        "investment_intelligence_judgment_bases",
    }
)
