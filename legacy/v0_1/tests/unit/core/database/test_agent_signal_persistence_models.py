from __future__ import annotations

from typing import cast

from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import JSONB

from core.database.base import Base
from core.database.models.agent_signals import AgentSignalModel


def test_agent_signal_model_is_imported_into_base_metadata() -> None:
    assert "agent_signals" in Base.metadata.tables


def test_agent_signal_model_persists_signal_lineage_and_scores() -> None:
    columns = AgentSignalModel.__table__.c
    primary_keys = {column.name for column in AgentSignalModel.__table__.primary_key}

    assert primary_keys == {"signal_id"}
    assert columns.agent_name.nullable is False
    assert columns.agent_type.nullable is False
    assert columns.workflow_name.nullable is True
    assert columns.execution_id.nullable is True
    assert columns.runtime_id.nullable is True
    assert columns.node_name.nullable is True
    assert columns.symbol.nullable is True
    assert columns.timestamp.nullable is False
    assert columns.directional_score.nullable is True
    assert columns.confidence.nullable is True
    assert columns.regime.nullable is True
    assert columns.reasoning_text.nullable is True
    assert columns.llm_response.nullable is True
    assert columns.created_at.server_default is not None
    assert columns.updated_at.server_default is not None


def test_agent_signal_model_uses_jsonb_at_persistence_boundaries() -> None:
    columns = AgentSignalModel.__table__.c

    assert isinstance(
        columns.universe.type,
        JSONB,
    )
    assert isinstance(
        columns.signals.type,
        JSONB,
    )
    assert isinstance(
        columns.risks.type,
        JSONB,
    )
    assert isinstance(
        columns.recommendations.type,
        JSONB,
    )
    assert isinstance(
        columns.features.type,
        JSONB,
    )
    assert isinstance(
        columns.metadata.type,
        JSONB,
    )


def test_agent_signal_model_indexes_query_paths() -> None:
    table = cast(Table, AgentSignalModel.__table__)
    index_names = {index.name for index in table.indexes}

    assert "idx_agent_signals_workflow_execution" in index_names
    assert "idx_agent_signals_agent_timestamp" in index_names
    assert "idx_agent_signals_type_timestamp" in index_names
    assert "idx_agent_signals_symbol_timestamp" in index_names
