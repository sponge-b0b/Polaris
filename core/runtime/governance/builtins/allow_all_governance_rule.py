from __future__ import annotations

from typing import Any

from core.runtime.governance.governance_result import GovernanceResult
from core.runtime.governance.governance_rule import BaseGovernanceRule


class AllowAllGovernanceRule(BaseGovernanceRule):
    """
    Built-in governance rule that always allows the subject.

    Useful for:
    - tests
    - default permissive governance mode
    - governance pipeline validation
    """

    rule_name = "allow_all_governance"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        return GovernanceResult.allow(
            rule_name=self.rule_name,
            message="Subject allowed by AllowAllGovernanceRule.",
            metadata={
                "subject_type": subject.__class__.__name__,
            },
        )
