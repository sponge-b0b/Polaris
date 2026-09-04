from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from application.projections.workflow_outputs.projection_models import (
    CompletedRunProjectionSummary,
    WorkflowOutputProjectionRequest,
)
from core.runtime.events.event_bus import EventBus
from core.runtime.events.runtime_events import RuntimeEvent, RuntimeEventType

logger = logging.getLogger(__name__)

_PROJECTABLE_WORKFLOW_EVENTS = frozenset(
    {
        RuntimeEventType.WORKFLOW_COMPLETED,
        RuntimeEventType.WORKFLOW_FAILED,
    }
)


class WorkflowOutputProjectionCoordinator(Protocol):
    """Application service boundary used by the workflow event subscriber."""

    async def project_completed_run(
        self,
        request: WorkflowOutputProjectionRequest,
    ) -> CompletedRunProjectionSummary:
        """Project one archived completed workflow run into curated records."""
        ...


@dataclass(frozen=True, slots=True)
class WorkflowOutputProjectionEventSubscriberConfig:
    """Configuration for terminal workflow-output projection events."""

    force_reproject: bool = False
    dry_run: bool = False


class WorkflowOutputProjectionEventSubscriber:
    """Subscribes terminal workflow events to curated-record projection.

    This application-owned handler intentionally does not modify the runtime or
    the workflow engine. The workflow engine archives completed runs before it
    emits terminal workflow events; this subscriber then loads that archive via
    the projection coordinator. Exceptions are not swallowed here: the EventBus
    non-fail-fast contract isolates subscriber failures and emits the canonical
    subscriber-failure warning without changing workflow success semantics.
    """

    def __init__(
        self,
        projection_service: WorkflowOutputProjectionCoordinator,
        *,
        config: WorkflowOutputProjectionEventSubscriberConfig | None = None,
    ) -> None:
        self._projection_service = projection_service
        self._config = config or WorkflowOutputProjectionEventSubscriberConfig()

    def subscribe(self, event_bus: EventBus) -> None:
        """Subscribe to terminal workflow events that have completed archives."""
        event_bus.subscribe(
            RuntimeEventType.WORKFLOW_COMPLETED,
            self.handle_event,
        )
        event_bus.subscribe(
            RuntimeEventType.WORKFLOW_FAILED,
            self.handle_event,
        )

    async def handle_event(self, event: RuntimeEvent) -> None:
        """Project eligible outputs for one archived terminal workflow event."""
        if event.event_type not in _PROJECTABLE_WORKFLOW_EVENTS:
            return

        workflow_name = _workflow_name_from_event(event)
        request = WorkflowOutputProjectionRequest(
            workflow_name=workflow_name,
            execution_id=event.execution_id,
            force_reproject=self._config.force_reproject,
            dry_run=self._config.dry_run,
        )
        logger.info(
            "workflow_output_projection.terminal_event_received",
            extra={
                "workflow_name": request.workflow_name,
                "execution_id": request.execution_id,
                "runtime_id": event.runtime_id,
                "event_type": event.event_type.value,
                "force_reproject": request.force_reproject,
                "dry_run": request.dry_run,
            },
        )
        summary = await self._projection_service.project_completed_run(request)
        logger.info(
            "workflow_output_projection.terminal_event_projected",
            extra={
                "workflow_name": summary.workflow_name,
                "execution_id": summary.execution_id,
                "run_id": summary.run_id,
                "event_type": event.event_type.value,
                "total_jobs": summary.total_jobs,
                "succeeded_jobs": summary.succeeded_jobs,
                "failed_jobs": summary.failed_jobs,
                "skipped_jobs": summary.skipped_jobs,
                "records_written": summary.records_written,
            },
        )


def _workflow_name_from_event(event: RuntimeEvent) -> str:
    return (
        _non_empty_text(event.payload.get("workflow_name"))
        or _non_empty_text(event.metadata.get("workflow_name"))
        or event.workflow_id
    )


def _non_empty_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned
