from __future__ import annotations

from typing import cast

from sqlalchemy import CheckConstraint
from sqlalchemy import Table
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB

from core.database.base import Base
from core.database.models.attribution import AttributionRecordModel
from core.database.models.attribution import RecommendationAttributionModel
from core.database.models.attribution import SignalAttributionModel


def test_attribution_models_are_imported_into_base_metadata() -> None:
    assert "attribution_records" in Base.metadata.tables
    assert "signal_attribution" in Base.metadata.tables
    assert "recommendation_attribution" in Base.metadata.tables


def test_attribution_record_model_persists_generic_target_attribution() -> None:
    columns = AttributionRecordModel.__table__.c
    primary_keys = _primary_key_names(AttributionRecordModel.__table__)

    assert primary_keys == {"attribution_id"}
    assert columns.target_record_type.nullable is False
    assert columns.target_record_id.nullable is False
    assert columns.attribution_type.nullable is False
    assert columns.contribution_type.nullable is False
    assert columns.contribution_score.nullable is False
    assert columns.confidence.nullable is False
    assert columns.explanation.nullable is False
    assert isinstance(columns.explanation.type, Text)
    assert columns.timestamp.nullable is False
    assert columns.agent_name.nullable is True
    assert columns.agent_type.nullable is True
    assert _foreign_key_targets(AttributionRecordModel.__table__) == set()


def test_signal_attribution_model_links_to_agent_signal_and_preserves_explanation() -> (
    None
):
    columns = SignalAttributionModel.__table__.c
    primary_keys = _primary_key_names(SignalAttributionModel.__table__)

    assert primary_keys == {"signal_attribution_id"}
    assert columns.signal_id.nullable is False
    assert _foreign_key_targets(SignalAttributionModel.__table__) == {
        "agent_signals.signal_id",
    }
    assert columns.attribution_type.nullable is False
    assert columns.contribution_type.nullable is False
    assert columns.contribution_score.nullable is False
    assert columns.confidence.nullable is False
    assert columns.explanation.nullable is False
    assert isinstance(columns.explanation.type, Text)
    assert columns.timestamp.nullable is False
    assert columns.signal_type.nullable is True
    assert columns.agent_name.nullable is True
    assert columns.agent_type.nullable is True
    assert columns.symbol.nullable is True
    assert columns.universe.nullable is True


def test_recommendation_attribution_model_links_recommendations_and_optional_signal() -> (
    None
):
    columns = RecommendationAttributionModel.__table__.c
    primary_keys = _primary_key_names(RecommendationAttributionModel.__table__)

    assert primary_keys == {"recommendation_attribution_id"}
    assert columns.recommendation_id.nullable is False
    assert columns.signal_id.nullable is True
    assert _foreign_key_targets(RecommendationAttributionModel.__table__) == {
        "agent_signals.signal_id",
        "recommendations.recommendation_id",
    }
    assert columns.attribution_type.nullable is False
    assert columns.contribution_type.nullable is False
    assert columns.contribution_score.nullable is False
    assert columns.confidence.nullable is False
    assert columns.explanation.nullable is False
    assert isinstance(columns.explanation.type, Text)
    assert columns.timestamp.nullable is False
    assert columns.agent_name.nullable is True
    assert columns.agent_type.nullable is True
    assert columns.symbol.nullable is True
    assert columns.universe.nullable is True


def test_attribution_models_use_jsonb_at_persistence_boundaries() -> None:
    for table in (
        AttributionRecordModel.__table__,
        SignalAttributionModel.__table__,
        RecommendationAttributionModel.__table__,
    ):
        assert isinstance(table.c.source_records.type, JSONB)
        assert isinstance(table.c.metadata.type, JSONB)


def test_attribution_models_include_lineage_and_row_timestamps() -> None:
    for table in (
        AttributionRecordModel.__table__,
        SignalAttributionModel.__table__,
        RecommendationAttributionModel.__table__,
    ):
        columns = table.c

        assert columns.workflow_name.nullable is True
        assert columns.execution_id.nullable is True
        assert columns.runtime_id.nullable is True
        assert columns.node_name.nullable is True
        assert columns.row_created_at.server_default is not None
        assert columns.row_updated_at.server_default is not None


def test_attribution_models_enforce_score_ranges() -> None:
    assert _check_constraint_names(AttributionRecordModel.__table__) >= {
        "ck_attribution_records_contribution_score_range",
        "ck_attribution_records_confidence_range",
    }
    assert _check_constraint_names(SignalAttributionModel.__table__) >= {
        "ck_signal_attribution_contribution_score_range",
        "ck_signal_attribution_confidence_range",
    }
    assert _check_constraint_names(RecommendationAttributionModel.__table__) >= {
        "ck_recommendation_attribution_contribution_score_range",
        "ck_recommendation_attribution_confidence_range",
    }


def test_attribution_models_index_core_query_paths() -> None:
    attribution_indexes = _index_names(AttributionRecordModel.__table__)
    signal_indexes = _index_names(SignalAttributionModel.__table__)
    recommendation_indexes = _index_names(RecommendationAttributionModel.__table__)

    assert "idx_attribution_records_target_record" in attribution_indexes
    assert "idx_attribution_records_agent_timestamp" in attribution_indexes
    assert "idx_attribution_records_type_timestamp" in attribution_indexes
    assert "idx_attribution_records_workflow_execution" in attribution_indexes

    assert "idx_signal_attribution_signal_timestamp" in signal_indexes
    assert "idx_signal_attribution_agent_timestamp" in signal_indexes
    assert "idx_signal_attribution_type_timestamp" in signal_indexes
    assert "idx_signal_attribution_symbol_timestamp" in signal_indexes
    assert "idx_signal_attribution_universe_timestamp" in signal_indexes
    assert "idx_signal_attribution_workflow_execution" in signal_indexes
    assert "ix_signal_attribution_signal_id" in signal_indexes

    assert (
        "idx_recommendation_attribution_recommendation_timestamp"
        in recommendation_indexes
    )
    assert "idx_recommendation_attribution_signal_timestamp" in recommendation_indexes
    assert "idx_recommendation_attribution_agent_timestamp" in recommendation_indexes
    assert "idx_recommendation_attribution_type_timestamp" in recommendation_indexes
    assert "idx_recommendation_attribution_symbol_timestamp" in recommendation_indexes
    assert "idx_recommendation_attribution_universe_timestamp" in recommendation_indexes
    assert "idx_recommendation_attribution_workflow_execution" in recommendation_indexes
    assert "ix_recommendation_attribution_recommendation_id" in recommendation_indexes
    assert "ix_recommendation_attribution_signal_id" in recommendation_indexes


def _primary_key_names(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    return {column.name for column in sqlalchemy_table.primary_key}


def _foreign_key_targets(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    return {
        foreign_key.target_fullname for foreign_key in sqlalchemy_table.foreign_keys
    }


def _check_constraint_names(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    names: set[str] = set()
    for constraint in sqlalchemy_table.constraints:
        if not isinstance(constraint, CheckConstraint):
            continue
        if isinstance(constraint.name, str):
            names.add(constraint.name)
    return names


def _index_names(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    return {index.name for index in sqlalchemy_table.indexes if index.name is not None}
