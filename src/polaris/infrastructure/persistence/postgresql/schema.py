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
    Index,
    Numeric,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID

from .schema_foundation import *  # noqa: F401,F403
from .schema_foundation import (
    POLARIS_TABLE_NAMES as _FOUNDATION_TABLE_NAMES,
    metadata,
)

portfolio_states = Table(
    "portfolio_states",
    metadata,
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
    Index("ix_portfolio_states_history", "portfolio_id", "as_of", "known_at"),
)

POLARIS_TABLE_NAMES = _FOUNDATION_TABLE_NAMES | frozenset({"portfolio_states"})
