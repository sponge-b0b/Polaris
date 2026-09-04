from __future__ import annotations

from core.storage.persistence.news.news_persistence_models import (
    NewsAnalysisSnapshotRecord,
    NewsArticleRecord,
    NewsPersistenceBundle,
    NewsPersistenceResult,
    new_news_analysis_snapshot_id,
    new_news_article_id,
)
from core.storage.persistence.news.news_persistence_repository import (
    NewsPersistenceRepository,
)

__all__ = [
    "NewsPersistenceRepository",
    "NewsAnalysisSnapshotRecord",
    "NewsArticleRecord",
    "NewsPersistenceBundle",
    "NewsPersistenceResult",
    "new_news_analysis_snapshot_id",
    "new_news_article_id",
]
