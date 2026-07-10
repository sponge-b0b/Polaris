from __future__ import annotations

from core.storage.persistence.news.news_persistence_repository import (
    NewsPersistenceRepository,
)
from core.storage.persistence.news.news_persistence_models import (
    NewsAnalysisSnapshotRecord,
)
from core.storage.persistence.news.news_persistence_models import NewsArticleRecord
from core.storage.persistence.news.news_persistence_models import NewsPersistenceBundle
from core.storage.persistence.news.news_persistence_models import NewsPersistenceResult
from core.storage.persistence.news.news_persistence_models import (
    new_news_analysis_snapshot_id,
)
from core.storage.persistence.news.news_persistence_models import new_news_article_id

__all__ = [
    "NewsPersistenceRepository",
    "NewsAnalysisSnapshotRecord",
    "NewsArticleRecord",
    "NewsPersistenceBundle",
    "NewsPersistenceResult",
    "new_news_analysis_snapshot_id",
    "new_news_article_id",
]
