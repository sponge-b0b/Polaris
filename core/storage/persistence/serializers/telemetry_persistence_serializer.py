from __future__ import annotations

from typing import Any
from typing import cast

from core.database.models.telemetry import AgentMetricModel
from core.database.models.telemetry import ProviderMetricModel
from core.database.models.telemetry import TelemetryEventModel
from core.database.models.telemetry import TelemetryMetricModel
from core.database.models.telemetry import TelemetryTraceModel
from core.database.models.telemetry import WorkflowMetricModel
from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.telemetry import AgentMetricRecord
from core.storage.persistence.telemetry import ProviderMetricRecord
from core.storage.persistence.telemetry import TelemetryEventRecord
from core.storage.persistence.telemetry import TelemetryMetricRecord
from core.storage.persistence.telemetry import TelemetryTraceRecord
from core.storage.persistence.telemetry import WorkflowMetricRecord


class TelemetryPersistenceSerializer:
    """
    Serializer between typed telemetry persistence records and PostgreSQL models.

    Telemetry payloads, dimensions, attributes, and metadata become dictionaries
    only at this persistence boundary. Runtime and application layers should use
    the typed telemetry records from ``core.storage.persistence.telemetry``.
    """

    @staticmethod
    def event_values(
        record: TelemetryEventRecord,
    ) -> dict[str, Any]:
        return {
            "telemetry_event_id": record.telemetry_event_id,
            "event_type": record.event_type,
            "source": record.source,
            "timestamp": record.timestamp,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "severity": record.severity,
            "message": record.message,
            "correlation_id": record.correlation_id,
            "trace_id": record.trace_id,
            "span_id": record.span_id,
            "payload": dict(record.payload),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def metric_values(
        record: TelemetryMetricRecord,
    ) -> dict[str, Any]:
        return {
            "metric_id": record.metric_id,
            "metric_name": record.metric_name,
            "source": record.source,
            "timestamp": record.timestamp,
            "metric_value": record.metric_value,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metric_unit": record.metric_unit,
            "metric_kind": record.metric_kind,
            "correlation_id": record.correlation_id,
            "dimensions": dict(record.dimensions),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def trace_values(
        record: TelemetryTraceRecord,
    ) -> dict[str, Any]:
        return {
            "trace_record_id": record.trace_record_id,
            "trace_id": record.trace_id,
            "span_id": record.span_id,
            "operation_name": record.operation_name,
            "source": record.source,
            "started_at": record.started_at,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "parent_span_id": record.parent_span_id,
            "ended_at": record.ended_at,
            "duration_seconds": record.duration_seconds,
            "status": record.status,
            "correlation_id": record.correlation_id,
            "terminal_event_id": record.terminal_event_id,
            "exception_type": record.exception_type,
            "exception_message": record.exception_message,
            "exception_stack_trace": record.exception_stack_trace,
            "exception_stack_trace_truncated": (record.exception_stack_trace_truncated),
            "attributes": dict(record.attributes),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def workflow_metric_values(
        record: WorkflowMetricRecord,
    ) -> dict[str, Any]:
        return {
            "workflow_metric_id": record.workflow_metric_id,
            "workflow_name": record.workflow_name,
            "metric_name": record.metric_name,
            "timestamp": record.timestamp,
            "metric_value": record.metric_value,
            "execution_id": record.execution_id,
            "runtime_id": record.runtime_id,
            "node_name": record.node_name,
            "metric_unit": record.metric_unit,
            "status": record.status,
            "duration_seconds": record.duration_seconds,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def agent_metric_values(
        record: AgentMetricRecord,
    ) -> dict[str, Any]:
        return {
            "agent_metric_id": record.agent_metric_id,
            "agent_name": record.agent_name,
            "agent_type": record.agent_type,
            "metric_name": record.metric_name,
            "timestamp": record.timestamp,
            "metric_value": record.metric_value,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metric_unit": record.metric_unit,
            "model_name": record.model_name,
            "symbol": record.symbol,
            "universe": record.universe,
            "correlation_id": record.correlation_id,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def provider_metric_values(
        record: ProviderMetricRecord,
    ) -> dict[str, Any]:
        return {
            "provider_metric_id": record.provider_metric_id,
            "provider_name": record.provider_name,
            "provider_type": record.provider_type,
            "metric_name": record.metric_name,
            "timestamp": record.timestamp,
            "metric_value": record.metric_value,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metric_unit": record.metric_unit,
            "endpoint": record.endpoint,
            "status_code": record.status_code,
            "success": record.success,
            "correlation_id": record.correlation_id,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def event_from_model(
        model: TelemetryEventModel,
    ) -> TelemetryEventRecord:
        return TelemetryEventRecord(
            telemetry_event_id=model.telemetry_event_id,
            event_type=model.event_type,
            source=model.source,
            timestamp=model.timestamp,
            lineage=_lineage_from_model(model),
            severity=model.severity,
            message=model.message,
            correlation_id=model.correlation_id,
            trace_id=model.trace_id,
            span_id=model.span_id,
            payload=cast(JsonObject, model.payload),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def metric_from_model(
        model: TelemetryMetricModel,
    ) -> TelemetryMetricRecord:
        return TelemetryMetricRecord(
            metric_id=model.metric_id,
            metric_name=model.metric_name,
            source=model.source,
            timestamp=model.timestamp,
            metric_value=model.metric_value,
            lineage=_lineage_from_model(model),
            metric_unit=model.metric_unit,
            metric_kind=model.metric_kind,
            correlation_id=model.correlation_id,
            dimensions=cast(JsonObject, model.dimensions),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def trace_from_model(
        model: TelemetryTraceModel,
    ) -> TelemetryTraceRecord:
        return TelemetryTraceRecord(
            trace_record_id=model.trace_record_id,
            trace_id=model.trace_id,
            span_id=model.span_id,
            operation_name=model.operation_name,
            source=model.source,
            started_at=model.started_at,
            lineage=_lineage_from_model(model),
            parent_span_id=model.parent_span_id,
            ended_at=model.ended_at,
            duration_seconds=model.duration_seconds,
            status=model.status,
            correlation_id=model.correlation_id,
            terminal_event_id=model.terminal_event_id,
            exception_type=model.exception_type,
            exception_message=model.exception_message,
            exception_stack_trace=model.exception_stack_trace,
            exception_stack_trace_truncated=(model.exception_stack_trace_truncated),
            attributes=cast(JsonObject, model.attributes),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def workflow_metric_from_model(
        model: WorkflowMetricModel,
    ) -> WorkflowMetricRecord:
        return WorkflowMetricRecord(
            workflow_metric_id=model.workflow_metric_id,
            workflow_name=model.workflow_name,
            metric_name=model.metric_name,
            timestamp=model.timestamp,
            metric_value=model.metric_value,
            execution_id=model.execution_id,
            runtime_id=model.runtime_id,
            node_name=model.node_name,
            metric_unit=model.metric_unit,
            status=model.status,
            duration_seconds=model.duration_seconds,
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def agent_metric_from_model(
        model: AgentMetricModel,
    ) -> AgentMetricRecord:
        return AgentMetricRecord(
            agent_metric_id=model.agent_metric_id,
            agent_name=model.agent_name,
            agent_type=model.agent_type,
            metric_name=model.metric_name,
            timestamp=model.timestamp,
            metric_value=model.metric_value,
            lineage=_lineage_from_model(model),
            metric_unit=model.metric_unit,
            model_name=model.model_name,
            symbol=model.symbol,
            universe=model.universe,
            correlation_id=model.correlation_id,
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def provider_metric_from_model(
        model: ProviderMetricModel,
    ) -> ProviderMetricRecord:
        return ProviderMetricRecord(
            provider_metric_id=model.provider_metric_id,
            provider_name=model.provider_name,
            provider_type=model.provider_type,
            metric_name=model.metric_name,
            timestamp=model.timestamp,
            metric_value=model.metric_value,
            lineage=_lineage_from_model(model),
            metric_unit=model.metric_unit,
            endpoint=model.endpoint,
            status_code=model.status_code,
            success=model.success,
            correlation_id=model.correlation_id,
            metadata=cast(JsonObject, model.metadata_payload),
        )


def _lineage_from_model(
    model: TelemetryEventModel
    | TelemetryMetricModel
    | TelemetryTraceModel
    | AgentMetricModel
    | ProviderMetricModel,
) -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name=model.workflow_name,
        execution_id=model.execution_id,
        runtime_id=model.runtime_id,
        node_name=model.node_name,
    )
