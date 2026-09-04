from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import application.projections.workflow_outputs.bootstrap as projection_bootstrap
from application.governance import AutomatedDecisionAuditService
from application.projections.workflow_outputs import (
    CompletedRunProjectionSummary,
    WorkflowOutputProjectionRegistry,
    WorkflowOutputProjectionRequest,
    build_default_workflow_output_projection_subscriber,
    subscribe_default_workflow_output_projection,
    subscribe_workflow_output_projection_event_subscriber,
)
from application.projections.workflow_outputs.bootstrap import (
    PostgresWorkflowOutputProjectionCoordinator,
    ProjectionSessionFactory,
)
from application.projections.workflow_outputs.projectors.strategy import (
    StrategySynthesisWorkflowOutputProjector,
)
from core.runtime.events.event_bus import EventBus
from core.runtime.events.runtime_events import RuntimeEventType
from core.workflow.registry.workflow_registry import WorkflowRegistry
from domain.workflow_outputs import (
    STRATEGY_SYNTHESIS_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)


def test_default_projection_subscription_is_idempotent_per_event_bus() -> None:
    event_bus = EventBus()
    workflow_registry = WorkflowRegistry()

    assert (
        subscribe_default_workflow_output_projection(
            event_bus=event_bus,
            workflow_registry=workflow_registry,
            session_factory=_fake_session_factory,
        )
        is True
    )
    assert (
        subscribe_default_workflow_output_projection(
            event_bus=event_bus,
            workflow_registry=workflow_registry,
            session_factory=_fake_session_factory,
        )
        is False
    )

    assert event_bus.subscriber_count(RuntimeEventType.WORKFLOW_COMPLETED) == 1
    assert event_bus.subscriber_count(RuntimeEventType.WORKFLOW_FAILED) == 1


def test_explicit_projection_subscription_is_idempotent_per_event_bus() -> None:
    event_bus = EventBus()
    workflow_registry = WorkflowRegistry()
    first_subscriber = build_default_workflow_output_projection_subscriber(
        workflow_registry=workflow_registry,
        session_factory=_fake_session_factory,
    )
    second_subscriber = build_default_workflow_output_projection_subscriber(
        workflow_registry=workflow_registry,
        session_factory=_fake_session_factory,
    )

    assert (
        subscribe_workflow_output_projection_event_subscriber(
            event_bus=event_bus,
            subscriber=first_subscriber,
        )
        is True
    )
    assert (
        subscribe_workflow_output_projection_event_subscriber(
            event_bus=event_bus,
            subscriber=second_subscriber,
        )
        is False
    )

    assert event_bus.subscriber_count(RuntimeEventType.WORKFLOW_COMPLETED) == 1
    assert event_bus.subscriber_count(RuntimeEventType.WORKFLOW_FAILED) == 1


def test_runtime_bootstrap_does_not_import_domain_projectors() -> None:
    bootstrap_source = Path(
        "core/workflow/bootstrap/workflow_runtime_assembler.py"
    ).read_text()

    assert "application.projections" not in bootstrap_source
    assert "WorkflowOutputProjection" not in bootstrap_source


@pytest.mark.asyncio
async def test_postgres_projection_coordinator_wires_canonical_release_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_kwargs: dict[str, object] = {}
    workflow_registry = WorkflowRegistry()

    class CapturingWorkflowOutputProjectionService:
        def __init__(self, **kwargs: object) -> None:
            captured_kwargs.update(kwargs)

        async def project_completed_run(
            self,
            request: WorkflowOutputProjectionRequest,
        ) -> CompletedRunProjectionSummary:
            return CompletedRunProjectionSummary(
                workflow_name=request.workflow_name,
                execution_id=request.execution_id,
            )

    monkeypatch.setattr(
        projection_bootstrap,
        "WorkflowOutputProjectionService",
        CapturingWorkflowOutputProjectionService,
    )
    coordinator = PostgresWorkflowOutputProjectionCoordinator(
        session_factory=_fake_session_factory,
        workflow_registry=workflow_registry,
    )

    summary = await coordinator.project_completed_run(
        WorkflowOutputProjectionRequest(
            workflow_name="morning_report",
            execution_id="exec-1",
        )
    )

    assert summary.workflow_name == "morning_report"
    assert isinstance(
        captured_kwargs["governed_output_release_service"],
        AutomatedDecisionAuditService,
    )
    registry = cast(WorkflowOutputProjectionRegistry, captured_kwargs["registry"])
    resolution = registry.resolve(
        output_contract=STRATEGY_SYNTHESIS_OUTPUT_CONTRACT,
        output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
    )
    assert resolution.registration is not None
    projector = resolution.registration.projector
    assert isinstance(projector, StrategySynthesisWorkflowOutputProjector)
    assert projector._workflow_registry is workflow_registry


@asynccontextmanager
async def _fake_session_context() -> AsyncIterator[AsyncSession]:
    yield cast(AsyncSession, object())


def _build_fake_session_factory():
    return _fake_session_context()


_fake_session_factory = cast(ProjectionSessionFactory, _build_fake_session_factory)
