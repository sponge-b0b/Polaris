"""Integrated PostgreSQL schema for the staged R3 provider handoff.

The certified Investment Intelligence foundation is retained byte-for-byte in
``schema_foundation``. This module composes that schema with the independently
certified Portfolio State table from #404 so both sibling ``0009`` migration
branches share one runtime metadata registry without rewriting either migration.
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID

from . import schema_foundation as _foundation
from .schema_foundation import *  # noqa: F401,F403

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
    Column("actor_attribution_kind", String(16), nullable=False),
    Column("actor_id", UUID(as_uuid=True)),
    Column("actor_candidate_ids", ARRAY(UUID(as_uuid=True))),
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
    ForeignKeyConstraint(
        ["source_state_id", "source_as_of"],
        ["portfolio_states.state_id", "portfolio_states.as_of"],
        name="fk_consequence_source_state_as_of",
    ),
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

POLARIS_TABLE_NAMES = _foundation.POLARIS_TABLE_NAMES | frozenset(
    {"portfolio_states", "projected_portfolio_consequences"}
)
