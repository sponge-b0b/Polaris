from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from core.database.base import Base


class RecommendationModel(Base):
    __tablename__ = "recommendations"

    recommendation_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    symbol: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    bias: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    setup_quality: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    risk_level: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    time_horizon: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    status: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    entry_context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    stop_context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    target_context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    supporting_signals: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
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
    "idx_recommendations_symbol_created_at",
    RecommendationModel.symbol,
    RecommendationModel.created_at,
)
Index(
    "idx_recommendations_workflow_execution",
    RecommendationModel.workflow_name,
    RecommendationModel.execution_id,
)
Index(
    "idx_recommendations_status_bias",
    RecommendationModel.status,
    RecommendationModel.bias,
)
Index(
    "idx_recommendations_risk_level_created_at",
    RecommendationModel.risk_level,
    RecommendationModel.created_at,
)


class RecommendationRationaleModel(Base):
    __tablename__ = "recommendation_rationales"

    rationale_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    recommendation_id: Mapped[str] = mapped_column(
        ForeignKey(
            "recommendations.recommendation_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    rationale_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    rationale_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    confidence: Mapped[float | None] = mapped_column(
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    supporting_signals: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
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
    "idx_recommendation_rationales_recommendation_created_at",
    RecommendationRationaleModel.recommendation_id,
    RecommendationRationaleModel.created_at,
)
Index(
    "idx_recommendation_rationales_workflow_execution",
    RecommendationRationaleModel.workflow_name,
    RecommendationRationaleModel.execution_id,
)


class RecommendationOutcomeModel(Base):
    __tablename__ = "recommendation_outcomes"

    outcome_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    recommendation_id: Mapped[str] = mapped_column(
        ForeignKey(
            "recommendations.recommendation_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    human_action: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    outcome: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    outcome_return: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    outcome_notes: Mapped[str | None] = mapped_column(
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
    "idx_recommendation_outcomes_recommendation_evaluated_at",
    RecommendationOutcomeModel.recommendation_id,
    RecommendationOutcomeModel.evaluated_at,
)
Index(
    "idx_recommendation_outcomes_workflow_execution",
    RecommendationOutcomeModel.workflow_name,
    RecommendationOutcomeModel.execution_id,
)
Index(
    "idx_recommendation_outcomes_action_outcome",
    RecommendationOutcomeModel.human_action,
    RecommendationOutcomeModel.outcome,
)


class TradeSetupModel(Base):
    __tablename__ = "trade_setups"

    setup_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    recommendation_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "recommendations.recommendation_id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    setup_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    bias: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    setup_quality: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    risk_reward_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    time_horizon: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    entry_context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    stop_context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    target_context: Mapped[dict[str, Any]] = mapped_column(
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
    "idx_trade_setups_symbol_created_at",
    TradeSetupModel.symbol,
    TradeSetupModel.created_at,
)
Index(
    "idx_trade_setups_workflow_execution",
    TradeSetupModel.workflow_name,
    TradeSetupModel.execution_id,
)
Index(
    "idx_trade_setups_bias_quality",
    TradeSetupModel.bias,
    TradeSetupModel.setup_quality,
)


class WatchlistItemModel(Base):
    __tablename__ = "watchlist_items"

    watchlist_item_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    recommendation_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "recommendations.recommendation_id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    status: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    bias: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    setup_quality: Mapped[float | None] = mapped_column(
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
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
    "idx_watchlist_items_symbol_created_at",
    WatchlistItemModel.symbol,
    WatchlistItemModel.created_at,
)
Index(
    "idx_watchlist_items_workflow_execution",
    WatchlistItemModel.workflow_name,
    WatchlistItemModel.execution_id,
)
Index(
    "idx_watchlist_items_status_priority",
    WatchlistItemModel.status,
    WatchlistItemModel.priority,
)
