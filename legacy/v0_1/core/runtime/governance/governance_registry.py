from __future__ import annotations

from typing import Any

from core.runtime.governance.governance_rule import GovernanceRule


class GovernanceRegistry:
    """
    Registry for runtime governance rules.

    Maintains named governance rule instances and provides ordered retrieval
    for governance evaluation.
    """

    def __init__(
        self,
        rules: list[GovernanceRule] | None = None,
    ) -> None:
        self._rules: dict[str, GovernanceRule] = {}

        for rule in rules or []:
            self.register(
                rule,
            )

    def register(
        self,
        rule: GovernanceRule,
        overwrite: bool = False,
    ) -> None:
        rule_name = rule.rule_name

        if not rule_name.strip():
            raise ValueError("Governance rule name cannot be empty.")

        if rule_name in self._rules and not overwrite:
            raise ValueError(f"Governance rule already registered: {rule_name}")

        self._rules[rule_name] = rule

    def unregister(
        self,
        rule_name: str,
    ) -> None:
        if rule_name not in self._rules:
            raise KeyError(f"Governance rule not registered: {rule_name}")

        del self._rules[rule_name]

    def get(
        self,
        rule_name: str,
    ) -> GovernanceRule:
        rule = self._rules.get(
            rule_name,
        )

        if rule is None:
            raise KeyError(f"Governance rule not registered: {rule_name}")

        return rule

    def exists(
        self,
        rule_name: str,
    ) -> bool:
        return rule_name in self._rules

    def list_rule_names(
        self,
        enabled_only: bool = False,
    ) -> list[str]:
        return [
            rule.rule_name
            for rule in self.list_rules(
                enabled_only=enabled_only,
            )
        ]

    def list_rules(
        self,
        enabled_only: bool = False,
    ) -> list[GovernanceRule]:
        rules = list(
            self._rules.values(),
        )

        if enabled_only:
            rules = [rule for rule in rules if rule.enabled]

        return sorted(
            rules,
            key=lambda rule: rule.rule_name,
        )

    def clear(
        self,
    ) -> None:
        self._rules.clear()

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "registry": self.__class__.__name__,
            "rule_count": len(self._rules),
            "rules": [
                {
                    "rule_name": rule.rule_name,
                    "enabled": rule.enabled,
                    "rule_class": rule.__class__.__name__,
                }
                for rule in self.list_rules()
            ],
        }
