from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class GovernanceDecision(StrEnum):
    ALLOW = "allow"
    WARN = "warn"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    SKIP = "skip"


@dataclass(frozen=True, slots=True)
class GovernanceResult:
    """
    Result from evaluating a governance rule.
    """

    rule_name: str
    decision: GovernanceDecision
    message: str = ""
    reason: str | None = None
    severity: str = "info"
    approval_required: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.decision in {
            GovernanceDecision.ALLOW,
            GovernanceDecision.WARN,
        }

    @property
    def denied(self) -> bool:
        return self.decision == GovernanceDecision.DENY

    @property
    def requires_approval(self) -> bool:
        return self.decision == GovernanceDecision.REQUIRE_APPROVAL

    @property
    def skipped(self) -> bool:
        return self.decision == GovernanceDecision.SKIP

    @property
    def blocking(self) -> bool:
        return self.denied or self.requires_approval

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "decision": self.decision.value,
            "message": self.message,
            "reason": self.reason,
            "severity": self.severity,
            "approval_required": self.approval_required,
            "allowed": self.allowed,
            "denied": self.denied,
            "requires_approval": self.requires_approval,
            "blocking": self.blocking,
            "metadata": deepcopy(self.metadata),
        }

    @classmethod
    def allow(
        cls,
        rule_name: str,
        message: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        return cls(
            rule_name=rule_name,
            decision=GovernanceDecision.ALLOW,
            message=message,
            metadata=deepcopy(metadata or {}),
        )

    @classmethod
    def warn(
        cls,
        rule_name: str,
        message: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        return cls(
            rule_name=rule_name,
            decision=GovernanceDecision.WARN,
            message=message,
            reason=reason,
            severity="warning",
            metadata=deepcopy(metadata or {}),
        )

    @classmethod
    def deny(
        cls,
        rule_name: str,
        message: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        return cls(
            rule_name=rule_name,
            decision=GovernanceDecision.DENY,
            message=message,
            reason=reason,
            severity="error",
            metadata=deepcopy(metadata or {}),
        )

    @classmethod
    def require_approval(
        cls,
        rule_name: str,
        message: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        return cls(
            rule_name=rule_name,
            decision=GovernanceDecision.REQUIRE_APPROVAL,
            message=message,
            reason=reason,
            severity="warning",
            approval_required=True,
            metadata=deepcopy(metadata or {}),
        )

    @classmethod
    def skip(
        cls,
        rule_name: str,
        message: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        return cls(
            rule_name=rule_name,
            decision=GovernanceDecision.SKIP,
            message=message,
            reason=reason,
            metadata=deepcopy(metadata or {}),
        )
