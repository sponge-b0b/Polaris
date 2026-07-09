from __future__ import annotations

from typing import Any

from core.runtime.policies.policy import RuntimePolicy


class PolicyRegistry:
    """
    Registry for runtime policies.

    Maintains named policy instances and provides ordered retrieval for
    policy evaluation.
    """

    def __init__(
        self,
        policies: list[RuntimePolicy] | None = None,
    ) -> None:
        self._policies: dict[str, RuntimePolicy] = {}

        for policy in policies or []:
            self.register(
                policy,
            )

    def register(
        self,
        policy: RuntimePolicy,
        overwrite: bool = False,
    ) -> None:
        policy_name = policy.policy_name

        if not policy_name.strip():
            raise ValueError("Policy name cannot be empty.")

        if policy_name in self._policies and not overwrite:
            raise ValueError(f"Policy already registered: {policy_name}")

        self._policies[policy_name] = policy

    def unregister(
        self,
        policy_name: str,
    ) -> None:
        if policy_name not in self._policies:
            raise KeyError(f"Policy not registered: {policy_name}")

        del self._policies[policy_name]

    def get(
        self,
        policy_name: str,
    ) -> RuntimePolicy:
        policy = self._policies.get(
            policy_name,
        )

        if policy is None:
            raise KeyError(f"Policy not registered: {policy_name}")

        return policy

    def exists(
        self,
        policy_name: str,
    ) -> bool:
        return policy_name in self._policies

    def list_policy_names(
        self,
        enabled_only: bool = False,
    ) -> list[str]:
        policies = self.list_policies(
            enabled_only=enabled_only,
        )

        return [policy.policy_name for policy in policies]

    def list_policies(
        self,
        enabled_only: bool = False,
    ) -> list[RuntimePolicy]:
        policies = list(
            self._policies.values(),
        )

        if enabled_only:
            policies = [policy for policy in policies if policy.enabled]

        return sorted(
            policies,
            key=lambda policy: policy.policy_name,
        )

    def clear(
        self,
    ) -> None:
        self._policies.clear()

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "registry": self.__class__.__name__,
            "policy_count": len(self._policies),
            "policies": [
                {
                    "policy_name": policy.policy_name,
                    "enabled": policy.enabled,
                    "policy_class": policy.__class__.__name__,
                }
                for policy in self.list_policies()
            ],
        }
