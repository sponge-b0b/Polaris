from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base

DECIMAL_NUMERIC = Numeric(
    38,
    18,
)


class BacktestScenarioModel(Base):
    __tablename__ = "backtest_scenarios"

    scenario_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    workflow_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    symbols: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    benchmark_symbol: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    initial_cash: Mapped[Decimal] = mapped_column(
        DECIMAL_NUMERIC,
        nullable=False,
    )
    provider_profile: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    initial_positions: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    expected_outcomes: Mapped[list[Any]] = mapped_column(
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
    "idx_backtest_scenarios_workflow_dates",
    BacktestScenarioModel.workflow_name,
    BacktestScenarioModel.start_date,
    BacktestScenarioModel.end_date,
)


class BacktestRunModel(Base):
    __tablename__ = "backtest_runs"

    backtest_run_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    scenario_id: Mapped[str] = mapped_column(
        ForeignKey(
            "backtest_scenarios.scenario_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )
    workflow_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    metrics_payload: Mapped[dict[str, Any]] = mapped_column(
        "metrics",
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
    "idx_backtest_runs_workflow_started_at",
    BacktestRunModel.workflow_name,
    BacktestRunModel.started_at,
)


class BacktestStepModel(Base):
    __tablename__ = "backtest_steps"
    __table_args__ = (
        UniqueConstraint(
            "backtest_run_id",
            "step_index",
            name="uq_backtest_steps_run_step_index",
        ),
    )

    step_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    backtest_run_id: Mapped[str] = mapped_column(
        ForeignKey(
            "backtest_runs.backtest_run_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    step_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    workflow_run_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
    )
    node_output_keys: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    summary_payload: Mapped[dict[str, Any]] = mapped_column(
        "summary",
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
    "idx_backtest_steps_run_timestamp",
    BacktestStepModel.backtest_run_id,
    BacktestStepModel.timestamp,
)


class BacktestPortfolioSnapshotModel(Base):
    __tablename__ = "backtest_portfolio_snapshots"

    snapshot_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    backtest_run_id: Mapped[str] = mapped_column(
        ForeignKey(
            "backtest_runs.backtest_run_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    step_id: Mapped[str] = mapped_column(
        ForeignKey(
            "backtest_steps.step_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    cash: Mapped[Decimal] = mapped_column(
        DECIMAL_NUMERIC,
        nullable=False,
    )
    equity: Mapped[Decimal] = mapped_column(
        DECIMAL_NUMERIC,
        nullable=False,
    )
    market_value: Mapped[Decimal] = mapped_column(
        DECIMAL_NUMERIC,
        nullable=False,
    )
    positions: Mapped[dict[str, Any]] = mapped_column(
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


class BacktestFillModel(Base):
    __tablename__ = "backtest_fills"

    fill_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    backtest_run_id: Mapped[str] = mapped_column(
        ForeignKey(
            "backtest_runs.backtest_run_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    step_id: Mapped[str] = mapped_column(
        ForeignKey(
            "backtest_steps.step_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    side: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(
        DECIMAL_NUMERIC,
        nullable=False,
    )
    price: Mapped[Decimal] = mapped_column(
        DECIMAL_NUMERIC,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    realized_pnl: Mapped[Decimal] = mapped_column(
        DECIMAL_NUMERIC,
        nullable=False,
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
    "idx_backtest_fills_run_symbol",
    BacktestFillModel.backtest_run_id,
    BacktestFillModel.symbol,
)


class BacktestMetricModel(Base):
    __tablename__ = "backtest_metrics"
    __table_args__ = (
        UniqueConstraint(
            "backtest_run_id",
            "metric_name",
            name="uq_backtest_metrics_run_metric",
        ),
    )

    metric_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    backtest_run_id: Mapped[str] = mapped_column(
        ForeignKey(
            "backtest_runs.backtest_run_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    metric_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    metric_value: Mapped[Decimal] = mapped_column(
        DECIMAL_NUMERIC,
        nullable=False,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
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


class BacktestArtifactModel(Base):
    __tablename__ = "backtest_artifacts"
    __table_args__ = (
        UniqueConstraint(
            "backtest_run_id",
            "artifact_format",
            name="uq_backtest_artifacts_run_format",
        ),
    )

    artifact_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    backtest_run_id: Mapped[str] = mapped_column(
        ForeignKey(
            "backtest_runs.backtest_run_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    artifact_format: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    mime_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
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
