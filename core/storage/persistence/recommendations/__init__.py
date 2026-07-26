from __future__ import annotations

from core.storage.persistence.recommendations.recommendation_persistence_models import (
    RecommendationClaimEvidenceLinkRecord,
    RecommendationOutcomeRecord,
    RecommendationPersistenceBundle,
    RecommendationPersistenceResult,
    RecommendationRationaleRecord,
    RecommendationRecord,
    TradeSetupRecord,
    WatchlistItemRecord,
    new_recommendation_child_id,
    new_recommendation_claim_evidence_link_id,
    new_recommendation_id,
)
from core.storage.persistence.recommendations.recommendation_persistence_repository import (  # noqa: E501 - canonical module path
    RecommendationPersistenceRepository,
)

__all__ = [
    "RecommendationClaimEvidenceLinkRecord",
    "RecommendationPersistenceRepository",
    "RecommendationOutcomeRecord",
    "RecommendationPersistenceBundle",
    "RecommendationPersistenceResult",
    "RecommendationRationaleRecord",
    "RecommendationRecord",
    "TradeSetupRecord",
    "WatchlistItemRecord",
    "new_recommendation_child_id",
    "new_recommendation_claim_evidence_link_id",
    "new_recommendation_id",
]
