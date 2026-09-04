from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base


class AttributionRecordModel(Base):
    __tablename__ = "attribution_records"
    __table_args__ = (
        CheckConstraint(
            "contribution_score >= -1.0 AND contribution_score <= 1.0",
            name="ck_attribution_records_contribution_score_range",
        ),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_attribution_records_confidence_range",
        ),
    )

    attribution_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    target_record_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    target_record_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    attribution_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    contribution_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    contribution_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    agent_type: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    source_records: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
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
    "idx_attribution_records_target_record",
    AttributionRecordModel.target_record_type,
    AttributionRecordModel.target_record_id,
)
Index(
    "idx_attribution_records_agent_timestamp",
    AttributionRecordModel.agent_name,
    AttributionRecordModel.timestamp,
)
Index(
    "idx_attribution_records_type_timestamp",
    AttributionRecordModel.agent_type,
    AttributionRecordModel.timestamp,
)
Index(
    "idx_attribution_records_workflow_execution",
    AttributionRecordModel.workflow_name,
    AttributionRecordModel.execution_id,
)


class SignalAttributionModel(Base):
    __tablename__ = "signal_attribution"
    __table_args__ = (
        CheckConstraint(
            "contribution_score >= -1.0 AND contribution_score <= 1.0",
            name="ck_signal_attribution_contribution_score_range",
        ),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_signal_attribution_confidence_range",
        ),
    )

    signal_attribution_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    signal_id: Mapped[str] = mapped_column(
        ForeignKey(
            "agent_signals.signal_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    attribution_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    contribution_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    contribution_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    signal_type: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    agent_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    agent_type: Mapped[str | None] = mapped_column(
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
    source_records: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
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
    "idx_signal_attribution_signal_timestamp",
    SignalAttributionModel.signal_id,
    SignalAttributionModel.timestamp,
)
Index(
    "idx_signal_attribution_agent_timestamp",
    SignalAttributionModel.agent_name,
    SignalAttributionModel.timestamp,
)
Index(
    "idx_signal_attribution_type_timestamp",
    SignalAttributionModel.agent_type,
    SignalAttributionModel.timestamp,
)
Index(
    "idx_signal_attribution_symbol_timestamp",
    SignalAttributionModel.symbol,
    SignalAttributionModel.timestamp,
)
Index(
    "idx_signal_attribution_universe_timestamp",
    SignalAttributionModel.universe,
    SignalAttributionModel.timestamp,
)
Index(
    "idx_signal_attribution_workflow_execution",
    SignalAttributionModel.workflow_name,
    SignalAttributionModel.execution_id,
)


class RecommendationAttributionModel(Base):
    __tablename__ = "recommendation_attribution"
    __table_args__ = (
        CheckConstraint(
            "contribution_score >= -1.0 AND contribution_score <= 1.0",
            name="ck_recommendation_attribution_contribution_score_range",
        ),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_recommendation_attribution_confidence_range",
        ),
    )

    recommendation_attribution_id: Mapped[str] = mapped_column(
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
    signal_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "agent_signals.signal_id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    attribution_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    contribution_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    contribution_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    agent_type: Mapped[str | None] = mapped_column(
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
    source_records: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
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
    "idx_recommendation_attribution_recommendation_timestamp",
    RecommendationAttributionModel.recommendation_id,
    RecommendationAttributionModel.timestamp,
)
Index(
    "idx_recommendation_attribution_signal_timestamp",
    RecommendationAttributionModel.signal_id,
    RecommendationAttributionModel.timestamp,
)
Index(
    "idx_recommendation_attribution_agent_timestamp",
    RecommendationAttributionModel.agent_name,
    RecommendationAttributionModel.timestamp,
)
Index(
    "idx_recommendation_attribution_type_timestamp",
    RecommendationAttributionModel.agent_type,
    RecommendationAttributionModel.timestamp,
)
Index(
    "idx_recommendation_attribution_symbol_timestamp",
    RecommendationAttributionModel.symbol,
    RecommendationAttributionModel.timestamp,
)
Index(
    "idx_recommendation_attribution_universe_timestamp",
    RecommendationAttributionModel.universe,
    RecommendationAttributionModel.timestamp,
)
Index(
    "idx_recommendation_attribution_workflow_execution",
    RecommendationAttributionModel.workflow_name,
    RecommendationAttributionModel.execution_id,
)
