from __future__ import annotations

from typing import Any

from core.runtime.governance.governance_result import (
    GovernanceResult,
)
from core.runtime.governance.governance_rule import (
    BaseGovernanceRule,
)


class RequireApprovalForLiveModeRule(
    BaseGovernanceRule,
):
    """
    Require approval before executing live workflows.

    Expected context:

        {
            "mode": "live"
        }

    or

        {
            "execution_mode": "live"
        }

    Any non-live mode is allowed.
    """

    rule_name = "require_approval_for_live_mode"

    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        context = context or {}

        mode = (
            context.get(
                "mode",
            )
            or context.get(
                "execution_mode",
            )
            or context.get(
                "runtime_mode",
            )
        )

        if mode != "live":
            return GovernanceResult.allow(
                rule_name=self.rule_name,
                message=("Execution mode does not require approval."),
                metadata={
                    "mode": mode,
                },
            )

        return GovernanceResult.require_approval(
            rule_name=self.rule_name,
            message=("Live execution requires approval."),
            reason="live_mode_requires_approval",
            metadata={
                "mode": mode,
                "subject_type": (subject.__class__.__name__),
            },
        )
