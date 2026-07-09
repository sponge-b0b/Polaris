from __future__ import annotations

from collections.abc import Awaitable
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec
from typing import TypeVar

from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.emitters.telemetry_emitter import TelemetryEmitter

P = ParamSpec("P")
R = TypeVar("R")


def trace(
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
            await emitter.emit(
                f"{event_type}.started",
                context=context,
                success=None,
            )

            result = await func(
                *args,
                **kwargs,
            )

            await emitter.emit(
                f"{event_type}.completed",
                context=context,
                success=True,
            )

            return result

        return wrapper

    return decorator
