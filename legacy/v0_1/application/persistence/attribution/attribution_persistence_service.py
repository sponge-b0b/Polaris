from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from application.persistence.query_result_helpers import (
    build_common_query,
    build_list_result,
)
from core.storage.persistence.attribution import (
    AttributionPersistenceBundle,
    AttributionPersistenceRepository,
    AttributionPersistenceResult,
    AttributionRecord,
    RecommendationAttributionRecord,
    SignalAttributionRecord,
)
from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.query import PersistenceCommonQuery, PersistenceListResult


@dataclass(
    frozen=True,
    slots=True,
)
class AttributionPersistenceFilters:
    """
    Typed application-layer filters for generic attribution retrieval.
    """

    target_record_type: str | None = None
    target_record_id: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    agent_name: str | None = None
    agent_type: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "target_record_type",
            clean_optional_identifier(
                self.target_record_type,
                "target_record_type",
            ),
        )
        object.__setattr__(
            self,
            "target_record_id",
            clean_optional_identifier(
                self.target_record_id,
                "target_record_id",
            ),
        )
        _normalize_common_filters(
            self,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SignalAttributionPersistenceFilters:
    """
    Typed application-layer filters for signal attribution retrieval.
    """

    signal_id: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    agent_name: str | None = None
    agent_type: str | None = None
    symbol: str | None = None
    universe: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "signal_id",
            clean_optional_identifier(
                self.signal_id,
                "signal_id",
            ),
        )
        _normalize_scoped_filters(
            self,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class RecommendationAttributionPersistenceFilters:
    """
    Typed application-layer filters for recommendation attribution retrieval.
    """

    recommendation_id: str | None = None
    signal_id: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    agent_name: str | None = None
    agent_type: str | None = None
    symbol: str | None = None
    universe: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "recommendation_id",
            clean_optional_identifier(
                self.recommendation_id,
                "recommendation_id",
            ),
        )
        object.__setattr__(
            self,
            "signal_id",
            clean_optional_identifier(
                self.signal_id,
                "signal_id",
            ),
        )
        _normalize_scoped_filters(
            self,
        )


class AttributionPersistenceService:
    """
    Application service for curated attribution persistence.

    This service coordinates typed attribution records through the repository
    protocol only. It does not infer attribution from raw runtime output; callers
    must provide curated attribution records with explicit source-record links.
    """

    def __init__(
        self,
        repository: AttributionPersistenceRepository,
    ) -> None:
        self._repository = repository

    async def persist_bundle(
        self,
        bundle: AttributionPersistenceBundle,
    ) -> AttributionPersistenceResult:
        return await self._repository.persist_attribution_bundle(
            bundle,
        )

    async def persist_records(
        self,
        *,
        attributions: Sequence[AttributionRecord] = (),
        signal_attributions: Sequence[SignalAttributionRecord] = (),
        recommendation_attributions: Sequence[RecommendationAttributionRecord] = (),
    ) -> AttributionPersistenceResult:
        return await self.persist_bundle(
            AttributionPersistenceBundle(
                attribution_records=tuple(
                    attributions,
                ),
                signal_attributions=tuple(
                    signal_attributions,
                ),
                recommendation_attributions=tuple(
                    recommendation_attributions,
                ),
            )
        )

    async def persist_attribution(
        self,
        attribution: AttributionRecord,
    ) -> AttributionPersistenceResult:
        return await self._repository.persist_attribution(
            attribution,
        )

    async def persist_signal_attribution(
        self,
        attribution: SignalAttributionRecord,
    ) -> AttributionPersistenceResult:
        return await self._repository.persist_signal_attribution(
            attribution,
        )

    async def persist_recommendation_attribution(
        self,
        attribution: RecommendationAttributionRecord,
    ) -> AttributionPersistenceResult:
        return await self._repository.persist_recommendation_attribution(
            attribution,
        )

    async def get_attribution(
        self,
        attribution_id: str,
    ) -> AttributionRecord | None:
        return await self._repository.get_attribution(
            attribution_id,
        )

    async def get_signal_attribution(
        self,
        signal_attribution_id: str,
    ) -> SignalAttributionRecord | None:
        return await self._repository.get_signal_attribution(
            signal_attribution_id,
        )

    async def get_recommendation_attribution(
        self,
        recommendation_attribution_id: str,
    ) -> RecommendationAttributionRecord | None:
        return await self._repository.get_recommendation_attribution(
            recommendation_attribution_id,
        )

    async def list_attributions(
        self,
        filters: AttributionPersistenceFilters | None = None,
    ) -> Sequence[AttributionRecord]:
        result = await self.list_attributions_result(
            filters,
        )
        return result.records

    async def list_attributions_result(
        self,
        filters: AttributionPersistenceFilters | None = None,
    ) -> PersistenceListResult[AttributionRecord]:
        active_filters = filters or AttributionPersistenceFilters()
        records = await self._repository.list_attributions(
            target_record_type=active_filters.target_record_type,
            target_record_id=active_filters.target_record_id,
            workflow_name=active_filters.workflow_name,
            execution_id=active_filters.execution_id,
            agent_name=active_filters.agent_name,
            agent_type=active_filters.agent_type,
            start=active_filters.start,
            end=active_filters.end,
        )
        query = build_common_query(
            record_type="attribution",
            workflow_name=active_filters.workflow_name,
            execution_id=active_filters.execution_id,
            start=active_filters.start,
            end=active_filters.end,
            metadata={
                "target_record_type": active_filters.target_record_type,
                "target_record_id": active_filters.target_record_id,
                "agent_name": active_filters.agent_name,
                "agent_type": active_filters.agent_type,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_signal_attributions(
        self,
        filters: SignalAttributionPersistenceFilters | None = None,
    ) -> Sequence[SignalAttributionRecord]:
        result = await self.list_signal_attributions_result(
            filters,
        )
        return result.records

    async def list_signal_attributions_result(
        self,
        filters: SignalAttributionPersistenceFilters | None = None,
    ) -> PersistenceListResult[SignalAttributionRecord]:
        active_filters = filters or SignalAttributionPersistenceFilters()
        records = await self._repository.list_signal_attributions(
            signal_id=active_filters.signal_id,
            workflow_name=active_filters.workflow_name,
            execution_id=active_filters.execution_id,
            agent_name=active_filters.agent_name,
            agent_type=active_filters.agent_type,
            symbol=active_filters.symbol,
            universe=active_filters.universe,
            start=active_filters.start,
            end=active_filters.end,
        )
        query = _build_scoped_attribution_query(
            record_type="signal_attribution",
            filters=active_filters,
            metadata={
                "signal_id": active_filters.signal_id,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_recommendation_attributions(
        self,
        filters: RecommendationAttributionPersistenceFilters | None = None,
    ) -> Sequence[RecommendationAttributionRecord]:
        result = await self.list_recommendation_attributions_result(
            filters,
        )
        return result.records

    async def list_recommendation_attributions_result(
        self,
        filters: RecommendationAttributionPersistenceFilters | None = None,
    ) -> PersistenceListResult[RecommendationAttributionRecord]:
        active_filters = filters or RecommendationAttributionPersistenceFilters()
        records = await self._repository.list_recommendation_attributions(
            recommendation_id=active_filters.recommendation_id,
            signal_id=active_filters.signal_id,
            workflow_name=active_filters.workflow_name,
            execution_id=active_filters.execution_id,
            agent_name=active_filters.agent_name,
            agent_type=active_filters.agent_type,
            symbol=active_filters.symbol,
            universe=active_filters.universe,
            start=active_filters.start,
            end=active_filters.end,
        )
        query = _build_scoped_attribution_query(
            record_type="recommendation_attribution",
            filters=active_filters,
            metadata={
                "recommendation_id": active_filters.recommendation_id,
                "signal_id": active_filters.signal_id,
            },
        )
        return build_list_result(
            records,
            query=query,
        )


def _build_scoped_attribution_query(
    *,
    record_type: str,
    filters: SignalAttributionPersistenceFilters
    | RecommendationAttributionPersistenceFilters,
    metadata: dict[str, str | None],
) -> PersistenceCommonQuery:
    return build_common_query(
        record_type=record_type,
        workflow_name=filters.workflow_name,
        execution_id=filters.execution_id,
        symbol=filters.symbol,
        start=filters.start,
        end=filters.end,
        metadata={
            **metadata,
            "agent_name": filters.agent_name,
            "agent_type": filters.agent_type,
            "universe": filters.universe,
        },
    )


def _normalize_common_filters(
    filters: AttributionPersistenceFilters
    | SignalAttributionPersistenceFilters
    | RecommendationAttributionPersistenceFilters,
) -> None:
    object.__setattr__(
        filters,
        "workflow_name",
        clean_optional_identifier(
            filters.workflow_name,
            "workflow_name",
        ),
    )
    object.__setattr__(
        filters,
        "execution_id",
        clean_optional_identifier(
            filters.execution_id,
            "execution_id",
        ),
    )
    object.__setattr__(
        filters,
        "agent_name",
        clean_optional_identifier(
            filters.agent_name,
            "agent_name",
        ),
    )
    object.__setattr__(
        filters,
        "agent_type",
        clean_optional_identifier(
            filters.agent_type,
            "agent_type",
        ),
    )
    _require_ordered_time_window(
        filters.start,
        filters.end,
    )


def _normalize_scoped_filters(
    filters: SignalAttributionPersistenceFilters
    | RecommendationAttributionPersistenceFilters,
) -> None:
    _normalize_common_filters(
        filters,
    )
    object.__setattr__(
        filters,
        "symbol",
        _clean_optional_symbol(
            filters.symbol,
        ),
    )
    object.__setattr__(
        filters,
        "universe",
        clean_optional_identifier(
            filters.universe,
            "universe",
        ),
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
