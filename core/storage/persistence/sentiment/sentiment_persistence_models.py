from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from uuid import uuid4

from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.lineage import require_non_empty_identifier


@dataclass(
    frozen=True,
    slots=True,
)
class SentimentSnapshotRecord:
    """
    Append-only curated sentiment snapshot.

    Sentiment snapshots preserve synthesized market/news/social sentiment state
    for reporting, audit, replay, and future curated RAG projections. Provider
    payloads should be normalized before becoming this persistence-boundary
    record.
    """

    sentiment_snapshot_id: str
    timestamp: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    source: str | None = None
    symbol: str | None = None
    universe: str | None = None
    market_regime: str | None = None
    market_bias: str | None = None
    fear_greed_score: float | None = None
    news_sentiment_score: float | None = None
    market_sentiment_score: float | None = None
    social_sentiment_score: float | None = None
    composite_sentiment: float | None = None
    confidence: float | None = None
    directional_signal: float | None = None
    momentum: float | None = None
    stability: float | None = None
    divergence: float | None = None
    fusion_components: JsonObject = field(default_factory=dict)
    providers_payload: JsonObject = field(default_factory=dict)
    features_payload: JsonObject = field(default_factory=dict)
    sentiment_payload: JsonObject = field(default_factory=dict)
    raw_payload: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "sentiment_snapshot_id",
            require_non_empty_identifier(
                self.sentiment_snapshot_id,
                "sentiment_snapshot_id",
            ),
        )
        object.__setattr__(
            self,
            "source",
            clean_optional_identifier(
                self.source,
                "source",
            ),
        )
        object.__setattr__(
            self,
            "symbol",
            _clean_optional_symbol(
                self.symbol,
            ),
        )
        object.__setattr__(
            self,
            "universe",
            clean_optional_identifier(
                self.universe,
                "universe",
            ),
        )
        object.__setattr__(
            self,
            "market_regime",
            clean_optional_identifier(
                self.market_regime,
                "market_regime",
            ),
        )
        _require_optional_ratio(
            self.fear_greed_score,
            "fear_greed_score",
        )
        _require_optional_stability_score(
            self.news_sentiment_score,
            "news_sentiment_score",
        )
        _require_optional_stability_score(
            self.market_sentiment_score,
            "market_sentiment_score",
        )
        _require_optional_stability_score(
            self.social_sentiment_score,
            "social_sentiment_score",
        )
        object.__setattr__(
            self,
            "market_bias",
            clean_optional_identifier(
                self.market_bias,
                "market_bias",
            ),
        )
        _require_optional_stability_score(
            self.composite_sentiment,
            "composite_sentiment",
        )
        _require_optional_ratio(
            self.confidence,
            "confidence",
        )
        _require_optional_stability_score(
            self.directional_signal,
            "directional_signal",
        )
        _require_optional_stability_score(
            self.momentum,
            "momentum",
        )
        _require_optional_ratio(
            self.stability,
            "stability",
        )
        _require_optional_non_negative_float(
            self.divergence,
            "divergence",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SentimentSourceRecord:
    """
    Append-only curated source contribution for a sentiment snapshot.

    Source records preserve normalized source-level sentiment contributions and
    optional source references. They are not raw vendor payload storage.
    """

    sentiment_source_id: str
    timestamp: datetime
    source: str
    source_type: str
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    sentiment_snapshot_id: str | None = None
    symbol: str | None = None
    universe: str | None = None
    sentiment_score: float | None = None
    confidence: float | None = None
    weight: float | None = None
    sample_size: int | None = None
    source_reference: str | None = None
    summary: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "sentiment_source_id",
            require_non_empty_identifier(
                self.sentiment_source_id,
                "sentiment_source_id",
            ),
        )
        object.__setattr__(
            self,
            "source",
            require_non_empty_identifier(
                self.source,
                "source",
            ),
        )
        object.__setattr__(
            self,
            "source_type",
            require_non_empty_identifier(
                self.source_type,
                "source_type",
            ),
        )
        object.__setattr__(
            self,
            "sentiment_snapshot_id",
            clean_optional_identifier(
                self.sentiment_snapshot_id,
                "sentiment_snapshot_id",
            ),
        )
        object.__setattr__(
            self,
            "symbol",
            _clean_optional_symbol(
                self.symbol,
            ),
        )
        object.__setattr__(
            self,
            "universe",
            clean_optional_identifier(
                self.universe,
                "universe",
            ),
        )
        object.__setattr__(
            self,
            "source_reference",
            clean_optional_identifier(
                self.source_reference,
                "source_reference",
            ),
        )
        object.__setattr__(
            self,
            "summary",
            _clean_optional_text(
                self.summary,
            ),
        )
        _require_optional_stability_score(
            self.sentiment_score,
            "sentiment_score",
        )
        _require_optional_ratio(
            self.confidence,
            "confidence",
        )
        _require_optional_ratio(
            self.weight,
            "weight",
        )
        _require_optional_non_negative_int(
            self.sample_size,
            "sample_size",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SentimentPersistenceBundle:
    """
    Atomic sentiment persistence payload.
    """

    snapshots: tuple[SentimentSnapshotRecord, ...] = ()
    sources: tuple[SentimentSourceRecord, ...] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class SentimentPersistenceResult:
    """
    Typed result returned by sentiment persistence adapters.
    """

    success: bool
    records_persisted: int = 0
    primary_record_id: str | None = None
    error: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if self.records_persisted < 0:
            raise ValueError("records_persisted cannot be negative.")

        if self.success and self.error is not None:
            raise ValueError("successful persistence results cannot include an error.")

        if self.success:
            require_non_empty_identifier(
                self.primary_record_id,
                "primary_record_id",
            )

        if not self.success:
            require_non_empty_identifier(
                self.error,
                "error",
            )

    @classmethod
    def succeeded(
        cls,
        *,
        primary_record_id: str,
        records_persisted: int = 1,
    ) -> SentimentPersistenceResult:
        return cls(
            success=True,
            records_persisted=records_persisted,
            primary_record_id=primary_record_id,
        )

    @classmethod
    def failed(
        cls,
        error: str,
    ) -> SentimentPersistenceResult:
        return cls(
            success=False,
            records_persisted=0,
            error=error,
        )


def new_sentiment_snapshot_id(
    *,
    timestamp: datetime,
    execution_id: str | None = None,
    source: str | None = None,
    snapshot_key: str | None = None,
    symbol: str | None = None,
    universe: str | None = None,
) -> str:
    clean_execution_id = clean_optional_identifier(
        execution_id,
        "execution_id",
    )
    clean_source = clean_optional_identifier(
        source,
        "source",
    )
    clean_snapshot_key = clean_optional_identifier(
        snapshot_key,
        "snapshot_key",
    )
    clean_symbol = _clean_optional_symbol(
        symbol,
    )
    clean_universe = clean_optional_identifier(
        universe,
        "universe",
    )

    if clean_execution_id is None:
        return f"sentiment_snapshot:{uuid4().hex}"

    parts = [
        "sentiment_snapshot",
        clean_execution_id,
        timestamp.isoformat(),
    ]
    if clean_source is not None:
        parts.append(clean_source)
    if clean_symbol is not None:
        parts.append(clean_symbol)
    if clean_universe is not None:
        parts.append(clean_universe)
    if clean_snapshot_key is not None:
        parts.append(clean_snapshot_key)

    return ":".join(parts)


def new_sentiment_source_id(
    *,
    source: str,
    source_type: str,
    timestamp: datetime,
    symbol: str | None = None,
    universe: str | None = None,
    source_reference: str | None = None,
) -> str:
    parts = [
        "sentiment_source",
        timestamp.isoformat(),
        require_non_empty_identifier(
            source,
            "source",
        ),
        require_non_empty_identifier(
            source_type,
            "source_type",
        ),
    ]
    clean_symbol = _clean_optional_symbol(
        symbol,
    )
    clean_universe = clean_optional_identifier(
        universe,
        "universe",
    )
    clean_source_reference = clean_optional_identifier(
        source_reference,
        "source_reference",
    )
    if clean_symbol is not None:
        parts.append(clean_symbol)
    if clean_universe is not None:
        parts.append(clean_universe)
    if clean_source_reference is not None:
        parts.append(clean_source_reference)

    return ":".join(parts)


def _clean_optional_symbol(
    symbol: str | None,
) -> str | None:
    clean_symbol = clean_optional_identifier(
        symbol,
        "symbol",
    )
    if clean_symbol is None:
        return None

    return clean_symbol.upper()


def _clean_optional_text(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    clean_value = value.strip()
    if not clean_value:
        return None

    return clean_value


def _require_optional_ratio(
    value: float | None,
    field_name: str,
) -> None:
    if value is None:
        return

    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0.")


def _require_optional_stability_score(
    value: float | None,
    field_name: str,
) -> None:
    if value is None:
        return

    if not -1.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between -1.0 and 1.0.")


def _require_optional_non_negative_float(
    value: float | None,
    field_name: str,
) -> None:
    if value is None:
        return

    if value < 0.0:
        raise ValueError(f"{field_name} cannot be negative.")


def _require_optional_non_negative_int(
    value: int | None,
    field_name: str,
) -> None:
    if value is None:
        return

    if value < 0:
        raise ValueError(f"{field_name} cannot be negative.")
