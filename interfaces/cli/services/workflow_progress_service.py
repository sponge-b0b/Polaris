from __future__ import annotations

from collections.abc import Callable
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from core.runtime.events import EventBus
from core.runtime.events import RuntimeEvent
from interfaces.cli.formatters.json_formatter import to_jsonable


ProgressNotificationHandler = Callable[
    ["WorkflowProgressNotification"],
    None,
]


@dataclass(frozen=True, slots=True)
class WorkflowProgressNotification:
    """
    CLI-facing typed progress notification derived from runtime events.
    """

    event_type: str
    execution_id: str
    workflow_id: str
    runtime_id: str | None = None
    node_name: str | None = None
    wave_index: int | None = None
    state: str | None = None
    message: str = ""
    payload: Mapping[str, Any] = field(
        default_factory=dict,
    )
    metadata: Mapping[str, Any] = field(
        default_factory=dict,
    )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "runtime_id": self.runtime_id,
            "node_name": self.node_name,
            "wave_index": self.wave_index,
            "state": self.state,
            "message": self.message,
            "payload": to_jsonable(
                dict(
                    self.payload,
                )
            ),
            "metadata": to_jsonable(
                dict(
                    self.metadata,
                )
            ),
        }


@dataclass(frozen=True, slots=True)
class WorkflowProgressSubscriptionRequest:
    """
    Typed CLI subscription request for runtime workflow progress events.
    """

    include_workflow_events: bool = True
    include_node_events: bool = True


class WorkflowProgressSubscription:
    """
    Subscribes a CLI handler to runtime progress events on the canonical EventBus.
    """

    def __init__(
        self,
        *,
        event_bus: EventBus,
        handler: ProgressNotificationHandler,
        request: WorkflowProgressSubscriptionRequest | None = None,
    ) -> None:
        self.event_bus = event_bus
        self.handler = handler
        self.request = request or WorkflowProgressSubscriptionRequest()
        self._started = False

    def start(
        self,
    ) -> None:
        if self._started:
            return

        self.event_bus.subscribe_all(
            self._handle_event,
        )
        self._started = True

    def stop(
        self,
    ) -> None:
        if not self._started:
            return

        self.event_bus.unsubscribe_all(
            self._handle_event,
        )
        self._started = False

    async def _handle_event(
        self,
        event: RuntimeEvent,
    ) -> None:
        if not self._should_include(
            event,
        ):
            return

        self.handler(
            progress_notification_from_event(
                event,
            )
        )

    def _should_include(
        self,
        event: RuntimeEvent,
    ) -> bool:
        event_type = event.event_type.value

        if self.request.include_workflow_events and event_type.startswith(
            "runtime.workflow.",
        ):
            return True

        if self.request.include_node_events and event_type.startswith(
            "runtime.node.",
        ):
            return True

        return False


def progress_notification_from_event(
    event: RuntimeEvent,
) -> WorkflowProgressNotification:
    payload = dict(
        event.payload,
    )
    state = payload.get(
        "state",
    )

    return WorkflowProgressNotification(
        event_type=event.event_type.value,
        execution_id=event.execution_id,
        workflow_id=event.workflow_id,
        runtime_id=event.runtime_id,
        node_name=event.node_name,
        wave_index=event.wave_index,
        state=state if isinstance(state, str) else None,
        message=_progress_message(
            event,
            state=state if isinstance(state, str) else None,
        ),
        payload=payload,
        metadata=dict(
            event.metadata,
        ),
    )


def format_workflow_progress_notification(
    notification: WorkflowProgressNotification,
) -> str:
    parts = [
        "[progress]",
        notification.message or notification.event_type,
        f"workflow={notification.workflow_id}",
        f"execution={notification.execution_id}",
    ]

    if notification.node_name:
        parts.append(
            f"node={notification.node_name}",
        )

    if notification.wave_index is not None:
        parts.append(
            f"wave={notification.wave_index}",
        )

    if notification.state:
        parts.append(
            f"state={notification.state}",
        )

    return " ".join(
        parts,
    )


ProgressLineEmitter = Callable[
    [str],
    None,
]


@dataclass(slots=True)
class WorkflowProgressBarState:
    """
    Mutable CLI-only progress bar state derived from runtime notifications.
    """

    total_nodes: int | None = None
    completed_nodes: set[str] = field(
        default_factory=set,
    )
    failed_nodes: set[str] = field(
        default_factory=set,
    )

    @property
    def completed_count(
        self,
    ) -> int:
        return len(
            self.completed_nodes,
        )

    @property
    def failed_count(
        self,
    ) -> int:
        return len(
            self.failed_nodes,
        )


class WorkflowProgressConsoleRenderer:
    """
    Emits progress notifications and a text progress bar for CLI stderr output.
    """

    def __init__(
        self,
        *,
        emitter: ProgressLineEmitter,
        width: int = 24,
    ) -> None:
        self.emitter = emitter
        self.width = max(
            width,
            1,
        )
        self.state = WorkflowProgressBarState()

    def handle(
        self,
        notification: WorkflowProgressNotification,
    ) -> None:
        update_progress_bar_state(
            self.state,
            notification,
        )
        self.emitter(
            format_workflow_progress_notification(
                notification,
            )
        )
        self.emitter(
            format_workflow_progress_bar(
                self.state,
                width=self.width,
            )
        )


def update_progress_bar_state(
    state: WorkflowProgressBarState,
    notification: WorkflowProgressNotification,
) -> WorkflowProgressBarState:
    total_nodes = _progress_total_nodes(
        notification,
    )
    if total_nodes is not None:
        state.total_nodes = max(
            total_nodes,
            state.total_nodes or 0,
        )

    if _is_terminal_node_event(
        notification,
    ):
        node_name = _progress_node_name(
            notification,
        )
        if node_name is not None:
            state.completed_nodes.add(
                node_name,
            )
            if notification.event_type.endswith(
                ".failed",
            ):
                state.failed_nodes.add(
                    node_name,
                )

    if state.total_nodes is not None and state.completed_count > state.total_nodes:
        state.total_nodes = state.completed_count

    return state


def format_workflow_progress_bar(
    state: WorkflowProgressBarState,
    *,
    width: int = 24,
) -> str:
    completed = state.completed_count
    total = state.total_nodes

    if total is None or total <= 0:
        return (
            "[progress-bar] "
            f"[{'-' * max(width, 1)}] "
            f"{completed}/? nodes"
            f"{_failed_suffix(state)}"
        )

    ratio = min(
        completed / total,
        1.0,
    )
    filled = int(
        round(
            ratio * max(width, 1),
        )
    )
    bar = "#" * filled + "-" * (max(width, 1) - filled)
    percent = int(
        round(
            ratio * 100,
        )
    )
    return (
        "[progress-bar] "
        f"[{bar}] "
        f"{completed}/{total} nodes "
        f"({percent}%)"
        f"{_failed_suffix(state)}"
    )


def _failed_suffix(
    state: WorkflowProgressBarState,
) -> str:
    if state.failed_count == 0:
        return ""

    return f" failed={state.failed_count}"


def _progress_total_nodes(
    notification: WorkflowProgressNotification,
) -> int | None:
    for source in _progress_sources(
        notification,
    ):
        value = source.get(
            "total_nodes",
        )
        if isinstance(
            value,
            int,
        ):
            return value
        if (
            isinstance(
                value,
                str,
            )
            and value.isdigit()
        ):
            return int(
                value,
            )

    return None


def _progress_sources(
    notification: WorkflowProgressNotification,
) -> tuple[Mapping[str, Any], ...]:
    sources: list[Mapping[str, Any]] = [
        notification.metadata,
        notification.payload,
    ]

    for value in (
        notification.metadata.get(
            "metadata",
        ),
        notification.payload.get(
            "metadata",
        ),
        notification.payload.get(
            "control_metadata",
        ),
    ):
        if isinstance(
            value,
            Mapping,
        ):
            sources.append(
                value,
            )

    return tuple(
        sources,
    )


def _is_terminal_node_event(
    notification: WorkflowProgressNotification,
) -> bool:
    return notification.event_type in {
        "runtime.node.completed",
        "runtime.node.failed",
        "runtime.node.skipped",
    }


def _progress_node_name(
    notification: WorkflowProgressNotification,
) -> str | None:
    if notification.node_name:
        return notification.node_name

    value = notification.payload.get(
        "node_name",
    )
    if (
        isinstance(
            value,
            str,
        )
        and value.strip()
    ):
        return value

    return None


def _progress_message(
    event: RuntimeEvent,
    *,
    state: str | None,
) -> str:
    event_name = event.event_type.value.removeprefix(
        "runtime.",
    )
    event_name = event_name.replace(
        ".",
        " ",
    )

    if event.node_name:
        return f"{event_name}: {event.node_name}"

    if event.wave_index is not None:
        return f"{event_name}: wave {event.wave_index}"

    if state:
        return f"{event_name}: {state}"

    return event_name
