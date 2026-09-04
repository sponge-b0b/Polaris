from __future__ import annotations

import pytest

from core.runtime.policies.builtins.allow_all_policy import AllowAllPolicy
from core.runtime.policies.policy_registry import PolicyRegistry


def test_policy_registry_registers_and_lists_policy() -> None:
    registry = PolicyRegistry()

    policy = AllowAllPolicy()

    registry.register(
        policy,
    )

    assert registry.exists(
        "allow_all",
    )

    assert (
        registry.get(
            "allow_all",
        )
        is policy
    )

    assert registry.list_policy_names() == [
        "allow_all",
    ]


def test_policy_registry_rejects_duplicate_without_overwrite() -> None:
    registry = PolicyRegistry()

    registry.register(
        AllowAllPolicy(),
    )

    with pytest.raises(
        ValueError,
    ):
        registry.register(
            AllowAllPolicy(),
        )


def test_policy_registry_allows_duplicate_with_overwrite() -> None:
    registry = PolicyRegistry()

    first_policy = AllowAllPolicy()
    second_policy = AllowAllPolicy()

    registry.register(
        first_policy,
    )

    registry.register(
        second_policy,
        overwrite=True,
    )

    assert (
        registry.get(
            "allow_all",
        )
        is second_policy
    )


def test_policy_registry_unregisters_policy() -> None:
    registry = PolicyRegistry()

    registry.register(
        AllowAllPolicy(),
    )

    registry.unregister(
        "allow_all",
    )

    assert not registry.exists(
        "allow_all",
    )


def test_policy_registry_unregister_missing_policy_raises() -> None:
    registry = PolicyRegistry()

    with pytest.raises(
        KeyError,
    ):
        registry.unregister(
            "missing_policy",
        )


def test_policy_registry_get_missing_policy_raises() -> None:
    registry = PolicyRegistry()

    with pytest.raises(
        KeyError,
    ):
        registry.get(
            "missing_policy",
        )


def test_policy_registry_to_dict() -> None:
    registry = PolicyRegistry(
        policies=[
            AllowAllPolicy(),
        ],
    )

    data = registry.to_dict()

    assert data["registry"] == "PolicyRegistry"
    assert data["policy_count"] == 1
    assert data["policies"][0]["policy_name"] == "allow_all"
    assert data["policies"][0]["enabled"] is True
    assert data["policies"][0]["policy_class"] == "AllowAllPolicy"
