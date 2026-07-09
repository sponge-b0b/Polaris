from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from core.storage.persistence.recommendations import RecommendationOutcomeRecord
from core.storage.persistence.recommendations import RecommendationPersistenceBundle
from core.storage.persistence.recommendations import RecommendationPersistenceRepository
from core.storage.persistence.recommendations import RecommendationPersistenceResult
from core.storage.persistence.recommendations import RecommendationRationaleRecord
from core.storage.persistence.recommendations import RecommendationRecord
from core.storage.persistence.recommendations import TradeSetupRecord
from core.storage.persistence.recommendations import WatchlistItemRecord
from core.storage.persistence.query import PersistenceListResult

from application.persistence.audit.audit_emission import PersistenceAuditEmission
from application.persistence.audit.audit_emission import PersistenceAuditEmitter
from application.persistence.audit.audit_emission import (
    emit_persistence_audit_events_non_fatal,
)
from application.persistence.query_result_helpers import build_common_query
from application.persistence.query_result_helpers import build_list_result


@dataclass(
    frozen=True,
    slots=True,
)
class RecommendationPersistenceFilters:
    """
    Typed application-layer filters for curated recommendation retrieval.
    """

    symbol: str | None = None
    status: str | None = None
    execution_id: str | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class TradeSetupPersistenceFilters:
    """
    Typed application-layer filters for trade setup retrieval.
    """

    recommendation_id: str | None = None
    symbol: str | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class WatchlistPersistenceFilters:
    """
    Typed application-layer filters for watchlist retrieval.
    """

    recommendation_id: str | None = None
    symbol: str | None = None
    status: str | None = None


class RecommendationPersistenceService:
    """
    Application service for curated recommendation persistence.

    This service coordinates typed recommendation persistence through the
    repository protocol. It intentionally does not auto-capture workflow output;
    runtime/workflow integration should call this service explicitly when a
    curated recommendation bundle is available.
    """

    def __init__(
        self,
        repository: RecommendationPersistenceRepository,
        audit_emitter: PersistenceAuditEmitter | None = None,
    ) -> None:
        self._repository = repository
        self._audit_emitter = audit_emitter

    async def persist_bundle(
        self,
        bundle: RecommendationPersistenceBundle,
    ) -> RecommendationPersistenceResult:
        result = await self._repository.persist_recommendation_bundle(
            bundle,
        )
        if result.success:
            await emit_persistence_audit_events_non_fatal(
                self._audit_emitter,
                _recommendation_audit_emissions(
                    bundle,
                ),
            )
        return result

    async def persist(
        self,
        recommendation: RecommendationRecord,
        *,
        rationales: Sequence[RecommendationRationaleRecord] = (),
        outcomes: Sequence[RecommendationOutcomeRecord] = (),
        trade_setups: Sequence[TradeSetupRecord] = (),
        watchlist_items: Sequence[WatchlistItemRecord] = (),
    ) -> RecommendationPersistenceResult:
        return await self.persist_bundle(
            RecommendationPersistenceBundle(
                recommendation=recommendation,
                rationales=tuple(
                    rationales,
                ),
                outcomes=tuple(
                    outcomes,
                ),
                trade_setups=tuple(
                    trade_setups,
                ),
                watchlist_items=tuple(
                    watchlist_items,
                ),
            )
        )

    async def get_recommendation(
        self,
        recommendation_id: str,
    ) -> RecommendationRecord | None:
        return await self._repository.get_recommendation(
            recommendation_id,
        )

    async def get_bundle(
        self,
        recommendation_id: str,
    ) -> RecommendationPersistenceBundle | None:
        recommendation = await self._repository.get_recommendation(
            recommendation_id,
        )
        if recommendation is None:
            return None

        rationales = await self._repository.list_rationales(
            recommendation_id,
        )
        outcomes = await self._repository.list_outcomes(
            recommendation_id,
        )
        trade_setups = await self._repository.list_trade_setups(
            recommendation_id=recommendation_id,
        )
        watchlist_items = await self._repository.list_watchlist_items(
            recommendation_id=recommendation_id,
        )

        return RecommendationPersistenceBundle(
            recommendation=recommendation,
            rationales=tuple(
                rationales,
            ),
            outcomes=tuple(
                outcomes,
            ),
            trade_setups=tuple(
                trade_setups,
            ),
            watchlist_items=tuple(
                watchlist_items,
            ),
        )

    async def list_recommendations(
        self,
        filters: RecommendationPersistenceFilters | None = None,
    ) -> Sequence[RecommendationRecord]:
        result = await self.list_recommendations_result(
            filters,
        )
        return result.records

    async def list_recommendations_result(
        self,
        filters: RecommendationPersistenceFilters | None = None,
    ) -> PersistenceListResult[RecommendationRecord]:
        active_filters = filters or RecommendationPersistenceFilters()
        records = await self._repository.list_recommendations(
            symbol=active_filters.symbol,
            status=active_filters.status,
            execution_id=active_filters.execution_id,
        )
        query = build_common_query(
            record_type="recommendation",
            symbol=active_filters.symbol,
            execution_id=active_filters.execution_id,
            metadata={
                "status": active_filters.status,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_trade_setups(
        self,
        filters: TradeSetupPersistenceFilters | None = None,
    ) -> Sequence[TradeSetupRecord]:
        result = await self.list_trade_setups_result(
            filters,
        )
        return result.records

    async def list_trade_setups_result(
        self,
        filters: TradeSetupPersistenceFilters | None = None,
    ) -> PersistenceListResult[TradeSetupRecord]:
        active_filters = filters or TradeSetupPersistenceFilters()
        records = await self._repository.list_trade_setups(
            recommendation_id=active_filters.recommendation_id,
            symbol=active_filters.symbol,
        )
        query = build_common_query(
            record_type="trade_setup",
            symbol=active_filters.symbol,
            metadata={
                "recommendation_id": active_filters.recommendation_id,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_watchlist_items(
        self,
        filters: WatchlistPersistenceFilters | None = None,
    ) -> Sequence[WatchlistItemRecord]:
        result = await self.list_watchlist_items_result(
            filters,
        )
        return result.records

    async def list_watchlist_items_result(
        self,
        filters: WatchlistPersistenceFilters | None = None,
    ) -> PersistenceListResult[WatchlistItemRecord]:
        active_filters = filters or WatchlistPersistenceFilters()
        records = await self._repository.list_watchlist_items(
            recommendation_id=active_filters.recommendation_id,
            symbol=active_filters.symbol,
            status=active_filters.status,
        )
        query = build_common_query(
            record_type="watchlist_item",
            symbol=active_filters.symbol,
            metadata={
                "recommendation_id": active_filters.recommendation_id,
                "status": active_filters.status,
            },
        )
        return build_list_result(
            records,
            query=query,
        )


def _recommendation_audit_emissions(
    bundle: RecommendationPersistenceBundle,
) -> tuple[PersistenceAuditEmission, ...]:
    recommendation = bundle.recommendation
    emissions: list[PersistenceAuditEmission] = [
        PersistenceAuditEmission(
            entity_type="recommendation",
            entity_id=recommendation.recommendation_id,
            action="persist",
            timestamp=recommendation.created_at,
            lineage=recommendation.lineage,
            metadata={
                "symbol": recommendation.symbol,
                "bias": recommendation.bias,
                "status": recommendation.status,
            },
        )
    ]
    emissions.extend(
        PersistenceAuditEmission(
            entity_type="recommendation_rationale",
            entity_id=rationale.rationale_id,
            action="persist",
            timestamp=rationale.created_at,
            lineage=rationale.lineage,
            metadata={
                "recommendation_id": rationale.recommendation_id,
                "rationale_type": rationale.rationale_type,
            },
        )
        for rationale in bundle.rationales
    )
    emissions.extend(
        PersistenceAuditEmission(
            entity_type="recommendation_outcome",
            entity_id=outcome.outcome_id,
            action="persist",
            timestamp=outcome.evaluated_at,
            lineage=outcome.lineage,
            metadata={
                "recommendation_id": outcome.recommendation_id,
                "human_action": outcome.human_action,
                "outcome": outcome.outcome,
            },
        )
        for outcome in bundle.outcomes
    )
    emissions.extend(
        PersistenceAuditEmission(
            entity_type="trade_setup",
            entity_id=trade_setup.setup_id,
            action="persist",
            timestamp=trade_setup.created_at,
            lineage=trade_setup.lineage,
            metadata={
                "recommendation_id": trade_setup.recommendation_id,
                "symbol": trade_setup.symbol,
                "bias": trade_setup.bias,
                "setup_type": trade_setup.setup_type,
            },
        )
        for trade_setup in bundle.trade_setups
    )
    emissions.extend(
        PersistenceAuditEmission(
            entity_type="watchlist_item",
            entity_id=watchlist_item.watchlist_item_id,
            action="persist",
            timestamp=watchlist_item.created_at,
            lineage=watchlist_item.lineage,
            metadata={
                "recommendation_id": watchlist_item.recommendation_id,
                "symbol": watchlist_item.symbol,
                "status": watchlist_item.status,
                "bias": watchlist_item.bias,
            },
        )
        for watchlist_item in bundle.watchlist_items
    )
    return tuple(
        emissions,
    )
