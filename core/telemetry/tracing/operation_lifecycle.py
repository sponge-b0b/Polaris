from __future__ import annotations

from core.telemetry.events.telemetry_event import TelemetryEvent

_OPERATION_EVENT_PREFIXES = (
    "runtime.workflow.",
    "runtime.node.",
    "application.service.",
    "application.rag.operation.",
    "workflow_output_projection.",
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
    names_by_kind = {
        "workflow_execution": "runtime.workflow",
        "runtime_node_attempt": "runtime.node",
        "runtime_node_transition": "runtime.node",
        "application_service": "application.service",
        "application_service_attempt": "application.service",
        "provider_call": "integration.provider.call",
    }
    if isinstance(operation_kind, str) and operation_kind in names_by_kind:
        return names_by_kind[operation_kind]

    event_type = event.event_type
    if event_type.startswith("integration.provider."):
        return "integration.provider.call"
    if event_type.startswith("workflow_output_projection.projector_"):
        return "workflow_output_projection.projector"
    if event_type.startswith("workflow_output_projection.completed_run_"):
        return "workflow_output_projection.completed_run"
    if event_type.startswith("workflow_control."):
        return "runtime.workflow"
    if event_type.startswith("workflow_progress.workflow_"):
        return "runtime.workflow"
    if event_type.startswith("workflow_progress.wave_"):
        return "runtime.workflow"
    if event_type.startswith("workflow_progress.node_"):
        return "runtime.node"
    if event_type.startswith("runtime.wave."):
        return "runtime.workflow"
    for prefix in _OPERATION_EVENT_PREFIXES:
        if event_type.startswith(prefix):
            return prefix.removesuffix(".")
    return event_type


def is_terminal_operation_event(event: TelemetryEvent) -> bool:
    """Return whether the event closes its canonical operation span."""
    return event.event_type in TERMINAL_OPERATION_EVENT_TYPES


__all__ = [
    "TERMINAL_OPERATION_EVENT_TYPES",
    "is_terminal_operation_event",
    "resolve_operation_name",
]
