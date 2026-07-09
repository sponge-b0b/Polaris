from __future__ import annotations

from typing import cast

from sqlalchemy import CheckConstraint
from sqlalchemy import Table
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from core.database.base import Base
from core.database.models.news import NewsAnalysisSnapshotModel
from core.database.models.news import NewsArticleModel


def test_news_models_are_imported_into_base_metadata() -> None:
    assert "news_articles" in Base.metadata.tables
    assert "news_analysis_snapshots" in Base.metadata.tables


def test_news_article_model_persists_curated_article_facts() -> None:
    columns = NewsArticleModel.__table__.c
    primary_keys = _primary_key_names(NewsArticleModel.__table__)
    unique_constraints = _unique_constraint_names(NewsArticleModel.__table__)
    check_constraints = _check_constraint_names(NewsArticleModel.__table__)

    assert primary_keys == {"article_id"}
    assert columns.source.nullable is False
    assert columns.external_id.nullable is True
    assert columns.url.nullable is True
    assert columns.title.nullable is False
    assert columns.summary.nullable is True
    assert "published_timestamp" not in columns
    assert columns.published_at.nullable is False
    assert columns.symbols.nullable is False
    assert columns.themes.nullable is False
    assert columns.importance_score.nullable is True
    assert columns.headline_score.nullable is True
    assert columns.relevance_score.nullable is True
    assert columns.sentiment_score.nullable is True
    assert columns.normalized_article_payload.nullable is False
    assert columns.raw_payload.nullable is False
    assert "uq_news_articles_source_external_id" in unique_constraints
    assert "uq_news_articles_source_url" in unique_constraints
    assert "ck_news_articles_source_identity" in check_constraints


def test_news_analysis_snapshot_model_persists_full_analysis_outputs() -> None:
    columns = NewsAnalysisSnapshotModel.__table__.c
    primary_keys = _primary_key_names(NewsAnalysisSnapshotModel.__table__)

    assert primary_keys == {"analysis_snapshot_id"}
    assert columns.timestamp.nullable is False
    assert columns.source.nullable is True
    assert columns.article_ids.nullable is False
    assert columns.symbols.nullable is False
    assert columns.themes.nullable is False
    assert columns.importance_score.nullable is True
    assert columns.sentiment_score.nullable is True
    assert columns.impact_score.nullable is True
    assert columns.confidence.nullable is True
    assert columns.llm_summary.nullable is True
    assert columns.full_llm_response.nullable is True
    assert columns.analysis_model.nullable is True
    assert "inputs" not in columns
    assert "outputs" not in columns
    assert isinstance(columns.inputs_payload.type, JSONB)
    assert isinstance(columns.analysis_payload.type, JSONB)


def test_news_models_use_jsonb_at_persistence_boundaries() -> None:
    assert isinstance(NewsArticleModel.__table__.c.symbols.type, JSONB)
    assert isinstance(NewsArticleModel.__table__.c.themes.type, JSONB)
    assert isinstance(
        NewsArticleModel.__table__.c.normalized_article_payload.type, JSONB
    )
    assert isinstance(NewsArticleModel.__table__.c.raw_payload.type, JSONB)
    assert isinstance(NewsArticleModel.__table__.c.metadata.type, JSONB)
    assert isinstance(NewsAnalysisSnapshotModel.__table__.c.article_ids.type, JSONB)
    assert isinstance(NewsAnalysisSnapshotModel.__table__.c.symbols.type, JSONB)
    assert isinstance(NewsAnalysisSnapshotModel.__table__.c.themes.type, JSONB)
    assert isinstance(NewsAnalysisSnapshotModel.__table__.c.inputs_payload.type, JSONB)
    assert isinstance(
        NewsAnalysisSnapshotModel.__table__.c.analysis_payload.type, JSONB
    )
    assert isinstance(NewsAnalysisSnapshotModel.__table__.c.metadata.type, JSONB)


def test_news_models_include_lineage_and_row_timestamps() -> None:
    for table in (
        NewsArticleModel.__table__,
        NewsAnalysisSnapshotModel.__table__,
    ):
        columns = table.c

        assert columns.workflow_name.nullable is True
        assert columns.execution_id.nullable is True
        assert columns.runtime_id.nullable is True
        assert columns.node_name.nullable is True
        assert columns.row_created_at.server_default is not None
        assert columns.row_updated_at.server_default is not None


def test_news_models_index_core_query_paths() -> None:
    article_indexes = _index_names(NewsArticleModel.__table__)
    analysis_indexes = _index_names(NewsAnalysisSnapshotModel.__table__)

    assert "idx_news_articles_source_published" in article_indexes
    assert "idx_news_articles_symbols" in article_indexes
    assert "idx_news_articles_themes" in article_indexes
    assert "idx_news_articles_workflow_execution" in article_indexes
    assert "idx_news_analysis_snapshots_timestamp_source" in analysis_indexes
    assert "idx_news_analysis_snapshots_article_ids" in analysis_indexes
    assert "idx_news_analysis_snapshots_symbols" in analysis_indexes
    assert "idx_news_analysis_snapshots_themes" in analysis_indexes
    assert "idx_news_analysis_snapshots_workflow_execution" in analysis_indexes


def test_news_jsonb_query_indexes_use_gin() -> None:
    gin_indexes = _gin_index_names(
        NewsArticleModel.__table__,
        NewsAnalysisSnapshotModel.__table__,
    )

    assert gin_indexes == {
        "idx_news_articles_symbols",
        "idx_news_articles_themes",
        "idx_news_analysis_snapshots_article_ids",
        "idx_news_analysis_snapshots_symbols",
        "idx_news_analysis_snapshots_themes",
    }


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


def _gin_index_names(
    *tables: object,
) -> set[str]:
    names: set[str] = set()
    for table in tables:
        sqlalchemy_table = cast(Table, table)
        for index in sqlalchemy_table.indexes:
            if index.dialect_options["postgresql"].get("using") != "gin":
                continue
            if index.name is not None:
                names.add(index.name)
    return names
