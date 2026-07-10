from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean
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


class StrategyHypothesisModel(Base):
    __tablename__ = "strategy_hypotheses"

    hypothesis_id: Mapped[str] = mapped_column(String, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)
    perspective: Mapped[str] = mapped_column(String, nullable=False, index=True)
    thesis: Mapped[str] = mapped_column(Text, nullable=False)
    directional_bias: Mapped[float] = mapped_column(Float, nullable=False)
    hypothesis_strength: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_fingerprint: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    invalidated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    horizon: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    as_of: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    workflow_name: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    execution_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    runtime_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    node_name: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    supporting_evidence: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    contradicting_evidence: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    key_assumptions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    invalidation_conditions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    risks: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    recommendations: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    data_quality_flags: Mapped[list[str]] = mapped_column(
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
    "idx_strategy_hypotheses_execution_node",
    StrategyHypothesisModel.execution_id,
    StrategyHypothesisModel.node_name,
)
Index(
    "idx_strategy_hypotheses_symbol_horizon_as_of",
    StrategyHypothesisModel.symbol,
    StrategyHypothesisModel.horizon,
    StrategyHypothesisModel.as_of,
)
Index(
    "idx_strategy_hypotheses_perspective_fingerprint",
    StrategyHypothesisModel.perspective,
    StrategyHypothesisModel.evidence_fingerprint,
)


class StrategySynthesisDecisionModel(Base):
    __tablename__ = "strategy_synthesis_decisions"

    decision_id: Mapped[str] = mapped_column(String, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)
    selected_perspective: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    selection_status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    directional_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    regime: Mapped[str] = mapped_column(String, nullable=False, index=True)
    uncertainty: Mapped[float] = mapped_column(Float, nullable=False)
    thesis: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_fingerprint: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    horizon: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    as_of: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    workflow_name: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    execution_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    runtime_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    node_name: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    signals: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    risks: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    recommendations: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    degraded_reasons: Mapped[list[str]] = mapped_column(
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
    "idx_strategy_decisions_execution_node",
    StrategySynthesisDecisionModel.execution_id,
    StrategySynthesisDecisionModel.node_name,
)
Index(
    "idx_strategy_decisions_symbol_horizon_as_of",
    StrategySynthesisDecisionModel.symbol,
    StrategySynthesisDecisionModel.horizon,
    StrategySynthesisDecisionModel.as_of,
)
Index(
    "idx_strategy_decisions_status_confidence",
    StrategySynthesisDecisionModel.selection_status,
    StrategySynthesisDecisionModel.confidence,
)


class StrategyHypothesisEvaluationModel(Base):
    __tablename__ = "strategy_hypothesis_evaluations"

    evaluation_id: Mapped[str] = mapped_column(String, primary_key=True)
    decision_id: Mapped[str] = mapped_column(
        ForeignKey(
            "strategy_synthesis_decisions.decision_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    hypothesis_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "strategy_hypotheses.hypothesis_id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)
    perspective: Mapped[str] = mapped_column(String, nullable=False, index=True)
    perspective_weight: Mapped[float] = mapped_column(Float, nullable=False)
    contradiction_burden: Mapped[float] = mapped_column(Float, nullable=False)
    assumption_support: Mapped[float] = mapped_column(Float, nullable=False)
    invalidated: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    candidate_score: Mapped[float] = mapped_column(Float, nullable=False)
    posterior_weight: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    selection_status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    evidence_fingerprint: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    horizon: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    as_of: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    workflow_name: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    execution_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    runtime_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    node_name: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    degraded_reasons: Mapped[list[str]] = mapped_column(
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
    "idx_strategy_evaluations_decision_perspective",
    StrategyHypothesisEvaluationModel.decision_id,
    StrategyHypothesisEvaluationModel.perspective,
)
Index(
    "idx_strategy_evaluations_execution_node",
    StrategyHypothesisEvaluationModel.execution_id,
    StrategyHypothesisEvaluationModel.node_name,
)
Index(
    "idx_strategy_evaluations_symbol_rank",
    StrategyHypothesisEvaluationModel.symbol,
    StrategyHypothesisEvaluationModel.rank,
)
