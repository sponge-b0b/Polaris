from __future__ import annotations

from typing import cast

from sqlalchemy import Table
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB

from core.database.base import Base
from core.database.models.agent_intelligence import AgentReasoningModel
from core.database.models.agent_intelligence import AgentRecommendationModel
from core.database.models.agent_intelligence import AgentRiskAssessmentModel


def test_agent_intelligence_models_are_imported_into_base_metadata() -> None:
    assert "agent_reasoning" in Base.metadata.tables
    assert "agent_recommendations" in Base.metadata.tables
    assert "agent_risk_assessments" in Base.metadata.tables


def test_agent_reasoning_model_persists_full_reasoning_and_signal_link() -> None:
    columns = AgentReasoningModel.__table__.c
    primary_keys = _primary_key_names(AgentReasoningModel.__table__)

    assert primary_keys == {"reasoning_id"}
    assert columns.agent_signal_id.nullable is False
    assert _foreign_key_targets(AgentReasoningModel.__table__) == {
        "agent_signals.signal_id",
    }
    assert columns.agent_name.nullable is False
    assert columns.agent_type.nullable is False
    assert columns.timestamp.nullable is False
    assert columns.reasoning_type.nullable is True
    assert columns.model_name.nullable is True
    assert columns.prompt_version.nullable is True
    assert columns.symbol.nullable is True
    assert columns.universe.nullable is True
    assert columns.reasoning_text.nullable is False
    assert isinstance(columns.reasoning_text.type, Text)
    assert columns.full_llm_response.nullable is True
    assert isinstance(columns.full_llm_response.type, Text)


def test_agent_recommendation_model_persists_recommendations_and_full_rationale() -> (
    None
):
    columns = AgentRecommendationModel.__table__.c
    primary_keys = _primary_key_names(AgentRecommendationModel.__table__)

    assert primary_keys == {"agent_recommendation_id"}
    assert columns.agent_signal_id.nullable is False
    assert _foreign_key_targets(AgentRecommendationModel.__table__) == {
        "agent_signals.signal_id",
    }
    assert columns.agent_name.nullable is False
    assert columns.agent_type.nullable is False
    assert columns.timestamp.nullable is False
    assert columns.recommendation_type.nullable is False
    assert columns.recommendation_text.nullable is False
    assert isinstance(columns.recommendation_text.type, Text)
    assert columns.confidence.nullable is True
    assert columns.conviction.nullable is True
    assert columns.rationale_text.nullable is True
    assert isinstance(columns.rationale_text.type, Text)
    assert columns.full_llm_response.nullable is True
    assert isinstance(columns.full_llm_response.type, Text)


def test_agent_risk_assessment_model_persists_risk_assessments_and_full_text() -> None:
    columns = AgentRiskAssessmentModel.__table__.c
    primary_keys = _primary_key_names(AgentRiskAssessmentModel.__table__)

    assert primary_keys == {"risk_assessment_id"}
    assert columns.agent_signal_id.nullable is False
    assert _foreign_key_targets(AgentRiskAssessmentModel.__table__) == {
        "agent_signals.signal_id",
    }
    assert columns.agent_name.nullable is False
    assert columns.agent_type.nullable is False
    assert columns.timestamp.nullable is False
    assert columns.risk_type.nullable is False
    assert columns.assessment_text.nullable is False
    assert isinstance(columns.assessment_text.type, Text)
    assert columns.risk_level.nullable is True
    assert columns.risk_score.nullable is True
    assert columns.confidence.nullable is True
    assert columns.mitigation.nullable is True
    assert isinstance(columns.mitigation.type, Text)
    assert columns.full_llm_response.nullable is True
    assert isinstance(columns.full_llm_response.type, Text)


def test_agent_intelligence_models_use_jsonb_at_persistence_boundaries() -> None:
    assert isinstance(AgentReasoningModel.__table__.c.inputs_payload.type, JSONB)
    assert isinstance(AgentReasoningModel.__table__.c.outputs_payload.type, JSONB)
    assert isinstance(AgentReasoningModel.__table__.c.linked_records.type, JSONB)
    assert isinstance(AgentReasoningModel.__table__.c.metadata.type, JSONB)
    assert isinstance(
        AgentRecommendationModel.__table__.c.supporting_signals.type, JSONB
    )
    assert isinstance(AgentRecommendationModel.__table__.c.inputs_payload.type, JSONB)
    assert isinstance(AgentRecommendationModel.__table__.c.outputs_payload.type, JSONB)
    assert isinstance(AgentRecommendationModel.__table__.c.metadata.type, JSONB)
    assert isinstance(AgentRiskAssessmentModel.__table__.c.inputs_payload.type, JSONB)
    assert isinstance(AgentRiskAssessmentModel.__table__.c.outputs_payload.type, JSONB)
    assert isinstance(
        AgentRiskAssessmentModel.__table__.c.supporting_signals.type, JSONB
    )
    assert isinstance(AgentRiskAssessmentModel.__table__.c.metadata.type, JSONB)


def test_agent_intelligence_payload_columns_use_canonical_physical_names() -> None:
    for model in (
        AgentReasoningModel,
        AgentRecommendationModel,
        AgentRiskAssessmentModel,
    ):
        columns = model.__table__.c

        assert "inputs" not in columns
        assert "outputs" not in columns
        assert "inputs_payload" in columns
        assert "outputs_payload" in columns


def test_agent_intelligence_models_include_lineage_and_row_timestamps() -> None:
    for table in (
        AgentReasoningModel.__table__,
        AgentRecommendationModel.__table__,
        AgentRiskAssessmentModel.__table__,
    ):
        columns = table.c

        assert columns.workflow_name.nullable is True
        assert columns.execution_id.nullable is True
        assert columns.runtime_id.nullable is True
        assert columns.node_name.nullable is True
        assert columns.row_created_at.server_default is not None
        assert columns.row_updated_at.server_default is not None


def test_agent_intelligence_models_index_core_query_paths() -> None:
    reasoning_indexes = _index_names(AgentReasoningModel.__table__)
    recommendation_indexes = _index_names(AgentRecommendationModel.__table__)
    risk_indexes = _index_names(AgentRiskAssessmentModel.__table__)

    assert "idx_agent_reasoning_signal_timestamp" in reasoning_indexes
    assert "idx_agent_reasoning_agent_timestamp" in reasoning_indexes
    assert "idx_agent_reasoning_type_timestamp" in reasoning_indexes
    assert "idx_agent_reasoning_symbol_timestamp" in reasoning_indexes
    assert "idx_agent_reasoning_universe_timestamp" in reasoning_indexes
    assert "idx_agent_reasoning_workflow_execution" in reasoning_indexes
    assert "ix_agent_reasoning_agent_signal_id" in reasoning_indexes

    assert "idx_agent_recommendations_signal_timestamp" in recommendation_indexes
    assert "idx_agent_recommendations_agent_timestamp" in recommendation_indexes
    assert "idx_agent_recommendations_type_timestamp" in recommendation_indexes
    assert "idx_agent_recommendations_symbol_timestamp" in recommendation_indexes
    assert "idx_agent_recommendations_universe_timestamp" in recommendation_indexes
    assert "idx_agent_recommendations_workflow_execution" in recommendation_indexes
    assert "idx_agent_recommendations_action_bias" in recommendation_indexes
    assert "ix_agent_recommendations_agent_signal_id" in recommendation_indexes

    assert "idx_agent_risk_assessments_signal_timestamp" in risk_indexes
    assert "idx_agent_risk_assessments_agent_timestamp" in risk_indexes
    assert "idx_agent_risk_assessments_type_timestamp" in risk_indexes
    assert "idx_agent_risk_assessments_risk_type_timestamp" in risk_indexes
    assert "idx_agent_risk_assessments_symbol_timestamp" in risk_indexes
    assert "idx_agent_risk_assessments_universe_timestamp" in risk_indexes
    assert "idx_agent_risk_assessments_workflow_execution" in risk_indexes
    assert "ix_agent_risk_assessments_agent_signal_id" in risk_indexes


def _primary_key_names(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    return {column.name for column in sqlalchemy_table.primary_key}


def _foreign_key_targets(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    return {
        foreign_key.target_fullname for foreign_key in sqlalchemy_table.foreign_keys
    }


def _index_names(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    return {index.name for index in sqlalchemy_table.indexes if index.name is not None}
