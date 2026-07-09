from __future__ import annotations

from typing import Any

from core.runtime.policies.policy import BaseRuntimePolicy
from core.runtime.policies.policy_result import PolicyResult


class DenyDisabledWorkflowPolicy(BaseRuntimePolicy):
    """
    Denies disabled workflow-like subjects.

    A subject is considered disabled when it exposes:

        enabled = False

    This works for workflow definitions, plugin manifests, execution plans,
    or any object that follows the enabled flag convention.
    """

    policy_name = "deny_disabled_workflow"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> PolicyResult:
        subject_enabled = getattr(
            subject,
            "enabled",
            True,
        )

        if subject_enabled is False:
            return PolicyResult.deny(
                policy_name=self.policy_name,
                message="Subject is disabled.",
                reason="enabled=False",
                metadata={
                    "subject_type": subject.__class__.__name__,
                },
            )

        return PolicyResult.allow(
            policy_name=self.policy_name,
            message="Subject is enabled.",
            metadata={
                "subject_type": subject.__class__.__name__,
            },
        )
