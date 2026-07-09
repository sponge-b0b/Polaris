from __future__ import annotations

from collections.abc import Awaitable
from collections.abc import Callable
from functools import wraps
from time import perf_counter
from typing import ParamSpec
from typing import TypeVar

from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.contracts.telemetry_severity import TelemetrySeverity
from core.telemetry.emitters.telemetry_emitter import TelemetryEmitter

P = ParamSpec("P")
R = TypeVar("R")


def instrumented(
    emitter: TelemetryEmitter,
    event_type: str,
    *,
    context: TelemetryContext | None = None,
) -> Callable[
    [Callable[P, Awaitable[R]]],
    Callable[P, Awaitable[R]],
]:
    def decorator(
        func: Callable[P, Awaitable[R]],
    ) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> R:
            started_at = perf_counter()

            await emitter.emit(
                f"{event_type}.started",
                context=context,
                success=None,
            )

            try:
                result = await func(
                    *args,
                    **kwargs,
                )
            except Exception:
                await emitter.emit(
                    f"{event_type}.failed",
                    severity=TelemetrySeverity.ERROR,
                    context=context,
                    duration_seconds=perf_counter() - started_at,
                    success=False,
                    error_count=1,
                )
                raise

            await emitter.emit(
                f"{event_type}.completed",
                context=context,
                duration_seconds=perf_counter() - started_at,
                success=True,
            )

            return result

        return wrapper

    return decorator
