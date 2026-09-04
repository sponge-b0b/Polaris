from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base


class AgentSignalModel(Base):
    __tablename__ = "agent_signals"

    signal_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
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
    symbol: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    universe: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    directional_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    regime: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    signal_payload: Mapped[dict[str, Any]] = mapped_column(
        "signals",
        JSONB,
        nullable=False,
        default=dict,
    )
    risk_payload: Mapped[dict[str, Any]] = mapped_column(
        "risks",
        JSONB,
        nullable=False,
        default=dict,
    )
    recommendation_payload: Mapped[dict[str, Any]] = mapped_column(
        "recommendations",
        JSONB,
        nullable=False,
        default=dict,
    )
    feature_payload: Mapped[dict[str, Any]] = mapped_column(
        "features",
        JSONB,
        nullable=False,
        default=dict,
    )
    reasoning_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    llm_response: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
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
    "idx_agent_signals_workflow_execution",
    AgentSignalModel.workflow_name,
    AgentSignalModel.execution_id,
)

Index(
    "idx_agent_signals_agent_timestamp",
    AgentSignalModel.agent_name,
    AgentSignalModel.timestamp,
)

Index(
    "idx_agent_signals_type_timestamp",
    AgentSignalModel.agent_type,
    AgentSignalModel.timestamp,
)

Index(
    "idx_agent_signals_symbol_timestamp",
    AgentSignalModel.symbol,
    AgentSignalModel.timestamp,
)
