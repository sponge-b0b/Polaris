from __future__ import annotations

import asyncio

from typing import TYPE_CHECKING
from typing import Any
from typing import Awaitable
from typing import Callable

from core.runtime.events.runtime_events import RuntimeEvent
from core.runtime.events.runtime_events import RuntimeEventType
from core.telemetry.events.telemetry_exception_details import (
    TelemetryExceptionDetails,
)

if TYPE_CHECKING:
    from core.runtime.lifecycle.runtime_lifecycle_manager import (
        RuntimeLifecycleManager,
    )


RuntimeEventHandler = Callable[
    [RuntimeEvent],
    Awaitable[None],
]


class EventBus:
    """
    Canonical async runtime event bus.
    """

    def __init__(
        self,
        fail_fast: bool = False,
    ) -> None:
        self.fail_fast = fail_fast
        self._emitting_subscriber_failure_event = False

        self._subscribers: dict[
            RuntimeEventType,
            list[RuntimeEventHandler],
        ] = {}

        self._global_subscribers: list[RuntimeEventHandler] = []

    # ========================================================
    # SUBSCRIBE
    # ========================================================

    def subscribe(
        self,
        event_type: RuntimeEventType,
        handler: RuntimeEventHandler,
    ) -> None:
        handlers = self._subscribers.setdefault(
            event_type,
            [],
        )

        if handler not in handlers:
            handlers.append(
                handler,
            )

    def subscribe_all(
        self,
        handler: RuntimeEventHandler,
    ) -> None:
        """
        Subscribe handler to every RuntimeEvent.
        """

        if handler not in self._global_subscribers:
            self._global_subscribers.append(
                handler,
            )

    def subscribe_lifecycle_manager(
        self,
        lifecycle_manager: RuntimeLifecycleManager,
    ) -> None:
        """
        Subscribe RuntimeLifecycleManager to all runtime events.

        This allows runtime events such as checkpoint/replay/workflow
        events to flow into lifecycle hooks and telemetry automatically.
        """

        self.subscribe_all(
            lifecycle_manager.on_runtime_event,
        )

    # ========================================================
    # UNSUBSCRIBE
    # ========================================================

    def unsubscribe(
        self,
        event_type: RuntimeEventType,
        handler: RuntimeEventHandler,
    ) -> None:
        handlers = self._subscribers.get(
            event_type,
            [],
        )

        if handler in handlers:
            handlers.remove(
                handler,
            )

        if not handlers and event_type in self._subscribers:
            del self._subscribers[event_type]

    def unsubscribe_all(
        self,
        handler: RuntimeEventHandler,
    ) -> None:
        if handler in self._global_subscribers:
            self._global_subscribers.remove(
                handler,
            )

    # ========================================================
    # EMIT
    # ========================================================

    async def emit(
        self,
        event: RuntimeEvent,
    ) -> None:
        handlers = self._get_handlers(
            event,
        )

        if not handlers:
            return

        if self.fail_fast:
            for handler in handlers:
                await handler(
                    event,
                )

            return

        results = await asyncio.gather(
            *[handler(event) for handler in handlers],
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, asyncio.CancelledError):
                raise result

        failures = [
            (handler, result)
            for handler, result in zip(
                handlers,
                results,
            )
            if isinstance(
                result,
                BaseException,
            )
        ]

        if failures:
            await self._emit_subscriber_failure_event(
                event=event,
                failures=failures,
            )

    # ========================================================
    # INSPECTION
    # ========================================================

    def subscriber_count(
        self,
        event_type: RuntimeEventType | None = None,
    ) -> int:
        if event_type is not None:
            return len(
                self._subscribers.get(
                    event_type,
                    [],
                )
            ) + len(
                self._global_subscribers,
            )

        return sum(len(handlers) for handlers in self._subscribers.values()) + len(
            self._global_subscribers
        )

    def global_subscriber_count(
        self,
    ) -> int:
        return len(
            self._global_subscribers,
        )

    # ========================================================
    # CLEAR
    # ========================================================

    def clear(
        self,
    ) -> None:
        self._subscribers.clear()
        self._global_subscribers.clear()

    # ========================================================
    # INTERNALS
    # ========================================================

    async def _emit_subscriber_failure_event(
        self,
        *,
        event: RuntimeEvent,
        failures: list[tuple[RuntimeEventHandler, BaseException]],
    ) -> None:
        if self._emitting_subscriber_failure_event:
            return

        self._emitting_subscriber_failure_event = True
        try:
            await self.emit(
                RuntimeEvent(
                    event_type=RuntimeEventType.SYSTEM_WARNING,
                    execution_id=event.execution_id,
                    workflow_id=event.workflow_id,
                    runtime_id=event.runtime_id,
                    node_name=event.node_name,
                    wave_index=event.wave_index,
                    payload={
                        "warning_type": "EventBusSubscriberFailure",
                        "failed_event": {
                            "event_type": event.event_type.value,
                            "timestamp": event.timestamp.isoformat(),
                            "execution_id": event.execution_id,
                            "workflow_id": event.workflow_id,
                            "runtime_id": event.runtime_id,
                            "node_name": event.node_name,
                            "wave_index": event.wave_index,
                        },
                        "failed_event_type": event.event_type.value,
                        "failure_count": len(
                            failures,
                        ),
                        "failures": [
                            {
                                "handler": self._handler_name(
                                    handler,
                                ),
                                "exception_details": (
                                    TelemetryExceptionDetails.from_exception(
                                        error,
                                    ).to_dict()
                                ),
                            }
                            for handler, error in failures
                        ],
                        **self._trace_payload(event),
                    },
                    metadata={
                        "source": "EventBus",
                        "original_event_type": event.event_type.value,
                        "original_event_timestamp": event.timestamp.isoformat(),
                        **self._trace_payload(event),
                    },
                )
            )
        finally:
            self._emitting_subscriber_failure_event = False

    @staticmethod
    def _trace_payload(
        event: RuntimeEvent,
    ) -> dict[str, str]:
        trace_payload: dict[str, str] = {}
        for key in ("trace_id", "span_id", "parent_span_id"):
            value = event.payload.get(key, event.metadata.get(key))
            if isinstance(value, str) and value:
                trace_payload[key] = value
        return trace_payload

    def _handler_name(
        self,
        handler: RuntimeEventHandler,
    ) -> str:
        qualname = getattr(
            handler,
            "__qualname__",
            None,
        )
        if isinstance(
            qualname,
            str,
        ):
            return qualname

        name = getattr(
            handler,
            "__name__",
            None,
        )
        if isinstance(
            name,
            str,
        ):
            return name

        return handler.__class__.__name__

    def _get_handlers(
        self,
        event: RuntimeEvent,
    ) -> list[RuntimeEventHandler]:
        handlers: list[RuntimeEventHandler] = []

        handlers.extend(
            self._subscribers.get(
                event.event_type,
                [],
            )
        )

        handlers.extend(
            self._global_subscribers,
        )

        deduped: list[RuntimeEventHandler] = []

        for handler in handlers:
            if handler not in deduped:
                deduped.append(
                    handler,
                )

        return deduped

    # ========================================================
    # SERIALIZATION
    # ========================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "fail_fast": self.fail_fast,
            "subscriber_counts": {
                event_type.value: len(handlers)
                for event_type, handlers in self._subscribers.items()
            },
            "global_subscriber_count": len(
                self._global_subscribers,
            ),
            "total_subscriber_count": self.subscriber_count(),
        }
