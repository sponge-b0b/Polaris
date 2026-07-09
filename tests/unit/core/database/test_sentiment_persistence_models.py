from __future__ import annotations

from typing import cast

from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import JSONB

from core.database.base import Base
from core.database.models.sentiment import SentimentSnapshotModel
from core.database.models.sentiment import SentimentSourceModel


def test_sentiment_models_are_imported_into_base_metadata() -> None:
    assert "sentiment_snapshots" in Base.metadata.tables
    assert "sentiment_sources" in Base.metadata.tables


def test_sentiment_snapshot_model_persists_curated_snapshot_state() -> None:
    columns = SentimentSnapshotModel.__table__.c
    primary_keys = _primary_key_names(SentimentSnapshotModel.__table__)

    assert primary_keys == {"sentiment_snapshot_id"}
    assert columns.timestamp.nullable is False
    assert columns.source.nullable is True
    assert columns.symbol.nullable is True
    assert columns.universe.nullable is True
    assert "sentiment_regime" not in columns
    assert columns.market_regime.nullable is True
    assert columns.market_bias.nullable is True
    assert columns.fear_greed_score.nullable is True
    assert columns.news_sentiment_score.nullable is True
    assert columns.market_sentiment_score.nullable is True
    assert columns.social_sentiment_score.nullable is True
    assert "composite_sentiment_score" not in columns
    assert columns.composite_sentiment.nullable is True
    assert columns.confidence.nullable is True
    assert columns.directional_signal.nullable is True
    assert columns.momentum.nullable is True
    assert columns.stability.nullable is True
    assert columns.divergence.nullable is True
    assert "component_scores" not in columns
    assert "inputs" not in columns
    assert "outputs" not in columns
    assert columns.fusion_components_payload.nullable is False
    assert columns.providers_payload.nullable is False
    assert columns.features_payload.nullable is False
    assert columns.sentiment_payload.nullable is False
    assert columns.raw_payload.nullable is False


def test_sentiment_source_model_persists_source_contributions() -> None:
    columns = SentimentSourceModel.__table__.c
    primary_keys = _primary_key_names(SentimentSourceModel.__table__)

    assert primary_keys == {"sentiment_source_id"}
    assert columns.sentiment_snapshot_id.nullable is True
    assert columns.timestamp.nullable is False
    assert columns.source.nullable is False
    assert columns.source_type.nullable is False
    assert columns.symbol.nullable is True
    assert columns.universe.nullable is True
    assert columns.sentiment_score.nullable is True
    assert columns.confidence.nullable is True
    assert columns.weight.nullable is True
    assert columns.sample_size.nullable is True
    assert columns.source_reference.nullable is True
    assert columns.summary.nullable is True


def test_sentiment_models_use_jsonb_at_persistence_boundaries() -> None:
    assert isinstance(
        SentimentSnapshotModel.__table__.c.fusion_components_payload.type,
        JSONB,
    )
    assert isinstance(SentimentSnapshotModel.__table__.c.providers_payload.type, JSONB)
    assert isinstance(SentimentSnapshotModel.__table__.c.features_payload.type, JSONB)
    assert isinstance(SentimentSnapshotModel.__table__.c.sentiment_payload.type, JSONB)
    assert isinstance(SentimentSnapshotModel.__table__.c.raw_payload.type, JSONB)
    assert isinstance(SentimentSnapshotModel.__table__.c.metadata.type, JSONB)
    assert isinstance(SentimentSourceModel.__table__.c.metadata.type, JSONB)


def test_sentiment_models_include_lineage_and_row_timestamps() -> None:
    for table in (
        SentimentSnapshotModel.__table__,
        SentimentSourceModel.__table__,
    ):
        columns = table.c

        assert columns.workflow_name.nullable is True
        assert columns.execution_id.nullable is True
        assert columns.runtime_id.nullable is True
        assert columns.node_name.nullable is True
        assert columns.row_created_at.server_default is not None
        assert columns.row_updated_at.server_default is not None


def test_sentiment_models_index_core_query_paths() -> None:
    snapshot_indexes = _index_names(SentimentSnapshotModel.__table__)
    source_indexes = _index_names(SentimentSourceModel.__table__)

    assert "idx_sentiment_snapshots_timestamp_source" in snapshot_indexes
    assert "idx_sentiment_snapshots_symbol_timestamp" in snapshot_indexes
    assert "idx_sentiment_snapshots_universe_timestamp" in snapshot_indexes
    assert "idx_sentiment_snapshots_workflow_execution" in snapshot_indexes
    assert "idx_sentiment_sources_timestamp_source" in source_indexes
    assert "idx_sentiment_sources_source_type_timestamp" in source_indexes
    assert "idx_sentiment_sources_snapshot_timestamp" in source_indexes
    assert "idx_sentiment_sources_symbol_timestamp" in source_indexes
    assert "idx_sentiment_sources_universe_timestamp" in source_indexes
    assert "idx_sentiment_sources_workflow_execution" in source_indexes


def _primary_key_names(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    return {column.name for column in sqlalchemy_table.primary_key}


def _index_names(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    return {index.name for index in sqlalchemy_table.indexes if index.name is not None}
