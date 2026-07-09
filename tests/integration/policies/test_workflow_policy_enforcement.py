from __future__ import annotations

from typing import Any

import pytest

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.control import WorkflowControlState
from core.runtime.policies.policy import BaseRuntimePolicy
from core.runtime.policies.policy_engine import PolicyEngine
from core.runtime.policies.policy_registry import PolicyRegistry
from core.runtime.policies.policy_result import PolicyResult
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.workflow.bootstrap.workflow_bootstrap import (
    WorkflowBootstrapConfig,
    build_workflow_runtime,
    build_workflow_runtime_async,
)
from core.workflow.models.workflow_graph_definition import (
    WorkflowGraphDefinition,
)
from core.workflow.models.workflow_node_definition import (
    WorkflowNodeDefinition,
)


class PolicyTestNode(RuntimeNode):
    node_name = "policy_test_node"
    node_type = "test.policy.node"
    node_version = "1.0.0"

    parallel_safe = True

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        return RuntimeNodeOutput.success_output(
            outputs={
                "ran": True,
            },
        )


class PolicyTestWorkflow(WorkflowGraphDefinition):
    @property
    def workflow_name(
        self,
    ) -> str:
        return "policy_test_workflow"

    @property
    def workflow_description(
        self,
    ) -> str:
        return "Workflow used for policy enforcement integration tests."

    def build_graph(
        self,
    ) -> list[WorkflowNodeDefinition]:
        return [
            WorkflowNodeDefinition(
                name="policy_node",
                node_type=PolicyTestNode,
                dependencies=(),
                enabled=True,
                tags=("policy", "test"),
            )
        ]


class DenyWorkflowRegistrationPolicy(BaseRuntimePolicy):
    policy_name = "deny_workflow_registration"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> PolicyResult:
        if (context or {}).get("policy_phase") == "workflow_registration":
            return PolicyResult.deny(
                policy_name=self.policy_name,
                message="Workflow registration denied by test policy.",
                reason="registration_blocked",
            )

        return PolicyResult.allow(
            policy_name=self.policy_name,
        )


class DenyWorkflowControlPolicy(BaseRuntimePolicy):
    policy_name = "deny_workflow_control"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> PolicyResult:
        if (context or {}).get("policy_phase") == "workflow_control_preflight":
            return PolicyResult.deny(
                policy_name=self.policy_name,
                message="Workflow control denied by test policy.",
                reason="control_blocked",
            )

        return PolicyResult.allow(
            policy_name=self.policy_name,
        )


class DenyWorkflowRunPolicy(BaseRuntimePolicy):
    policy_name = "deny_workflow_run"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> PolicyResult:
        if (context or {}).get("policy_phase") == "workflow_run_preflight":
            return PolicyResult.deny(
                policy_name=self.policy_name,
                message="Workflow run denied by test policy.",
                reason="run_blocked",
            )

        return PolicyResult.allow(
            policy_name=self.policy_name,
        )


@pytest.mark.asyncio
async def test_policy_denies_workflow_registration() -> None:
    policy_engine = PolicyEngine(
        registry=PolicyRegistry(
            policies=[
                DenyWorkflowRegistrationPolicy(),
            ],
        )
    )

    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            enable_governance=False,
            enable_policies=True,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
        ),
        policy_engine=policy_engine,
    )

    with pytest.raises(
        RuntimeError,
        match="registration_blocked",
    ):
        await runtime.facade.register_workflow_async(
            workflow_definition=PolicyTestWorkflow(),
        )


@pytest.mark.asyncio
async def test_policy_denies_workflow_run_preflight() -> None:
    policy_engine = PolicyEngine(
        registry=PolicyRegistry(
            policies=[
                DenyWorkflowRunPolicy(),
            ],
        )
    )

    runtime = await build_workflow_runtime_async(
        config=WorkflowBootstrapConfig(
            enable_governance=False,
            enable_policies=True,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
        ),
        workflow_definitions=[
            PolicyTestWorkflow(),
        ],
        policy_engine=policy_engine,
    )

    with pytest.raises(
        RuntimeError,
        match="run_blocked",
    ):
        await runtime.facade.run_workflow(
            workflow_name="policy_test_workflow",
            mode="simulation",
            archive_on_completion=False,
            checkpoint_on_completion=False,
        )


@pytest.mark.asyncio
async def test_policy_allows_workflow_registration_and_run_when_no_denial() -> None:
    runtime = await build_workflow_runtime_async(
        config=WorkflowBootstrapConfig(
            enable_governance=False,
            enable_policies=True,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
        ),
        workflow_definitions=[
            PolicyTestWorkflow(),
        ],
    )

    result = await runtime.facade.run_workflow(
        workflow_name="policy_test_workflow",
        mode="simulation",
        archive_on_completion=False,
        checkpoint_on_completion=False,
    )

    assert result.success is True

    output = result.execution_result.final_context.node_outputs["policy_node"]

    assert output["success"] is True
    assert output["outputs"]["ran"] is True


@pytest.mark.asyncio
async def test_policy_denies_workflow_control_before_state_mutation() -> None:
    policy_engine = PolicyEngine(
        registry=PolicyRegistry(
            policies=[
                DenyWorkflowControlPolicy(),
            ],
        )
    )
    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            enable_governance=False,
            enable_policies=True,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
        ),
        policy_engine=policy_engine,
    )

    with pytest.raises(RuntimeError, match="control_blocked"):
        await runtime.facade.cancel_workflow(
            execution_id="blocked-execution",
            reason="test",
            requested_by="test",
        )

    assert (
        runtime.workflow_control_manager.get_state("blocked-execution")
        is WorkflowControlState.PENDING
    )
