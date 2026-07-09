from __future__ import annotations

import asyncio

from typing import Any

import pytest

from core.runtime.policies.policy import BaseRuntimePolicy
from core.runtime.policies.policy_engine import PolicyEngine
from core.runtime.policies.policy_registry import PolicyRegistry
from core.runtime.policies.policy_result import PolicyResult


class AllowTestPolicy(BaseRuntimePolicy):
    policy_name = "allow_test"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> PolicyResult:
        return PolicyResult.allow(
            policy_name=self.policy_name,
            message="Allowed.",
        )


class DenyTestPolicy(BaseRuntimePolicy):
    policy_name = "deny_test"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> PolicyResult:
        return PolicyResult.deny(
            policy_name=self.policy_name,
            message="Denied.",
            reason="test_denial",
        )


class WarnTestPolicy(BaseRuntimePolicy):
    policy_name = "warn_test"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> PolicyResult:
        return PolicyResult.warn(
            policy_name=self.policy_name,
            message="Warning.",
            reason="test_warning",
        )


class DisabledTestPolicy(BaseRuntimePolicy):
    policy_name = "disabled_test"
    enabled = False

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> PolicyResult:
        return PolicyResult.deny(
            policy_name=self.policy_name,
            message="Should not run.",
        )


class ExceptionTestPolicy(BaseRuntimePolicy):
    policy_name = "exception_test"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> PolicyResult:
        raise RuntimeError("policy exploded")


@pytest.mark.asyncio
async def test_policy_engine_allows_when_all_policies_allow() -> None:
    engine = PolicyEngine(
        registry=PolicyRegistry(
            policies=[
                AllowTestPolicy(),
            ],
        ),
    )

    result = await engine.evaluate(
        subject={"name": "subject"},
    )

    assert result.allowed is True
    assert result.denied is False
    assert result.denial_count == 0
    assert result.warning_count == 0
    assert len(result.results) == 1
    assert result.results[0].policy_name == "allow_test"


@pytest.mark.asyncio
async def test_policy_engine_denies_when_any_policy_denies() -> None:
    engine = PolicyEngine(
        registry=PolicyRegistry(
            policies=[
                AllowTestPolicy(),
                DenyTestPolicy(),
            ],
        ),
    )

    result = await engine.evaluate(
        subject={"name": "subject"},
    )

    assert result.allowed is False
    assert result.denied is True
    assert result.denial_count == 1
    assert any(
        policy_result.policy_name == "deny_test" for policy_result in result.results
    )


@pytest.mark.asyncio
async def test_policy_engine_counts_warnings() -> None:
    engine = PolicyEngine(
        registry=PolicyRegistry(
            policies=[
                AllowTestPolicy(),
                WarnTestPolicy(),
            ],
        ),
    )

    result = await engine.evaluate(
        subject={"name": "subject"},
    )

    assert result.allowed is True
    assert result.denied is False
    assert result.warning_count == 1
    assert result.denial_count == 0


@pytest.mark.asyncio
async def test_policy_engine_excludes_disabled_policies_by_default() -> None:
    engine = PolicyEngine(
        registry=PolicyRegistry(
            policies=[
                AllowTestPolicy(),
                DisabledTestPolicy(),
            ],
        ),
    )

    result = await engine.evaluate(
        subject={"name": "subject"},
    )

    assert result.allowed is True
    assert len(result.results) == 1
    assert result.results[0].policy_name == "allow_test"


@pytest.mark.asyncio
async def test_policy_engine_can_evaluate_selected_policy_names() -> None:
    engine = PolicyEngine(
        registry=PolicyRegistry(
            policies=[
                AllowTestPolicy(),
                DenyTestPolicy(),
            ],
        ),
    )

    result = await engine.evaluate(
        subject={"name": "subject"},
        policy_names=[
            "allow_test",
        ],
    )

    assert result.allowed is True
    assert len(result.results) == 1
    assert result.results[0].policy_name == "allow_test"


@pytest.mark.asyncio
async def test_policy_engine_turns_policy_exception_into_denial() -> None:
    engine = PolicyEngine(
        registry=PolicyRegistry(
            policies=[
                ExceptionTestPolicy(),
            ],
        ),
    )

    result = await engine.evaluate(
        subject={"name": "subject"},
    )

    assert result.denied is True
    assert result.denial_count == 1
    assert result.results[0].policy_name == "exception_test"
    assert result.results[0].reason == "policy exploded"
    assert result.results[0].metadata["error_type"] == "RuntimeError"
    assert len(result.failures) == 1
    assert result.failures[0].policy_name == "exception_test"
    assert result.failures[0].exception_details.exception_type == "RuntimeError"
    assert result.failures[0].exception_details.message == "policy exploded"
    assert "test_policy_engine.py" in (result.failures[0].exception_details.stack_trace)


@pytest.mark.asyncio
async def test_policy_engine_fail_fast_stops_after_first_denial() -> None:
    engine = PolicyEngine(
        registry=PolicyRegistry(
            policies=[
                DenyTestPolicy(),
                AllowTestPolicy(),
            ],
        ),
        fail_fast=True,
    )

    result = await engine.evaluate(
        subject={"name": "subject"},
    )

    result = await engine.evaluate(
        subject={"name": "subject"},
        policy_names=[
            "deny_test",
            "allow_test",
        ],
    )

    assert result.denied is True
    assert len(result.results) == 1
    assert result.results[0].policy_name == "deny_test"


@pytest.mark.asyncio
async def test_policy_engine_require_allowed_raises_when_denied() -> None:
    engine = PolicyEngine(
        registry=PolicyRegistry(
            policies=[
                DenyTestPolicy(),
            ],
        ),
    )

    with pytest.raises(
        RuntimeError,
    ):
        await engine.require_allowed(
            subject={"name": "subject"},
        )


@pytest.mark.asyncio
async def test_policy_engine_require_allowed_returns_when_allowed() -> None:
    engine = PolicyEngine(
        registry=PolicyRegistry(
            policies=[
                AllowTestPolicy(),
            ],
        ),
    )

    result = await engine.require_allowed(
        subject={"name": "subject"},
    )

    assert result.allowed is True


def test_policy_engine_to_dict() -> None:
    engine = PolicyEngine(
        registry=PolicyRegistry(
            policies=[
                AllowTestPolicy(),
            ],
        ),
        fail_fast=True,
    )

    data = engine.to_dict()

    assert data["engine"] == "PolicyEngine"
    assert data["fail_fast"] is True
    assert data["registry"]["policy_count"] == 1


class CancelledTestPolicy(BaseRuntimePolicy):
    policy_name = "cancelled_test"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> PolicyResult:
        raise asyncio.CancelledError


@pytest.mark.asyncio
async def test_policy_engine_propagates_policy_cancellation() -> None:
    engine = PolicyEngine(
        registry=PolicyRegistry(policies=[CancelledTestPolicy()]),
    )

    with pytest.raises(asyncio.CancelledError):
        await engine.evaluate(subject={"name": "subject"})
