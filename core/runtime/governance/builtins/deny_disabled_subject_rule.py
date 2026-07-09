from __future__ import annotations

from typing import Any

from core.runtime.governance.governance_result import GovernanceResult
from core.runtime.governance.governance_rule import BaseGovernanceRule


class DenyDisabledSubjectRule(BaseGovernanceRule):
    """
    Deny subjects that expose enabled=False.

    Useful for:
    - disabled workflows
    - disabled plugins
    - disabled runtime nodes
    - disabled execution plans
    """

    rule_name = "deny_disabled_subject"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        subject_enabled = getattr(
            subject,
            "enabled",
            True,
        )

        if subject_enabled is False:
            return GovernanceResult.deny(
                rule_name=self.rule_name,
                message="Subject is disabled.",
                reason="enabled_false",
                metadata={
                    "subject_type": subject.__class__.__name__,
                },
            )

        return GovernanceResult.allow(
            rule_name=self.rule_name,
            message="Subject is enabled.",
            metadata={
                "subject_type": subject.__class__.__name__,
            },
        )
