from __future__ import annotations

from collections.abc import Iterable
from contextlib import AbstractAsyncContextManager
from typing import Callable
from weakref import WeakSet

from sqlalchemy.ext.asyncio import AsyncSession

from application.projections.workflow_outputs.projection_eligibility import (
    WorkflowOutputProjectionEligibilityPolicy,
)
from application.projections.workflow_outputs.projection_event_subscriber import (
    WorkflowOutputProjectionEventSubscriber,
)
from application.projections.workflow_outputs.projection_event_subscriber import (
    WorkflowOutputProjectionEventSubscriberConfig,
)
from application.projections.workflow_outputs.projection_models import (
    CompletedRunProjectionSummary,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectionRequest,
)
from application.projections.workflow_outputs.projection_registry import (
    WorkflowOutputProjectorRegistration,
)
from application.projections.workflow_outputs.projection_registry import (
    WorkflowOutputProjectionRegistry,
)
from application.projections.workflow_outputs.projection_service import (
    WorkflowOutputProjectionService,
)
from core.runtime.events.event_bus import EventBus
from core.storage.persistence.postgres_completed_run_archive import (
    PostgresCompletedRunArchive,
)
from core.storage.persistence.repositories.postgres_workflow_output_projection_job_repository import (
    PostgresWorkflowOutputProjectionJobRepository,
)
from core.telemetry.observability.observability_manager import ObservabilityManager

ProjectionSessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]

_SUBSCRIBED_EVENT_BUSES: WeakSet[EventBus] = WeakSet()


class PostgresWorkflowOutputProjectionCoordinator:
    """Owns per-event PostgreSQL request/session scope for projection events."""

    def __init__(
        self,
        *,
        session_factory: ProjectionSessionFactory,
        registry: WorkflowOutputProjectionRegistry | None = None,
        projector_registrations: Iterable[WorkflowOutputProjectorRegistration] = (),
        eligibility_policy: WorkflowOutputProjectionEligibilityPolicy | None = None,
        observability_manager: ObservabilityManager | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._registry = registry or WorkflowOutputProjectionRegistry(
            projector_registrations,
        )
        self._eligibility_policy = (
            eligibility_policy or WorkflowOutputProjectionEligibilityPolicy()
        )
        self._observability_manager = observability_manager

    async def project_completed_run(
        self,
        request: WorkflowOutputProjectionRequest,
    ) -> CompletedRunProjectionSummary:
        """Project one completed run using a fresh PostgreSQL session."""
        async with self._session_factory() as session:
            service = WorkflowOutputProjectionService(
                completed_run_archive=PostgresCompletedRunArchive(
                    session_factory=self._session_factory,
                ),
                projection_job_repository=PostgresWorkflowOutputProjectionJobRepository(
                    session,
                ),
                registry=self._registry,
                eligibility_policy=self._eligibility_policy,
                observability_manager=self._observability_manager,
            )
            return await service.project_completed_run(request)


def build_default_workflow_output_projection_subscriber(
    *,
    observability_manager: ObservabilityManager | None = None,
    config: WorkflowOutputProjectionEventSubscriberConfig | None = None,
) -> WorkflowOutputProjectionEventSubscriber:
    """Build the default application-owned projection event subscriber."""
    from core.database.postgres import AsyncSessionLocal

    return WorkflowOutputProjectionEventSubscriber(
        PostgresWorkflowOutputProjectionCoordinator(
            session_factory=AsyncSessionLocal,
            observability_manager=observability_manager,
        ),
        config=config,
    )


def subscribe_workflow_output_projection_event_subscriber(
    *,
    event_bus: EventBus,
    subscriber: WorkflowOutputProjectionEventSubscriber,
) -> bool:
    """Subscribe once per EventBus and report whether a new subscription happened."""
    if event_bus in _SUBSCRIBED_EVENT_BUSES:
        return False
    subscriber.subscribe(event_bus)
    _SUBSCRIBED_EVENT_BUSES.add(event_bus)
    return True


def subscribe_default_workflow_output_projection(
    *,
    event_bus: EventBus,
    observability_manager: ObservabilityManager | None = None,
    config: WorkflowOutputProjectionEventSubscriberConfig | None = None,
) -> bool:
    """Attach the canonical projection subscriber once to an application EventBus."""
    return subscribe_workflow_output_projection_event_subscriber(
        event_bus=event_bus,
        subscriber=build_default_workflow_output_projection_subscriber(
            observability_manager=observability_manager,
            config=config,
        ),
    )
