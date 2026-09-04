from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from core.storage.persistence.lineage import (
    JsonObject,
    PersistenceLineage,
    clean_optional_identifier,
    require_non_empty_identifier,
)


@dataclass(
    frozen=True,
    slots=True,
)
class NewsArticleRecord:
    """
    Typed persistence-boundary record for a curated news article.

    News client/provider payloads should be normalized before becoming this
    record. Raw article payloads remain at external/provider boundaries; this
    contract represents the PostgreSQL system-of-record input for reporting,
    attribution, audit, and future RAG projections.
    """

    article_id: str
    source: str
    title: str
    published_timestamp: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    external_id: str | None = None
    url: str | None = None
    summary: str | None = None
    symbols: tuple[str, ...] = ()
    themes: tuple[str, ...] = ()
    importance_score: float | None = None
    headline_score: float | None = None
    relevance_score: float | None = None
    sentiment_score: float | None = None
    normalized_article_payload: JsonObject = field(default_factory=dict)
    raw_payload: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "article_id",
            require_non_empty_identifier(
                self.article_id,
                "article_id",
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
            "title",
            require_non_empty_identifier(
                self.title,
                "title",
            ),
        )
        object.__setattr__(
            self,
            "external_id",
            clean_optional_identifier(
                self.external_id,
                "external_id",
            ),
        )
        object.__setattr__(
            self,
            "url",
            clean_optional_identifier(
                self.url,
                "url",
            ),
        )
        object.__setattr__(
            self,
            "summary",
            clean_optional_text(
                self.summary,
            ),
        )
        object.__setattr__(
            self,
            "symbols",
            _normalize_symbols(
                self.symbols,
            ),
        )
        object.__setattr__(
            self,
            "themes",
            _normalize_identifier_tuple(
                self.themes,
                "theme",
            ),
        )
        _require_article_source_identity(
            external_id=self.external_id,
            url=self.url,
        )
        _require_optional_ratio(
            self.importance_score,
            "importance_score",
        )
        _require_optional_ratio(
            self.headline_score,
            "headline_score",
        )
        _require_optional_ratio(
            self.relevance_score,
            "relevance_score",
        )
        _require_optional_stability_score(
            self.sentiment_score,
            "sentiment_score",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class NewsAnalysisSnapshotRecord:
    """
    Append-only curated news analysis snapshot.

    LLM-derived text is preserved without truncation. Serialization layers may
    store it in PostgreSQL text columns, but they should not shorten it unless a
    caller explicitly creates a separate shortened field.
    """

    analysis_snapshot_id: str
    timestamp: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    source: str | None = None
    article_ids: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()
    themes: tuple[str, ...] = ()
    importance_score: float | None = None
    sentiment_score: float | None = None
    impact_score: float | None = None
    confidence: float | None = None
    llm_summary: str | None = None
    full_llm_response: str | None = None
    analysis_model: str | None = None
    inputs: JsonObject = field(default_factory=dict)
    outputs: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "analysis_snapshot_id",
            require_non_empty_identifier(
                self.analysis_snapshot_id,
                "analysis_snapshot_id",
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
            "article_ids",
            _normalize_identifier_tuple(
                self.article_ids,
                "article_id",
            ),
        )
        object.__setattr__(
            self,
            "symbols",
            _normalize_symbols(
                self.symbols,
            ),
        )
        object.__setattr__(
            self,
            "themes",
            _normalize_identifier_tuple(
                self.themes,
                "theme",
            ),
        )
        object.__setattr__(
            self,
            "llm_summary",
            clean_optional_text(
                self.llm_summary,
            ),
        )
        object.__setattr__(
            self,
            "full_llm_response",
            clean_optional_text(
                self.full_llm_response,
            ),
        )
        object.__setattr__(
            self,
            "analysis_model",
            clean_optional_identifier(
                self.analysis_model,
                "analysis_model",
            ),
        )
        _require_optional_ratio(
            self.importance_score,
            "importance_score",
        )
        _require_optional_stability_score(
            self.sentiment_score,
            "sentiment_score",
        )
        _require_optional_stability_score(
            self.impact_score,
            "impact_score",
        )
        _require_optional_ratio(
            self.confidence,
            "confidence",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class NewsPersistenceBundle:
    """
    Atomic news persistence payload.
    """

    articles: tuple[NewsArticleRecord, ...] = ()
    analysis_snapshots: tuple[NewsAnalysisSnapshotRecord, ...] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class NewsPersistenceResult:
    """
    Typed result returned by news persistence adapters.
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
    ) -> NewsPersistenceResult:
        return cls(
            success=True,
            records_persisted=records_persisted,
            primary_record_id=primary_record_id,
        )

    @classmethod
    def failed(
        cls,
        error: str,
    ) -> NewsPersistenceResult:
        return cls(
            success=False,
            records_persisted=0,
            error=error,
        )


def new_news_article_id(
    *,
    source: str,
    published_timestamp: datetime,
    external_id: str | None = None,
    url: str | None = None,
) -> str:
    clean_source = require_non_empty_identifier(
        source,
        "source",
    )
    clean_external_id = clean_optional_identifier(
        external_id,
        "external_id",
    )
    clean_url = clean_optional_identifier(
        url,
        "url",
    )
    _require_article_source_identity(
        external_id=clean_external_id,
        url=clean_url,
    )

    source_key = clean_external_id or clean_url
    return ":".join(
        (
            "news_article",
            clean_source,
            published_timestamp.isoformat(),
            require_non_empty_identifier(
                source_key,
                "source_key",
            ),
        )
    )


def new_news_analysis_snapshot_id(
    *,
    timestamp: datetime,
    execution_id: str | None = None,
    snapshot_key: str | None = None,
    article_id: str | None = None,
    symbol: str | None = None,
) -> str:
    clean_execution_id = clean_optional_identifier(
        execution_id,
        "execution_id",
    )
    clean_snapshot_key = clean_optional_identifier(
        snapshot_key,
        "snapshot_key",
    )
    clean_article_id = clean_optional_identifier(
        article_id,
        "article_id",
    )
    clean_symbol = clean_optional_identifier(
        symbol,
        "symbol",
    )

    if clean_execution_id is None:
        return f"news_analysis_snapshot:{uuid4().hex}"

    parts = [
        "news_analysis_snapshot",
        clean_execution_id,
        timestamp.isoformat(),
    ]
    if clean_article_id is not None:
        parts.append(clean_article_id)
    if clean_symbol is not None:
        parts.append(
            clean_symbol.upper(),
        )
    if clean_snapshot_key is not None:
        parts.append(clean_snapshot_key)

    return ":".join(parts)


def clean_optional_text(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    if not value.strip():
        return None

    return value


def _require_article_source_identity(
    *,
    external_id: str | None,
    url: str | None,
) -> None:
    if external_id is None and url is None:
        raise ValueError("news articles require either external_id or url.")


def _normalize_symbols(
    symbols: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(
        require_non_empty_identifier(
            symbol,
            "symbol",
        ).upper()
        for symbol in symbols
    )


def _normalize_identifier_tuple(
    values: tuple[str, ...],
    field_name: str,
) -> tuple[str, ...]:
    return tuple(
        require_non_empty_identifier(
            value,
            field_name,
        )
        for value in values
    )


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
