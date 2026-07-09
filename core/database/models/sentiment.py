from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from core.database.base import Base


class SentimentSnapshotModel(Base):
    __tablename__ = "sentiment_snapshots"

    sentiment_snapshot_id: Mapped[str] = mapped_column(
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
    symbol: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    universe: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    market_regime: Mapped[str | None] = mapped_column(
        "market_regime",
        String,
        nullable=True,
        index=True,
    )
    market_bias: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    fear_greed_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    news_sentiment_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    market_sentiment_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    social_sentiment_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    composite_sentiment: Mapped[float | None] = mapped_column(
        "composite_sentiment",
        Float,
        nullable=True,
    )
    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    directional_signal: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    momentum: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    stability: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    divergence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    fusion_components: Mapped[dict[str, Any]] = mapped_column(
        "fusion_components_payload",
        JSONB,
        nullable=False,
        default=dict,
    )
    providers_payload: Mapped[dict[str, Any]] = mapped_column(
        "providers_payload",
        JSONB,
        nullable=False,
        default=dict,
    )
    features_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    sentiment_payload: Mapped[dict[str, Any]] = mapped_column(
        "sentiment_payload",
        JSONB,
        nullable=False,
        default=dict,
    )
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
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
    "idx_sentiment_snapshots_timestamp_source",
    SentimentSnapshotModel.timestamp,
    SentimentSnapshotModel.source,
)
Index(
    "idx_sentiment_snapshots_symbol_timestamp",
    SentimentSnapshotModel.symbol,
    SentimentSnapshotModel.timestamp,
)
Index(
    "idx_sentiment_snapshots_universe_timestamp",
    SentimentSnapshotModel.universe,
    SentimentSnapshotModel.timestamp,
)
Index(
    "idx_sentiment_snapshots_workflow_execution",
    SentimentSnapshotModel.workflow_name,
    SentimentSnapshotModel.execution_id,
)


class SentimentSourceModel(Base):
    __tablename__ = "sentiment_sources"

    sentiment_source_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    sentiment_snapshot_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    symbol: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    universe: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    sentiment_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    weight: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    sample_size: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    source_reference: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )
    summary: Mapped[str | None] = mapped_column(
        Text,
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
    "idx_sentiment_sources_timestamp_source",
    SentimentSourceModel.timestamp,
    SentimentSourceModel.source,
)
Index(
    "idx_sentiment_sources_source_type_timestamp",
    SentimentSourceModel.source_type,
    SentimentSourceModel.timestamp,
)
Index(
    "idx_sentiment_sources_snapshot_timestamp",
    SentimentSourceModel.sentiment_snapshot_id,
    SentimentSourceModel.timestamp,
)
Index(
    "idx_sentiment_sources_symbol_timestamp",
    SentimentSourceModel.symbol,
    SentimentSourceModel.timestamp,
)
Index(
    "idx_sentiment_sources_universe_timestamp",
    SentimentSourceModel.universe,
    SentimentSourceModel.timestamp,
)
Index(
    "idx_sentiment_sources_workflow_execution",
    SentimentSourceModel.workflow_name,
    SentimentSourceModel.execution_id,
)
