from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from core.database.base import Base


class TelemetryEventModel(Base):
    __tablename__ = "telemetry_events"

    telemetry_event_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    event_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
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
    severity: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    correlation_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    trace_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    span_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
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
    "idx_telemetry_events_timestamp_type",
    TelemetryEventModel.timestamp,
    TelemetryEventModel.event_type,
)
Index(
    "idx_telemetry_events_source_timestamp",
    TelemetryEventModel.source,
    TelemetryEventModel.timestamp,
)
Index(
    "idx_telemetry_events_workflow_execution",
    TelemetryEventModel.workflow_name,
    TelemetryEventModel.execution_id,
)
Index(
    "idx_telemetry_events_correlation_timestamp",
    TelemetryEventModel.correlation_id,
    TelemetryEventModel.timestamp,
)
Index(
    "idx_telemetry_events_trace_span",
    TelemetryEventModel.trace_id,
    TelemetryEventModel.span_id,
)


class TelemetryMetricModel(Base):
    __tablename__ = "telemetry_metrics"

    metric_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    metric_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    metric_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
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
    metric_unit: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    metric_kind: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    correlation_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    dimensions: Mapped[dict[str, Any]] = mapped_column(
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
    "idx_telemetry_metrics_name_timestamp",
    TelemetryMetricModel.metric_name,
    TelemetryMetricModel.timestamp,
)
Index(
    "idx_telemetry_metrics_source_timestamp",
    TelemetryMetricModel.source,
    TelemetryMetricModel.timestamp,
)
Index(
    "idx_telemetry_metrics_workflow_execution",
    TelemetryMetricModel.workflow_name,
    TelemetryMetricModel.execution_id,
)
Index(
    "idx_telemetry_metrics_correlation_timestamp",
    TelemetryMetricModel.correlation_id,
    TelemetryMetricModel.timestamp,
)


class TelemetryTraceModel(Base):
    __tablename__ = "telemetry_traces"
    __table_args__ = (
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_telemetry_traces_duration_non_negative",
        ),
        CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="ck_telemetry_traces_ended_at_not_before_started_at",
        ),
        UniqueConstraint(
            "trace_id",
            "span_id",
            name="uq_telemetry_traces_trace_span",
        ),
    )

    trace_record_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    trace_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    span_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    operation_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
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
    parent_span_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    status: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    correlation_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    terminal_event_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    exception_type: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    exception_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    exception_stack_trace: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    exception_stack_trace_truncated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    attributes: Mapped[dict[str, Any]] = mapped_column(
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
    "idx_telemetry_traces_source_started_at",
    TelemetryTraceModel.source,
    TelemetryTraceModel.started_at,
)
Index(
    "idx_telemetry_traces_operation_started_at",
    TelemetryTraceModel.operation_name,
    TelemetryTraceModel.started_at,
)
Index(
    "idx_telemetry_traces_workflow_execution",
    TelemetryTraceModel.workflow_name,
    TelemetryTraceModel.execution_id,
)
Index(
    "idx_telemetry_traces_correlation_started_at",
    TelemetryTraceModel.correlation_id,
    TelemetryTraceModel.started_at,
)


class WorkflowMetricModel(Base):
    __tablename__ = "workflow_metrics"
    __table_args__ = (
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_workflow_metrics_duration_non_negative",
        ),
    )

    workflow_metric_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    workflow_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    metric_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    metric_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
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
    metric_unit: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    status: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
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
    "idx_workflow_metrics_workflow_metric_timestamp",
    WorkflowMetricModel.workflow_name,
    WorkflowMetricModel.metric_name,
    WorkflowMetricModel.timestamp,
)
Index(
    "idx_workflow_metrics_workflow_execution",
    WorkflowMetricModel.workflow_name,
    WorkflowMetricModel.execution_id,
)
Index(
    "idx_workflow_metrics_status_timestamp",
    WorkflowMetricModel.status,
    WorkflowMetricModel.timestamp,
)


class AgentMetricModel(Base):
    __tablename__ = "agent_metrics"

    agent_metric_id: Mapped[str] = mapped_column(
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
    metric_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    metric_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
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
    metric_unit: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    model_name: Mapped[str | None] = mapped_column(
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
    correlation_id: Mapped[str | None] = mapped_column(
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
    "idx_agent_metrics_agent_metric_timestamp",
    AgentMetricModel.agent_name,
    AgentMetricModel.metric_name,
    AgentMetricModel.timestamp,
)
Index(
    "idx_agent_metrics_type_metric_timestamp",
    AgentMetricModel.agent_type,
    AgentMetricModel.metric_name,
    AgentMetricModel.timestamp,
)
Index(
    "idx_agent_metrics_workflow_execution",
    AgentMetricModel.workflow_name,
    AgentMetricModel.execution_id,
)
Index(
    "idx_agent_metrics_correlation_timestamp",
    AgentMetricModel.correlation_id,
    AgentMetricModel.timestamp,
)
Index(
    "idx_agent_metrics_symbol_timestamp",
    AgentMetricModel.symbol,
    AgentMetricModel.timestamp,
)


class ProviderMetricModel(Base):
    __tablename__ = "provider_metrics"
    __table_args__ = (
        CheckConstraint(
            "status_code IS NULL OR status_code >= 0",
            name="ck_provider_metrics_status_code_non_negative",
        ),
    )

    provider_metric_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    provider_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    provider_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    metric_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    metric_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
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
    metric_unit: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    endpoint: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    status_code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )
    success: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        index=True,
    )
    correlation_id: Mapped[str | None] = mapped_column(
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
    "idx_provider_metrics_provider_metric_timestamp",
    ProviderMetricModel.provider_name,
    ProviderMetricModel.metric_name,
    ProviderMetricModel.timestamp,
)
Index(
    "idx_provider_metrics_type_metric_timestamp",
    ProviderMetricModel.provider_type,
    ProviderMetricModel.metric_name,
    ProviderMetricModel.timestamp,
)
Index(
    "idx_provider_metrics_workflow_execution",
    ProviderMetricModel.workflow_name,
    ProviderMetricModel.execution_id,
)
Index(
    "idx_provider_metrics_correlation_timestamp",
    ProviderMetricModel.correlation_id,
    ProviderMetricModel.timestamp,
)
Index(
    "idx_provider_metrics_endpoint_timestamp",
    ProviderMetricModel.endpoint,
    ProviderMetricModel.timestamp,
)
