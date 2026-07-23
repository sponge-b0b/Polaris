from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from core.storage.persistence.idempotency import (
    PersistenceIdempotencyKey,
    build_persistence_idempotency_key,
    symbol_idempotency_component,
    timestamp_idempotency_component,
)


def test_persistence_idempotency_key_builds_stable_key() -> None:
    key = PersistenceIdempotencyKey(
        namespace=" postgres ",
        version=" v1 ",
        record_type=" news_article ",
        components=(
            " reuters ",
            " article-123 ",
        ),
    )

    assert key.key == "postgres:v1:news_article:reuters:article-123"
    assert str(key) == key.key
    assert key.as_dict() == {
        "namespace": "postgres",
        "version": "v1",
        "record_type": "news_article",
        "components": (
            "reuters",
            "article-123",
        ),
        "key": "postgres:v1:news_article:reuters:article-123",
    }


def test_persistence_idempotency_key_requires_components() -> None:
    with pytest.raises(ValueError, match="at least one idempotency component"):
        PersistenceIdempotencyKey(
            record_type="recommendation",
            components=(),
        )

    with pytest.raises(ValueError, match="idempotency_component cannot be empty"):
        PersistenceIdempotencyKey(
            record_type="recommendation",
            components=(" ",),
        )


@pytest.mark.parametrize(
    "component",
    [
        None,
        " ",
    ],
)
def test_build_persistence_idempotency_key_requires_required_components(
    component: object,
) -> None:
    with pytest.raises(ValueError):
        build_persistence_idempotency_key(
            record_type="market_ohlcv",
            components=(component,),  # type: ignore[arg-type]
        )


def test_build_persistence_idempotency_key_omits_missing_optional_components() -> None:
    timestamp = _timestamp()

    key = build_persistence_idempotency_key(
        record_type="market_ohlcv",
        components=(
            "SPY",
            timestamp,
            "polygon",
        ),
        optional_components=(
            None,
            " 1d ",
        ),
    )

    assert key.key == "market_ohlcv:SPY:2026-05-31T14:00:00+00:00:polygon:1d"


def test_build_persistence_idempotency_key_normalizes_supported_component_types() -> (
    None
):
    key = build_persistence_idempotency_key(
        record_type="example_record",
        components=(
            " source ",
            7,
            1.25,
            True,
            _timestamp(),
        ),
    )

    assert key.components == (
        "source",
        "7",
        "1.25",
        "true",
        "2026-05-31T14:00:00+00:00",
    )


def test_symbol_and_timestamp_components_are_stable() -> None:
    assert symbol_idempotency_component(" spy ") == "SPY"
    assert symbol_idempotency_component(" ") is None
    assert timestamp_idempotency_component(_timestamp()) == "2026-05-31T14:00:00+00:00"


def test_idempotency_key_is_immutable() -> None:
    key = PersistenceIdempotencyKey(
        record_type="recommendation",
        components=("rec-1",),
    )

    with pytest.raises(FrozenInstanceError):
        key.record_type = "other"  # type: ignore[misc]


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=UTC)
