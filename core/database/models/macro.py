from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Index
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from core.database.base import Base


class MacroObservationModel(Base):
    __tablename__ = "macro_observations"
    __table_args__ = (
        UniqueConstraint(
            "indicator_name",
            "observation_timestamp",
            "source",
            "region",
            name="uq_macro_observations_indicator_timestamp_source_region",
        ),
    )

    observation_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    indicator_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    observation_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    indicator_category: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    region: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    unit: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    frequency: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    release_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    vintage_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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
    "idx_macro_observations_indicator_timestamp",
    MacroObservationModel.indicator_name,
    MacroObservationModel.observation_timestamp,
)
Index(
    "idx_macro_observations_category_timestamp",
    MacroObservationModel.indicator_category,
    MacroObservationModel.observation_timestamp,
)
Index(
    "idx_macro_observations_source_timestamp",
    MacroObservationModel.source,
    MacroObservationModel.observation_timestamp,
)
Index(
    "idx_macro_observations_workflow_execution",
    MacroObservationModel.workflow_name,
    MacroObservationModel.execution_id,
)


class MacroRegimeSnapshotModel(Base):
    __tablename__ = "macro_regime_snapshots"

    regime_snapshot_id: Mapped[str] = mapped_column(
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
    region: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    inflation_regime: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    liquidity_regime: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    growth_regime: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    fed_stance: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    yield_curve_regime: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    market_bias: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    summary: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    macro_regime: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    economic_regime: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    inflation_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    liquidity_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    growth_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    yield_curve_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    macro_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    inputs: Mapped[dict[str, Any]] = mapped_column(
        "macro_data_payload",
        JSONB,
        nullable=False,
        default=dict,
    )
    inflation_analysis_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    fed_analysis_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    liquidity_analysis_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    yield_curve_analysis_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    outputs: Mapped[dict[str, Any]] = mapped_column(
        "economic_regime_payload",
        JSONB,
        nullable=False,
        default=dict,
    )
    components_payload: Mapped[dict[str, Any]] = mapped_column(
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
    "idx_macro_regime_snapshots_timestamp_source",
    MacroRegimeSnapshotModel.timestamp,
    MacroRegimeSnapshotModel.source,
)
Index(
    "idx_macro_regime_snapshots_region_timestamp",
    MacroRegimeSnapshotModel.region,
    MacroRegimeSnapshotModel.timestamp,
)
Index(
    "idx_macro_regime_snapshots_regime_timestamp",
    MacroRegimeSnapshotModel.macro_regime,
    MacroRegimeSnapshotModel.timestamp,
)
Index(
    "idx_macro_regime_snapshots_workflow_execution",
    MacroRegimeSnapshotModel.workflow_name,
    MacroRegimeSnapshotModel.execution_id,
)


class EconomicCalendarEventModel(Base):
    __tablename__ = "economic_calendar_events"
    __table_args__ = (
        UniqueConstraint(
            "event_name",
            "event_timestamp",
            "source",
            "region",
            name="uq_economic_calendar_events_name_timestamp_source_region",
        ),
    )

    event_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    event_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    region: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    event_type: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    importance_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    actual_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    forecast_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    previous_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    surprise_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    unit: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    currency: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    release_status: Mapped[str | None] = mapped_column(
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
    "idx_economic_calendar_events_name_timestamp",
    EconomicCalendarEventModel.event_name,
    EconomicCalendarEventModel.event_timestamp,
)
Index(
    "idx_economic_calendar_events_source_timestamp",
    EconomicCalendarEventModel.source,
    EconomicCalendarEventModel.event_timestamp,
)
Index(
    "idx_economic_calendar_events_region_timestamp",
    EconomicCalendarEventModel.region,
    EconomicCalendarEventModel.event_timestamp,
)
Index(
    "idx_economic_calendar_events_type_timestamp",
    EconomicCalendarEventModel.event_type,
    EconomicCalendarEventModel.event_timestamp,
)
Index(
    "idx_economic_calendar_events_workflow_execution",
    EconomicCalendarEventModel.workflow_name,
    EconomicCalendarEventModel.execution_id,
)
