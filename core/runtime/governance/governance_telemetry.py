from __future__ import annotations

from typing import Any

from core.runtime.governance.governance_engine import (
    GovernanceEvaluationResult,
)
from core.telemetry.events.telemetry_event import (
    TelemetryEvent,
    TelemetryEventLevel,
)
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)


class GovernanceTelemetryEmitter:
    """
    Emits telemetry for governance evaluations.
    """

    def __init__(
        self,
        observability_manager: ObservabilityManager,
        source: str = "runtime.governance",
    ) -> None:
        self.observability_manager = observability_manager
        self.source = source

    async def emit_governance_evaluated(
        self,
        result: GovernanceEvaluationResult,
        subject: Any | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        await self.observability_manager.emit(
            TelemetryEvent(
                event_type="runtime.governance.evaluated",
                source=self.source,
                level=self._level_from_result(
                    result,
                ),
                success=result.allowed,
                error_count=result.denial_count,
                payload={
                    "subject_type": result.subject_type,
                    "subject_repr": (repr(subject) if subject is not None else None),
                    "governance_phase": ((context or {}).get("governance_phase")),
                    "context": dict(context or {}),
                    "evaluation": result.to_dict(),
                },
                attributes={
                    "subject_type": result.subject_type,
                    "rule_count": len(result.results),
                    "warning_count": result.warning_count,
                    "denial_count": result.denial_count,
                    "approval_count": result.approval_count,
                    "skipped_count": result.skipped_count,
                    "evaluation_failure_count": len(result.failures),
                    "allowed": result.allowed,
                    "denied": result.denied,
                    "requires_approval": result.requires_approval,
                    "blocking": result.blocking,
                },
            )
        )

    async def emit_governance_blocked(
        self,
        result: GovernanceEvaluationResult,
        subject: Any | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        if not result.blocking:
            return

        await self.observability_manager.emit(
            TelemetryEvent(
                event_type="runtime.governance.blocked",
                source=self.source,
                level=(
                    TelemetryEventLevel.ERROR
                    if result.denied
                    else TelemetryEventLevel.WARNING
                ),
                success=False,
                error_count=(
                    result.denial_count
                    if result.denial_count > 0
                    else result.approval_count
                ),
                exception_details=(
                    result.failures[0].exception_details if result.failures else None
                ),
                payload={
                    "subject_type": result.subject_type,
                    "subject_repr": (repr(subject) if subject is not None else None),
                    "governance_phase": ((context or {}).get("governance_phase")),
                    "context": dict(context or {}),
                    "evaluation": result.to_dict(),
                },
                attributes={
                    "subject_type": result.subject_type,
                    "denial_count": result.denial_count,
                    "approval_count": result.approval_count,
                    "requires_approval": result.requires_approval,
                    "blocking": result.blocking,
                    "evaluation_failure_count": len(result.failures),
                },
            )
        )

    def _level_from_result(
        self,
        result: GovernanceEvaluationResult,
    ) -> TelemetryEventLevel:
        if result.denied:
            return TelemetryEventLevel.ERROR

        if result.requires_approval or result.warning_count > 0:
            return TelemetryEventLevel.WARNING

        return TelemetryEventLevel.INFO
