from __future__ import annotations

from pathlib import Path

from application.projections.workflow_outputs import (
    build_default_workflow_output_projection_subscriber,
)
from application.projections.workflow_outputs import (
    subscribe_default_workflow_output_projection,
)
from application.projections.workflow_outputs import (
    subscribe_workflow_output_projection_event_subscriber,
)
from core.runtime.events.event_bus import EventBus
from core.runtime.events.runtime_events import RuntimeEventType


def test_default_projection_subscription_is_idempotent_per_event_bus() -> None:
    event_bus = EventBus()

    assert subscribe_default_workflow_output_projection(event_bus=event_bus) is True
    assert subscribe_default_workflow_output_projection(event_bus=event_bus) is False

    assert event_bus.subscriber_count(RuntimeEventType.WORKFLOW_COMPLETED) == 1
    assert event_bus.subscriber_count(RuntimeEventType.WORKFLOW_FAILED) == 1


def test_explicit_projection_subscription_is_idempotent_per_event_bus() -> None:
    event_bus = EventBus()
    first_subscriber = build_default_workflow_output_projection_subscriber()
    second_subscriber = build_default_workflow_output_projection_subscriber()

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
