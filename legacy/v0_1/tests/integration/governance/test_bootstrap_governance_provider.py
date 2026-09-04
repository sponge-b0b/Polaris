from __future__ import annotations

from dishka import make_container

from core.bootstrap.workflow_providers import (
    WorkflowInfrastructureProvider,
)
from core.runtime.governance.governance_engine import GovernanceEngine
from core.runtime.governance.governance_telemetry import (
    GovernanceTelemetryEmitter,
)
from core.runtime.policies.policy_engine import PolicyEngine
from core.runtime.policies.policy_telemetry import PolicyTelemetryEmitter
from core.workflow.execution.workflow_facade import WorkflowFacade


def test_workflow_provider_resolves_governance_engine() -> None:
    container = make_container(
        WorkflowInfrastructureProvider(),
    )

    governance_engine = container.get(
        GovernanceEngine,
    )

    assert isinstance(
        governance_engine,
        GovernanceEngine,
    )

    assert governance_engine.telemetry_emitter is not None
    assert isinstance(
        governance_engine.telemetry_emitter,
        GovernanceTelemetryEmitter,
    )


def test_workflow_provider_resolves_policy_engine() -> None:
    container = make_container(
        WorkflowInfrastructureProvider(),
    )

    policy_engine = container.get(
        PolicyEngine,
    )

    assert isinstance(
        policy_engine,
        PolicyEngine,
    )

    assert policy_engine.telemetry_emitter is not None
    assert isinstance(
        policy_engine.telemetry_emitter,
        PolicyTelemetryEmitter,
    )


def test_workflow_provider_wires_governance_and_policy_into_facade() -> None:
    container = make_container(
        WorkflowInfrastructureProvider(),
    )

    facade = container.get(
        WorkflowFacade,
    )

    assert isinstance(
        facade,
        WorkflowFacade,
    )

    assert facade.governance_engine is not None
    assert isinstance(
        facade.governance_engine,
        GovernanceEngine,
    )

    assert facade.governance_engine.telemetry_emitter is not None
    assert isinstance(
        facade.governance_engine.telemetry_emitter,
        GovernanceTelemetryEmitter,
    )

    assert facade.policy_engine is not None
    assert isinstance(
        facade.policy_engine,
        PolicyEngine,
    )

    assert facade.policy_engine.telemetry_emitter is not None
    assert isinstance(
        facade.policy_engine.telemetry_emitter,
        PolicyTelemetryEmitter,
    )
