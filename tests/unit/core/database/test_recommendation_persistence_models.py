from __future__ import annotations

from typing import cast

from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import JSONB

from core.database.base import Base
from core.database.models.recommendations import (
    RecommendationModel,
    RecommendationOutcomeModel,
    RecommendationRationaleModel,
    TradeSetupModel,
    WatchlistItemModel,
)


def test_recommendation_models_are_imported_into_base_metadata() -> None:
    assert "recommendations" in Base.metadata.tables
    assert "recommendation_rationales" in Base.metadata.tables
    assert "recommendation_outcomes" in Base.metadata.tables
    assert "trade_setups" in Base.metadata.tables
    assert "watchlist_items" in Base.metadata.tables


def test_recommendation_model_persists_core_recommendation_fields() -> None:
    columns = RecommendationModel.__table__.c
    primary_keys = {column.name for column in RecommendationModel.__table__.primary_key}

    assert primary_keys == {"recommendation_id"}
    assert columns.symbol.nullable is False
    assert columns.bias.nullable is False
    assert columns.confidence.nullable is False
    assert columns.setup_quality.nullable is True
    assert columns.risk_score.nullable is True
    assert columns.risk_level.nullable is True
    assert columns.time_horizon.nullable is True
    assert columns.status.nullable is True
    assert columns.workflow_name.nullable is True
    assert columns.execution_id.nullable is True
    assert columns.runtime_id.nullable is True
    assert columns.node_name.nullable is True
    assert columns.created_at.nullable is False
    assert columns.row_created_at.server_default is not None
    assert columns.row_updated_at.server_default is not None


def test_recommendation_rationale_model_preserves_full_text() -> None:
    columns = RecommendationRationaleModel.__table__.c
    primary_keys = {
        column.name for column in RecommendationRationaleModel.__table__.primary_key
    }
    foreign_keys = {
        foreign_key.target_fullname
        for foreign_key in columns.recommendation_id.foreign_keys
    }

    assert primary_keys == {"rationale_id"}
    assert columns.recommendation_id.nullable is False
    assert columns.rationale_type.nullable is False
    assert columns.rationale_text.nullable is False
    assert columns.confidence.nullable is True
    assert foreign_keys == {"recommendations.recommendation_id"}


def test_recommendation_outcome_model_persists_human_feedback() -> None:
    columns = RecommendationOutcomeModel.__table__.c
    primary_keys = {
        column.name for column in RecommendationOutcomeModel.__table__.primary_key
    }
    foreign_keys = {
        foreign_key.target_fullname
        for foreign_key in columns.recommendation_id.foreign_keys
    }

    assert primary_keys == {"outcome_id"}
    assert columns.recommendation_id.nullable is False
    assert columns.evaluated_at.nullable is False
    assert columns.human_action.nullable is True
    assert columns.outcome.nullable is True
    assert columns.outcome_return.nullable is True
    assert columns.outcome_notes.nullable is True
    assert foreign_keys == {"recommendations.recommendation_id"}


def test_trade_setup_model_persists_setup_context() -> None:
    columns = TradeSetupModel.__table__.c
    primary_keys = {column.name for column in TradeSetupModel.__table__.primary_key}
    foreign_keys = {
        foreign_key.target_fullname
        for foreign_key in columns.recommendation_id.foreign_keys
    }

    assert primary_keys == {"setup_id"}
    assert columns.recommendation_id.nullable is True
    assert columns.symbol.nullable is False
    assert columns.setup_type.nullable is False
    assert columns.bias.nullable is False
    assert columns.setup_quality.nullable is True
    assert columns.confidence.nullable is True
    assert columns.risk_score.nullable is True
    assert columns.risk_reward_ratio.nullable is True
    assert columns.created_at.nullable is False
    assert foreign_keys == {"recommendations.recommendation_id"}


def test_watchlist_item_model_persists_reviewable_candidates() -> None:
    columns = WatchlistItemModel.__table__.c
    primary_keys = {column.name for column in WatchlistItemModel.__table__.primary_key}
    foreign_keys = {
        foreign_key.target_fullname
        for foreign_key in columns.recommendation_id.foreign_keys
    }

    assert primary_keys == {"watchlist_item_id"}
    assert columns.recommendation_id.nullable is True
    assert columns.symbol.nullable is False
    assert columns.reason.nullable is False
    assert columns.priority.nullable is False
    assert columns.status.nullable is True
    assert columns.bias.nullable is True
    assert columns.confidence.nullable is True
    assert columns.setup_quality.nullable is True
    assert foreign_keys == {"recommendations.recommendation_id"}


def test_recommendation_models_use_jsonb_at_persistence_boundaries() -> None:
    assert isinstance(RecommendationModel.__table__.c.entry_context.type, JSONB)
    assert isinstance(RecommendationModel.__table__.c.stop_context.type, JSONB)
    assert isinstance(RecommendationModel.__table__.c.target_context.type, JSONB)
    assert isinstance(RecommendationModel.__table__.c.supporting_signals.type, JSONB)
    assert isinstance(RecommendationModel.__table__.c.metadata.type, JSONB)
    assert isinstance(
        RecommendationRationaleModel.__table__.c.supporting_signals.type,
        JSONB,
    )
    assert isinstance(RecommendationRationaleModel.__table__.c.metadata.type, JSONB)
    assert isinstance(RecommendationOutcomeModel.__table__.c.metadata.type, JSONB)
    assert isinstance(TradeSetupModel.__table__.c.entry_context.type, JSONB)
    assert isinstance(TradeSetupModel.__table__.c.stop_context.type, JSONB)
    assert isinstance(TradeSetupModel.__table__.c.target_context.type, JSONB)
    assert isinstance(TradeSetupModel.__table__.c.metadata.type, JSONB)
    assert isinstance(WatchlistItemModel.__table__.c.metadata.type, JSONB)


def test_recommendation_model_indexes_query_paths() -> None:
    recommendation_indexes = _index_names(RecommendationModel.__table__)
    rationale_indexes = _index_names(RecommendationRationaleModel.__table__)
    outcome_indexes = _index_names(RecommendationOutcomeModel.__table__)
    setup_indexes = _index_names(TradeSetupModel.__table__)
    watchlist_indexes = _index_names(WatchlistItemModel.__table__)

    assert "idx_recommendations_symbol_created_at" in recommendation_indexes
    assert "idx_recommendations_workflow_execution" in recommendation_indexes
    assert "idx_recommendations_status_bias" in recommendation_indexes
    assert "idx_recommendations_risk_level_created_at" in recommendation_indexes
    assert (
        "idx_recommendation_rationales_recommendation_created_at" in rationale_indexes
    )
    assert "idx_recommendation_rationales_workflow_execution" in rationale_indexes
    assert "idx_recommendation_outcomes_recommendation_evaluated_at" in outcome_indexes
    assert "idx_recommendation_outcomes_workflow_execution" in outcome_indexes
    assert "idx_recommendation_outcomes_action_outcome" in outcome_indexes
    assert "idx_trade_setups_symbol_created_at" in setup_indexes
    assert "idx_trade_setups_workflow_execution" in setup_indexes
    assert "idx_trade_setups_bias_quality" in setup_indexes
    assert "idx_watchlist_items_symbol_created_at" in watchlist_indexes
    assert "idx_watchlist_items_workflow_execution" in watchlist_indexes
    assert "idx_watchlist_items_status_priority" in watchlist_indexes


def _index_names(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    return {index.name for index in sqlalchemy_table.indexes if index.name is not None}
