from __future__ import annotations

from datetime import datetime
from datetime import timezone

from core.database.models.news import NewsAnalysisSnapshotModel
from core.database.models.news import NewsArticleModel
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.news import NewsAnalysisSnapshotRecord
from core.storage.persistence.news import NewsArticleRecord
from core.storage.persistence.serializers.news_persistence_serializer import (
    NewsPersistenceSerializer,
)


def test_news_serializer_flattens_article_record() -> None:
    record = _article()

    values = NewsPersistenceSerializer.article_values(record)

    assert values["article_id"] == "article-1"
    assert values["source"] == "reuters"
    assert values["external_id"] == "article-123"
    assert values["url"] == "https://example.com/fed-signals-patience"
    assert values["symbols"] == ["SPY", "QQQ"]
    assert values["themes"] == ["macro", "fed_policy"]
    assert values["headline_score"] == 0.7
    assert values["relevance_score"] == 0.9
    assert values["normalized_article_payload"] == {"id": "article-1"}
    assert values["raw_payload"] == {"vendor_id": "article-123"}
    assert values["workflow_name"] == "morning_report"
    assert values["execution_id"] == "exec-1"
    assert values["metadata_payload"] == {"publisher": "Reuters"}


def test_news_serializer_round_trips_article_record() -> None:
    model = NewsArticleModel(**NewsPersistenceSerializer.article_values(_article()))

    record = NewsPersistenceSerializer.article_from_model(
        model,
    )

    assert record.article_id == "article-1"
    assert record.source == "reuters"
    assert record.external_id == "article-123"
    assert record.symbols == ("SPY", "QQQ")
    assert record.themes == ("macro", "fed_policy")
    assert record.headline_score == 0.7
    assert record.relevance_score == 0.9
    assert record.normalized_article_payload == {"id": "article-1"}
    assert record.raw_payload == {"vendor_id": "article-123"}
    assert record.lineage.node_name == "news_node"
    assert record.metadata == {"publisher": "Reuters"}


def test_news_serializer_preserves_full_llm_response_without_truncation() -> None:
    snapshot = _analysis_snapshot()
    model = NewsAnalysisSnapshotModel(
        **NewsPersistenceSerializer.analysis_snapshot_values(snapshot)
    )

    record = NewsPersistenceSerializer.analysis_snapshot_from_model(
        model,
    )

    assert record.analysis_snapshot_id == "news-analysis-1"
    assert record.article_ids == ("article-1", "article-2")
    assert record.symbols == ("SPY", "QQQ")
    assert record.themes == ("macro", "rates")
    assert record.inputs == {"article_count": 2}
    assert record.outputs == {"summary": "Policy uncertainty dominates."}
    assert record.full_llm_response == snapshot.full_llm_response
    assert len(record.full_llm_response or "") == len(snapshot.full_llm_response or "")
    assert record.metadata == {"prompt_version": "v1"}


def _article() -> NewsArticleRecord:
    return NewsArticleRecord(
        article_id="article-1",
        source="reuters",
        external_id="article-123",
        title="Fed signals patience",
        published_timestamp=_timestamp(),
        url="https://example.com/fed-signals-patience",
        summary="Policy makers emphasized incoming data.",
        symbols=("SPY", "QQQ"),
        themes=("macro", "fed_policy"),
        importance_score=0.8,
        headline_score=0.7,
        relevance_score=0.9,
        sentiment_score=0.25,
        lineage=_lineage(),
        normalized_article_payload={"id": "article-1"},
        raw_payload={"vendor_id": "article-123"},
        metadata={"publisher": "Reuters"},
    )


def _analysis_snapshot() -> NewsAnalysisSnapshotRecord:
    full_response = "\n".join(
        f"Paragraph {index}: full response content is retained." for index in range(120)
    )
    return NewsAnalysisSnapshotRecord(
        analysis_snapshot_id="news-analysis-1",
        timestamp=_timestamp(),
        source="morning_report",
        article_ids=("article-1", "article-2"),
        symbols=("SPY", "QQQ"),
        themes=("macro", "rates"),
        importance_score=0.85,
        sentiment_score=-0.2,
        impact_score=0.4,
        confidence=0.9,
        llm_summary="Markets are focused on policy path.",
        full_llm_response=full_response,
        analysis_model="gpt-test",
        inputs={"article_count": 2},
        outputs={"summary": "Policy uncertainty dominates."},
        metadata={"prompt_version": "v1"},
        lineage=_lineage(),
    )


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="news_node",
    )


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=timezone.utc)
