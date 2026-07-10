from __future__ import annotations

from core.storage.persistence.recommendations.recommendation_persistence_repository import (
    RecommendationPersistenceRepository,
)
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
from core.storage.persistence.recommendations.recommendation_persistence_models import (
    new_recommendation_child_id,
)
from core.storage.persistence.recommendations.recommendation_persistence_models import (
    new_recommendation_id,
)

__all__ = [
    "RecommendationPersistenceRepository",
    "RecommendationOutcomeRecord",
    "RecommendationPersistenceBundle",
    "RecommendationPersistenceResult",
    "RecommendationRationaleRecord",
    "RecommendationRecord",
    "TradeSetupRecord",
    "WatchlistItemRecord",
    "new_recommendation_child_id",
    "new_recommendation_id",
]
