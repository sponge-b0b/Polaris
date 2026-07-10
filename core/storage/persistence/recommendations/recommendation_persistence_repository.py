from __future__ import annotations

from typing import Protocol
from typing import Sequence

from core.storage.persistence.recommendations.recommendation_persistence_models import (
    RecommendationOutcomeRecord,
)
from core.storage.persistence.recommendations.recommendation_persistence_models import (
    RecommendationPersistenceBundle,
)
from core.storage.persistence.recommendations.recommendation_persistence_models import (
    RecommendationPersistenceResult,
)
from core.storage.persistence.recommendations.recommendation_persistence_models import (
    RecommendationRationaleRecord,
)
from core.storage.persistence.recommendations.recommendation_persistence_models import (
    RecommendationRecord,
)
from core.storage.persistence.recommendations.recommendation_persistence_models import (
    TradeSetupRecord,
)
from core.storage.persistence.recommendations.recommendation_persistence_models import (
    WatchlistItemRecord,
)


class RecommendationPersistenceRepository(Protocol):
    """
    Async repository contract for durable curated recommendation persistence.

    Recommendations, rationales, outcomes, trade setups, and watchlist entries
    are Postgres system-of-record objects. RAG/vector stores should later be
    populated from these curated records, not from raw workflow payloads.
    """

    async def persist_recommendation_bundle(
        self,
        bundle: RecommendationPersistenceBundle,
    ) -> RecommendationPersistenceResult: ...

    async def get_recommendation(
        self,
        recommendation_id: str,
    ) -> RecommendationRecord | None: ...

    async def list_recommendations(
        self,
        *,
        symbol: str | None = None,
        status: str | None = None,
        execution_id: str | None = None,
    ) -> Sequence[RecommendationRecord]: ...

    async def list_rationales(
        self,
        recommendation_id: str,
    ) -> Sequence[RecommendationRationaleRecord]: ...

    async def list_outcomes(
        self,
        recommendation_id: str,
    ) -> Sequence[RecommendationOutcomeRecord]: ...

    async def list_trade_setups(
        self,
        *,
        recommendation_id: str | None = None,
        symbol: str | None = None,
    ) -> Sequence[TradeSetupRecord]: ...

    async def list_watchlist_items(
        self,
        *,
        recommendation_id: str | None = None,
        symbol: str | None = None,
        status: str | None = None,
    ) -> Sequence[WatchlistItemRecord]: ...
