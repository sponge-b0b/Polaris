from __future__ import annotations

from core.telemetry.events.telemetry_event import TelemetryEvent

_OPERATION_NAMES_BY_KIND = {
    "workflow_execution": "runtime.workflow",
    "runtime_node_attempt": "runtime.node",
    "runtime_node_transition": "runtime.node",
    "application_service": "application.service",
    "application_service_attempt": "application.service",
    "provider_call": "integration.provider.call",
}

_EVENT_TYPE_OPERATION_PREFIXES = (
    ("integration.provider.", "integration.provider.call"),
    (
        "workflow_output_projection.projector_",
        "workflow_output_projection.projector",
    ),
    (
        "workflow_output_projection.completed_run_",
        "workflow_output_projection.completed_run",
    ),
    ("workflow_control.", "runtime.workflow"),
    ("workflow_progress.workflow_", "runtime.workflow"),
    ("workflow_progress.wave_", "runtime.workflow"),
    ("workflow_progress.node_", "runtime.node"),
    ("runtime.wave.", "runtime.workflow"),
    ("runtime.workflow.", "runtime.workflow"),
    ("runtime.node.", "runtime.node"),
    ("application.service.", "application.service"),
    ("application.rag.operation.", "application.rag.operation"),
    ("workflow_output_projection.", "workflow_output_projection"),
)

TERMINAL_OPERATION_EVENT_TYPES = frozenset(
    {
        "runtime.workflow.completed",
        "runtime.workflow.failed",
        "runtime.node.completed",
        "runtime.node.failed",
        "runtime.node.skipped",
        "application.service.completed",
        "application.service.failed",
        "application.service.configuration_failed",
        "application.service.cancelled",
        "application.rag.operation.completed",
        "application.rag.operation.failed",
        "workflow_output_projection.completed_run_finished",
        "workflow_output_projection.completed_run_failed",
        "workflow_output_projection.completed_run_not_found",
        "workflow_output_projection.projector_completed",
        "workflow_output_projection.projector_failed",
        "workflow_output_projection.projector_skipped",
        "integration.provider.call",
        "integration.provider.cancelled",
    }
)


def resolve_operation_name(event: TelemetryEvent) -> str:
    """Return the stable operation name shared by span lifecycle projections."""
    operation_kind = event.attributes.get("operation_kind")
    if isinstance(operation_kind, str) and operation_kind in _OPERATION_NAMES_BY_KIND:
        return _OPERATION_NAMES_BY_KIND[operation_kind]

    return _resolve_event_type_operation_name(
        event.event_type,
    )


def _resolve_event_type_operation_name(
    event_type: str,
) -> str:
    for prefix, operation_name in _EVENT_TYPE_OPERATION_PREFIXES:
        if event_type.startswith(prefix):
            return operation_name
    return event_type


def is_terminal_operation_event(event: TelemetryEvent) -> bool:
    """Return whether the event closes its canonical operation span."""
    return event.event_type in TERMINAL_OPERATION_EVENT_TYPES


__all__ = [
    "TERMINAL_OPERATION_EVENT_TYPES",
    "is_terminal_operation_event",
    "resolve_operation_name",
]
