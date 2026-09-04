from __future__ import annotations

from typing import Any

import pytest

from core.runtime.policies.policy import BaseRuntimePolicy
from core.runtime.policies.policy_engine import PolicyEngine
from core.runtime.policies.policy_registry import PolicyRegistry
from core.runtime.policies.policy_result import PolicyResult
from core.workflow.bootstrap.workflow_bootstrap import (
    WorkflowBootstrapConfig,
    build_workflow_runtime_async,
)


class DenyExamplePluginManifestPolicy(BaseRuntimePolicy):
    policy_name = "deny_example_plugin_manifest"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> PolicyResult:
        context = context or {}

        if context.get("policy_phase") != "plugin_manifest_validation":
            return PolicyResult.allow(
                policy_name=self.policy_name,
            )

        plugin_name = getattr(
            subject,
            "plugin_name",
            None,
        )

        if plugin_name == "example_market_plugin":
            return PolicyResult.deny(
                policy_name=self.policy_name,
                message="Example plugin manifest denied by test policy.",
                reason="plugin_manifest_blocked",
                metadata={
                    "plugin_name": plugin_name,
                },
            )

        return PolicyResult.allow(
            policy_name=self.policy_name,
            metadata={
                "plugin_name": plugin_name,
            },
        )


@pytest.mark.asyncio
async def test_plugin_manifest_policy_denies_plugin_loading() -> None:
    policy_engine = PolicyEngine(
        registry=PolicyRegistry(
            policies=[
                DenyExamplePluginManifestPolicy(),
            ],
        )
    )

    runtime = await build_workflow_runtime_async(
        config=WorkflowBootstrapConfig(
            enable_policies=True,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
        ),
        policy_engine=policy_engine,
    )

    load_result = await runtime.facade.load_plugins_from_dir(
        plugin_dir="plugins/example_market_plugin",
        recursive=False,
        overwrite=True,
        register_workflows=True,
    )

    assert load_result.success is False

    assert load_result.validation_errors
    assert load_result.validation_errors[0]["error_type"] == "PluginPolicyDenied"

    assert (
        load_result.validation_errors[0]["policy_result"]["results"][0]["reason"]
        == "plugin_manifest_blocked"
    )

    assert not load_result.runtime_load_results
    assert not load_result.workflow_load_results
    assert not load_result.workflows

    assert not runtime.facade.workflow_exists(
        "example_plugin_workflow",
    )


@pytest.mark.asyncio
async def test_plugin_manifest_policy_allows_plugin_loading_by_default() -> None:
    runtime = await build_workflow_runtime_async(
        config=WorkflowBootstrapConfig(
            enable_policies=True,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
        ),
    )

    load_result = await runtime.facade.load_plugins_from_dir(
        plugin_dir="plugins/example_market_plugin",
        recursive=False,
        overwrite=True,
        register_workflows=True,
    )

    assert load_result.success is True
    assert not load_result.validation_errors

    assert runtime.facade.workflow_exists(
        "example_plugin_workflow",
    )
