from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

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


class RecommendationClaimEvidenceLinkModel(Base):
    """Durable recommendation claim-to-decision-evidence-packet audit link."""

    __tablename__ = "recommendation_claim_evidence_links"
    __table_args__ = (
        CheckConstraint(
            "risk_tier IN ('enhanced', 'vigilant')",
            name="ck_recommendation_claim_evidence_links_risk_tier",
        ),
        CheckConstraint(
            "jsonb_typeof(supporting_evidence_ids) = 'array'",
            name="ck_recommendation_claim_evidence_links_supporting_ids_array",
        ),
        CheckConstraint(
            "jsonb_typeof(reconstruction_reference_ids) = 'array'",
            name="ck_recommendation_claim_evidence_links_reconstruction_ids_array",
        ),
        CheckConstraint(
            "jsonb_typeof(uncertainty_ids) = 'array'",
            name="ck_recommendation_claim_evidence_links_uncertainty_ids_array",
        ),
        CheckConstraint(
            "jsonb_typeof(limitation_ids) = 'array'",
            name="ck_recommendation_claim_evidence_links_limitation_ids_array",
        ),
        CheckConstraint(
            "NOT (material AND (jsonb_array_length(supporting_evidence_ids) = 0 "
            "OR jsonb_array_length(reconstruction_reference_ids) = 0))",
            name="ck_recommendation_claim_evidence_links_material_has_support",
        ),
    )

    link_id: Mapped[str] = mapped_column(
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
    rationale_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "recommendation_rationales.rationale_id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    claim_target_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    packet_id: Mapped[str] = mapped_column(
        ForeignKey(
            "decision_evidence_packets.packet_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    packet_claim_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    risk_tier: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    material: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    supporting_evidence_ids: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    reconstruction_reference_ids: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    uncertainty_ids: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    limitation_ids: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_recommendation_claim_evidence_links_recommendation_claim",
    RecommendationClaimEvidenceLinkModel.recommendation_id,
    RecommendationClaimEvidenceLinkModel.claim_target_id,
)

Index(
    "idx_recommendation_claim_evidence_links_packet_claim",
    RecommendationClaimEvidenceLinkModel.packet_id,
    RecommendationClaimEvidenceLinkModel.packet_claim_id,
)
