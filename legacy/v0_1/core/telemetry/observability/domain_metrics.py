from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.telemetry.events.telemetry_event import TelemetryEvent
from core.telemetry.metrics.metrics_store import MetricsStore

_OPERATIONAL_COUNTERS: dict[str, tuple[str, str]] = {
    "application.service.configuration_failed": (
        "application.service.configuration_failures",
        "failed",
    ),
    "application.service.retry_scheduled": (
        "application.service.retries",
        "retry_scheduled",
    ),
    "application.service.degraded": (
        "application.service.degraded",
        "degraded",
    ),
    "integration.client.retry_scheduled": (
        "integration.client.retries",
        "retry_scheduled",
    ),
    "plugin.lifecycle.hook_failed": (
        "plugin.lifecycle.callback_failures",
        "failed",
    ),
    "runtime.lifecycle.hook_failed": (
        "runtime.lifecycle.callback_failures",
        "failed",
    ),
    "platform.bootstrap.configuration_failed": (
        "platform.bootstrap.configuration_failures",
        "failed",
    ),
}


class DomainMetricsRecorder:
    """Map canonical telemetry events to stable operational metrics."""

    def record(
        self,
        event: TelemetryEvent,
        metrics_store: MetricsStore,
    ) -> None:
        if self._record_operational_event(event, metrics_store):
            return
        if self._record_workflow_event(event, metrics_store):
            return
        if self._record_runtime_node_event(event, metrics_store):
            return
        if self._record_application_service_event(event, metrics_store):
            return
        if self._record_rag_event(event, metrics_store):
            return
        if self._record_provider_event(event, metrics_store):
            return

        if event.event_type == "intelligence.agent.signal":
            self._increment(
                metrics_store,
                event,
                "intelligence.agent.signals.total",
            )

    def _record_operational_event(
        self,
        event: TelemetryEvent,
        metrics_store: MetricsStore,
    ) -> bool:
        metric = _OPERATIONAL_COUNTERS.get(event.event_type)
        if metric is not None:
            metric_name, outcome = metric
            self._increment(
                metrics_store,
                event,
                metric_name,
                attributes={
                    "outcome": outcome,
                    **self._operational_attributes(event),
                },
            )
            return True

        if not self._is_event_bus_subscriber_failure(event):
            return False

        runtime_event = self._nested_runtime_event(event)
        nested_payload = runtime_event.get("payload", {})
        self._increment(
            metrics_store,
            event,
            "runtime.event_bus.subscriber_failures",
            attributes={
                "component_name": "EventBus",
                "operation": nested_payload.get("failed_event_type", "dispatch"),
                "outcome": "failed",
            },
        )
        return True

    def _record_workflow_event(
        self,
        event: TelemetryEvent,
        metrics_store: MetricsStore,
    ) -> bool:
        if event.event_type == "runtime.workflow.started":
            self._increment(metrics_store, event, "workflow.executions.total")
            return True

        if event.event_type == "runtime.workflow.failed":
            self._increment(metrics_store, event, "workflow.executions.failed")
            self._observe_duration(metrics_store, event, "workflow.duration_seconds")
            return True

        if event.event_type != "runtime.workflow.completed":
            return False

        if self._is_failure(event):
            self._increment(metrics_store, event, "workflow.executions.failed")
        self._observe_duration(metrics_store, event, "workflow.duration_seconds")
        return True

    def _record_runtime_node_event(
        self,
        event: TelemetryEvent,
        metrics_store: MetricsStore,
    ) -> bool:
        if event.event_type == "runtime.node.started":
            self._increment(metrics_store, event, "runtime.nodes.total")
            return True

        if event.event_type == "runtime.node.failed":
            self._increment(metrics_store, event, "runtime.nodes.failed")
            self._observe_duration(
                metrics_store,
                event,
                "runtime.node.duration_seconds",
            )
            return True

        if event.event_type == "runtime.node.skipped":
            self._increment(metrics_store, event, "runtime.nodes.skipped")
            self._observe_duration(
                metrics_store,
                event,
                "runtime.node.duration_seconds",
            )
            return True

        if event.event_type != "runtime.node.completed":
            return False

        if self._is_failure(event):
            self._increment(metrics_store, event, "runtime.nodes.failed")
        self._observe_duration(
            metrics_store,
            event,
            "runtime.node.duration_seconds",
        )
        return True

    def _record_application_service_event(
        self,
        event: TelemetryEvent,
        metrics_store: MetricsStore,
    ) -> bool:
        if event.event_type == "application.service.started":
            self._increment(metrics_store, event, "application.service.calls.total")
            return True

        if event.event_type == "application.service.failed":
            self._increment(metrics_store, event, "application.service.calls.failed")
            self._observe_duration(
                metrics_store,
                event,
                "application.service.duration_seconds",
            )
            return True

        if event.event_type == "application.service.cancelled":
            self._increment(
                metrics_store,
                event,
                "application.service.calls.cancelled",
            )
            self._observe_duration(
                metrics_store,
                event,
                "application.service.duration_seconds",
            )
            return True

        if event.event_type != "application.service.completed":
            return False

        if self._is_failure(event):
            self._increment(metrics_store, event, "application.service.calls.failed")
        self._observe_duration(
            metrics_store,
            event,
            "application.service.duration_seconds",
        )
        return True

    def _record_rag_event(
        self,
        event: TelemetryEvent,
        metrics_store: MetricsStore,
    ) -> bool:
        if event.event_type == "application.rag.operation.started":
            self._increment(metrics_store, event, "application.rag.operations.total")
            return True

        if event.event_type == "application.rag.operation.failed":
            self._increment(metrics_store, event, "application.rag.operations.failed")
            self._observe_duration(
                metrics_store,
                event,
                "application.rag.operation.duration_seconds",
            )
            return True

        if event.event_type != "application.rag.operation.completed":
            return False

        if self._is_failure(event):
            self._increment(metrics_store, event, "application.rag.operations.failed")
        self._observe_duration(
            metrics_store,
            event,
            "application.rag.operation.duration_seconds",
        )
        return True

    def _record_provider_event(
        self,
        event: TelemetryEvent,
        metrics_store: MetricsStore,
    ) -> bool:
        if event.event_type == "integration.provider.cancelled":
            self._increment(metrics_store, event, "integration.provider.calls.total")
            self._increment(
                metrics_store,
                event,
                "integration.provider.calls.cancelled",
            )
            self._observe_duration(
                metrics_store,
                event,
                "integration.provider.duration_seconds",
            )
            return True

        if event.event_type != "integration.provider.call":
            return False

        self._increment(metrics_store, event, "integration.provider.calls.total")
        if self._is_failure(event):
            self._increment(metrics_store, event, "integration.provider.calls.failed")
        self._observe_duration(
            metrics_store,
            event,
            "integration.provider.duration_seconds",
        )
        return True

    def _increment(
        self,
        metrics_store: MetricsStore,
        event: TelemetryEvent,
        name: str,
        *,
        attributes: Mapping[str, Any] | None = None,
    ) -> None:
        metrics_store.increment(
            name=name,
            tags=self._tags(event),
            attributes={
                **self._attributes(event),
                **dict(attributes or {}),
            },
        )

    def _observe_duration(
        self,
        metrics_store: MetricsStore,
        event: TelemetryEvent,
        name: str,
    ) -> None:
        if event.duration_seconds is None:
            return

        metrics_store.observe(
            name=name,
            value=event.duration_seconds,
            tags=self._tags(event),
            attributes=self._attributes(event),
        )

    def _tags(
        self,
        event: TelemetryEvent,
    ) -> tuple[str, ...]:
        return (
            event.source,
            event.level.value,
        )

    def _attributes(
        self,
        event: TelemetryEvent,
    ) -> dict[str, Any]:
        attributes: dict[str, Any] = {
            "event_type": event.event_type,
        }

        values = {
            "workflow_id": event.workflow_id,
            "runtime_id": event.runtime_id,
            "workflow_name": event.attributes.get(
                "workflow_name",
                event.payload.get("workflow_name"),
            ),
            "node_name": event.node_name,
            "service_name": event.attributes.get("service_name"),
            "provider_name": event.attributes.get("provider_name"),
            "component_name": event.attributes.get("component_name"),
            "operation": event.attributes.get("operation"),
            "agent_name": event.attributes.get("agent_name"),
            "signal_name": event.attributes.get("signal_name"),
            "outcome": event.attributes.get("outcome"),
            "success": event.success,
        }
        for key, value in values.items():
            self._add_optional(attributes, key, value)

        return attributes

    def _operational_attributes(
        self,
        event: TelemetryEvent,
    ) -> dict[str, Any]:
        attributes: dict[str, Any] = {}
        if event.event_type == "integration.client.retry_scheduled":
            self._add_optional(
                attributes,
                "component_name",
                event.attributes.get("client_name"),
            )
        if event.event_type in {
            "plugin.lifecycle.hook_failed",
            "runtime.lifecycle.hook_failed",
        }:
            self._add_optional(
                attributes,
                "component_name",
                event.payload.get("hook"),
            )
            self._add_optional(
                attributes,
                "operation",
                event.payload.get("lifecycle_event"),
            )
        if event.event_type == "platform.bootstrap.configuration_failed":
            attributes["operation"] = "configuration"
            startup_action = event.payload.get("startup_action")
            if isinstance(startup_action, str):
                attributes["outcome"] = startup_action
        return attributes

    def _is_event_bus_subscriber_failure(
        self,
        event: TelemetryEvent,
    ) -> bool:
        if event.event_type != "runtime.event":
            return False
        nested_payload = self._nested_runtime_event(event).get("payload", {})
        return (
            isinstance(nested_payload, dict)
            and nested_payload.get("warning_type") == "EventBusSubscriberFailure"
        )

    def _nested_runtime_event(
        self,
        event: TelemetryEvent,
    ) -> dict[str, Any]:
        runtime_event = event.payload.get("runtime_event")
        return runtime_event if isinstance(runtime_event, dict) else {}

    def _add_optional(
        self,
        attributes: dict[str, Any],
        key: str,
        value: Any,
    ) -> None:
        if value is not None:
            attributes[key] = value

    def _is_failure(
        self,
        event: TelemetryEvent,
    ) -> bool:
        return event.success is False or event.error_count > 0
