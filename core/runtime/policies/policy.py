from __future__ import annotations

from typing import Any
from typing import Protocol

from core.runtime.policies.policy_result import PolicyResult


class RuntimePolicy(Protocol):
    """
    Runtime policy contract.

    Policies inspect runtime inputs and return PolicyResult.
    They should not mutate state or execute business actions.
    """

    @property
    def policy_name(self) -> str: ...

    @property
    def enabled(self) -> bool: ...

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> PolicyResult: ...


class BaseRuntimePolicy:
    """
    Base class for runtime policies.
    """

    policy_name: str = "base_runtime_policy"
    enabled: bool = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> PolicyResult:
        return PolicyResult.allow(
            policy_name=self.policy_name,
            message="Policy allowed subject.",
        )
