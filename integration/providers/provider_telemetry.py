from __future__ import annotations

import asyncio

from collections.abc import Awaitable
from collections.abc import Callable
from time import perf_counter
from typing import Any
from typing import TypeVar

from core.telemetry.context import get_active_telemetry_context
from core.telemetry.context import telemetry_context_scope
from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry

R = TypeVar("R")


async def record_provider_call(
    telemetry: IntegrationTelemetry | None,
    provider_name: str,
    operation: str,
    call: Callable[[], Awaitable[R]],
    context: TelemetryContext | None = None,
    attributes: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> R:
    started_at = perf_counter()
    parent_context = context or get_active_telemetry_context() or TelemetryContext()
    telemetry_context = parent_context.child_operation(
        attributes={
            "operation_kind": "provider_call",
            "provider_name": provider_name,
            "provider_operation": operation,
        },
    )

    try:
        with telemetry_context_scope(telemetry_context):
            result = await call()
    except asyncio.CancelledError:
        if telemetry is not None:
            await telemetry.emit_provider_cancelled(
                provider_name=provider_name,
                operation=operation,
                context=telemetry_context,
                duration_seconds=perf_counter() - started_at,
                attributes=attributes,
                payload=payload,
            )
        raise
    except Exception as exc:
        if telemetry is not None:
            await telemetry.emit_provider_call(
                provider_name=provider_name,
                operation=operation,
                context=telemetry_context,
                duration_seconds=perf_counter() - started_at,
                success=False,
                error=exc,
                attributes=attributes,
                payload={
                    **dict(payload or {}),
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            )
        raise

    if telemetry is not None:
        await telemetry.emit_provider_call(
            provider_name=provider_name,
            operation=operation,
            context=telemetry_context,
            duration_seconds=perf_counter() - started_at,
            success=True,
            attributes=attributes,
            payload=payload,
        )

    return result
