from __future__ import annotations

from typing import cast

from application.projections.workflow_outputs import WorkflowOutputProjectionDIProvider
from application.projections.workflow_outputs import WorkflowOutputProjectionService
from core.storage.persistence.completed_run_archive import CompletedRunArchive
from core.storage.persistence.projections import WorkflowOutputProjectionJobRepository
from core.telemetry.observability.observability_manager import ObservabilityManager


class _FakeCompletedRunArchive:
    pass


class _FakeProjectionJobRepository:
    pass


def test_projection_di_provider_builds_typed_projection_service() -> None:
    provider = WorkflowOutputProjectionDIProvider()
    registry = provider.provide_workflow_output_projection_registry()
    policy = provider.provide_workflow_output_projection_policy()
    observability = ObservabilityManager()

    service = provider.provide_workflow_output_projection_service(
        completed_run_archive=cast(CompletedRunArchive, _FakeCompletedRunArchive()),
        projection_job_repository=cast(
            WorkflowOutputProjectionJobRepository,
            _FakeProjectionJobRepository(),
        ),
        registry=registry,
        eligibility_policy=policy,
        observability_manager=observability,
    )

    assert isinstance(service, WorkflowOutputProjectionService)
    assert service._registry is registry
    assert service._eligibility_policy is policy
    assert service._observability_manager is observability
