from __future__ import annotations

from datetime import UTC, datetime

from core.database.models.sentiment import SentimentSnapshotModel, SentimentSourceModel
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.sentiment import (
    SentimentSnapshotRecord,
    SentimentSourceRecord,
)
from core.storage.persistence.serializers.sentiment_persistence_serializer import (
    SentimentPersistenceSerializer,
)


def test_sentiment_serializer_flattens_snapshot_record() -> None:
    record = _snapshot()

    values = SentimentPersistenceSerializer.snapshot_values(record)

    assert values["sentiment_snapshot_id"] == "sentiment-snapshot-1"
    assert values["source"] == "morning_report"
    assert values["symbol"] == "SPY"
    assert values["universe"] == "us_equities"
    assert values["market_regime"] == "risk_on"
    assert values["fear_greed_score"] == 0.72
    assert values["fusion_components"] == {"news": 0.4, "market": 0.6}
    assert values["providers_payload"] == {"article_count": 25}
    assert values["sentiment_payload"] == {"summary": "Constructive sentiment."}
    assert values["workflow_name"] == "morning_report"
    assert values["execution_id"] == "exec-1"
    assert values["metadata_payload"] == {"prompt_version": "v1"}


def test_sentiment_serializer_round_trips_snapshot_record() -> None:
    model = SentimentSnapshotModel(
        **SentimentPersistenceSerializer.snapshot_values(_snapshot())
    )

    record = SentimentPersistenceSerializer.snapshot_from_model(
        model,
    )

    assert record.sentiment_snapshot_id == "sentiment-snapshot-1"
    assert record.source == "morning_report"
    assert record.symbol == "SPY"
    assert record.universe == "us_equities"
    assert record.market_regime == "risk_on"
    assert record.fusion_components == {"news": 0.4, "market": 0.6}
    assert record.providers_payload == {"article_count": 25}
    assert record.sentiment_payload == {"summary": "Constructive sentiment."}
    assert record.lineage.node_name == "sentiment_node"
    assert record.metadata == {"prompt_version": "v1"}


def test_sentiment_serializer_flattens_source_record() -> None:
    record = _source()

    values = SentimentPersistenceSerializer.source_values(record)

    assert values["sentiment_source_id"] == "sentiment-source-1"
    assert values["sentiment_snapshot_id"] == "sentiment-snapshot-1"
    assert values["source"] == "reuters"
    assert values["source_type"] == "news"
    assert values["symbol"] == "SPY"
    assert values["universe"] == "us_equities"
    assert values["sentiment_score"] == 0.35
    assert values["confidence"] == 0.8
    assert values["weight"] == 0.5
    assert values["sample_size"] == 14
    assert values["source_reference"] == "article-group-1"
    assert values["summary"] == "News tone improved."
    assert values["metadata_payload"] == {"curated": True}


def test_sentiment_serializer_round_trips_source_record() -> None:
    model = SentimentSourceModel(
        **SentimentPersistenceSerializer.source_values(_source())
    )

    record = SentimentPersistenceSerializer.source_from_model(
        model,
    )

    assert record.sentiment_source_id == "sentiment-source-1"
    assert record.sentiment_snapshot_id == "sentiment-snapshot-1"
    assert record.source == "reuters"
    assert record.source_type == "news"
    assert record.symbol == "SPY"
    assert record.universe == "us_equities"
    assert record.sentiment_score == 0.35
    assert record.source_reference == "article-group-1"
    assert record.summary == "News tone improved."
    assert record.lineage.workflow_name == "morning_report"
    assert record.metadata == {"curated": True}


def _snapshot() -> SentimentSnapshotRecord:
    return SentimentSnapshotRecord(
        sentiment_snapshot_id="sentiment-snapshot-1",
        timestamp=_timestamp(),
        source="morning_report",
        symbol="spy",
        universe="us_equities",
        market_regime="risk_on",
        fear_greed_score=0.72,
        news_sentiment_score=0.4,
        market_sentiment_score=0.6,
        social_sentiment_score=0.1,
        composite_sentiment=0.5,
        confidence=0.86,
        market_bias="constructive",
        directional_signal=0.44,
        momentum=0.31,
        stability=0.78,
        divergence=0.12,
        fusion_components={"news": 0.4, "market": 0.6},
        providers_payload={"article_count": 25},
        features_payload={"breadth": 0.61},
        sentiment_payload={"summary": "Constructive sentiment."},
        raw_payload={"provider": "normalized"},
        metadata={"prompt_version": "v1"},
        lineage=_lineage(),
    )


def _source() -> SentimentSourceRecord:
    return SentimentSourceRecord(
        sentiment_source_id="sentiment-source-1",
        sentiment_snapshot_id="sentiment-snapshot-1",
        timestamp=_timestamp(),
        source="reuters",
        source_type="news",
        symbol="spy",
        universe="us_equities",
        sentiment_score=0.35,
        confidence=0.8,
        weight=0.5,
        sample_size=14,
        source_reference="article-group-1",
        summary="News tone improved.",
        metadata={"curated": True},
        lineage=_lineage(),
    )


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="sentiment_node",
    )


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=UTC)
