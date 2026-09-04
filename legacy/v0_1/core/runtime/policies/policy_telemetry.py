from __future__ import annotations

from typing import Any

from core.runtime.policies.policy_engine import PolicyEvaluationResult
from core.telemetry.events.telemetry_event import (
    TelemetryEvent,
    TelemetryEventLevel,
)
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)


class PolicyTelemetryEmitter:
    """
    Emits telemetry for runtime policy decisions.

    Bridges:

        PolicyEvaluationResult
            -> TelemetryEvent
            -> ObservabilityManager
    """

    def __init__(
        self,
        observability_manager: ObservabilityManager,
        source: str = "runtime.policies",
    ) -> None:
        self.observability_manager = observability_manager
        self.source = source

    async def emit_policy_evaluated(
        self,
        result: PolicyEvaluationResult,
        subject: Any | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        await self.observability_manager.emit(
            TelemetryEvent(
                event_type="runtime.policy.evaluated",
                source=self.source,
                level=(
                    TelemetryEventLevel.ERROR
                    if result.denied
                    else (
                        TelemetryEventLevel.WARNING
                        if result.warning_count > 0
                        else TelemetryEventLevel.INFO
                    )
                ),
                success=result.allowed,
                error_count=result.denial_count,
                payload={
                    "subject_type": result.subject_type,
                    "subject_repr": (repr(subject) if subject is not None else None),
                    "policy_phase": ((context or {}).get("policy_phase")),
                    "context": dict(context or {}),
                    "evaluation": result.to_dict(),
                },
                attributes={
                    "subject_type": result.subject_type,
                    "policy_count": len(result.results),
                    "warning_count": result.warning_count,
                    "denial_count": result.denial_count,
                    "skipped_count": result.skipped_count,
                    "evaluation_failure_count": len(result.failures),
                    "allowed": result.allowed,
                    "denied": result.denied,
                },
            )
        )

    async def emit_policy_denied(
        self,
        result: PolicyEvaluationResult,
        subject: Any | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        if not result.denied:
            return

        await self.observability_manager.emit(
            TelemetryEvent(
                event_type="runtime.policy.denied",
                source=self.source,
                level=TelemetryEventLevel.ERROR,
                success=False,
                error_count=result.denial_count,
                exception_details=(
                    result.failures[0].exception_details if result.failures else None
                ),
                payload={
                    "subject_type": result.subject_type,
                    "subject_repr": (repr(subject) if subject is not None else None),
                    "policy_phase": ((context or {}).get("policy_phase")),
                    "context": dict(context or {}),
                    "evaluation": result.to_dict(),
                },
                attributes={
                    "subject_type": result.subject_type,
                    "denial_count": result.denial_count,
                    "evaluation_failure_count": len(result.failures),
                },
            )
        )
