from __future__ import annotations

import asyncio
from typing import Any

import pytest

from application.services.base import (
    ApplicationService,
    ServiceDegradation,
    ServiceRequest,
    ServiceResult,
    ServiceRunner,
    ServiceRunnerConfig,
)
from core.runtime.policies.policy import BaseRuntimePolicy
from core.runtime.policies.policy_engine import PolicyEngine
from core.runtime.policies.policy_registry import PolicyRegistry
from core.runtime.policies.policy_result import PolicyResult
from core.telemetry.context import get_active_telemetry_context
from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.emitters.application_service_telemetry import (
    ApplicationServiceTelemetry,
)
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink


class EchoService(ApplicationService[dict[str, str], dict[str, str]]):
    service_name = "echo_service"

    def __init__(
        self,
        *,
        failures_before_success: int = 0,
    ) -> None:
        self.failures_before_success = failures_before_success
        self.calls = 0

    async def run(
        self,
        request: ServiceRequest[dict[str, str]],
    ) -> ServiceResult[dict[str, str]]:
        self.calls += 1

        if self.calls <= self.failures_before_success:
            raise RuntimeError("temporary failure")

        return ServiceResult.ok(
            request_id=request.request_id,
            request_name=request.request_name,
            result=request.payload,
        )

    async def _execute(
        self,
        request: dict[str, str],
    ) -> dict[str, str]:
        return request


class InvalidRequestService(EchoService):
    async def validate_request(
        self,
        request: ServiceRequest[dict[str, str]],
    ) -> tuple[str, ...]:
        return ("payload is invalid.",)


class ActiveContextService(EchoService):
    def __init__(
        self,
    ) -> None:
        super().__init__()
        self.active_context: TelemetryContext | None = None

    async def run(
        self,
        request: ServiceRequest[dict[str, str]],
    ) -> ServiceResult[dict[str, str]]:
        self.active_context = get_active_telemetry_context()
        return await super().run(
            request,
        )


class DegradedEchoService(EchoService):
    async def run(
        self,
        request: ServiceRequest[dict[str, str]],
    ) -> ServiceResult[dict[str, str]]:
        self.calls += 1
        return ServiceResult.ok(
            request_id=request.request_id,
            request_name=request.request_name,
            result=request.payload,
            degradations=(
                ServiceDegradation(
                    code="provider_call_failed",
                    component="secondary_provider",
                    summary="Secondary provider data was unavailable.",
                    error_type="RuntimeError",
                ),
            ),
        )


class DenyRequestPolicy(BaseRuntimePolicy):
    policy_name = "deny_service_request"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> PolicyResult:
        return PolicyResult.deny(
            policy_name=self.policy_name,
            message="Denied.",
            reason="test_denial",
        )


def build_telemetry() -> tuple[ApplicationServiceTelemetry, InMemoryTelemetrySink]:
    sink = InMemoryTelemetrySink()
    manager = ObservabilityManager()
    manager.add_sink(
        sink,
    )

    return ApplicationServiceTelemetry(
        observability_manager=manager,
    ), sink


@pytest.mark.asyncio
async def test_service_runner_returns_success_and_emits_telemetry() -> None:
    telemetry, sink = build_telemetry()
    runner: ServiceRunner[dict[str, str], dict[str, str]] = ServiceRunner(
        telemetry=telemetry,
    )
    request: ServiceRequest[dict[str, str]] = ServiceRequest(
        payload={
            "message": "hello",
        },
    )

    result = await runner.run(
        service=EchoService(),
        request=request,
    )

    assert result.success is True
    assert result.result == {
        "message": "hello",
    }
    assert result.attempts == 1

    event_types = [event.event_type for event in sink.events]
    assert event_types == [
        "application.service.started",
        "application.service.completed",
    ]
    for event in sink.events:
        assert "operation" not in event.attributes
        assert "operation" not in event.payload


@pytest.mark.asyncio
async def test_service_runner_emits_degradation_before_completion() -> None:
    telemetry, sink = build_telemetry()
    runner: ServiceRunner[dict[str, str], dict[str, str]] = ServiceRunner(
        telemetry=telemetry,
    )
    request: ServiceRequest[dict[str, str]] = ServiceRequest(
        payload={"message": "hello"},
    )

    result = await runner.run(
        service=DegradedEchoService(),
        request=request,
    )

    assert result.success is True
    assert result.degradations[0].component == "secondary_provider"
    assert [event.event_type for event in sink.events] == [
        "application.service.started",
        "application.service.degraded",
        "application.service.completed",
    ]
    degraded = sink.events[1]
    assert degraded.success is True
    assert degraded.error_count == 0
    assert degraded.exception_details is None
    assert degraded.attributes["request_id"] == request.request_id
    assert degraded.attributes["degradation_count"] == 1
    assert degraded.payload["degradations"] == [
        {
            "code": "provider_call_failed",
            "component": "secondary_provider",
            "summary": "Secondary provider data was unavailable.",
            "error_type": "RuntimeError",
        }
    ]


def test_service_result_serializes_typed_degradations() -> None:
    result = ServiceResult.ok(
        request_id="request-1",
        request_name="example_request",
        result={"message": "hello"},
        degradations=(
            ServiceDegradation(
                code="invalid_provider_payload",
                component="market_news",
                summary="Provider payload was invalid.",
                error_type="InvalidProviderPayload",
            ),
        ),
    )

    assert result.to_dict()["degradations"] == [
        {
            "code": "invalid_provider_payload",
            "component": "market_news",
            "summary": "Provider payload was invalid.",
            "error_type": "InvalidProviderPayload",
        }
    ]


@pytest.mark.asyncio
async def test_service_runner_propagates_telemetry_context_to_success_events() -> None:
    telemetry, sink = build_telemetry()
    runner: ServiceRunner[dict[str, str], dict[str, str]] = ServiceRunner(
        telemetry=telemetry,
    )
    context = TelemetryContext(
        workflow_id="workflow-1",
        execution_id="execution-1",
        runtime_id="runtime-1",
        node_name="technical_node",
        correlation_id="correlation-1",
        trace_id="trace-1",
        span_id="node-span-1",
        parent_span_id="workflow-span-1",
        tags=("morning_report",),
        attributes={
            "source_node": "technical_node",
        },
    )
    request: ServiceRequest[dict[str, str]] = ServiceRequest(
        payload={
            "message": "hello",
        },
        telemetry_context=context,
    )
    service = ActiveContextService()

    result = await runner.run(
        service=service,
        request=request,
    )

    assert result.success is True
    assert service.active_context is not None
    assert service.active_context.trace_id == "trace-1"
    assert service.active_context.span_id != "node-span-1"
    assert service.active_context.parent_span_id == "node-span-1"
    assert (service.active_context.attributes or {})[
        "operation_kind"
    ] == "application_service_attempt"

    assert [event.event_type for event in sink.events] == [
        "application.service.started",
        "application.service.completed",
    ]

    for event in sink.events:
        assert event.workflow_id == "workflow-1"
        assert event.execution_id == "execution-1"
        assert event.runtime_id == "runtime-1"
        assert event.node_name == "technical_node"
        assert event.correlation_id == "correlation-1"
        assert event.tags == ("morning_report",)
        assert event.attributes["source_node"] == "technical_node"
        assert event.attributes["request_id"] == request.request_id
        assert event.attributes["trace_id"] == "trace-1"
        assert event.attributes["span_id"] == service.active_context.span_id
        assert event.attributes["parent_span_id"] == "node-span-1"
        assert event.attributes["operation_kind"] == "application_service_attempt"
        assert event.attributes["attempt"] == 1

    policy_context = request.policy_context()["telemetry_context"]
    assert policy_context["trace_id"] == "trace-1"
    assert policy_context["span_id"] == "node-span-1"
    assert policy_context["parent_span_id"] == "workflow-span-1"


@pytest.mark.asyncio
async def test_service_runner_propagates_telemetry_context_to_failed_events() -> None:
    telemetry, sink = build_telemetry()
    runner: ServiceRunner[dict[str, str], dict[str, str]] = ServiceRunner(
        telemetry=telemetry,
    )
    context = TelemetryContext(
        workflow_id="workflow-2",
        execution_id="execution-2",
        runtime_id="runtime-2",
        node_name="validation_node",
        correlation_id="correlation-2",
        trace_id="trace-2",
        span_id="node-span-2",
        parent_span_id="workflow-span-2",
    )
    request: ServiceRequest[dict[str, str]] = ServiceRequest(
        payload={},
        telemetry_context=context,
    )

    result = await runner.run(
        service=InvalidRequestService(),
        request=request,
    )

    assert result.success is False
    assert [event.event_type for event in sink.events] == [
        "application.service.failed",
    ]

    event = sink.events[0]
    assert event.workflow_id == "workflow-2"
    assert event.execution_id == "execution-2"
    assert event.runtime_id == "runtime-2"
    assert event.node_name == "validation_node"
    assert event.correlation_id == "correlation-2"
    assert event.attributes["request_id"] == request.request_id
    assert event.attributes["trace_id"] == "trace-2"
    assert event.attributes["span_id"] != "node-span-2"
    assert event.attributes["parent_span_id"] == "node-span-2"
    assert event.attributes["operation_kind"] == "application_service_attempt"
    assert event.attributes["attempt"] == 1
    assert event.payload["validation_errors"] == [
        "payload is required.",
        "payload is invalid.",
    ]
    assert event.exception_details is None


@pytest.mark.asyncio
async def test_service_runner_returns_validation_failure() -> None:
    telemetry, sink = build_telemetry()
    runner: ServiceRunner[dict[str, str], dict[str, str]] = ServiceRunner(
        telemetry=telemetry,
    )
    request: ServiceRequest[dict[str, str]] = ServiceRequest(
        payload={},
    )

    result = await runner.run(
        service=InvalidRequestService(),
        request=request,
    )

    assert result.success is False
    assert result.validation_errors == (
        "payload is required.",
        "payload is invalid.",
    )
    assert result.error_type == "ServiceError"
    assert [event.event_type for event in sink.events] == [
        "application.service.failed",
    ]


@pytest.mark.asyncio
async def test_service_runner_retries_failed_attempts() -> None:
    telemetry, sink = build_telemetry()
    runner: ServiceRunner[dict[str, str], dict[str, str]] = ServiceRunner(
        telemetry=telemetry,
        config=ServiceRunnerConfig(
            max_attempts=2,
            retry_backoff_seconds=0.0,
        ),
    )
    service = EchoService(
        failures_before_success=1,
    )
    request: ServiceRequest[dict[str, str]] = ServiceRequest(
        payload={
            "message": "hello",
        },
    )

    result = await runner.run(
        service=service,
        request=request,
    )

    assert result.success is True
    assert result.attempts == 2
    assert service.calls == 2
    assert [event.event_type for event in sink.events] == [
        "application.service.started",
        "application.service.failed",
        "application.service.retry_scheduled",
        "application.service.started",
        "application.service.completed",
    ]
    first_attempt = sink.events[:3]
    second_attempt = sink.events[3:]
    assert len({event.attributes["span_id"] for event in first_attempt}) == 1
    assert len({event.attributes["span_id"] for event in second_attempt}) == 1
    assert (
        first_attempt[0].attributes["span_id"]
        != second_attempt[0].attributes["span_id"]
    )
    assert first_attempt[0].attributes["attempt"] == 1
    assert second_attempt[0].attributes["attempt"] == 2
    assert (
        first_attempt[0].attributes["trace_id"]
        == second_attempt[0].attributes["trace_id"]
    )
    retry = sink.events[2]
    assert retry.attributes["request_id"] == request.request_id
    assert retry.payload["attempt"] == 1
    assert retry.payload["next_attempt"] == 2
    assert retry.payload["maximum_attempts"] == 2
    assert retry.payload["backoff_seconds"] == 0.0
    assert retry.payload["reason"] == "temporary failure"
    assert retry.payload["error_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_service_runner_returns_policy_denial() -> None:
    telemetry, sink = build_telemetry()
    policy_engine = PolicyEngine(
        registry=PolicyRegistry(
            policies=[
                DenyRequestPolicy(),
            ],
        ),
    )
    runner: ServiceRunner[dict[str, str], dict[str, str]] = ServiceRunner(
        telemetry=telemetry,
        policy_engine=policy_engine,
    )
    request: ServiceRequest[dict[str, str]] = ServiceRequest(
        payload={
            "message": "hello",
        },
    )

    result = await runner.run(
        service=EchoService(),
        request=request,
    )

    assert result.success is False
    assert result.error_message == "Service request denied by policy."
    assert result.metadata["policy"]["denied"] is True
    assert [event.event_type for event in sink.events] == [
        "application.service.failed",
    ]
    assert sink.events[0].exception_details is None


@pytest.mark.asyncio
async def test_service_runner_records_cancellation_and_reraises() -> None:
    class CancelledService(EchoService):
        async def run(
            self,
            request: ServiceRequest[dict[str, str]],
        ) -> ServiceResult[dict[str, str]]:
            raise asyncio.CancelledError

    telemetry, sink = build_telemetry()
    runner: ServiceRunner[dict[str, str], dict[str, str]] = ServiceRunner(
        telemetry=telemetry,
        config=ServiceRunnerConfig(max_attempts=3),
    )

    with pytest.raises(asyncio.CancelledError):
        await runner.run(
            service=CancelledService(),
            request=ServiceRequest(payload={"message": "cancel"}),
        )

    assert [event.event_type for event in sink.events] == [
        "application.service.started",
        "application.service.cancelled",
    ]
    cancelled = sink.events[-1]
    assert cancelled.success is False
    assert cancelled.error_count == 0
    assert cancelled.attributes["outcome"] == "cancelled"


@pytest.mark.asyncio
async def test_service_runner_emits_invalid_configuration_before_returning() -> None:
    telemetry, sink = build_telemetry()
    runner: ServiceRunner[dict[str, str], dict[str, str]] = ServiceRunner(
        telemetry=telemetry,
        config=ServiceRunnerConfig(
            max_attempts=0,
            retry_backoff_seconds=-1.0,
        ),
    )
    service = EchoService()
    request: ServiceRequest[dict[str, str]] = ServiceRequest(
        payload={"message": "hello"},
    )

    result = await runner.run(service=service, request=request)

    assert result.success is False
    assert service.calls == 0
    assert result.validation_errors == (
        "max_attempts must be at least 1.",
        "retry_backoff_seconds cannot be negative.",
    )
    assert [event.event_type for event in sink.events] == [
        "application.service.configuration_failed"
    ]
    event = sink.events[0]
    assert event.attributes["request_id"] == request.request_id
    assert event.attributes["max_attempts"] == 0
    assert event.attributes["retry_backoff_seconds"] == -1.0
    assert event.exception_details is None


@pytest.mark.asyncio
async def test_service_runner_retry_exhaustion_emits_one_terminal_exception() -> None:
    telemetry, sink = build_telemetry()
    runner: ServiceRunner[dict[str, str], dict[str, str]] = ServiceRunner(
        telemetry=telemetry,
        config=ServiceRunnerConfig(max_attempts=2),
    )
    service = EchoService(failures_before_success=2)
    request: ServiceRequest[dict[str, str]] = ServiceRequest(
        payload={"message": "hello"},
    )

    result = await runner.run(service=service, request=request)

    assert result.success is False
    assert result.attempts == 2
    assert service.calls == 2
    assert [event.event_type for event in sink.events] == [
        "application.service.started",
        "application.service.failed",
        "application.service.retry_scheduled",
        "application.service.started",
        "application.service.failed",
    ]
    retry = sink.events[2]
    assert retry.exception_details is None
    terminal = sink.events[4]
    assert sink.events[0].attributes["span_id"] == sink.events[1].attributes["span_id"]
    assert sink.events[1].attributes["span_id"] == retry.attributes["span_id"]
    assert sink.events[3].attributes["span_id"] == terminal.attributes["span_id"]
    assert retry.attributes["span_id"] != terminal.attributes["span_id"]
    assert terminal.payload["error_type"] == "RuntimeError"
    assert terminal.payload["error_message"] == "temporary failure"
    assert terminal.exception_details is not None
    assert terminal.exception_details.exception_type == "RuntimeError"
    assert terminal.exception_details.message == "temporary failure"
    assert "raise RuntimeError" in terminal.exception_details.stack_trace
