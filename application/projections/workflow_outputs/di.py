from __future__ import annotations

from dishka import Provider
from dishka import Scope
from dishka import provide

from application.projections.workflow_outputs.projection_eligibility import (
    WorkflowOutputProjectionEligibilityPolicy,
)
from application.projections.workflow_outputs.projection_registry import (
    WorkflowOutputProjectionRegistry,
)
from application.projections.workflow_outputs.projection_service import (
    WorkflowOutputProjectionService,
)
from core.storage.persistence.completed_run_archive import CompletedRunArchive
from core.storage.persistence.projections import WorkflowOutputProjectionJobRepository
from core.telemetry.observability.observability_manager import ObservabilityManager


class WorkflowOutputProjectionDIProvider(Provider):
    """Dishka composition for canonical workflow-output projection services."""

    scope = Scope.REQUEST

    @provide(scope=Scope.APP)
    def provide_workflow_output_projection_registry(
        self,
    ) -> WorkflowOutputProjectionRegistry:
        """Return the shared application registry for domain projectors.

        Domain projector registrations are intentionally empty at this stage of
        the plan. Later projector steps add registrations here without changing
        the runtime bootstrap or projection coordinator contracts.
        """
        return WorkflowOutputProjectionRegistry()

    @provide(scope=Scope.APP)
    def provide_workflow_output_projection_policy(
        self,
    ) -> WorkflowOutputProjectionEligibilityPolicy:
        return WorkflowOutputProjectionEligibilityPolicy()

    @provide
    def provide_workflow_output_projection_service(
        self,
        completed_run_archive: CompletedRunArchive,
        projection_job_repository: WorkflowOutputProjectionJobRepository,
        registry: WorkflowOutputProjectionRegistry,
        eligibility_policy: WorkflowOutputProjectionEligibilityPolicy,
        observability_manager: ObservabilityManager,
    ) -> WorkflowOutputProjectionService:
        return WorkflowOutputProjectionService(
            completed_run_archive=completed_run_archive,
            projection_job_repository=projection_job_repository,
            registry=registry,
            eligibility_policy=eligibility_policy,
            observability_manager=observability_manager,
        )
