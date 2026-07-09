from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from core.telemetry.contracts.telemetry_context import TelemetryContext

_active_telemetry_context: ContextVar[TelemetryContext | None] = ContextVar(
    "active_telemetry_context",
    default=None,
)


def get_active_telemetry_context() -> TelemetryContext | None:
    """
    Return the telemetry context active for the current async execution scope.
    """

    return _active_telemetry_context.get()


@contextmanager
def telemetry_context_scope(
    context: TelemetryContext | None,
) -> Iterator[None]:
    """
    Temporarily activate telemetry context for downstream async calls.
    """

    token = _active_telemetry_context.set(
        context,
    )
    try:
        yield
    finally:
        _active_telemetry_context.reset(
            token,
        )
