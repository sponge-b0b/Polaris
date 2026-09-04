from __future__ import annotations

from typing import Any

import pytest

from core.runtime.governance.governance_engine import GovernanceEngine
from core.runtime.governance.governance_registry import GovernanceRegistry
from core.runtime.governance.governance_result import GovernanceResult
from core.runtime.governance.governance_rule import BaseGovernanceRule
from core.runtime.governance.governance_telemetry import (
    GovernanceTelemetryEmitter,
)
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink


class AllowGovernanceTelemetryTestRule(BaseGovernanceRule):
    rule_name = "allow_governance_telemetry_test"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        return GovernanceResult.allow(
            rule_name=self.rule_name,
            message="Allowed for governance telemetry test.",
        )


class DenyGovernanceTelemetryTestRule(BaseGovernanceRule):
    rule_name = "deny_governance_telemetry_test"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        return GovernanceResult.deny(
            rule_name=self.rule_name,
            message="Denied for governance telemetry test.",
            reason="governance_telemetry_test_denial",
        )


class ApprovalGovernanceTelemetryTestRule(BaseGovernanceRule):
    rule_name = "approval_governance_telemetry_test"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        return GovernanceResult.require_approval(
            rule_name=self.rule_name,
            message="Approval required for governance telemetry test.",
            reason="governance_telemetry_test_approval",
        )


@pytest.mark.asyncio
async def test_governance_engine_emits_governance_evaluated_telemetry() -> None:
    sink = InMemoryTelemetrySink()

    observability_manager = ObservabilityManager()
    observability_manager.add_sink(
        sink,
    )

    governance_engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                AllowGovernanceTelemetryTestRule(),
            ],
        ),
        telemetry_emitter=GovernanceTelemetryEmitter(
            observability_manager=observability_manager,
        ),
    )

    result = await governance_engine.evaluate(
        subject={
            "operation": "test_governance_telemetry",
        },
        context={
            "governance_phase": "test_governance_phase",
        },
    )

    assert result.allowed is True

    event_types = [event.event_type for event in sink.events]

    assert "runtime.governance.evaluated" in event_types
    assert "runtime.governance.blocked" not in event_types

    evaluated_event = sink.events[-1]

    assert evaluated_event.event_type == "runtime.governance.evaluated"
    assert evaluated_event.success is True
    assert evaluated_event.error_count == 0
    assert evaluated_event.payload["governance_phase"] == ("test_governance_phase")
    assert evaluated_event.payload["evaluation"]["allowed"] is True


@pytest.mark.asyncio
async def test_governance_engine_emits_governance_blocked_for_denial() -> None:
    sink = InMemoryTelemetrySink()

    observability_manager = ObservabilityManager()
    observability_manager.add_sink(
        sink,
    )

    governance_engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                DenyGovernanceTelemetryTestRule(),
            ],
        ),
        telemetry_emitter=GovernanceTelemetryEmitter(
            observability_manager=observability_manager,
        ),
    )

    result = await governance_engine.evaluate(
        subject={
            "operation": "test_governance_denial",
        },
        context={
            "governance_phase": "test_governance_denial_phase",
        },
    )

    assert result.denied is True
    assert result.blocking is True

    event_types = [event.event_type for event in sink.events]

    assert "runtime.governance.evaluated" in event_types
    assert "runtime.governance.blocked" in event_types

    blocked_event = [
        event
        for event in sink.events
        if event.event_type == "runtime.governance.blocked"
    ][-1]

    assert blocked_event.success is False
    assert blocked_event.error_count == 1
    assert blocked_event.payload["governance_phase"] == ("test_governance_denial_phase")
    assert blocked_event.payload["evaluation"]["denied"] is True
    assert (
        blocked_event.payload["evaluation"]["results"][0]["reason"]
        == "governance_telemetry_test_denial"
    )


@pytest.mark.asyncio
async def test_governance_engine_emits_governance_blocked_for_approval_required() -> (
    None
):
    sink = InMemoryTelemetrySink()

    observability_manager = ObservabilityManager()
    observability_manager.add_sink(
        sink,
    )

    governance_engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                ApprovalGovernanceTelemetryTestRule(),
            ],
        ),
        telemetry_emitter=GovernanceTelemetryEmitter(
            observability_manager=observability_manager,
        ),
    )

    result = await governance_engine.evaluate(
        subject={
            "operation": "test_governance_approval",
        },
        context={
            "governance_phase": "test_governance_approval_phase",
        },
    )

    assert result.requires_approval is True
    assert result.blocking is True

    event_types = [event.event_type for event in sink.events]

    assert "runtime.governance.evaluated" in event_types
    assert "runtime.governance.blocked" in event_types

    blocked_event = [
        event
        for event in sink.events
        if event.event_type == "runtime.governance.blocked"
    ][-1]

    assert blocked_event.success is False
    assert blocked_event.error_count == 1
    assert blocked_event.payload["evaluation"]["requires_approval"] is True
    assert (
        blocked_event.payload["evaluation"]["results"][0]["reason"]
        == "governance_telemetry_test_approval"
    )


@pytest.mark.asyncio
async def test_governance_engine_require_allowed_emits_blocked_telemetry_before_raise() -> (  # noqa: E501 - descriptive pytest node id
    None
):
    sink = InMemoryTelemetrySink()

    observability_manager = ObservabilityManager()
    observability_manager.add_sink(
        sink,
    )

    governance_engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                DenyGovernanceTelemetryTestRule(),
            ],
        ),
        telemetry_emitter=GovernanceTelemetryEmitter(
            observability_manager=observability_manager,
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="governance_telemetry_test_denial",
    ):
        await governance_engine.require_allowed(
            subject={
                "operation": "test_governance_denial_raise",
            },
            context={
                "governance_phase": "test_governance_denial_raise_phase",
            },
        )

    event_types = [event.event_type for event in sink.events]

    assert "runtime.governance.evaluated" in event_types
    assert "runtime.governance.blocked" in event_types


class ExceptionGovernanceTelemetryTestRule(BaseGovernanceRule):
    rule_name = "exception_governance_telemetry_test"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        raise RuntimeError("governance telemetry exploded")


@pytest.mark.asyncio
async def test_governance_exception_diagnostics_attach_to_blocked_event_once() -> None:
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(sink)
    governance_engine = GovernanceEngine(
        registry=GovernanceRegistry(rules=[ExceptionGovernanceTelemetryTestRule()]),
        telemetry_emitter=GovernanceTelemetryEmitter(observability_manager),
    )

    result = await governance_engine.evaluate(subject={"operation": "exception"})

    assert result.blocking is True
    evaluated_events = [
        event
        for event in sink.events
        if event.event_type == "runtime.governance.evaluated"
    ]
    blocked_events = [
        event
        for event in sink.events
        if event.event_type == "runtime.governance.blocked"
    ]
    assert len(evaluated_events) == 1
    assert len(blocked_events) == 1
    assert evaluated_events[0].exception_details is None
    assert evaluated_events[0].attributes["evaluation_failure_count"] == 1
    assert blocked_events[0].exception_details is not None
    assert blocked_events[0].exception_details.exception_type == "RuntimeError"
    assert blocked_events[0].exception_details.message == (
        "governance telemetry exploded"
    )
    assert "test_governance_telemetry.py" in (
        blocked_events[0].exception_details.stack_trace
    )
