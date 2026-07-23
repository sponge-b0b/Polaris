from __future__ import annotations

from typing import Any

import pytest

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.governance.builtins.require_approval_for_live_mode_rule import (
    RequireApprovalForLiveModeRule,
)
from core.runtime.governance.governance_engine import GovernanceEngine
from core.runtime.governance.governance_registry import GovernanceRegistry
from core.runtime.governance.governance_result import GovernanceResult
from core.runtime.governance.governance_rule import BaseGovernanceRule
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.workflow.bootstrap.workflow_bootstrap import (
    WorkflowBootstrapConfig,
    build_workflow_runtime,
    build_workflow_runtime_async,
)
from core.workflow.models.destructive_operation_confirmation import (
    DestructiveOperationConfirmation,
    DestructiveWorkflowOperation,
)
from core.workflow.models.workflow_graph_definition import (
    WorkflowGraphDefinition,
)
from core.workflow.models.workflow_node_definition import (
    WorkflowNodeDefinition,
)


class GovernanceTestNode(RuntimeNode):
    node_name = "governance_test_node"
    node_type = "test.governance.node"
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


class GovernanceTestWorkflow(WorkflowGraphDefinition):
    @property
    def workflow_name(
        self,
    ) -> str:
        return "governance_test_workflow"

    @property
    def workflow_description(
        self,
    ) -> str:
        return "Workflow used for governance enforcement integration tests."

    def build_graph(
        self,
    ) -> list[WorkflowNodeDefinition]:
        return [
            WorkflowNodeDefinition(
                name="governance_node",
                node_type=GovernanceTestNode,
                dependencies=(),
                enabled=True,
                tags=("governance", "test"),
            )
        ]


class DenyWorkflowRegistrationGovernanceRule(BaseGovernanceRule):
    rule_name = "deny_workflow_registration_governance"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        if (context or {}).get("governance_phase") == ("workflow_registration"):
            return GovernanceResult.deny(
                rule_name=self.rule_name,
                message="Workflow registration denied by governance.",
                reason="governance_registration_blocked",
            )

        return GovernanceResult.allow(
            rule_name=self.rule_name,
        )


class DenyWorkflowUnregisterGovernanceRule(BaseGovernanceRule):
    rule_name = "deny_workflow_unregister_governance"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        if (context or {}).get("governance_phase") == ("workflow_unregister_preflight"):
            return GovernanceResult.deny(
                rule_name=self.rule_name,
                message="Workflow unregister denied by governance.",
                reason="governance_unregister_blocked",
            )

        return GovernanceResult.allow(
            rule_name=self.rule_name,
        )


class DenyWorkflowRunGovernanceRule(BaseGovernanceRule):
    rule_name = "deny_workflow_run_governance"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        if (context or {}).get("governance_phase") == ("workflow_run_preflight"):
            return GovernanceResult.deny(
                rule_name=self.rule_name,
                message="Workflow run denied by governance.",
                reason="governance_run_blocked",
            )

        return GovernanceResult.allow(
            rule_name=self.rule_name,
        )


def test_governance_denies_workflow_registration() -> None:
    governance_engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                DenyWorkflowRegistrationGovernanceRule(),
            ],
        )
    )

    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            enable_governance=True,
            enable_policies=False,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
        ),
        governance_engine=governance_engine,
    )

    with pytest.raises(
        RuntimeError,
        match="governance_registration_blocked",
    ):
        runtime.facade.register_workflow(
            workflow_definition=GovernanceTestWorkflow(),
        )


@pytest.mark.asyncio
async def test_governance_denies_workflow_run_preflight() -> None:
    governance_engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                DenyWorkflowRunGovernanceRule(),
            ],
        )
    )

    runtime = await build_workflow_runtime_async(
        config=WorkflowBootstrapConfig(
            enable_governance=True,
            enable_policies=False,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
        ),
        workflow_definitions=[
            GovernanceTestWorkflow(),
        ],
        governance_engine=governance_engine,
    )

    with pytest.raises(
        RuntimeError,
        match="governance_run_blocked",
    ):
        await runtime.facade.run_workflow(
            workflow_name="governance_test_workflow",
            mode="simulation",
            archive_on_completion=False,
            checkpoint_on_completion=False,
        )


@pytest.mark.asyncio
async def test_governance_requires_approval_for_live_mode() -> None:
    governance_engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                RequireApprovalForLiveModeRule(),
            ],
        )
    )

    runtime = await build_workflow_runtime_async(
        config=WorkflowBootstrapConfig(
            enable_governance=True,
            enable_policies=False,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
        ),
        workflow_definitions=[
            GovernanceTestWorkflow(),
        ],
        governance_engine=governance_engine,
    )

    with pytest.raises(
        RuntimeError,
        match="live_mode_requires_approval",
    ):
        await runtime.facade.run_workflow(
            workflow_name="governance_test_workflow",
            mode="live",
            archive_on_completion=False,
            checkpoint_on_completion=False,
        )


@pytest.mark.asyncio
async def test_governance_allows_simulation_workflow_run() -> None:
    governance_engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                RequireApprovalForLiveModeRule(),
            ],
        )
    )

    runtime = await build_workflow_runtime_async(
        config=WorkflowBootstrapConfig(
            enable_governance=True,
            enable_policies=False,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
        ),
        workflow_definitions=[
            GovernanceTestWorkflow(),
        ],
        governance_engine=governance_engine,
    )

    result = await runtime.facade.run_workflow(
        workflow_name="governance_test_workflow",
        mode="simulation",
        archive_on_completion=False,
        checkpoint_on_completion=False,
    )

    assert result.success is True

    output = result.execution_result.final_context.node_outputs["governance_node"]

    assert output["success"] is True
    assert output["outputs"]["ran"] is True


def test_governance_denies_destructive_workflow_unregister() -> None:
    governance_engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                DenyWorkflowUnregisterGovernanceRule(),
            ],
        )
    )
    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            enable_governance=True,
            enable_policies=False,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
        ),
        governance_engine=governance_engine,
    )
    runtime.facade.register_workflow(
        workflow_definition=GovernanceTestWorkflow(),
    )

    with pytest.raises(RuntimeError, match="governance_unregister_blocked"):
        runtime.facade.unregister_workflow(
            "governance_test_workflow",
            confirmation=DestructiveOperationConfirmation(
                operation=DestructiveWorkflowOperation.UNREGISTER_WORKFLOW,
                target="governance_test_workflow",
                requested_by="test",
                confirmed=True,
            ),
        )

    assert runtime.facade.registry.exists("governance_test_workflow") is True
