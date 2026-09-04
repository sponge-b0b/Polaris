from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base


class AgentReasoningModel(Base):
    __tablename__ = "agent_reasoning"

    reasoning_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    agent_signal_id: Mapped[str] = mapped_column(
        ForeignKey(
            "agent_signals.signal_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    agent_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    reasoning_type: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    model_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    prompt_version: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
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
    reasoning_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    full_llm_response: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    inputs: Mapped[dict[str, Any]] = mapped_column(
        "inputs_payload",
        JSONB,
        nullable=False,
        default=dict,
    )
    outputs: Mapped[dict[str, Any]] = mapped_column(
        "outputs_payload",
        JSONB,
        nullable=False,
        default=dict,
    )
    linked_records: Mapped[list[dict[str, Any]]] = mapped_column(
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
    "idx_agent_reasoning_signal_timestamp",
    AgentReasoningModel.agent_signal_id,
    AgentReasoningModel.timestamp,
)
Index(
    "idx_agent_reasoning_agent_timestamp",
    AgentReasoningModel.agent_name,
    AgentReasoningModel.timestamp,
)
Index(
    "idx_agent_reasoning_type_timestamp",
    AgentReasoningModel.agent_type,
    AgentReasoningModel.timestamp,
)
Index(
    "idx_agent_reasoning_symbol_timestamp",
    AgentReasoningModel.symbol,
    AgentReasoningModel.timestamp,
)
Index(
    "idx_agent_reasoning_universe_timestamp",
    AgentReasoningModel.universe,
    AgentReasoningModel.timestamp,
)
Index(
    "idx_agent_reasoning_workflow_execution",
    AgentReasoningModel.workflow_name,
    AgentReasoningModel.execution_id,
)


class AgentRecommendationModel(Base):
    __tablename__ = "agent_recommendations"

    agent_recommendation_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    agent_signal_id: Mapped[str] = mapped_column(
        ForeignKey(
            "agent_signals.signal_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    agent_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    recommendation_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    recommendation_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
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
    bias: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    action: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    conviction: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    time_horizon: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    rationale_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    full_llm_response: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    supporting_signals: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    inputs: Mapped[dict[str, Any]] = mapped_column(
        "inputs_payload",
        JSONB,
        nullable=False,
        default=dict,
    )
    outputs: Mapped[dict[str, Any]] = mapped_column(
        "outputs_payload",
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
    "idx_agent_recommendations_signal_timestamp",
    AgentRecommendationModel.agent_signal_id,
    AgentRecommendationModel.timestamp,
)
Index(
    "idx_agent_recommendations_agent_timestamp",
    AgentRecommendationModel.agent_name,
    AgentRecommendationModel.timestamp,
)
Index(
    "idx_agent_recommendations_type_timestamp",
    AgentRecommendationModel.agent_type,
    AgentRecommendationModel.timestamp,
)
Index(
    "idx_agent_recommendations_symbol_timestamp",
    AgentRecommendationModel.symbol,
    AgentRecommendationModel.timestamp,
)
Index(
    "idx_agent_recommendations_universe_timestamp",
    AgentRecommendationModel.universe,
    AgentRecommendationModel.timestamp,
)
Index(
    "idx_agent_recommendations_workflow_execution",
    AgentRecommendationModel.workflow_name,
    AgentRecommendationModel.execution_id,
)
Index(
    "idx_agent_recommendations_action_bias",
    AgentRecommendationModel.action,
    AgentRecommendationModel.bias,
)


class AgentRiskAssessmentModel(Base):
    __tablename__ = "agent_risk_assessments"

    risk_assessment_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    agent_signal_id: Mapped[str] = mapped_column(
        ForeignKey(
            "agent_signals.signal_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    agent_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    risk_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    assessment_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
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
    risk_level: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    mitigation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    full_llm_response: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    inputs: Mapped[dict[str, Any]] = mapped_column(
        "inputs_payload",
        JSONB,
        nullable=False,
        default=dict,
    )
    outputs: Mapped[dict[str, Any]] = mapped_column(
        "outputs_payload",
        JSONB,
        nullable=False,
        default=dict,
    )
    supporting_signals: Mapped[list[dict[str, Any]]] = mapped_column(
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
    "idx_agent_risk_assessments_signal_timestamp",
    AgentRiskAssessmentModel.agent_signal_id,
    AgentRiskAssessmentModel.timestamp,
)
Index(
    "idx_agent_risk_assessments_agent_timestamp",
    AgentRiskAssessmentModel.agent_name,
    AgentRiskAssessmentModel.timestamp,
)
Index(
    "idx_agent_risk_assessments_type_timestamp",
    AgentRiskAssessmentModel.agent_type,
    AgentRiskAssessmentModel.timestamp,
)
Index(
    "idx_agent_risk_assessments_risk_type_timestamp",
    AgentRiskAssessmentModel.risk_type,
    AgentRiskAssessmentModel.timestamp,
)
Index(
    "idx_agent_risk_assessments_symbol_timestamp",
    AgentRiskAssessmentModel.symbol,
    AgentRiskAssessmentModel.timestamp,
)
Index(
    "idx_agent_risk_assessments_universe_timestamp",
    AgentRiskAssessmentModel.universe,
    AgentRiskAssessmentModel.timestamp,
)
Index(
    "idx_agent_risk_assessments_workflow_execution",
    AgentRiskAssessmentModel.workflow_name,
    AgentRiskAssessmentModel.execution_id,
)
