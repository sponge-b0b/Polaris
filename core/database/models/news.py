from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Index
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from core.database.base import Base


class NewsArticleModel(Base):
    __tablename__ = "news_articles"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_id",
            name="uq_news_articles_source_external_id",
        ),
        UniqueConstraint(
            "source",
            "url",
            name="uq_news_articles_source_url",
        ),
        CheckConstraint(
            "external_id IS NOT NULL OR url IS NOT NULL",
            name="ck_news_articles_source_identity",
        ),
    )

    article_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    source: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    external_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    published_timestamp: Mapped[datetime] = mapped_column(
        "published_at",
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    symbols: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    themes: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    importance_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    headline_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    relevance_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    sentiment_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    workflow_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    execution_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    runtime_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    node_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    normalized_article_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    row_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    row_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_news_articles_source_published",
    NewsArticleModel.source,
    NewsArticleModel.published_timestamp,
)
Index(
    "idx_news_articles_workflow_execution",
    NewsArticleModel.workflow_name,
    NewsArticleModel.execution_id,
)
Index(
    "idx_news_articles_symbols",
    NewsArticleModel.symbols,
    postgresql_using="gin",
)
Index(
    "idx_news_articles_themes",
    NewsArticleModel.themes,
    postgresql_using="gin",
)


class NewsAnalysisSnapshotModel(Base):
    __tablename__ = "news_analysis_snapshots"

    analysis_snapshot_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    source: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    article_ids: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    symbols: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    themes: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    importance_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    sentiment_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    impact_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    llm_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    full_llm_response: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    analysis_model: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    inputs: Mapped[dict[str, Any]] = mapped_column(
        "inputs_payload",
        JSONB,
        nullable=False,
        default=dict,
    )
    outputs: Mapped[dict[str, Any]] = mapped_column(
        "analysis_payload",
        JSONB,
        nullable=False,
        default=dict,
    )
    workflow_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    execution_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    runtime_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    node_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    row_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    row_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_news_analysis_snapshots_timestamp_source",
    NewsAnalysisSnapshotModel.timestamp,
    NewsAnalysisSnapshotModel.source,
)
Index(
    "idx_news_analysis_snapshots_workflow_execution",
    NewsAnalysisSnapshotModel.workflow_name,
    NewsAnalysisSnapshotModel.execution_id,
)
Index(
    "idx_news_analysis_snapshots_article_ids",
    NewsAnalysisSnapshotModel.article_ids,
    postgresql_using="gin",
)
Index(
    "idx_news_analysis_snapshots_symbols",
    NewsAnalysisSnapshotModel.symbols,
    postgresql_using="gin",
)
Index(
    "idx_news_analysis_snapshots_themes",
    NewsAnalysisSnapshotModel.themes,
    postgresql_using="gin",
)
