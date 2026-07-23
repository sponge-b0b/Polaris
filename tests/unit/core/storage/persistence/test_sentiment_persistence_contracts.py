from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.sentiment import (
    SentimentPersistenceBundle,
    SentimentPersistenceResult,
    SentimentSnapshotRecord,
    SentimentSourceRecord,
    new_sentiment_snapshot_id,
    new_sentiment_source_id,
)


def test_sentiment_snapshot_record_is_typed_normalized_and_immutable() -> None:
    record = SentimentSnapshotRecord(
        sentiment_snapshot_id="snapshot-1",
        timestamp=_timestamp(),
        source=" sentiment-service ",
        symbol=" spy ",
        universe=" sp500 ",
        market_regime=" risk_on ",
        fear_greed_score=0.72,
        news_sentiment_score=0.25,
        market_sentiment_score=0.4,
        social_sentiment_score=-0.1,
        composite_sentiment=0.32,
        confidence=0.84,
        fusion_components={"news": 0.25, "market": 0.4},
        providers_payload={"articles": 42},
        sentiment_payload={"summary": "constructive sentiment"},
        metadata={"model": "unit-test"},
        lineage=_lineage(),
    )

    assert record.source == "sentiment-service"
    assert record.symbol == "SPY"
    assert record.universe == "sp500"
    assert record.market_regime == "risk_on"
    assert record.fear_greed_score == 0.72
    assert record.news_sentiment_score == 0.25
    assert record.market_sentiment_score == 0.4
    assert record.social_sentiment_score == -0.1
    assert record.composite_sentiment == 0.32
    assert record.confidence == 0.84
    assert record.fusion_components == {"news": 0.25, "market": 0.4}
    assert record.lineage.execution_id == "exec-1"

    with pytest.raises(FrozenInstanceError):
        record.symbol = "QQQ"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"sentiment_snapshot_id": " "}, "sentiment_snapshot_id"),
        ({"fear_greed_score": 1.1}, "fear_greed_score"),
        ({"news_sentiment_score": -1.1}, "news_sentiment_score"),
        ({"market_sentiment_score": 1.1}, "market_sentiment_score"),
        ({"social_sentiment_score": -1.1}, "social_sentiment_score"),
        ({"composite_sentiment": 1.1}, "composite_sentiment"),
        ({"confidence": -0.1}, "confidence"),
    ],
)
def test_sentiment_snapshot_validates_identifiers_and_scores(
    kwargs: dict[str, object],
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "sentiment_snapshot_id": "snapshot-1",
        "timestamp": _timestamp(),
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        SentimentSnapshotRecord(**values)  # type: ignore[arg-type]


def test_sentiment_snapshot_cleans_blank_optional_identifiers_to_none() -> None:
    record = SentimentSnapshotRecord(
        sentiment_snapshot_id="snapshot-1",
        timestamp=_timestamp(),
        source=" ",
        symbol=" ",
        universe=" ",
        market_regime=" ",
    )

    assert record.source is None
    assert record.symbol is None
    assert record.universe is None
    assert record.market_regime is None


def test_sentiment_source_record_is_typed_normalized_and_immutable() -> None:
    record = SentimentSourceRecord(
        sentiment_source_id="source-1",
        timestamp=_timestamp(),
        source=" cnn-fear-greed ",
        source_type=" index ",
        sentiment_snapshot_id=" snapshot-1 ",
        symbol=" qqq ",
        universe=" nasdaq100 ",
        sentiment_score=-0.2,
        confidence=0.8,
        weight=0.35,
        sample_size=100,
        source_reference=" fear-greed-2026-05-31 ",
        summary=" Source sentiment contribution. ",
        metadata={"provider": "cnn"},
        lineage=_lineage(),
    )

    assert record.source == "cnn-fear-greed"
    assert record.source_type == "index"
    assert record.sentiment_snapshot_id == "snapshot-1"
    assert record.symbol == "QQQ"
    assert record.universe == "nasdaq100"
    assert record.sentiment_score == -0.2
    assert record.confidence == 0.8
    assert record.weight == 0.35
    assert record.sample_size == 100
    assert record.source_reference == "fear-greed-2026-05-31"
    assert record.summary == "Source sentiment contribution."

    with pytest.raises(FrozenInstanceError):
        record.source = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"sentiment_source_id": " "}, "sentiment_source_id"),
        ({"source": " "}, "source"),
        ({"source_type": " "}, "source_type"),
        ({"sentiment_score": -1.1}, "sentiment_score"),
        ({"confidence": 1.1}, "confidence"),
        ({"weight": -0.1}, "weight"),
        ({"sample_size": -1}, "sample_size"),
    ],
)
def test_sentiment_source_validates_identifiers_and_scores(
    kwargs: dict[str, object],
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "sentiment_source_id": "source-1",
        "timestamp": _timestamp(),
        "source": "cnn-fear-greed",
        "source_type": "index",
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        SentimentSourceRecord(**values)  # type: ignore[arg-type]


def test_sentiment_source_cleans_blank_optional_identifiers_to_none() -> None:
    record = SentimentSourceRecord(
        sentiment_source_id="source-1",
        timestamp=_timestamp(),
        source="cnn-fear-greed",
        source_type="index",
        sentiment_snapshot_id=" ",
        symbol=" ",
        universe=" ",
        source_reference=" ",
        summary=" ",
    )

    assert record.sentiment_snapshot_id is None
    assert record.symbol is None
    assert record.universe is None
    assert record.source_reference is None
    assert record.summary is None


def test_sentiment_bundle_groups_atomic_persistence_payload() -> None:
    bundle = SentimentPersistenceBundle(
        snapshots=(_snapshot(),),
        sources=(_source(),),
    )

    assert len(bundle.snapshots) == 1
    assert len(bundle.sources) == 1


def test_sentiment_persistence_result_validates_state() -> None:
    success = SentimentPersistenceResult.succeeded(
        primary_record_id="sentiment-record-1",
        records_persisted=2,
    )
    failure = SentimentPersistenceResult.failed(
        "database unavailable",
    )

    assert success.success is True
    assert success.records_persisted == 2
    assert failure.success is False
    assert failure.error == "database unavailable"

    with pytest.raises(ValueError, match="records_persisted"):
        SentimentPersistenceResult(
            success=True,
            primary_record_id="sentiment-record-1",
            records_persisted=-1,
        )

    with pytest.raises(ValueError, match="primary_record_id"):
        SentimentPersistenceResult(
            success=True,
        )

    with pytest.raises(ValueError, match="error"):
        SentimentPersistenceResult(
            success=False,
        )


def test_sentiment_id_helpers_are_stable_and_lineage_aware() -> None:
    snapshot_id = new_sentiment_snapshot_id(
        timestamp=_timestamp(),
        execution_id="exec-1",
        symbol="spy",
        universe="sp500",
        snapshot_key="open",
    )
    repeat_snapshot_id = new_sentiment_snapshot_id(
        timestamp=_timestamp(),
        execution_id="exec-1",
        symbol="spy",
        universe="sp500",
        snapshot_key="open",
    )
    random_snapshot_id = new_sentiment_snapshot_id(
        timestamp=_timestamp(),
    )
    source_id = new_sentiment_source_id(
        source="cnn-fear-greed",
        source_type="index",
        timestamp=_timestamp(),
        symbol="spy",
        universe="sp500",
        source_reference="fear-greed-2026-05-31",
    )
    repeat_source_id = new_sentiment_source_id(
        source="cnn-fear-greed",
        source_type="index",
        timestamp=_timestamp(),
        symbol="spy",
        universe="sp500",
        source_reference="fear-greed-2026-05-31",
    )

    assert snapshot_id == repeat_snapshot_id
    assert snapshot_id == (
        "sentiment_snapshot:exec-1:2026-05-31T14:00:00+00:00:SPY:sp500:open"
    )
    assert random_snapshot_id.startswith("sentiment_snapshot:")
    assert source_id == repeat_source_id
    assert source_id == (
        "sentiment_source:2026-05-31T14:00:00+00:00:"
        "cnn-fear-greed:index:SPY:sp500:fear-greed-2026-05-31"
    )

    with pytest.raises(ValueError, match="source"):
        new_sentiment_source_id(
            source=" ",
            source_type="index",
            timestamp=_timestamp(),
        )


def test_sentiment_snapshot_id_helper_is_stable_by_source_timestamp_and_context() -> (
    None
):
    snapshot_id = new_sentiment_snapshot_id(
        timestamp=_timestamp(),
        execution_id=" exec-1 ",
        source=" sentiment-service ",
        symbol=" spy ",
        universe=" sp500 ",
        snapshot_key=" open ",
    )
    repeat_snapshot_id = new_sentiment_snapshot_id(
        timestamp=_timestamp(),
        execution_id="exec-1",
        source="sentiment-service",
        symbol="SPY",
        universe="sp500",
        snapshot_key="open",
    )
    alternate_source_snapshot_id = new_sentiment_snapshot_id(
        timestamp=_timestamp(),
        execution_id="exec-1",
        source="news-sentiment-service",
        symbol="SPY",
        universe="sp500",
        snapshot_key="open",
    )

    assert snapshot_id == repeat_snapshot_id
    assert snapshot_id != alternate_source_snapshot_id
    assert snapshot_id == (
        "sentiment_snapshot:exec-1:2026-05-31T14:00:00+00:00:"
        "sentiment-service:SPY:sp500:open"
    )


def _snapshot() -> SentimentSnapshotRecord:
    return SentimentSnapshotRecord(
        sentiment_snapshot_id="snapshot-1",
        timestamp=_timestamp(),
        source="sentiment-service",
        symbol="SPY",
        universe="sp500",
        market_regime="risk_on",
        fear_greed_score=0.72,
        news_sentiment_score=0.25,
        market_sentiment_score=0.4,
        social_sentiment_score=-0.1,
        composite_sentiment=0.32,
        confidence=0.84,
        fusion_components={"news": 0.25, "market": 0.4},
        providers_payload={"articles": 42},
        sentiment_payload={"summary": "constructive sentiment"},
        metadata={"model": "unit-test"},
        lineage=_lineage(),
    )


def _source() -> SentimentSourceRecord:
    return SentimentSourceRecord(
        sentiment_source_id="source-1",
        timestamp=_timestamp(),
        source="cnn-fear-greed",
        source_type="index",
        sentiment_snapshot_id="snapshot-1",
        symbol="SPY",
        universe="sp500",
        sentiment_score=-0.2,
        confidence=0.8,
        weight=0.35,
        sample_size=100,
        source_reference="fear-greed-2026-05-31",
        summary="Source sentiment contribution.",
        metadata={"provider": "cnn"},
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
