from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    DENY = "deny"
    SKIP = "skip"


@dataclass(frozen=True, slots=True)
class PolicyResult:
    policy_name: str
    decision: PolicyDecision
    message: str = ""
    reason: str | None = None
    severity: str = "info"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.decision in {
            PolicyDecision.ALLOW,
            PolicyDecision.WARN,
        }

    @property
    def denied(self) -> bool:
        return self.decision == PolicyDecision.DENY

    @property
    def skipped(self) -> bool:
        return self.decision == PolicyDecision.SKIP

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_name": self.policy_name,
            "decision": self.decision.value,
            "message": self.message,
            "reason": self.reason,
            "severity": self.severity,
            "allowed": self.allowed,
            "metadata": deepcopy(self.metadata),
        }

    @classmethod
    def allow(
        cls,
        policy_name: str,
        message: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> PolicyResult:
        return cls(
            policy_name=policy_name,
            decision=PolicyDecision.ALLOW,
            message=message,
            metadata=deepcopy(metadata or {}),
        )

    @classmethod
    def warn(
        cls,
        policy_name: str,
        message: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PolicyResult:
        return cls(
            policy_name=policy_name,
            decision=PolicyDecision.WARN,
            message=message,
            reason=reason,
            severity="warning",
            metadata=deepcopy(metadata or {}),
        )

    @classmethod
    def deny(
        cls,
        policy_name: str,
        message: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PolicyResult:
        return cls(
            policy_name=policy_name,
            decision=PolicyDecision.DENY,
            message=message,
            reason=reason,
            severity="error",
            metadata=deepcopy(metadata or {}),
        )

    @classmethod
    def skip(
        cls,
        policy_name: str,
        message: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PolicyResult:
        return cls(
            policy_name=policy_name,
            decision=PolicyDecision.SKIP,
            message=message,
            reason=reason,
            metadata=deepcopy(metadata or {}),
        )
