from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from math import isfinite
from uuid import uuid4

from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.lineage import require_non_empty_identifier


@dataclass(
    frozen=True,
    slots=True,
)
class TelemetryEventRecord:
    """
    Operational telemetry event persisted for observability and audit.

    Telemetry records are operational data, not curated RAG source records.
    They may carry serialized payload/metadata at the PostgreSQL boundary, but
    runtime/application code should use this typed contract internally.
    """

    telemetry_event_id: str
    event_type: str
    source: str
    timestamp: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    severity: str | None = None
    message: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    payload: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _set_required_identifier(self, "telemetry_event_id", self.telemetry_event_id)
        _set_required_identifier(self, "event_type", self.event_type)
        _set_required_identifier(self, "source", self.source)
        _set_common_optional_observability_fields(self)
        object.__setattr__(
            self,
            "severity",
            clean_optional_identifier(self.severity, "severity"),
        )
        object.__setattr__(
            self,
            "message",
            _clean_optional_text(self.message),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class TelemetryMetricRecord:
    """
    Generic operational metric observation.
    """

    metric_id: str
    metric_name: str
    source: str
    timestamp: datetime
    metric_value: float
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    metric_unit: str | None = None
    metric_kind: str | None = None
    correlation_id: str | None = None
    dimensions: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _set_required_identifier(self, "metric_id", self.metric_id)
        _set_required_identifier(self, "metric_name", self.metric_name)
        _set_required_identifier(self, "source", self.source)
        _require_finite_number(self.metric_value, "metric_value")
        object.__setattr__(
            self,
            "metric_unit",
            clean_optional_identifier(self.metric_unit, "metric_unit"),
        )
        object.__setattr__(
            self,
            "metric_kind",
            clean_optional_identifier(self.metric_kind, "metric_kind"),
        )
        object.__setattr__(
            self,
            "correlation_id",
            clean_optional_identifier(self.correlation_id, "correlation_id"),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class TelemetryTraceRecord:
    """
    Operational trace/span record.
    """

    trace_record_id: str
    trace_id: str
    span_id: str
    operation_name: str
    source: str
    started_at: datetime
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    parent_span_id: str | None = None
    ended_at: datetime | None = None
    duration_seconds: float | None = None
    status: str | None = None
    correlation_id: str | None = None
    terminal_event_id: str | None = None
    exception_type: str | None = None
    exception_message: str | None = None
    exception_stack_trace: str | None = None
    exception_stack_trace_truncated: bool = False
    attributes: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _set_required_identifier(self, "trace_record_id", self.trace_record_id)
        _set_required_identifier(self, "trace_id", self.trace_id)
        _set_required_identifier(self, "span_id", self.span_id)
        _set_required_identifier(self, "operation_name", self.operation_name)
        _set_required_identifier(self, "source", self.source)
        object.__setattr__(
            self,
            "parent_span_id",
            clean_optional_identifier(self.parent_span_id, "parent_span_id"),
        )
        object.__setattr__(
            self,
            "status",
            clean_optional_identifier(self.status, "status"),
        )
        object.__setattr__(
            self,
            "correlation_id",
            clean_optional_identifier(self.correlation_id, "correlation_id"),
        )
        object.__setattr__(
            self,
            "terminal_event_id",
            clean_optional_identifier(self.terminal_event_id, "terminal_event_id"),
        )
        object.__setattr__(
            self,
            "exception_type",
            clean_optional_identifier(self.exception_type, "exception_type"),
        )
        object.__setattr__(
            self,
            "exception_message",
            _clean_optional_text(self.exception_message),
        )
        object.__setattr__(
            self,
            "exception_stack_trace",
            _clean_optional_text(self.exception_stack_trace),
        )
        _require_optional_non_negative_number(
            self.duration_seconds,
            "duration_seconds",
        )
        _require_optional_timestamp_order(
            self.started_at,
            self.ended_at,
            "ended_at",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class WorkflowMetricRecord:
    """
    Workflow-scoped operational metric.
    """

    workflow_metric_id: str
    workflow_name: str
    metric_name: str
    timestamp: datetime
    metric_value: float
    execution_id: str | None = None
    runtime_id: str | None = None
    node_name: str | None = None
    metric_unit: str | None = None
    status: str | None = None
    duration_seconds: float | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _set_required_identifier(self, "workflow_metric_id", self.workflow_metric_id)
        _set_required_identifier(self, "workflow_name", self.workflow_name)
        _set_required_identifier(self, "metric_name", self.metric_name)
        _require_finite_number(self.metric_value, "metric_value")
        _set_optional_lineage_fields(self)
        object.__setattr__(
            self,
            "metric_unit",
            clean_optional_identifier(self.metric_unit, "metric_unit"),
        )
        object.__setattr__(
            self,
            "status",
            clean_optional_identifier(self.status, "status"),
        )
        _require_optional_non_negative_number(
            self.duration_seconds,
            "duration_seconds",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AgentMetricRecord:
    """
    Agent-scoped operational metric.
    """

    agent_metric_id: str
    agent_name: str
    agent_type: str
    metric_name: str
    timestamp: datetime
    metric_value: float
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    metric_unit: str | None = None
    model_name: str | None = None
    symbol: str | None = None
    universe: str | None = None
    correlation_id: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _set_required_identifier(self, "agent_metric_id", self.agent_metric_id)
        _set_required_identifier(self, "agent_name", self.agent_name)
        _set_required_identifier(self, "agent_type", self.agent_type)
        _set_required_identifier(self, "metric_name", self.metric_name)
        _require_finite_number(self.metric_value, "metric_value")
        object.__setattr__(
            self,
            "metric_unit",
            clean_optional_identifier(self.metric_unit, "metric_unit"),
        )
        object.__setattr__(
            self,
            "model_name",
            clean_optional_identifier(self.model_name, "model_name"),
        )
        object.__setattr__(
            self,
            "symbol",
            _clean_optional_symbol(self.symbol),
        )
        object.__setattr__(
            self,
            "universe",
            clean_optional_identifier(self.universe, "universe"),
        )
        object.__setattr__(
            self,
            "correlation_id",
            clean_optional_identifier(self.correlation_id, "correlation_id"),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ProviderMetricRecord:
    """
    External-provider operational metric.
    """

    provider_metric_id: str
    provider_name: str
    provider_type: str
    metric_name: str
    timestamp: datetime
    metric_value: float
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    metric_unit: str | None = None
    endpoint: str | None = None
    status_code: int | None = None
    success: bool | None = None
    correlation_id: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _set_required_identifier(self, "provider_metric_id", self.provider_metric_id)
        _set_required_identifier(self, "provider_name", self.provider_name)
        _set_required_identifier(self, "provider_type", self.provider_type)
        _set_required_identifier(self, "metric_name", self.metric_name)
        _require_finite_number(self.metric_value, "metric_value")
        object.__setattr__(
            self,
            "metric_unit",
            clean_optional_identifier(self.metric_unit, "metric_unit"),
        )
        object.__setattr__(
            self,
            "endpoint",
            clean_optional_identifier(self.endpoint, "endpoint"),
        )
        object.__setattr__(
            self,
            "correlation_id",
            clean_optional_identifier(self.correlation_id, "correlation_id"),
        )
        if self.status_code is not None and self.status_code < 0:
            raise ValueError("status_code cannot be negative.")


@dataclass(
    frozen=True,
    slots=True,
)
class TelemetryPersistenceBundle:
    """
    Atomic telemetry persistence payload.

    This bundle is operational observability data and must not be treated as a
    curated RAG ingestion source.
    """

    events: tuple[TelemetryEventRecord, ...] = ()
    metrics: tuple[TelemetryMetricRecord, ...] = ()
    traces: tuple[TelemetryTraceRecord, ...] = ()
    workflow_metrics: tuple[WorkflowMetricRecord, ...] = ()
    agent_metrics: tuple[AgentMetricRecord, ...] = ()
    provider_metrics: tuple[ProviderMetricRecord, ...] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class TelemetryPersistenceResult:
    """
    Typed result returned by telemetry persistence adapters.
    """

    success: bool
    records_persisted: int = 0
    primary_record_id: str | None = None
    error: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if self.records_persisted < 0:
            raise ValueError("records_persisted cannot be negative.")
        if self.success and self.error is not None:
            raise ValueError("successful persistence results cannot include an error.")
        if self.success:
            require_non_empty_identifier(self.primary_record_id, "primary_record_id")
        if not self.success:
            require_non_empty_identifier(self.error, "error")

    @classmethod
    def succeeded(
        cls,
        *,
        primary_record_id: str,
        records_persisted: int = 1,
    ) -> TelemetryPersistenceResult:
        return cls(
            success=True,
            records_persisted=records_persisted,
            primary_record_id=primary_record_id,
        )

    @classmethod
    def failed(
        cls,
        error: str,
    ) -> TelemetryPersistenceResult:
        return cls(
            success=False,
            records_persisted=0,
            error=error,
        )


def new_telemetry_event_id(
    *,
    source: str,
    event_type: str,
    timestamp: datetime,
    correlation_id: str | None = None,
) -> str:
    return _new_telemetry_id(
        prefix="telemetry_event",
        timestamp=timestamp,
        parts=(source, event_type),
        key=correlation_id,
    )


def new_telemetry_metric_id(
    *,
    source: str,
    metric_name: str,
    timestamp: datetime,
    dimensions_key: str | None = None,
) -> str:
    return _new_telemetry_id(
        prefix="telemetry_metric",
        timestamp=timestamp,
        parts=(source, metric_name),
        key=dimensions_key,
    )


def new_telemetry_trace_record_id(
    *,
    trace_id: str,
    span_id: str,
) -> str:
    clean_trace_id = require_non_empty_identifier(trace_id, "trace_id")
    clean_span_id = require_non_empty_identifier(span_id, "span_id")
    return f"telemetry_trace:{clean_trace_id}:{clean_span_id}"


def new_workflow_metric_id(
    *,
    workflow_name: str,
    metric_name: str,
    timestamp: datetime,
    execution_id: str | None = None,
) -> str:
    return _new_telemetry_id(
        prefix="workflow_metric",
        timestamp=timestamp,
        parts=(workflow_name, metric_name),
        key=execution_id,
    )


def new_agent_metric_id(
    *,
    agent_name: str,
    agent_type: str,
    metric_name: str,
    timestamp: datetime,
) -> str:
    return _new_telemetry_id(
        prefix="agent_metric",
        timestamp=timestamp,
        parts=(agent_name, agent_type, metric_name),
        key=None,
    )


def new_provider_metric_id(
    *,
    provider_name: str,
    provider_type: str,
    metric_name: str,
    timestamp: datetime,
) -> str:
    return _new_telemetry_id(
        prefix="provider_metric",
        timestamp=timestamp,
        parts=(provider_name, provider_type, metric_name),
        key=None,
    )


def new_random_telemetry_id(
    prefix: str,
) -> str:
    clean_prefix = require_non_empty_identifier(prefix, "prefix")
    return f"{clean_prefix}:{uuid4().hex}"


def _new_telemetry_id(
    *,
    prefix: str,
    timestamp: datetime,
    parts: tuple[str, ...],
    key: str | None,
) -> str:
    clean_prefix = require_non_empty_identifier(prefix, "prefix")
    clean_parts = tuple(require_non_empty_identifier(part, "id_part") for part in parts)
    clean_key = clean_optional_identifier(key, "key")
    id_parts = [
        clean_prefix,
        *clean_parts,
        timestamp.isoformat(),
    ]
    if clean_key is not None:
        id_parts.append(clean_key)

    return ":".join(id_parts)


def _set_required_identifier(
    record: object,
    field_name: str,
    value: str,
) -> None:
    object.__setattr__(
        record,
        field_name,
        require_non_empty_identifier(value, field_name),
    )


def _set_common_optional_observability_fields(
    record: TelemetryEventRecord,
) -> None:
    object.__setattr__(
        record,
        "correlation_id",
        clean_optional_identifier(record.correlation_id, "correlation_id"),
    )
    object.__setattr__(
        record,
        "trace_id",
        clean_optional_identifier(record.trace_id, "trace_id"),
    )
    object.__setattr__(
        record,
        "span_id",
        clean_optional_identifier(record.span_id, "span_id"),
    )


def _set_optional_lineage_fields(
    record: WorkflowMetricRecord,
) -> None:
    object.__setattr__(
        record,
        "execution_id",
        clean_optional_identifier(record.execution_id, "execution_id"),
    )
    object.__setattr__(
        record,
        "runtime_id",
        clean_optional_identifier(record.runtime_id, "runtime_id"),
    )
    object.__setattr__(
        record,
        "node_name",
        clean_optional_identifier(record.node_name, "node_name"),
    )


def _clean_optional_text(
    value: str | None,
) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped


def _clean_optional_symbol(
    value: str | None,
) -> str | None:
    clean_value = clean_optional_identifier(value, "symbol")
    if clean_value is None:
        return None
    return clean_value.upper()


def _require_finite_number(
    value: float,
    field_name: str,
) -> None:
    if not isfinite(value):
        raise ValueError(f"{field_name} must be finite.")


def _require_optional_non_negative_number(
    value: float | None,
    field_name: str,
) -> None:
    if value is None:
        return
    _require_finite_number(value, field_name)
    if value < 0.0:
        raise ValueError(f"{field_name} cannot be negative.")


def _require_optional_timestamp_order(
    start: datetime,
    end: datetime | None,
    end_field_name: str,
) -> None:
    if end is None:
        return
    if end < start:
        raise ValueError(f"{end_field_name} cannot be earlier than started_at.")
