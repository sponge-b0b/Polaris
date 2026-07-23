from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from time import perf_counter
from typing import ParamSpec, TypeVar

from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.emitters.telemetry_emitter import TelemetryEmitter

P = ParamSpec("P")
R = TypeVar("R")


def timed(
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

            try:
                result = await func(
                    *args,
                    **kwargs,
                )
            except Exception:
                await emitter.emit(
                    event_type,
                    context=context,
                    duration_seconds=perf_counter() - started_at,
                    success=False,
                    error_count=1,
                )
                raise

            await emitter.emit(
                event_type,
                context=context,
                duration_seconds=perf_counter() - started_at,
                success=True,
            )

            return result

        return wrapper

    return decorator
