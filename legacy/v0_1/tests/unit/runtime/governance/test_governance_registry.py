from __future__ import annotations

import pytest

from core.runtime.governance.builtins.allow_all_governance_rule import (
    AllowAllGovernanceRule,
)
from core.runtime.governance.governance_registry import GovernanceRegistry


def test_governance_registry_registers_and_lists_rule() -> None:
    registry = GovernanceRegistry()

    rule = AllowAllGovernanceRule()

    registry.register(
        rule,
    )

    assert registry.exists(
        "allow_all_governance",
    )

    assert (
        registry.get(
            "allow_all_governance",
        )
        is rule
    )

    assert registry.list_rule_names() == [
        "allow_all_governance",
    ]


def test_governance_registry_rejects_duplicate_without_overwrite() -> None:
    registry = GovernanceRegistry()

    registry.register(
        AllowAllGovernanceRule(),
    )

    with pytest.raises(
        ValueError,
    ):
        registry.register(
            AllowAllGovernanceRule(),
        )


def test_governance_registry_allows_duplicate_with_overwrite() -> None:
    registry = GovernanceRegistry()

    first_rule = AllowAllGovernanceRule()
    second_rule = AllowAllGovernanceRule()

    registry.register(
        first_rule,
    )

    registry.register(
        second_rule,
        overwrite=True,
    )

    assert (
        registry.get(
            "allow_all_governance",
        )
        is second_rule
    )


def test_governance_registry_unregisters_rule() -> None:
    registry = GovernanceRegistry()

    registry.register(
        AllowAllGovernanceRule(),
    )

    registry.unregister(
        "allow_all_governance",
    )

    assert not registry.exists(
        "allow_all_governance",
    )


def test_governance_registry_unregister_missing_rule_raises() -> None:
    registry = GovernanceRegistry()

    with pytest.raises(
        KeyError,
    ):
        registry.unregister(
            "missing_rule",
        )


def test_governance_registry_get_missing_rule_raises() -> None:
    registry = GovernanceRegistry()

    with pytest.raises(
        KeyError,
    ):
        registry.get(
            "missing_rule",
        )


def test_governance_registry_to_dict() -> None:
    registry = GovernanceRegistry(
        rules=[
            AllowAllGovernanceRule(),
        ],
    )

    data = registry.to_dict()

    assert data["registry"] == "GovernanceRegistry"
    assert data["rule_count"] == 1
    assert data["rules"][0]["rule_name"] == "allow_all_governance"
    assert data["rules"][0]["enabled"] is True
    assert data["rules"][0]["rule_class"] == "AllowAllGovernanceRule"
