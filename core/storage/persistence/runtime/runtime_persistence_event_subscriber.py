from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Awaitable
from typing import Callable
from typing import TypeAlias
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from core.runtime.events import EventBus
from core.runtime.events import RuntimeEvent
from core.runtime.events import RuntimeEventType
from core.storage.persistence.runtime.runtime_persistence_models import JsonObject
from core.storage.persistence.runtime.runtime_persistence_models import JsonValue
from core.storage.persistence.runtime.runtime_persistence_models import (
    RuntimePersistenceResult,
)
from core.storage.persistence.runtime.runtime_persistence_models import (
    WorkflowEventRecord,
)
from core.storage.persistence.runtime.runtime_persistence_models import (
    WorkflowNodeRunRecord,
)
from core.storage.persistence.runtime.runtime_persistence_models import (
    WorkflowRunRecord,
)
from core.storage.persistence.runtime.runtime_persistence_repository import (
    RuntimePersistenceRepository,
)

RuntimePersistenceSessionFactory: TypeAlias = Callable[
    [],
    AbstractAsyncContextManager[AsyncSession],
]
RuntimePersistenceRepositoryFactory: TypeAlias = Callable[
    [AsyncSession],
    RuntimePersistenceRepository,
]


@dataclass(
    frozen=True,
    slots=True,
)
class RuntimePersistenceEventSubscriberConfig:
    """
    Configuration for EventBus-backed runtime persistence.

    The subscriber persists canonical RuntimeEvent envelopes and derived summary
    records at the storage boundary. It does not execute workflows and does not
    mutate runtime state.
    """

    persist_events: bool = True
    persist_workflow_summaries: bool = True
    persist_node_summaries: bool = True
    fail_fast: bool = False


class RuntimePersistenceEventSubscriber:
    """
    EventBus subscriber that projects canonical runtime events to PostgreSQL.

    This keeps durable runtime persistence behind WorkflowBootstrap/EventBus so
    callers do not bypass WorkflowFacade or introduce parallel execution paths.
    """

    def __init__(
        self,
        session_factory: RuntimePersistenceSessionFactory,
        repository_factory: RuntimePersistenceRepositoryFactory | None = None,
        config: RuntimePersistenceEventSubscriberConfig | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._repository_factory = repository_factory or _default_repository_factory
        self._config = config or RuntimePersistenceEventSubscriberConfig()

    def subscribe(
        self,
        event_bus: EventBus,
    ) -> None:
        event_bus.subscribe_all(
            self.handle_event,
        )

    async def handle_event(
        self,
        event: RuntimeEvent,
    ) -> None:
        workflow_name = _workflow_name(event)
        if workflow_name is None:
            return

        async with self._session_factory() as session:
            repository = self._repository_factory(
                session,
            )

            if self._config.persist_events:
                await self._persist_record(
                    repository.persist_event(
                        _event_record(
                            event=event,
                            workflow_name=workflow_name,
                        )
                    )
                )

            if self._config.persist_workflow_summaries:
                workflow_record = _workflow_run_record(
                    event=event,
                    workflow_name=workflow_name,
                )
                if workflow_record is not None:
                    await self._persist_record(
                        repository.persist_workflow_run(
                            workflow_record,
                        )
                    )

            if self._config.persist_node_summaries:
                node_record = _node_run_record(
                    event=event,
                    workflow_name=workflow_name,
                )
                if node_record is not None:
                    await self._persist_record(
                        repository.persist_node_run(
                            node_record,
                        )
                    )

    async def _persist_record(
        self,
        persistence_call: Awaitable[RuntimePersistenceResult],
    ) -> None:
        result = await persistence_call
        if result.success:
            return

        if self._config.fail_fast:
            raise RuntimeError(result.error or "Runtime persistence failed.")


def _default_repository_factory(
    session: AsyncSession,
) -> RuntimePersistenceRepository:
    from core.storage.persistence.repositories.postgres_runtime_persistence_repository import (
        PostgresRuntimePersistenceRepository,
    )

    return PostgresRuntimePersistenceRepository(
        session,
    )


_WORKFLOW_EVENT_STATUSES: Mapping[RuntimeEventType, str] = {
    RuntimeEventType.WORKFLOW_STARTED: "started",
    RuntimeEventType.WORKFLOW_COMPLETED: "completed",
    RuntimeEventType.WORKFLOW_FAILED: "failed",
    RuntimeEventType.WORKFLOW_CANCELLED: "cancelled",
    RuntimeEventType.WORKFLOW_PAUSED: "paused",
    RuntimeEventType.WORKFLOW_RESUMED: "running",
    RuntimeEventType.WORKFLOW_STATE_CHANGED: "state_changed",
    RuntimeEventType.WORKFLOW_PROGRESS_STARTED: "started",
    RuntimeEventType.WORKFLOW_PROGRESS_RUNNING: "running",
    RuntimeEventType.WORKFLOW_PROGRESS_PAUSING: "pausing",
    RuntimeEventType.WORKFLOW_PROGRESS_PAUSED: "paused",
    RuntimeEventType.WORKFLOW_PROGRESS_RESUMING: "resuming",
    RuntimeEventType.WORKFLOW_PROGRESS_RESUMED: "running",
    RuntimeEventType.WORKFLOW_PROGRESS_CANCELLING: "cancelling",
    RuntimeEventType.WORKFLOW_PROGRESS_CANCELLED: "cancelled",
    RuntimeEventType.WORKFLOW_PROGRESS_COMPLETED: "completed",
    RuntimeEventType.WORKFLOW_PROGRESS_FAILED: "failed",
    RuntimeEventType.EXECUTION_STARTED: "started",
    RuntimeEventType.EXECUTION_COMPLETED: "completed",
    RuntimeEventType.EXECUTION_FAILED: "failed",
    RuntimeEventType.EXECUTION_STOPPED: "stopped",
}

_NODE_EVENT_STATUSES: Mapping[RuntimeEventType, str] = {
    RuntimeEventType.NODE_STARTED: "started",
    RuntimeEventType.NODE_COMPLETED: "succeeded",
    RuntimeEventType.NODE_FAILED: "failed",
    RuntimeEventType.NODE_SKIPPED: "skipped",
    RuntimeEventType.NODE_RETRYING: "retrying",
    RuntimeEventType.NODE_PROGRESS_STARTED: "started",
    RuntimeEventType.NODE_PROGRESS_RUNNING: "running",
    RuntimeEventType.NODE_PROGRESS_COMPLETED: "succeeded",
    RuntimeEventType.NODE_PROGRESS_FAILED: "failed",
}

_START_STATUSES = {
    "pending",
    "started",
    "running",
}

_TERMINAL_STATUSES = {
    "completed",
    "failed",
    "cancelled",
    "succeeded",
    "skipped",
    "stopped",
}


def _event_record(
    *,
    event: RuntimeEvent,
    workflow_name: str,
) -> WorkflowEventRecord:
    return WorkflowEventRecord(
        event_type=event.event_type.value,
        workflow_name=workflow_name,
        execution_id=event.execution_id,
        runtime_id=event.runtime_id,
        node_name=event.node_name,
        wave_index=event.wave_index,
        timestamp=event.timestamp,
        payload=_json_object(event.payload),
        metadata=_json_object(event.metadata),
    )


def _workflow_run_record(
    *,
    event: RuntimeEvent,
    workflow_name: str,
) -> WorkflowRunRecord | None:
    status = _workflow_status(event)
    if status is None:
        return None

    return WorkflowRunRecord(
        workflow_name=workflow_name,
        execution_id=event.execution_id,
        runtime_id=event.runtime_id,
        status=status,
        started_at=event.timestamp if status in _START_STATUSES else None,
        completed_at=event.timestamp if status in _TERMINAL_STATUSES else None,
        duration_seconds=_float_from(
            event.payload,
            "duration_seconds",
        )
        or _float_from(
            event.payload,
            "duration",
        ),
        mode=_string_from(event.metadata, "mode")
        or _string_from(event.payload, "mode"),
        error=_error_from(event),
        metadata=_json_object(event.metadata),
        state_payload=_json_object(event.payload),
    )


def _node_run_record(
    *,
    event: RuntimeEvent,
    workflow_name: str,
) -> WorkflowNodeRunRecord | None:
    status = _NODE_EVENT_STATUSES.get(
        event.event_type,
    )
    if status is None or event.node_name is None:
        return None

    return WorkflowNodeRunRecord(
        workflow_name=workflow_name,
        execution_id=event.execution_id,
        runtime_id=event.runtime_id,
        node_name=event.node_name,
        wave_index=event.wave_index,
        status=status,
        started_at=event.timestamp if status in _START_STATUSES else None,
        completed_at=event.timestamp if status in _TERMINAL_STATUSES else None,
        duration_seconds=_float_from(
            event.payload,
            "duration_seconds",
        )
        or _float_from(
            event.payload,
            "duration",
        ),
        error=_error_from(event),
        metadata=_json_object(event.metadata),
        outputs=_json_object(event.payload) if status in _TERMINAL_STATUSES else {},
    )


def _workflow_status(
    event: RuntimeEvent,
) -> str | None:
    mapped_status = _WORKFLOW_EVENT_STATUSES.get(
        event.event_type,
    )
    if mapped_status is None:
        return None

    if event.event_type is RuntimeEventType.WORKFLOW_STATE_CHANGED:
        return (
            _string_from(
                event.payload,
                "state",
            )
            or mapped_status
        )

    if event.event_type.value.startswith("runtime.workflow."):
        return (
            _string_from(
                event.payload,
                "state",
            )
            or mapped_status
        )

    return mapped_status


def _workflow_name(
    event: RuntimeEvent,
) -> str | None:
    workflow_name = (
        _string_from(
            event.payload,
            "workflow_name",
        )
        or _string_from(
            event.metadata,
            "workflow_name",
        )
        or event.workflow_id
    )

    if not workflow_name.strip():
        return None

    return workflow_name


def _error_from(
    event: RuntimeEvent,
) -> str | None:
    if not event.is_error:
        return None

    return (
        _string_from(event.payload, "error")
        or _string_from(event.payload, "reason")
        or _string_from(event.payload, "message")
        or _string_from(event.metadata, "error")
        or _string_from(event.metadata, "reason")
        or _string_from(event.metadata, "message")
    )


def _string_from(
    source: Mapping[str, object],
    key: str,
) -> str | None:
    value = source.get(
        key,
    )
    if value is None:
        return None

    text = str(
        value,
    )
    if not text.strip():
        return None

    return text


def _float_from(
    source: Mapping[str, object],
    key: str,
) -> float | None:
    value = source.get(
        key,
    )
    if isinstance(
        value,
        bool,
    ):
        return None

    if isinstance(
        value,
        int | float,
    ):
        return float(
            value,
        )

    return None


def _json_object(
    value: Mapping[str, object],
) -> JsonObject:
    return {str(key): _json_value(item) for key, item in value.items()}


def _json_value(
    value: object,
) -> JsonValue:
    if value is None or isinstance(
        value,
        str | int | float | bool,
    ):
        return value

    if isinstance(
        value,
        datetime,
    ):
        return value.isoformat()

    if isinstance(
        value,
        Enum,
    ):
        return cast(
            JsonValue,
            value.value,
        )

    if isinstance(
        value,
        Mapping,
    ):
        return {str(key): _json_value(item) for key, item in value.items()}

    if isinstance(
        value,
        Sequence,
    ) and not isinstance(
        value,
        str | bytes | bytearray,
    ):
        return [_json_value(item) for item in value]

    return str(
        value,
    )


__all__ = [
    "RuntimePersistenceEventSubscriber",
    "RuntimePersistenceEventSubscriberConfig",
    "RuntimePersistenceRepositoryFactory",
    "RuntimePersistenceSessionFactory",
]
