from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from application.persistence.audit.audit_emission import (
    PersistenceAuditEmission,
    PersistenceAuditEmitter,
    emit_persistence_audit_events_non_fatal,
)
from application.persistence.query_result_helpers import (
    build_common_query,
    build_list_result,
)
from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.news import (
    NewsAnalysisSnapshotRecord,
    NewsArticleRecord,
    NewsPersistenceBundle,
    NewsPersistenceRepository,
    NewsPersistenceResult,
)
from core.storage.persistence.query import PersistenceCommonQuery, PersistenceListResult


@dataclass(
    frozen=True,
    slots=True,
)
class NewsArticlePersistenceFilters:
    """
    Typed application-layer filters for curated news article retrieval.
    """

    source: str | None = None
    symbol: str | None = None
    theme: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
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
            "theme",
            clean_optional_identifier(
                self.theme,
                "theme",
            ),
        )
        _require_ordered_time_window(
            self.start,
            self.end,
        )

    def to_common_query(
        self,
    ) -> PersistenceCommonQuery:
        return build_common_query(
            record_type="news_article",
            source=self.source,
            symbol=self.symbol,
            metadata={
                "theme": self.theme,
            },
            start=self.start,
            end=self.end,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class NewsAnalysisSnapshotPersistenceFilters:
    """
    Typed application-layer filters for curated news analysis retrieval.
    """

    source: str | None = None
    symbol: str | None = None
    theme: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
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
            "theme",
            clean_optional_identifier(
                self.theme,
                "theme",
            ),
        )
        _require_ordered_time_window(
            self.start,
            self.end,
        )

    def to_common_query(
        self,
    ) -> PersistenceCommonQuery:
        return build_common_query(
            record_type="news_analysis_snapshot",
            source=self.source,
            symbol=self.symbol,
            metadata={
                "theme": self.theme,
            },
            start=self.start,
            end=self.end,
        )


class NewsPersistenceService:
    """
    Application service for curated news persistence.

    This service coordinates typed news persistence through the repository
    protocol only. It intentionally accepts curated typed records, not raw news
    provider payloads, and does not auto-capture workflow node output.
    """

    def __init__(
        self,
        repository: NewsPersistenceRepository,
        audit_emitter: PersistenceAuditEmitter | None = None,
    ) -> None:
        self._repository = repository
        self._audit_emitter = audit_emitter

    async def persist_bundle(
        self,
        bundle: NewsPersistenceBundle,
    ) -> NewsPersistenceResult:
        result = await self._repository.persist_news_bundle(
            bundle,
        )
        if result.success:
            await emit_persistence_audit_events_non_fatal(
                self._audit_emitter,
                _news_audit_emissions(
                    bundle,
                ),
            )
        return result

    async def persist_records(
        self,
        *,
        articles: Sequence[NewsArticleRecord] = (),
        analysis_snapshots: Sequence[NewsAnalysisSnapshotRecord] = (),
    ) -> NewsPersistenceResult:
        return await self.persist_bundle(
            NewsPersistenceBundle(
                articles=tuple(
                    articles,
                ),
                analysis_snapshots=tuple(
                    analysis_snapshots,
                ),
            )
        )

    async def list_articles(
        self,
        filters: NewsArticlePersistenceFilters | None = None,
    ) -> Sequence[NewsArticleRecord]:
        result = await self.list_articles_result(
            filters,
        )
        return result.records

    async def list_articles_result(
        self,
        filters: NewsArticlePersistenceFilters | None = None,
    ) -> PersistenceListResult[NewsArticleRecord]:
        active_filters = filters or NewsArticlePersistenceFilters()
        records = tuple(
            await self._repository.list_articles(
                source=active_filters.source,
                symbol=active_filters.symbol,
                theme=active_filters.theme,
                start=active_filters.start,
                end=active_filters.end,
            )
        )
        query = active_filters.to_common_query()
        return build_list_result(
            records,
            query=query,
        )

    async def list_analysis_snapshots(
        self,
        filters: NewsAnalysisSnapshotPersistenceFilters | None = None,
    ) -> Sequence[NewsAnalysisSnapshotRecord]:
        result = await self.list_analysis_snapshots_result(
            filters,
        )
        return result.records

    async def list_analysis_snapshots_result(
        self,
        filters: NewsAnalysisSnapshotPersistenceFilters | None = None,
    ) -> PersistenceListResult[NewsAnalysisSnapshotRecord]:
        active_filters = filters or NewsAnalysisSnapshotPersistenceFilters()
        records = tuple(
            await self._repository.list_analysis_snapshots(
                source=active_filters.source,
                symbol=active_filters.symbol,
                theme=active_filters.theme,
                start=active_filters.start,
                end=active_filters.end,
            )
        )
        query = active_filters.to_common_query()
        return build_list_result(
            records,
            query=query,
        )


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


def _require_ordered_time_window(
    start: datetime | None,
    end: datetime | None,
) -> None:
    if start is not None and end is not None and start > end:
        raise ValueError("start must be less than or equal to end.")


def _news_audit_emissions(
    bundle: NewsPersistenceBundle,
) -> tuple[PersistenceAuditEmission, ...]:
    emissions: list[PersistenceAuditEmission] = []
    emissions.extend(
        PersistenceAuditEmission(
            entity_type="news_article",
            entity_id=article.article_id,
            action="persist",
            timestamp=article.published_timestamp,
            lineage=article.lineage,
            metadata={
                "source": article.source,
                "symbols": article.symbols,
                "themes": article.themes,
            },
        )
        for article in bundle.articles
    )
    emissions.extend(
        PersistenceAuditEmission(
            entity_type="news_analysis_snapshot",
            entity_id=snapshot.analysis_snapshot_id,
            action="persist",
            timestamp=snapshot.timestamp,
            lineage=snapshot.lineage,
            metadata={
                "source": snapshot.source,
                "article_ids": snapshot.article_ids,
                "symbols": snapshot.symbols,
                "themes": snapshot.themes,
            },
        )
        for snapshot in bundle.analysis_snapshots
    )
    return tuple(
        emissions,
    )
