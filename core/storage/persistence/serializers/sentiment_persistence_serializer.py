from __future__ import annotations

from typing import Any, cast

from core.database.models.sentiment import SentimentSnapshotModel, SentimentSourceModel
from core.storage.persistence.lineage import JsonObject, PersistenceLineage
from core.storage.persistence.sentiment import (
    SentimentSnapshotRecord,
    SentimentSourceRecord,
)


class SentimentPersistenceSerializer:
    """
    Serializer between typed sentiment persistence records and SQLAlchemy models.

    Sentiment provider/client payloads should be normalized into typed records
    before this persistence boundary. JSON dictionaries are introduced here only
    for PostgreSQL JSONB columns used for component scores, curated
    inputs/outputs, and metadata required by audit, replay, reporting, and
    future curated RAG source projections.
    """

    @staticmethod
    def snapshot_values(
        record: SentimentSnapshotRecord,
    ) -> dict[str, Any]:
        return {
            "sentiment_snapshot_id": record.sentiment_snapshot_id,
            "timestamp": record.timestamp,
            "source": record.source,
            "symbol": record.symbol,
            "universe": record.universe,
            "market_regime": record.market_regime,
            "market_bias": record.market_bias,
            "fear_greed_score": record.fear_greed_score,
            "news_sentiment_score": record.news_sentiment_score,
            "market_sentiment_score": record.market_sentiment_score,
            "social_sentiment_score": record.social_sentiment_score,
            "composite_sentiment": record.composite_sentiment,
            "confidence": record.confidence,
            "directional_signal": record.directional_signal,
            "momentum": record.momentum,
            "stability": record.stability,
            "divergence": record.divergence,
            "fusion_components": dict(record.fusion_components),
            "providers_payload": dict(record.providers_payload),
            "features_payload": dict(record.features_payload),
            "sentiment_payload": dict(record.sentiment_payload),
            "raw_payload": dict(record.raw_payload),
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def source_values(
        record: SentimentSourceRecord,
    ) -> dict[str, Any]:
        return {
            "sentiment_source_id": record.sentiment_source_id,
            "sentiment_snapshot_id": record.sentiment_snapshot_id,
            "timestamp": record.timestamp,
            "source": record.source,
            "source_type": record.source_type,
            "symbol": record.symbol,
            "universe": record.universe,
            "sentiment_score": record.sentiment_score,
            "confidence": record.confidence,
            "weight": record.weight,
            "sample_size": record.sample_size,
            "source_reference": record.source_reference,
            "summary": record.summary,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def snapshot_from_model(
        model: SentimentSnapshotModel,
    ) -> SentimentSnapshotRecord:
        return SentimentSnapshotRecord(
            sentiment_snapshot_id=model.sentiment_snapshot_id,
            timestamp=model.timestamp,
            source=model.source,
            symbol=model.symbol,
            universe=model.universe,
            market_regime=model.market_regime,
            market_bias=model.market_bias,
            fear_greed_score=model.fear_greed_score,
            news_sentiment_score=model.news_sentiment_score,
            market_sentiment_score=model.market_sentiment_score,
            social_sentiment_score=model.social_sentiment_score,
            composite_sentiment=model.composite_sentiment,
            confidence=model.confidence,
            directional_signal=model.directional_signal,
            momentum=model.momentum,
            stability=model.stability,
            divergence=model.divergence,
            fusion_components=cast(JsonObject, model.fusion_components),
            providers_payload=cast(JsonObject, model.providers_payload),
            features_payload=cast(JsonObject, model.features_payload),
            sentiment_payload=cast(JsonObject, model.sentiment_payload),
            raw_payload=cast(JsonObject, model.raw_payload),
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def source_from_model(
        model: SentimentSourceModel,
    ) -> SentimentSourceRecord:
        return SentimentSourceRecord(
            sentiment_source_id=model.sentiment_source_id,
            sentiment_snapshot_id=model.sentiment_snapshot_id,
            timestamp=model.timestamp,
            source=model.source,
            source_type=model.source_type,
            symbol=model.symbol,
            universe=model.universe,
            sentiment_score=model.sentiment_score,
            confidence=model.confidence,
            weight=model.weight,
            sample_size=model.sample_size,
            source_reference=model.source_reference,
            summary=model.summary,
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )


def _lineage_from_model(
    model: SentimentSnapshotModel | SentimentSourceModel,
) -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name=model.workflow_name,
        execution_id=model.execution_id,
        runtime_id=model.runtime_id,
        node_name=model.node_name,
    )
