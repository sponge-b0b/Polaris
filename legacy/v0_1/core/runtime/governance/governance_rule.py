from __future__ import annotations

from typing import Any, Protocol

from core.runtime.governance.governance_result import GovernanceResult


class GovernanceRule(Protocol):
    """
    Runtime governance rule contract.

    Governance rules answer:

        Should this be allowed under operational/business constraints?

    They should not mutate runtime state or execute business actions.
    """

    @property
    def rule_name(
        self,
    ) -> str: ...

    @property
    def enabled(
        self,
    ) -> bool: ...

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult: ...


class BaseGovernanceRule:
    """
    Base class for governance rules.
    """

    rule_name: str = "base_governance_rule"

    enabled: bool = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        return GovernanceResult.allow(
            rule_name=self.rule_name,
            message="Governance rule allowed subject.",
        )
