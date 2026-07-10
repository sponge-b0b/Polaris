from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime
from datetime import timezone

import pytest

from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.news import NewsAnalysisSnapshotRecord
from core.storage.persistence.news import NewsArticleRecord
from core.storage.persistence.news import NewsPersistenceBundle
from core.storage.persistence.news import NewsPersistenceResult
from core.storage.persistence.news import new_news_analysis_snapshot_id
from core.storage.persistence.news import new_news_article_id


def test_news_article_record_is_typed_normalized_and_immutable() -> None:
    record = NewsArticleRecord(
        article_id="article-1",
        source=" reuters ",
        external_id=" article-123 ",
        title=" Fed signals patience ",
        summary="Policy makers emphasized incoming data.",
        url=" https://example.com/fed-signals-patience ",
        published_timestamp=_timestamp(),
        symbols=(" spy ", "qqq"),
        themes=(" macro ", "fed_policy"),
        importance_score=0.8,
        headline_score=0.7,
        relevance_score=0.9,
        sentiment_score=0.25,
        lineage=_lineage(),
        normalized_article_payload={"id": "article-1"},
        raw_payload={"vendor_id": "article-123"},
        metadata={"publisher": "Reuters"},
    )

    assert record.source == "reuters"
    assert record.external_id == "article-123"
    assert record.title == "Fed signals patience"
    assert record.url == "https://example.com/fed-signals-patience"
    assert record.symbols == ("SPY", "QQQ")
    assert record.themes == ("macro", "fed_policy")
    assert record.importance_score == 0.8
    assert record.headline_score == 0.7
    assert record.relevance_score == 0.9
    assert record.sentiment_score == 0.25
    assert record.normalized_article_payload == {"id": "article-1"}
    assert record.raw_payload == {"vendor_id": "article-123"}
    assert record.lineage.execution_id == "exec-1"

    with pytest.raises(FrozenInstanceError):
        record.title = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"article_id": " "}, "article_id"),
        ({"source": ""}, "source"),
        ({"title": " "}, "title"),
        ({"external_id": None, "url": " "}, "external_id or url"),
        ({"symbols": ("SPY", "")}, "symbol"),
        ({"themes": ("macro", " ")}, "theme"),
        ({"importance_score": 1.1}, "importance_score"),
        ({"headline_score": 1.1}, "headline_score"),
        ({"relevance_score": -0.1}, "relevance_score"),
        ({"sentiment_score": -1.1}, "sentiment_score"),
    ],
)
def test_news_article_record_validates_required_identifiers_and_scores(
    kwargs: dict[str, object],
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "article_id": "article-1",
        "source": "reuters",
        "external_id": "article-123",
        "title": "Fed signals patience",
        "published_timestamp": _timestamp(),
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        NewsArticleRecord(**values)  # type: ignore[arg-type]


def test_news_analysis_snapshot_preserves_full_llm_response_without_truncation() -> (
    None
):
    full_response = "\n".join(
        f"Paragraph {index}: detailed analysis remains intact." for index in range(200)
    )
    record = NewsAnalysisSnapshotRecord(
        analysis_snapshot_id="news-analysis-1",
        timestamp=_timestamp(),
        source=" morning_report ",
        article_ids=(" article-1 ", "article-2"),
        symbols=(" spy ", "qqq"),
        themes=(" macro ", "rates"),
        importance_score=0.85,
        sentiment_score=-0.2,
        impact_score=0.4,
        confidence=0.9,
        llm_summary="Markets are focused on policy path.",
        full_llm_response=full_response,
        analysis_model=" gpt-test ",
        inputs={"article_count": 2},
        outputs={"summary": "Policy uncertainty dominates."},
        metadata={"prompt_version": "v1"},
        lineage=_lineage(),
    )

    assert record.source == "morning_report"
    assert record.article_ids == ("article-1", "article-2")
    assert record.symbols == ("SPY", "QQQ")
    assert record.themes == ("macro", "rates")
    assert record.analysis_model == "gpt-test"
    assert record.llm_summary == "Markets are focused on policy path."
    assert record.full_llm_response == full_response
    assert len(record.full_llm_response) == len(full_response)
    assert record.inputs == {"article_count": 2}
    assert record.outputs == {"summary": "Policy uncertainty dominates."}


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"analysis_snapshot_id": " "}, "analysis_snapshot_id"),
        ({"article_ids": ("article-1", "")}, "article_id"),
        ({"symbols": ("SPY", " ")}, "symbol"),
        ({"themes": ("macro", " ")}, "theme"),
        ({"importance_score": -0.1}, "importance_score"),
        ({"sentiment_score": 1.1}, "sentiment_score"),
        ({"impact_score": -1.1}, "impact_score"),
        ({"confidence": 1.1}, "confidence"),
    ],
)
def test_news_analysis_snapshot_validates_identifiers_and_scores(
    kwargs: dict[str, object],
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "analysis_snapshot_id": "news-analysis-1",
        "timestamp": _timestamp(),
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        NewsAnalysisSnapshotRecord(**values)  # type: ignore[arg-type]


def test_news_bundle_groups_atomic_persistence_payload() -> None:
    bundle = NewsPersistenceBundle(
        articles=(_article(),),
        analysis_snapshots=(_analysis_snapshot(),),
    )

    assert len(bundle.articles) == 1
    assert len(bundle.analysis_snapshots) == 1


def test_news_persistence_result_validates_state() -> None:
    success = NewsPersistenceResult.succeeded(
        primary_record_id="news-record-1",
        records_persisted=2,
    )
    failure = NewsPersistenceResult.failed(
        "database unavailable",
    )

    assert success.success is True
    assert success.records_persisted == 2
    assert failure.success is False
    assert failure.error == "database unavailable"

    with pytest.raises(ValueError, match="records_persisted"):
        NewsPersistenceResult(
            success=True,
            primary_record_id="news-record-1",
            records_persisted=-1,
        )

    with pytest.raises(ValueError, match="primary_record_id"):
        NewsPersistenceResult(
            success=True,
        )

    with pytest.raises(ValueError, match="error"):
        NewsPersistenceResult(
            success=False,
        )


def test_news_id_helpers_are_stable_and_lineage_aware() -> None:
    first_article_id = new_news_article_id(
        source="reuters",
        external_id="article-123",
        published_timestamp=_timestamp(),
    )
    second_article_id = new_news_article_id(
        source="reuters",
        external_id="article-123",
        published_timestamp=_timestamp(),
    )
    url_article_id = new_news_article_id(
        source="reuters",
        url="https://example.com/article",
        published_timestamp=_timestamp(),
    )
    analysis_id = new_news_analysis_snapshot_id(
        timestamp=_timestamp(),
        execution_id="exec-1",
        article_id="article-1",
        symbol="spy",
        snapshot_key="open",
    )
    random_analysis_id = new_news_analysis_snapshot_id(
        timestamp=_timestamp(),
    )

    assert first_article_id == second_article_id
    assert (
        first_article_id == "news_article:reuters:2026-05-31T14:00:00+00:00:article-123"
    )
    assert url_article_id == (
        "news_article:reuters:2026-05-31T14:00:00+00:00:https://example.com/article"
    )
    assert analysis_id == (
        "news_analysis_snapshot:exec-1:2026-05-31T14:00:00+00:00:article-1:SPY:open"
    )
    assert random_analysis_id.startswith("news_analysis_snapshot:")

    with pytest.raises(ValueError, match="external_id or url"):
        new_news_article_id(
            source="reuters",
            published_timestamp=_timestamp(),
        )


def test_news_article_id_helpers_dedupe_by_source_external_id_or_url() -> None:
    external_id_article_id = new_news_article_id(
        source=" reuters ",
        external_id=" article-123 ",
        url="https://example.com/article-a",
        published_timestamp=_timestamp(),
    )
    repeat_external_id_article_id = new_news_article_id(
        source="reuters",
        external_id="article-123",
        url="https://example.com/article-b",
        published_timestamp=_timestamp(),
    )
    alternate_source_article_id = new_news_article_id(
        source="ap",
        external_id="article-123",
        published_timestamp=_timestamp(),
    )
    url_article_id = new_news_article_id(
        source=" reuters ",
        url=" https://example.com/article-a ",
        published_timestamp=_timestamp(),
    )
    repeat_url_article_id = new_news_article_id(
        source="reuters",
        url="https://example.com/article-a",
        published_timestamp=_timestamp(),
    )

    assert external_id_article_id == repeat_external_id_article_id
    assert external_id_article_id != alternate_source_article_id
    assert url_article_id == repeat_url_article_id
    assert external_id_article_id.endswith(":article-123")
    assert url_article_id.endswith(":https://example.com/article-a")


def _article() -> NewsArticleRecord:
    return NewsArticleRecord(
        article_id="article-1",
        source="reuters",
        external_id="article-123",
        title="Fed signals patience",
        published_timestamp=_timestamp(),
        url="https://example.com/fed-signals-patience",
        summary="Policy makers emphasized incoming data.",
        symbols=("SPY",),
        themes=("macro",),
        importance_score=0.8,
        sentiment_score=0.25,
    )


def _analysis_snapshot() -> NewsAnalysisSnapshotRecord:
    return NewsAnalysisSnapshotRecord(
        analysis_snapshot_id="news-analysis-1",
        timestamp=_timestamp(),
        source="morning_report",
        article_ids=("article-1",),
        symbols=("SPY",),
        themes=("macro",),
        importance_score=0.85,
        sentiment_score=-0.2,
        impact_score=0.4,
        confidence=0.9,
        llm_summary="Markets are focused on policy path.",
        full_llm_response="Full response is preserved.",
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
