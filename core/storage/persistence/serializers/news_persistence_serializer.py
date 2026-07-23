from __future__ import annotations

from typing import Any, cast

from core.database.models.news import NewsAnalysisSnapshotModel, NewsArticleModel
from core.storage.persistence.lineage import JsonObject, PersistenceLineage
from core.storage.persistence.news import NewsAnalysisSnapshotRecord, NewsArticleRecord


class NewsPersistenceSerializer:
    """
    Serializer between typed news persistence records and SQLAlchemy models.

    News client/provider payloads should be normalized into typed records before
    this persistence boundary. JSON dictionaries/lists are introduced here only
    for PostgreSQL JSONB columns used for symbols, themes, article ids, curated
    inputs/outputs, and metadata needed by replay, audit, and future RAG source
    curation.
    """

    @staticmethod
    def article_values(
        record: NewsArticleRecord,
    ) -> dict[str, Any]:
        return {
            "article_id": record.article_id,
            "source": record.source,
            "external_id": record.external_id,
            "url": record.url,
            "title": record.title,
            "summary": record.summary,
            "published_timestamp": record.published_timestamp,
            "symbols": list(record.symbols),
            "themes": list(record.themes),
            "importance_score": record.importance_score,
            "headline_score": record.headline_score,
            "relevance_score": record.relevance_score,
            "sentiment_score": record.sentiment_score,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "normalized_article_payload": dict(record.normalized_article_payload),
            "raw_payload": dict(record.raw_payload),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def analysis_snapshot_values(
        record: NewsAnalysisSnapshotRecord,
    ) -> dict[str, Any]:
        return {
            "analysis_snapshot_id": record.analysis_snapshot_id,
            "timestamp": record.timestamp,
            "source": record.source,
            "article_ids": list(record.article_ids),
            "symbols": list(record.symbols),
            "themes": list(record.themes),
            "importance_score": record.importance_score,
            "sentiment_score": record.sentiment_score,
            "impact_score": record.impact_score,
            "confidence": record.confidence,
            "llm_summary": record.llm_summary,
            "full_llm_response": record.full_llm_response,
            "analysis_model": record.analysis_model,
            "inputs": dict(record.inputs),
            "outputs": dict(record.outputs),
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def article_from_model(
        model: NewsArticleModel,
    ) -> NewsArticleRecord:
        return NewsArticleRecord(
            article_id=model.article_id,
            source=model.source,
            external_id=model.external_id,
            url=model.url,
            title=model.title,
            summary=model.summary,
            published_timestamp=model.published_timestamp,
            symbols=tuple(model.symbols),
            themes=tuple(model.themes),
            importance_score=model.importance_score,
            headline_score=model.headline_score,
            relevance_score=model.relevance_score,
            sentiment_score=model.sentiment_score,
            lineage=_lineage_from_model(model),
            normalized_article_payload=cast(
                JsonObject, model.normalized_article_payload
            ),
            raw_payload=cast(JsonObject, model.raw_payload),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def analysis_snapshot_from_model(
        model: NewsAnalysisSnapshotModel,
    ) -> NewsAnalysisSnapshotRecord:
        return NewsAnalysisSnapshotRecord(
            analysis_snapshot_id=model.analysis_snapshot_id,
            timestamp=model.timestamp,
            source=model.source,
            article_ids=tuple(model.article_ids),
            symbols=tuple(model.symbols),
            themes=tuple(model.themes),
            importance_score=model.importance_score,
            sentiment_score=model.sentiment_score,
            impact_score=model.impact_score,
            confidence=model.confidence,
            llm_summary=model.llm_summary,
            full_llm_response=model.full_llm_response,
            analysis_model=model.analysis_model,
            inputs=cast(JsonObject, model.inputs),
            outputs=cast(JsonObject, model.outputs),
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )


def _lineage_from_model(
    model: NewsArticleModel | NewsAnalysisSnapshotModel,
) -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name=model.workflow_name,
        execution_id=model.execution_id,
        runtime_id=model.runtime_id,
        node_name=model.node_name,
    )
