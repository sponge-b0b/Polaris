from __future__ import annotations

from typing import cast

from sqlalchemy import Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from core.database.base import Base
from core.database.models.macro import (
    EconomicCalendarEventModel,
    MacroObservationModel,
    MacroRegimeSnapshotModel,
)


def test_macro_models_are_imported_into_base_metadata() -> None:
    assert "macro_observations" in Base.metadata.tables
    assert "macro_regime_snapshots" in Base.metadata.tables
    assert "economic_calendar_events" in Base.metadata.tables


def test_macro_observation_model_persists_curated_indicator_facts() -> None:
    columns = MacroObservationModel.__table__.c
    primary_keys = _primary_key_names(MacroObservationModel.__table__)
    unique_constraints = _unique_constraint_names(MacroObservationModel.__table__)

    assert primary_keys == {"observation_id"}
    assert columns.indicator_name.nullable is False
    assert columns.observation_timestamp.nullable is False
    assert columns.source.nullable is False
    assert columns.value.nullable is False
    assert columns.indicator_category.nullable is True
    assert columns.region.nullable is True
    assert columns.unit.nullable is True
    assert columns.frequency.nullable is True
    assert columns.release_timestamp.nullable is True
    assert columns.vintage_timestamp.nullable is True
    assert (
        "uq_macro_observations_indicator_timestamp_source_region" in unique_constraints
    )


def test_macro_regime_snapshot_model_persists_final_macro_outputs() -> None:
    columns = MacroRegimeSnapshotModel.__table__.c
    primary_keys = _primary_key_names(MacroRegimeSnapshotModel.__table__)

    assert primary_keys == {"regime_snapshot_id"}
    assert columns.timestamp.nullable is False
    assert columns.source.nullable is True
    assert columns.region.nullable is True
    assert columns.inflation_regime.nullable is True
    assert columns.liquidity_regime.nullable is True
    assert columns.growth_regime.nullable is True
    assert columns.fed_stance.nullable is True
    assert columns.yield_curve_regime.nullable is True
    assert columns.market_bias.nullable is True
    assert columns.summary.nullable is True
    assert columns.macro_regime.nullable is True
    assert columns.economic_regime.nullable is True
    assert columns.inflation_score.nullable is True
    assert columns.liquidity_score.nullable is True
    assert columns.growth_score.nullable is True
    assert columns.yield_curve_score.nullable is True
    assert columns.macro_score.nullable is True
    assert columns.risk_score.nullable is True
    assert columns.confidence.nullable is True
    assert "inputs" not in columns
    assert "outputs" not in columns
    assert isinstance(columns.macro_data_payload.type, JSONB)
    assert isinstance(columns.inflation_analysis_payload.type, JSONB)
    assert isinstance(columns.fed_analysis_payload.type, JSONB)
    assert isinstance(columns.liquidity_analysis_payload.type, JSONB)
    assert isinstance(columns.yield_curve_analysis_payload.type, JSONB)
    assert isinstance(columns.economic_regime_payload.type, JSONB)
    assert isinstance(columns.components_payload.type, JSONB)


def test_economic_calendar_event_model_persists_event_facts() -> None:
    columns = EconomicCalendarEventModel.__table__.c
    primary_keys = _primary_key_names(EconomicCalendarEventModel.__table__)
    unique_constraints = _unique_constraint_names(EconomicCalendarEventModel.__table__)

    assert primary_keys == {"event_id"}
    assert columns.event_name.nullable is False
    assert columns.event_timestamp.nullable is False
    assert columns.source.nullable is False
    assert columns.region.nullable is True
    assert columns.event_type.nullable is True
    assert columns.importance_score.nullable is True
    assert columns.actual_value.nullable is True
    assert columns.forecast_value.nullable is True
    assert columns.previous_value.nullable is True
    assert columns.surprise_score.nullable is True
    assert columns.unit.nullable is True
    assert columns.currency.nullable is True
    assert columns.release_status.nullable is True
    assert (
        "uq_economic_calendar_events_name_timestamp_source_region" in unique_constraints
    )


def test_macro_models_use_jsonb_at_persistence_boundaries() -> None:
    assert isinstance(MacroObservationModel.__table__.c.metadata.type, JSONB)
    assert isinstance(
        MacroRegimeSnapshotModel.__table__.c.macro_data_payload.type, JSONB
    )
    assert isinstance(
        MacroRegimeSnapshotModel.__table__.c.inflation_analysis_payload.type,
        JSONB,
    )
    assert isinstance(
        MacroRegimeSnapshotModel.__table__.c.fed_analysis_payload.type,
        JSONB,
    )
    assert isinstance(
        MacroRegimeSnapshotModel.__table__.c.liquidity_analysis_payload.type,
        JSONB,
    )
    assert isinstance(
        MacroRegimeSnapshotModel.__table__.c.yield_curve_analysis_payload.type,
        JSONB,
    )
    assert isinstance(
        MacroRegimeSnapshotModel.__table__.c.economic_regime_payload.type,
        JSONB,
    )
    assert isinstance(
        MacroRegimeSnapshotModel.__table__.c.components_payload.type, JSONB
    )
    assert isinstance(MacroRegimeSnapshotModel.__table__.c.metadata.type, JSONB)
    assert isinstance(EconomicCalendarEventModel.__table__.c.metadata.type, JSONB)


def test_macro_models_include_lineage_and_row_timestamps() -> None:
    for table in (
        MacroObservationModel.__table__,
        MacroRegimeSnapshotModel.__table__,
        EconomicCalendarEventModel.__table__,
    ):
        columns = table.c

        assert columns.workflow_name.nullable is True
        assert columns.execution_id.nullable is True
        assert columns.runtime_id.nullable is True
        assert columns.node_name.nullable is True
        assert columns.row_created_at.server_default is not None
        assert columns.row_updated_at.server_default is not None


def test_macro_models_index_core_query_paths() -> None:
    observation_indexes = _index_names(MacroObservationModel.__table__)
    regime_indexes = _index_names(MacroRegimeSnapshotModel.__table__)
    calendar_indexes = _index_names(EconomicCalendarEventModel.__table__)

    assert "idx_macro_observations_indicator_timestamp" in observation_indexes
    assert "idx_macro_observations_category_timestamp" in observation_indexes
    assert "idx_macro_observations_source_timestamp" in observation_indexes
    assert "idx_macro_observations_workflow_execution" in observation_indexes
    assert "idx_macro_regime_snapshots_timestamp_source" in regime_indexes
    assert "idx_macro_regime_snapshots_region_timestamp" in regime_indexes
    assert "idx_macro_regime_snapshots_regime_timestamp" in regime_indexes
    assert "idx_macro_regime_snapshots_workflow_execution" in regime_indexes
    assert "idx_economic_calendar_events_name_timestamp" in calendar_indexes
    assert "idx_economic_calendar_events_source_timestamp" in calendar_indexes
    assert "idx_economic_calendar_events_region_timestamp" in calendar_indexes
    assert "idx_economic_calendar_events_type_timestamp" in calendar_indexes
    assert "idx_economic_calendar_events_workflow_execution" in calendar_indexes


def _primary_key_names(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    return {column.name for column in sqlalchemy_table.primary_key}


def _unique_constraint_names(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    names: set[str] = set()
    for constraint in sqlalchemy_table.constraints:
        if not isinstance(constraint, UniqueConstraint):
            continue
        if isinstance(constraint.name, str):
            names.add(constraint.name)
    return names


def _index_names(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    return {index.name for index in sqlalchemy_table.indexes if index.name is not None}
