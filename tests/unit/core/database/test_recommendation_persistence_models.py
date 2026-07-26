from __future__ import annotations

from typing import cast

from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import JSONB

from core.database.base import Base
from core.database.models.recommendations import (
    RecommendationClaimEvidenceLinkModel,
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
    assert "recommendation_claim_evidence_links" in Base.metadata.tables


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


def test_recommendation_claim_evidence_link_model_fields() -> None:
    table = cast(Table, RecommendationClaimEvidenceLinkModel.__table__)
    columns = table.c
    primary_keys = {column.name for column in table.primary_key}
    recommendation_foreign_keys = {
        foreign_key.target_fullname
        for foreign_key in columns.recommendation_id.foreign_keys
    }
    rationale_foreign_keys = {
        foreign_key.target_fullname for foreign_key in columns.rationale_id.foreign_keys
    }
    packet_foreign_keys = {
        foreign_key.target_fullname for foreign_key in columns.packet_id.foreign_keys
    }
    check_constraints = {constraint.name for constraint in table.constraints}
    index_names = {index.name for index in table.indexes}

    assert primary_keys == {"link_id"}
    assert columns.recommendation_id.nullable is False
    assert columns.rationale_id.nullable is True
    assert columns.claim_target_id.nullable is False
    assert columns.packet_id.nullable is False
    assert columns.packet_claim_id.nullable is False
    assert columns.risk_tier.nullable is False
    assert columns.material.nullable is False
    assert columns.supporting_evidence_ids.nullable is False
    assert columns.reconstruction_reference_ids.nullable is False
    assert recommendation_foreign_keys == {"recommendations.recommendation_id"}
    assert rationale_foreign_keys == {"recommendation_rationales.rationale_id"}
    assert packet_foreign_keys == {"decision_evidence_packets.packet_id"}
    assert "ck_recommendation_claim_evidence_links_risk_tier" in check_constraints
    assert (
        "ck_recommendation_claim_evidence_links_material_has_support"
        in check_constraints
    )
    assert "idx_recommendation_claim_evidence_links_recommendation_claim" in index_names
    assert "idx_recommendation_claim_evidence_links_packet_claim" in index_names


def test_recommendation_claim_evidence_link_model_uses_jsonb_reference_arrays() -> None:
    assert isinstance(
        RecommendationClaimEvidenceLinkModel.__table__.c.supporting_evidence_ids.type,
        JSONB,
    )
    assert isinstance(
        RecommendationClaimEvidenceLinkModel.__table__.c.reconstruction_reference_ids.type,
        JSONB,
    )
    assert isinstance(
        RecommendationClaimEvidenceLinkModel.__table__.c.uncertainty_ids.type,
        JSONB,
    )
    assert isinstance(
        RecommendationClaimEvidenceLinkModel.__table__.c.limitation_ids.type,
        JSONB,
    )
