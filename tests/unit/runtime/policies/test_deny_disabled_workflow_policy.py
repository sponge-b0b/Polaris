from __future__ import annotations

import pytest

from core.runtime.policies.builtins.deny_disabled_workflow_policy import (
    DenyDisabledWorkflowPolicy,
)
from core.runtime.policies.policy_result import PolicyDecision


class EnabledSubject:
    enabled = True


class DisabledSubject:
    enabled = False


class NoEnabledAttributeSubject:
    pass


@pytest.mark.asyncio
async def test_deny_disabled_workflow_policy_allows_enabled_subject() -> None:
    policy = DenyDisabledWorkflowPolicy()

    result = await policy.evaluate(
        subject=EnabledSubject(),
        context={
            "mode": "test",
        },
    )

    assert result.policy_name == "deny_disabled_workflow"
    assert result.decision == PolicyDecision.ALLOW
    assert result.allowed is True
    assert result.denied is False
    assert result.message == "Subject is enabled."
    assert result.metadata["subject_type"] == "EnabledSubject"


@pytest.mark.asyncio
async def test_deny_disabled_workflow_policy_denies_disabled_subject() -> None:
    policy = DenyDisabledWorkflowPolicy()

    result = await policy.evaluate(
        subject=DisabledSubject(),
        context={
            "mode": "test",
        },
    )

    assert result.policy_name == "deny_disabled_workflow"
    assert result.decision == PolicyDecision.DENY
    assert result.allowed is False
    assert result.denied is True
    assert result.message == "Subject is disabled."
    assert result.reason == "enabled=False"
    assert result.metadata["subject_type"] == "DisabledSubject"


@pytest.mark.asyncio
async def test_deny_disabled_workflow_policy_allows_subject_without_enabled_attribute() -> (
    None
):
    policy = DenyDisabledWorkflowPolicy()

    result = await policy.evaluate(
        subject=NoEnabledAttributeSubject(),
        context={
            "mode": "test",
        },
    )

    assert result.policy_name == "deny_disabled_workflow"
    assert result.decision == PolicyDecision.ALLOW
    assert result.allowed is True
    assert result.denied is False
    assert result.message == "Subject is enabled."
    assert result.metadata["subject_type"] == "NoEnabledAttributeSubject"


def test_deny_disabled_workflow_policy_metadata() -> None:
    policy = DenyDisabledWorkflowPolicy()

    assert policy.policy_name == "deny_disabled_workflow"
    assert policy.enabled is True
