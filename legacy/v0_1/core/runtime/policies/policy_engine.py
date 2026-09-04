from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from core.runtime.policies.policy import RuntimePolicy
from core.runtime.policies.policy_registry import PolicyRegistry
from core.runtime.policies.policy_result import (
    PolicyDecision,
    PolicyResult,
)
from core.telemetry.events.telemetry_exception_details import (
    TelemetryExceptionDetails,
)

if TYPE_CHECKING:
    from core.runtime.policies.policy_telemetry import (
        PolicyTelemetryEmitter,
    )


@dataclass(frozen=True, slots=True)
class PolicyEvaluationFailure:
    policy_name: str
    exception_details: TelemetryExceptionDetails

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_name": self.policy_name,
            "exception_type": self.exception_details.exception_type,
            "message": self.exception_details.message,
        }


@dataclass(frozen=True, slots=True)
class PolicyEvaluationResult:
    """
    Aggregate result from evaluating one or more runtime policies.
    """

    subject_type: str

    results: tuple[PolicyResult, ...]

    failures: tuple[PolicyEvaluationFailure, ...] = ()

    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    completed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    @property
    def allowed(
        self,
    ) -> bool:
        return not any(result.denied for result in self.results)

    @property
    def denied(
        self,
    ) -> bool:
        return not self.allowed

    @property
    def warning_count(
        self,
    ) -> int:
        return sum(
            1 for result in self.results if result.decision == PolicyDecision.WARN
        )

    @property
    def denial_count(
        self,
    ) -> int:
        return sum(
            1 for result in self.results if result.decision == PolicyDecision.DENY
        )

    @property
    def skipped_count(
        self,
    ) -> int:
        return sum(
            1 for result in self.results if result.decision == PolicyDecision.SKIP
        )

    def raise_if_denied(
        self,
    ) -> None:
        if not self.denied:
            return

        denied_results = [result.to_dict() for result in self.results if result.denied]

        raise RuntimeError(f"Policy evaluation denied subject: {denied_results}")

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "subject_type": self.subject_type,
            "allowed": self.allowed,
            "denied": self.denied,
            "warning_count": self.warning_count,
            "denial_count": self.denial_count,
            "skipped_count": self.skipped_count,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "results": [result.to_dict() for result in self.results],
            "failures": [failure.to_dict() for failure in self.failures],
            "metadata": deepcopy(self.metadata),
        }


class PolicyEngine:
    """
    Runtime policy evaluation engine.

    Evaluates registered runtime policies against a subject and optionally
    emits observability telemetry for policy decisions.
    """

    def __init__(
        self,
        registry: PolicyRegistry | None = None,
        fail_fast: bool = False,
        telemetry_emitter: PolicyTelemetryEmitter | None = None,
    ) -> None:
        self.registry = registry or PolicyRegistry()
        self.fail_fast = fail_fast
        self.telemetry_emitter = telemetry_emitter

    def register_policy(
        self,
        policy: RuntimePolicy,
        overwrite: bool = False,
    ) -> None:
        self.registry.register(
            policy=policy,
            overwrite=overwrite,
        )

    def unregister_policy(
        self,
        policy_name: str,
    ) -> None:
        self.registry.unregister(
            policy_name,
        )

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
        policy_names: list[str] | None = None,
        emit_telemetry: bool = True,
    ) -> PolicyEvaluationResult:
        started_at = datetime.now(UTC)

        policies = self._select_policies(
            policy_names=policy_names,
        )

        results: list[PolicyResult] = []
        failures: list[PolicyEvaluationFailure] = []

        if self.fail_fast:
            for policy in policies:
                result = await self._evaluate_policy(
                    policy=policy,
                    subject=subject,
                    context=context,
                )

                results.append(
                    result,
                )

                if result.denied:
                    break

        else:
            gathered = await asyncio.gather(
                *[
                    self._evaluate_policy(
                        policy=policy,
                        subject=subject,
                        context=context,
                    )
                    for policy in policies
                ],
                return_exceptions=True,
            )

            for policy, gathered_result in zip(
                policies,
                gathered,
                strict=False,
            ):
                if isinstance(gathered_result, PolicyResult):
                    results.append(
                        gathered_result,
                    )
                    continue

                if isinstance(gathered_result, asyncio.CancelledError):
                    raise gathered_result

                if isinstance(gathered_result, BaseException):
                    failures.append(
                        PolicyEvaluationFailure(
                            policy_name=policy.policy_name,
                            exception_details=(
                                TelemetryExceptionDetails.from_exception(
                                    gathered_result,
                                )
                            ),
                        )
                    )
                    results.append(
                        PolicyResult.deny(
                            policy_name=policy.policy_name,
                            message=("Policy evaluation failed with exception."),
                            reason=str(gathered_result),
                            metadata={
                                "error_type": type(gathered_result).__name__,
                            },
                        )
                    )

        completed_at = datetime.now(UTC)

        evaluation_result = PolicyEvaluationResult(
            subject_type=subject.__class__.__name__,
            results=tuple(results),
            failures=tuple(failures),
            started_at=started_at,
            completed_at=completed_at,
            metadata={
                "policy_count": len(policies),
                "fail_fast": self.fail_fast,
                "selected_policy_names": (
                    list(policy_names) if policy_names is not None else None
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
        policy_names: list[str] | None = None,
        emit_telemetry: bool = True,
    ) -> PolicyEvaluationResult:
        result = await self.evaluate(
            subject=subject,
            context=context,
            policy_names=policy_names,
            emit_telemetry=emit_telemetry,
        )

        result.raise_if_denied()

        return result

    def to_dict(
        self,
    ) -> dict[str, Any]:
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

    def _select_policies(
        self,
        policy_names: list[str] | None,
    ) -> list[RuntimePolicy]:
        if policy_names is None:
            return self.registry.list_policies(
                enabled_only=True,
            )

        selected: list[RuntimePolicy] = []

        for policy_name in policy_names:
            policy = self.registry.get(
                policy_name,
            )

            if policy.enabled:
                selected.append(
                    policy,
                )

        return selected

    async def _evaluate_policy(
        self,
        policy: RuntimePolicy,
        subject: Any,
        context: dict[str, Any] | None,
    ) -> PolicyResult:
        if not policy.enabled:
            return PolicyResult.skip(
                policy_name=policy.policy_name,
                message="Policy is disabled.",
            )

        return await policy.evaluate(
            subject=subject,
            context=context or {},
        )

    async def _emit_telemetry(
        self,
        result: PolicyEvaluationResult,
        subject: Any,
        context: dict[str, Any] | None,
    ) -> None:
        if self.telemetry_emitter is None:
            return

        await self.telemetry_emitter.emit_policy_evaluated(
            result=result,
            subject=subject,
            context=context,
        )

        if result.denied:
            await self.telemetry_emitter.emit_policy_denied(
                result=result,
                subject=subject,
                context=context,
            )
