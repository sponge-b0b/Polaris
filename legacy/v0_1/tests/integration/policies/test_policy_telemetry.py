from __future__ import annotations

from typing import Any

import pytest

from core.runtime.policies.policy import BaseRuntimePolicy
from core.runtime.policies.policy_engine import PolicyEngine
from core.runtime.policies.policy_registry import PolicyRegistry
from core.runtime.policies.policy_result import PolicyResult
from core.runtime.policies.policy_telemetry import PolicyTelemetryEmitter
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink


class DenyPolicyTelemetryTestPolicy(BaseRuntimePolicy):
    policy_name = "deny_policy_telemetry_test"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> PolicyResult:
        return PolicyResult.deny(
            policy_name=self.policy_name,
            message="Denied for telemetry test.",
            reason="telemetry_test_denial",
        )


class AllowPolicyTelemetryTestPolicy(BaseRuntimePolicy):
    policy_name = "allow_policy_telemetry_test"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> PolicyResult:
        return PolicyResult.allow(
            policy_name=self.policy_name,
            message="Allowed for telemetry test.",
        )


@pytest.mark.asyncio
async def test_policy_engine_emits_policy_evaluated_telemetry() -> None:
    sink = InMemoryTelemetrySink()

    observability_manager = ObservabilityManager()
    observability_manager.add_sink(
        sink,
    )

    policy_engine = PolicyEngine(
        registry=PolicyRegistry(
            policies=[
                AllowPolicyTelemetryTestPolicy(),
            ],
        ),
        telemetry_emitter=PolicyTelemetryEmitter(
            observability_manager=observability_manager,
        ),
    )

    result = await policy_engine.evaluate(
        subject={
            "operation": "test_policy_telemetry",
        },
        context={
            "policy_phase": "test_policy_phase",
        },
    )

    assert result.allowed is True

    event_types = [event.event_type for event in sink.events]

    assert "runtime.policy.evaluated" in event_types
    assert "runtime.policy.denied" not in event_types

    evaluated_event = sink.events[-1]

    assert evaluated_event.event_type == "runtime.policy.evaluated"
    assert evaluated_event.success is True
    assert evaluated_event.error_count == 0
    assert evaluated_event.payload["policy_phase"] == "test_policy_phase"
    assert evaluated_event.payload["evaluation"]["allowed"] is True


@pytest.mark.asyncio
async def test_policy_engine_emits_policy_denied_telemetry() -> None:
    sink = InMemoryTelemetrySink()

    observability_manager = ObservabilityManager()
    observability_manager.add_sink(
        sink,
    )

    policy_engine = PolicyEngine(
        registry=PolicyRegistry(
            policies=[
                DenyPolicyTelemetryTestPolicy(),
            ],
        ),
        telemetry_emitter=PolicyTelemetryEmitter(
            observability_manager=observability_manager,
        ),
    )

    result = await policy_engine.evaluate(
        subject={
            "operation": "test_policy_denial",
        },
        context={
            "policy_phase": "test_policy_denial_phase",
        },
    )

    assert result.denied is True

    event_types = [event.event_type for event in sink.events]

    assert "runtime.policy.evaluated" in event_types
    assert "runtime.policy.denied" in event_types

    denied_event = [
        event for event in sink.events if event.event_type == "runtime.policy.denied"
    ][-1]

    assert denied_event.success is False
    assert denied_event.error_count == 1
    assert denied_event.payload["policy_phase"] == ("test_policy_denial_phase")
    assert denied_event.payload["evaluation"]["denied"] is True
    assert (
        denied_event.payload["evaluation"]["results"][0]["reason"]
        == "telemetry_test_denial"
    )


@pytest.mark.asyncio
async def test_policy_engine_require_allowed_emits_denied_telemetry_before_raise() -> (
    None
):
    sink = InMemoryTelemetrySink()

    observability_manager = ObservabilityManager()
    observability_manager.add_sink(
        sink,
    )

    policy_engine = PolicyEngine(
        registry=PolicyRegistry(
            policies=[
                DenyPolicyTelemetryTestPolicy(),
            ],
        ),
        telemetry_emitter=PolicyTelemetryEmitter(
            observability_manager=observability_manager,
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="telemetry_test_denial",
    ):
        await policy_engine.require_allowed(
            subject={
                "operation": "test_policy_denial_raise",
            },
            context={
                "policy_phase": "test_policy_denial_raise_phase",
            },
        )

    event_types = [event.event_type for event in sink.events]

    assert "runtime.policy.evaluated" in event_types
    assert "runtime.policy.denied" in event_types


class ExceptionPolicyTelemetryTestPolicy(BaseRuntimePolicy):
    policy_name = "exception_policy_telemetry_test"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> PolicyResult:
        raise RuntimeError("policy telemetry exploded")


@pytest.mark.asyncio
async def test_policy_exception_diagnostics_attach_to_terminal_denied_event_once() -> (
    None
):
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(sink)
    policy_engine = PolicyEngine(
        registry=PolicyRegistry(policies=[ExceptionPolicyTelemetryTestPolicy()]),
        telemetry_emitter=PolicyTelemetryEmitter(observability_manager),
    )

    result = await policy_engine.evaluate(subject={"operation": "exception"})

    assert result.denied is True
    evaluated_events = [
        event for event in sink.events if event.event_type == "runtime.policy.evaluated"
    ]
    denied_events = [
        event for event in sink.events if event.event_type == "runtime.policy.denied"
    ]
    assert len(evaluated_events) == 1
    assert len(denied_events) == 1
    assert evaluated_events[0].exception_details is None
    assert evaluated_events[0].attributes["evaluation_failure_count"] == 1
    assert denied_events[0].exception_details is not None
    assert denied_events[0].exception_details.exception_type == "RuntimeError"
    assert denied_events[0].exception_details.message == "policy telemetry exploded"
    assert "test_policy_telemetry.py" in (
        denied_events[0].exception_details.stack_trace
    )
