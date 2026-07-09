from __future__ import annotations

import asyncio
from collections.abc import Mapping
import logging
import re
from typing import Any

from core.security.sensitive_data import sanitize_sensitive_value
from core.telemetry.context import get_active_telemetry_context
from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.events.telemetry_event import TelemetryEvent
from core.telemetry.events.telemetry_event import TelemetryEventLevel
from core.telemetry.observability.observability_manager import ObservabilityManager

_CONFIGURATION_FAILURE_EVENT = "platform.bootstrap.configuration_failed"
_CONFIGURATION_FAILURE_SOURCE = "core.workflow.bootstrap"
_URL_PATTERN = re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s,;]+", re.IGNORECASE)
_SETTING_NAME_PATTERN = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")
_PENDING_EMISSIONS: set[asyncio.Task[None]] = set()
_logger = logging.getLogger(__name__)


class BootstrapConfigurationTelemetry:
    """Report composition failures without creating a parallel bootstrap path."""

    def __init__(
        self,
        observability_manager: ObservabilityManager,
    ) -> None:
        self._observability_manager = observability_manager

    def emit_configuration_failure(
        self,
        *,
        component: str,
        invalid_setting_names: tuple[str, ...],
        required: bool,
        error: BaseException,
        details: Mapping[str, Any] | None = None,
    ) -> TelemetryEvent:
        context = _configuration_context(self._observability_manager)
        event = TelemetryEvent(
            event_type=_CONFIGURATION_FAILURE_EVENT,
            source=_CONFIGURATION_FAILURE_SOURCE,
            level=(
                TelemetryEventLevel.ERROR if required else TelemetryEventLevel.WARNING
            ),
            workflow_id=context.workflow_id,
            execution_id=context.execution_id,
            runtime_id=context.runtime_id,
            node_name=context.node_name,
            correlation_id=context.correlation_id,
            trace_id=context.trace_id,
            span_id=context.span_id,
            parent_span_id=context.parent_span_id,
            success=False,
            error_count=1,
            tags=context.tags,
            attributes=context.merged_attributes(
                {
                    "component_name": component,
                    "required": required,
                }
            ),
            payload={
                "component": component,
                "invalid_setting_names": list(invalid_setting_names),
                "required": required,
                "error_type": type(error).__name__,
                "startup_action": "failed" if required else "continued_degraded",
                "details": _sanitize_configuration_details(details or {}),
            },
        )
        _emit_from_sync_boundary(
            self._observability_manager,
            event,
        )
        return event


def emergency_log_configuration_failure(
    *,
    component: str,
    invalid_setting_names: tuple[str, ...],
    error: BaseException,
    details: Mapping[str, Any] | None = None,
) -> None:
    """Emit one safe CRITICAL record when observability is unavailable."""
    safe_error = RuntimeError(
        f"{component} configuration initialization failed ({type(error).__name__})."
    )
    _logger.critical(
        "Platform bootstrap configuration failure: component=%s "
        "invalid_setting_names=%s details=%s",
        component,
        invalid_setting_names,
        _sanitize_configuration_details(details or {}),
        exc_info=(type(safe_error), safe_error, error.__traceback__),
    )


def configuration_setting_names(
    error: BaseException,
    *,
    fallback: tuple[str, ...],
) -> tuple[str, ...]:
    """Extract setting identifiers without retaining configuration values."""
    names = tuple(dict.fromkeys(_SETTING_NAME_PATTERN.findall(str(error))))
    return names or fallback


def _configuration_context(
    observability_manager: ObservabilityManager,
) -> TelemetryContext:
    active_context = get_active_telemetry_context()
    if (
        active_context is not None
        and active_context.trace_id is not None
        and active_context.span_id is not None
    ):
        return active_context

    trace_context = observability_manager.create_trace_context(
        workflow_id=(active_context.workflow_id if active_context else None),
        execution_id=(active_context.execution_id if active_context else None),
        runtime_id=(active_context.runtime_id if active_context else None),
        node_name=(active_context.node_name if active_context else None),
        correlation_id=(active_context.correlation_id if active_context else None),
        attributes={"bootstrap_phase": "configuration"},
    )
    return TelemetryContext.from_trace_context(
        trace_context,
        tags=(active_context.tags if active_context else ()),
        attributes=(active_context.attributes if active_context else None),
    )


def _emit_from_sync_boundary(
    observability_manager: ObservabilityManager,
    event: TelemetryEvent,
) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(observability_manager.emit(event))
        return

    task = loop.create_task(
        _emit_nonfatal(observability_manager, event),
        name="polaris-bootstrap-configuration-telemetry",
    )
    _PENDING_EMISSIONS.add(task)
    task.add_done_callback(_PENDING_EMISSIONS.discard)


async def _emit_nonfatal(
    observability_manager: ObservabilityManager,
    event: TelemetryEvent,
) -> None:
    try:
        await observability_manager.emit(event)
    except asyncio.CancelledError:
        raise
    except Exception:
        _logger.exception(
            "Failed to emit bootstrap configuration telemetry: component=%s",
            event.payload.get("component", "unknown"),
        )


def _sanitize_configuration_details(
    details: Mapping[str, Any],
) -> dict[str, Any]:
    sanitized = sanitize_sensitive_value(dict(details))
    assert isinstance(sanitized, dict)
    return {str(key): _redact_urls(value) for key, value in sanitized.items()}


def _redact_urls(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _redact_urls(nested_value) for key, nested_value in value.items()
        }
    if isinstance(value, tuple):
        return tuple(_redact_urls(item) for item in value)
    if isinstance(value, list):
        return [_redact_urls(item) for item in value]
    if isinstance(value, str):
        return _URL_PATTERN.sub("[REDACTED_URL]", value)
    return value


__all__ = [
    "BootstrapConfigurationTelemetry",
    "configuration_setting_names",
    "emergency_log_configuration_failure",
]
