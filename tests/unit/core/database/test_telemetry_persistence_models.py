from __future__ import annotations

from typing import cast

from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import JSONB

from core.database.base import Base
from core.database.models.telemetry import AgentMetricModel
from core.database.models.telemetry import ProviderMetricModel
from core.database.models.telemetry import TelemetryEventModel
from core.database.models.telemetry import TelemetryMetricModel
from core.database.models.telemetry import TelemetryTraceModel
from core.database.models.telemetry import WorkflowMetricModel


def _index_names(table: Table) -> set[str]:
    return {str(index.name) for index in table.indexes}


def _constraint_names(table: Table) -> set[str]:
    return {
        str(constraint.name)
        for constraint in table.constraints
        if constraint.name is not None
    }


def test_telemetry_models_are_imported_into_base_metadata() -> None:
    assert "telemetry_events" in Base.metadata.tables
    assert "telemetry_metrics" in Base.metadata.tables
    assert "telemetry_traces" in Base.metadata.tables
    assert "workflow_metrics" in Base.metadata.tables
    assert "agent_metrics" in Base.metadata.tables
    assert "provider_metrics" in Base.metadata.tables


def test_telemetry_event_model_persists_event_payload_and_lineage() -> None:
    table = cast(Table, TelemetryEventModel.__table__)
    columns = table.c
    primary_keys = {column.name for column in table.primary_key}
    index_names = _index_names(table)

    assert primary_keys == {"telemetry_event_id"}
    assert columns.event_type.nullable is False
    assert columns.source.nullable is False
    assert columns.timestamp.nullable is False
    assert columns.workflow_name.nullable is True
    assert columns.execution_id.nullable is True
    assert columns.runtime_id.nullable is True
    assert columns.node_name.nullable is True
    assert columns.correlation_id.nullable is True
    assert columns.trace_id.nullable is True
    assert columns.span_id.nullable is True
    assert isinstance(columns.payload.type, JSONB)
    assert isinstance(columns.metadata.type, JSONB)
    assert "idx_telemetry_events_timestamp_type" in index_names
    assert "idx_telemetry_events_source_timestamp" in index_names
    assert "idx_telemetry_events_workflow_execution" in index_names
    assert "idx_telemetry_events_correlation_timestamp" in index_names
    assert "idx_telemetry_events_trace_span" in index_names
    assert columns.row_created_at.server_default is not None
    assert columns.row_updated_at.server_default is not None


def test_telemetry_metric_model_persists_dimensions_and_query_fields() -> None:
    table = cast(Table, TelemetryMetricModel.__table__)
    columns = table.c
    primary_keys = {column.name for column in table.primary_key}
    index_names = _index_names(table)

    assert primary_keys == {"metric_id"}
    assert columns.metric_name.nullable is False
    assert columns.source.nullable is False
    assert columns.timestamp.nullable is False
    assert columns.metric_value.nullable is False
    assert columns.metric_kind.nullable is True
    assert columns.correlation_id.nullable is True
    assert isinstance(columns.dimensions.type, JSONB)
    assert isinstance(columns.metadata.type, JSONB)
    assert "idx_telemetry_metrics_name_timestamp" in index_names
    assert "idx_telemetry_metrics_source_timestamp" in index_names
    assert "idx_telemetry_metrics_workflow_execution" in index_names
    assert "idx_telemetry_metrics_correlation_timestamp" in index_names
    assert columns.row_created_at.server_default is not None
    assert columns.row_updated_at.server_default is not None


def test_telemetry_trace_model_persists_trace_span_and_validation() -> None:
    table = cast(Table, TelemetryTraceModel.__table__)
    columns = table.c
    primary_keys = {column.name for column in table.primary_key}
    index_names = _index_names(table)
    constraint_names = _constraint_names(table)

    assert primary_keys == {"trace_record_id"}
    assert columns.trace_id.nullable is False
    assert columns.span_id.nullable is False
    assert columns.operation_name.nullable is False
    assert columns.source.nullable is False
    assert columns.started_at.nullable is False
    assert columns.ended_at.nullable is True
    assert columns.duration_seconds.nullable is True
    assert columns.status.nullable is True
    assert columns.terminal_event_id.nullable is True
    assert columns.exception_type.nullable is True
    assert columns.exception_message.nullable is True
    assert columns.exception_stack_trace.nullable is True
    assert columns.exception_stack_trace_truncated.nullable is False
    assert isinstance(columns.attributes.type, JSONB)
    assert isinstance(columns.metadata.type, JSONB)
    assert "ck_telemetry_traces_duration_non_negative" in constraint_names
    assert "ck_telemetry_traces_ended_at_not_before_started_at" in constraint_names
    assert "uq_telemetry_traces_trace_span" in constraint_names
    assert "idx_telemetry_traces_trace_span" not in index_names
    assert "idx_telemetry_traces_source_started_at" in index_names
    assert "idx_telemetry_traces_operation_started_at" in index_names
    assert "idx_telemetry_traces_workflow_execution" in index_names
    assert "idx_telemetry_traces_correlation_started_at" in index_names


def test_workflow_metric_model_persists_workflow_scoped_metrics() -> None:
    table = cast(Table, WorkflowMetricModel.__table__)
    columns = table.c
    primary_keys = {column.name for column in table.primary_key}
    index_names = _index_names(table)
    constraint_names = _constraint_names(table)

    assert primary_keys == {"workflow_metric_id"}
    assert columns.workflow_name.nullable is False
    assert columns.metric_name.nullable is False
    assert columns.timestamp.nullable is False
    assert columns.metric_value.nullable is False
    assert columns.execution_id.nullable is True
    assert columns.runtime_id.nullable is True
    assert columns.node_name.nullable is True
    assert isinstance(columns.metadata.type, JSONB)
    assert "ck_workflow_metrics_duration_non_negative" in constraint_names
    assert "idx_workflow_metrics_workflow_metric_timestamp" in index_names
    assert "idx_workflow_metrics_workflow_execution" in index_names
    assert "idx_workflow_metrics_status_timestamp" in index_names


def test_agent_metric_model_persists_agent_scoped_metrics() -> None:
    table = cast(Table, AgentMetricModel.__table__)
    columns = table.c
    primary_keys = {column.name for column in table.primary_key}
    index_names = _index_names(table)

    assert primary_keys == {"agent_metric_id"}
    assert columns.agent_name.nullable is False
    assert columns.agent_type.nullable is False
    assert columns.metric_name.nullable is False
    assert columns.timestamp.nullable is False
    assert columns.metric_value.nullable is False
    assert columns.model_name.nullable is True
    assert columns.symbol.nullable is True
    assert columns.universe.nullable is True
    assert columns.correlation_id.nullable is True
    assert isinstance(columns.metadata.type, JSONB)
    assert "idx_agent_metrics_agent_metric_timestamp" in index_names
    assert "idx_agent_metrics_type_metric_timestamp" in index_names
    assert "idx_agent_metrics_workflow_execution" in index_names
    assert "idx_agent_metrics_correlation_timestamp" in index_names
    assert "idx_agent_metrics_symbol_timestamp" in index_names


def test_provider_metric_model_persists_provider_scoped_metrics() -> None:
    table = cast(Table, ProviderMetricModel.__table__)
    columns = table.c
    primary_keys = {column.name for column in table.primary_key}
    index_names = _index_names(table)
    constraint_names = _constraint_names(table)

    assert primary_keys == {"provider_metric_id"}
    assert columns.provider_name.nullable is False
    assert columns.provider_type.nullable is False
    assert columns.metric_name.nullable is False
    assert columns.timestamp.nullable is False
    assert columns.metric_value.nullable is False
    assert columns.endpoint.nullable is True
    assert columns.status_code.nullable is True
    assert columns.success.nullable is True
    assert columns.correlation_id.nullable is True
    assert isinstance(columns.metadata.type, JSONB)
    assert "ck_provider_metrics_status_code_non_negative" in constraint_names
    assert "idx_provider_metrics_provider_metric_timestamp" in index_names
    assert "idx_provider_metrics_type_metric_timestamp" in index_names
    assert "idx_provider_metrics_workflow_execution" in index_names
    assert "idx_provider_metrics_correlation_timestamp" in index_names
    assert "idx_provider_metrics_endpoint_timestamp" in index_names
