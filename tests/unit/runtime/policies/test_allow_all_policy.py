from __future__ import annotations

import pytest

from core.runtime.policies.builtins.allow_all_policy import (
    AllowAllPolicy,
)
from core.runtime.policies.policy_result import PolicyDecision


@pytest.mark.asyncio
async def test_allow_all_policy_allows_subject() -> None:
    policy = AllowAllPolicy()

    subject = {
        "name": "test_subject",
    }

    result = await policy.evaluate(
        subject=subject,
        context={
            "mode": "test",
        },
    )

    assert result.policy_name == "allow_all"
    assert result.decision == PolicyDecision.ALLOW
    assert result.allowed is True
    assert result.denied is False
    assert result.message == "Subject allowed by AllowAllPolicy."
    assert result.metadata["subject_type"] == "dict"


def test_allow_all_policy_metadata() -> None:
    policy = AllowAllPolicy()

    assert policy.policy_name == "allow_all"
    assert policy.enabled is True
