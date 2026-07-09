from __future__ import annotations

import asyncio

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import TYPE_CHECKING
from typing import Any

from core.runtime.governance.governance_registry import GovernanceRegistry
from core.runtime.governance.governance_result import (
    GovernanceDecision,
    GovernanceResult,
)
from core.runtime.governance.governance_rule import GovernanceRule
from core.telemetry.events.telemetry_exception_details import (
    TelemetryExceptionDetails,
)

if TYPE_CHECKING:
    from core.runtime.governance.governance_telemetry import (
        GovernanceTelemetryEmitter,
    )


@dataclass(frozen=True, slots=True)
class GovernanceEvaluationFailure:
    rule_name: str
    exception_details: TelemetryExceptionDetails

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "exception_type": self.exception_details.exception_type,
            "message": self.exception_details.message,
        }


@dataclass(frozen=True, slots=True)
class GovernanceEvaluationResult:
    subject_type: str
    results: tuple[GovernanceResult, ...]
    failures: tuple[GovernanceEvaluationFailure, ...] = ()
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return not any(result.blocking for result in self.results)

    @property
    def denied(self) -> bool:
        return any(result.denied for result in self.results)

    @property
    def requires_approval(self) -> bool:
        return any(result.requires_approval for result in self.results)

    @property
    def blocking(self) -> bool:
        return self.denied or self.requires_approval

    @property
    def warning_count(self) -> int:
        return sum(
            1 for result in self.results if result.decision == GovernanceDecision.WARN
        )

    @property
    def denial_count(self) -> int:
        return sum(
            1 for result in self.results if result.decision == GovernanceDecision.DENY
        )

    @property
    def approval_count(self) -> int:
        return sum(
            1
            for result in self.results
            if result.decision == GovernanceDecision.REQUIRE_APPROVAL
        )

    @property
    def skipped_count(self) -> int:
        return sum(
            1 for result in self.results if result.decision == GovernanceDecision.SKIP
        )

    def raise_if_blocking(self) -> None:
        if not self.blocking:
            return

        blocking_results = [
            result.to_dict() for result in self.results if result.blocking
        ]

        raise RuntimeError(f"Governance evaluation blocked subject: {blocking_results}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_type": self.subject_type,
            "allowed": self.allowed,
            "denied": self.denied,
            "requires_approval": self.requires_approval,
            "blocking": self.blocking,
            "warning_count": self.warning_count,
            "denial_count": self.denial_count,
            "approval_count": self.approval_count,
            "skipped_count": self.skipped_count,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "results": [result.to_dict() for result in self.results],
            "failures": [failure.to_dict() for failure in self.failures],
            "metadata": deepcopy(self.metadata),
        }


class GovernanceEngine:
    def __init__(
        self,
        registry: GovernanceRegistry | None = None,
        fail_fast: bool = False,
        telemetry_emitter: GovernanceTelemetryEmitter | None = None,
    ) -> None:
        self.registry = registry or GovernanceRegistry()
        self.fail_fast = fail_fast
        self.telemetry_emitter = telemetry_emitter

    def register_rule(
        self,
        rule: GovernanceRule,
        overwrite: bool = False,
    ) -> None:
        self.registry.register(
            rule=rule,
            overwrite=overwrite,
        )

    def unregister_rule(
        self,
        rule_name: str,
    ) -> None:
        self.registry.unregister(
            rule_name,
        )

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
        rule_names: list[str] | None = None,
        emit_telemetry: bool = True,
    ) -> GovernanceEvaluationResult:
        started_at = datetime.now(timezone.utc)

        rules = self._select_rules(
            rule_names=rule_names,
        )

        results: list[GovernanceResult] = []
        failures: list[GovernanceEvaluationFailure] = []

        if self.fail_fast:
            for rule in rules:
                result = await self._evaluate_rule(
                    rule=rule,
                    subject=subject,
                    context=context,
                )

                results.append(result)

                if result.blocking:
                    break
        else:
            gathered = await asyncio.gather(
                *[
                    self._evaluate_rule(
                        rule=rule,
                        subject=subject,
                        context=context,
                    )
                    for rule in rules
                ],
                return_exceptions=True,
            )

            for rule, gathered_result in zip(rules, gathered):
                if isinstance(gathered_result, GovernanceResult):
                    results.append(gathered_result)
                    continue

                if isinstance(gathered_result, asyncio.CancelledError):
                    raise gathered_result

                if isinstance(gathered_result, BaseException):
                    failures.append(
                        GovernanceEvaluationFailure(
                            rule_name=rule.rule_name,
                            exception_details=(
                                TelemetryExceptionDetails.from_exception(
                                    gathered_result,
                                )
                            ),
                        )
                    )
                    results.append(
                        GovernanceResult.deny(
                            rule_name=rule.rule_name,
                            message=(
                                "Governance rule evaluation failed with exception."
                            ),
                            reason=str(gathered_result),
                            metadata={
                                "error_type": type(gathered_result).__name__,
                            },
                        )
                    )

        completed_at = datetime.now(timezone.utc)

        evaluation_result = GovernanceEvaluationResult(
            subject_type=subject.__class__.__name__,
            results=tuple(results),
            failures=tuple(failures),
            started_at=started_at,
            completed_at=completed_at,
            metadata={
                "rule_count": len(rules),
                "fail_fast": self.fail_fast,
                "selected_rule_names": (
                    list(rule_names) if rule_names is not None else None
                ),
            },
        )

        if emit_telemetry:
            await self._emit_telemetry(
                result=evaluation_result,
                subject=subject,
                context=context,
            )

        return evaluation_result

    async def require_allowed(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
        rule_names: list[str] | None = None,
        emit_telemetry: bool = True,
    ) -> GovernanceEvaluationResult:
        result = await self.evaluate(
            subject=subject,
            context=context,
            rule_names=rule_names,
            emit_telemetry=emit_telemetry,
        )

        result.raise_if_blocking()

        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine": self.__class__.__name__,
            "fail_fast": self.fail_fast,
            "registry": self.registry.to_dict(),
            "telemetry_enabled": self.telemetry_emitter is not None,
            "telemetry_emitter": (
                self.telemetry_emitter.__class__.__name__
                if self.telemetry_emitter is not None
                else None
            ),
        }

    def _select_rules(
        self,
        rule_names: list[str] | None,
    ) -> list[GovernanceRule]:
        if rule_names is None:
            return self.registry.list_rules(
                enabled_only=True,
            )

        selected: list[GovernanceRule] = []

        for rule_name in rule_names:
            rule = self.registry.get(rule_name)

            if rule.enabled:
                selected.append(rule)

        return selected

    async def _evaluate_rule(
        self,
        rule: GovernanceRule,
        subject: Any,
        context: dict[str, Any] | None,
    ) -> GovernanceResult:
        if not rule.enabled:
            return GovernanceResult.skip(
                rule_name=rule.rule_name,
                message="Governance rule is disabled.",
            )

        return await rule.evaluate(
            subject=subject,
            context=context or {},
        )

    async def _emit_telemetry(
        self,
        result: GovernanceEvaluationResult,
        subject: Any,
        context: dict[str, Any] | None,
    ) -> None:
        if self.telemetry_emitter is None:
            return

        await self.telemetry_emitter.emit_governance_evaluated(
            result=result,
            subject=subject,
            context=context,
        )

        if result.blocking:
            await self.telemetry_emitter.emit_governance_blocked(
                result=result,
                subject=subject,
                context=context,
            )
