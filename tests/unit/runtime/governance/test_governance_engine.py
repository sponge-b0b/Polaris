from __future__ import annotations

import asyncio
from typing import Any

import pytest

from core.runtime.governance.governance_engine import GovernanceEngine
from core.runtime.governance.governance_registry import GovernanceRegistry
from core.runtime.governance.governance_result import GovernanceResult
from core.runtime.governance.governance_rule import BaseGovernanceRule


class AllowTestRule(BaseGovernanceRule):
    rule_name = "allow_test"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        return GovernanceResult.allow(
            rule_name=self.rule_name,
            message="Allowed.",
        )


class WarnTestRule(BaseGovernanceRule):
    rule_name = "warn_test"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        return GovernanceResult.warn(
            rule_name=self.rule_name,
            message="Warning.",
            reason="test_warning",
        )


class DenyTestRule(BaseGovernanceRule):
    rule_name = "deny_test"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        return GovernanceResult.deny(
            rule_name=self.rule_name,
            message="Denied.",
            reason="test_denial",
        )


class ApprovalTestRule(BaseGovernanceRule):
    rule_name = "approval_test"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        return GovernanceResult.require_approval(
            rule_name=self.rule_name,
            message="Approval required.",
            reason="test_approval_required",
        )


class DisabledTestRule(BaseGovernanceRule):
    rule_name = "disabled_test"
    enabled = False

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        return GovernanceResult.deny(
            rule_name=self.rule_name,
            message="Should not run.",
        )


class ExceptionTestRule(BaseGovernanceRule):
    rule_name = "exception_test"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        raise RuntimeError("governance exploded")


@pytest.mark.asyncio
async def test_governance_engine_allows_when_all_rules_allow() -> None:
    engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                AllowTestRule(),
            ],
        ),
    )

    result = await engine.evaluate(
        subject={
            "name": "subject",
        },
    )

    assert result.allowed is True
    assert result.blocking is False
    assert result.denied is False
    assert result.requires_approval is False
    assert result.denial_count == 0
    assert result.approval_count == 0
    assert len(result.results) == 1
    assert result.results[0].rule_name == "allow_test"


@pytest.mark.asyncio
async def test_governance_engine_warns_without_blocking() -> None:
    engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                AllowTestRule(),
                WarnTestRule(),
            ],
        ),
    )

    result = await engine.evaluate(
        subject={
            "name": "subject",
        },
    )

    assert result.allowed is True
    assert result.blocking is False
    assert result.warning_count == 1
    assert result.denial_count == 0
    assert result.approval_count == 0


@pytest.mark.asyncio
async def test_governance_engine_denies_when_any_rule_denies() -> None:
    engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                AllowTestRule(),
                DenyTestRule(),
            ],
        ),
    )

    result = await engine.evaluate(
        subject={
            "name": "subject",
        },
    )

    assert result.allowed is False
    assert result.blocking is True
    assert result.denied is True
    assert result.denial_count == 1
    assert any(rule_result.rule_name == "deny_test" for rule_result in result.results)


@pytest.mark.asyncio
async def test_governance_engine_blocks_when_approval_required() -> None:
    engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                AllowTestRule(),
                ApprovalTestRule(),
            ],
        ),
    )

    result = await engine.evaluate(
        subject={
            "name": "subject",
        },
    )

    assert result.allowed is False
    assert result.blocking is True
    assert result.denied is False
    assert result.requires_approval is True
    assert result.approval_count == 1
    assert any(
        rule_result.rule_name == "approval_test" for rule_result in result.results
    )


@pytest.mark.asyncio
async def test_governance_engine_excludes_disabled_rules_by_default() -> None:
    engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                AllowTestRule(),
                DisabledTestRule(),
            ],
        ),
    )

    result = await engine.evaluate(
        subject={
            "name": "subject",
        },
    )

    assert result.allowed is True
    assert len(result.results) == 1
    assert result.results[0].rule_name == "allow_test"


@pytest.mark.asyncio
async def test_governance_engine_can_evaluate_selected_rule_names() -> None:
    engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                AllowTestRule(),
                DenyTestRule(),
            ],
        ),
    )

    result = await engine.evaluate(
        subject={
            "name": "subject",
        },
        rule_names=[
            "allow_test",
        ],
    )

    assert result.allowed is True
    assert len(result.results) == 1
    assert result.results[0].rule_name == "allow_test"


@pytest.mark.asyncio
async def test_governance_engine_turns_rule_exception_into_denial() -> None:
    engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                ExceptionTestRule(),
            ],
        ),
    )

    result = await engine.evaluate(
        subject={
            "name": "subject",
        },
    )

    assert result.blocking is True
    assert result.denied is True
    assert result.denial_count == 1
    assert result.results[0].rule_name == "exception_test"
    assert result.results[0].reason == "governance exploded"
    assert result.results[0].metadata["error_type"] == "RuntimeError"
    assert len(result.failures) == 1
    assert result.failures[0].rule_name == "exception_test"
    assert result.failures[0].exception_details.exception_type == "RuntimeError"
    assert result.failures[0].exception_details.message == "governance exploded"
    assert "test_governance_engine.py" in (
        result.failures[0].exception_details.stack_trace
    )


@pytest.mark.asyncio
async def test_governance_engine_fail_fast_stops_after_first_blocking_rule() -> None:
    engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                DenyTestRule(),
                AllowTestRule(),
            ],
        ),
        fail_fast=True,
    )

    result = await engine.evaluate(
        subject={
            "name": "subject",
        },
        rule_names=[
            "deny_test",
            "allow_test",
        ],
    )

    assert result.blocking is True
    assert len(result.results) == 1
    assert result.results[0].rule_name == "deny_test"


@pytest.mark.asyncio
async def test_governance_engine_require_allowed_raises_when_denied() -> None:
    engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                DenyTestRule(),
            ],
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="test_denial",
    ):
        await engine.require_allowed(
            subject={
                "name": "subject",
            },
        )


@pytest.mark.asyncio
async def test_governance_engine_require_allowed_raises_when_approval_required() -> (
    None
):
    engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                ApprovalTestRule(),
            ],
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="test_approval_required",
    ):
        await engine.require_allowed(
            subject={
                "name": "subject",
            },
        )


@pytest.mark.asyncio
async def test_governance_engine_require_allowed_returns_when_allowed() -> None:
    engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                AllowTestRule(),
            ],
        ),
    )

    result = await engine.require_allowed(
        subject={
            "name": "subject",
        },
    )

    assert result.allowed is True


def test_governance_engine_to_dict() -> None:
    engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                AllowTestRule(),
            ],
        ),
        fail_fast=True,
    )

    data = engine.to_dict()

    assert data["engine"] == "GovernanceEngine"
    assert data["fail_fast"] is True
    assert data["registry"]["rule_count"] == 1


class CancelledTestRule(BaseGovernanceRule):
    rule_name = "cancelled_test"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        raise asyncio.CancelledError


@pytest.mark.asyncio
async def test_governance_engine_propagates_rule_cancellation() -> None:
    engine = GovernanceEngine(
        registry=GovernanceRegistry(rules=[CancelledTestRule()]),
    )

    with pytest.raises(asyncio.CancelledError):
        await engine.evaluate(subject={"name": "subject"})
