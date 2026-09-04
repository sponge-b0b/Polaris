from __future__ import annotations

from typing import Any

from core.runtime.policies.policy import BaseRuntimePolicy
from core.runtime.policies.policy_result import PolicyResult


class AllowAllPolicy(BaseRuntimePolicy):
    """
    Built-in policy that always allows the subject.

    Useful for:
    - tests
    - default permissive runtime mode
    - policy pipeline validation
    """

    policy_name = "allow_all"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> PolicyResult:
        return PolicyResult.allow(
            policy_name=self.policy_name,
            message="Subject allowed by AllowAllPolicy.",
            metadata={
                "subject_type": subject.__class__.__name__,
            },
        )
