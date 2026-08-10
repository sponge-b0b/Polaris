from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from application.decision_evidence import DecisionEvidencePacketNotFoundError
from application.governance import (
    AutomatedDecisionAuditContext,
    GovernedWorkflowExecutionEvidenceRequiredError,
    GovernedWorkflowExecutionService,
)
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
from core.storage.persistence.governance_audit import (
    AutomatedDecisionAuditPersistenceResult,
    AutomatedDecisionSubject,
)
from core.workflow.bootstrap.workflow_bootstrap import (
    WorkflowBootstrapConfig,
    build_workflow_runtime,
    build_workflow_runtime_async,
)
from core.workflow.governance_audit import (
    WorkflowExecutionAuditCapability,
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
from domain.authority import classify_risk_authority
from domain.decision_evidence import DecisionEvidencePacket
from tests.helpers.risk_authority_examples import workflow_curation_authority_input


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


def test_execution_audit_capability_rejects_direct_construction() -> None:
    with pytest.raises(
        TypeError,
        match="governed workflow execution service",
    ):
        WorkflowExecutionAuditCapability(
            _service=AsyncMock(),
            _context=AutomatedDecisionAuditContext(
                subject=AutomatedDecisionSubject(
                    "workflow",
                    "direct-construction-test",
                ),
                authority=classify_risk_authority(
                    workflow_curation_authority_input(),
                ),
            ),
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
        match="execution audit capability",
    ):
        await runtime.facade.run_workflow(
            workflow_name="governance_test_workflow",
            mode="simulation",
            archive_on_completion=False,
            checkpoint_on_completion=False,
        )


@pytest.mark.asyncio
async def test_governed_execution_requires_canonical_evidence_before_evaluation() -> (
    None
):
    runtime = await build_workflow_runtime_async(
        config=WorkflowBootstrapConfig(
            enable_governance=True,
            enable_policies=False,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
        ),
        workflow_definitions=[GovernanceTestWorkflow()],
    )
    execution_service = GovernedWorkflowExecutionService(
        workflow_facade=runtime.facade,
        automated_decision_audit_service=AsyncMock(),
        decision_evidence_packet_persistence_service=AsyncMock(),
    )

    with pytest.raises(GovernedWorkflowExecutionEvidenceRequiredError):
        await execution_service.run_workflow(
            workflow_name="governance_test_workflow",
            decision_evidence_packet=None,
            archive_on_completion=False,
            checkpoint_on_completion=False,
        )


@pytest.mark.asyncio
async def test_governed_execution_fails_closed_when_packet_is_not_durable() -> None:
    runtime = await build_workflow_runtime_async(
        config=WorkflowBootstrapConfig(
            enable_governance=True,
            enable_policies=False,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
        ),
        workflow_definitions=[GovernanceTestWorkflow()],
    )
    packet = Mock(spec=DecisionEvidencePacket)
    packet.packet_id = "missing-packet"
    packet_persistence_service = AsyncMock()
    packet_persistence_service.reconstruct_packet.side_effect = (
        DecisionEvidencePacketNotFoundError("missing-packet")
    )
    execution_service = GovernedWorkflowExecutionService(
        workflow_facade=runtime.facade,
        automated_decision_audit_service=AsyncMock(),
        decision_evidence_packet_persistence_service=packet_persistence_service,
    )

    with pytest.raises(DecisionEvidencePacketNotFoundError):
        await execution_service.run_workflow(
            workflow_name="governance_test_workflow",
            decision_evidence_packet=packet,
            archive_on_completion=False,
            checkpoint_on_completion=False,
        )

    packet_persistence_service.reconstruct_packet.assert_awaited_once_with(
        "missing-packet"
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
            execution_audit_capability=await _audit_capability(runtime),
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
        execution_audit_capability=await _audit_capability(runtime),
    )

    assert result.success is True

    output = result.execution_result.final_context.node_outputs["governance_node"]

    assert output["success"] is True
    assert output["outputs"]["ran"] is True


@pytest.mark.asyncio
async def test_governed_facade_rejects_reused_execution_audit_capability() -> None:
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
        workflow_definitions=[GovernanceTestWorkflow()],
        governance_engine=governance_engine,
    )
    capability = await _audit_capability(runtime)

    await runtime.facade.run_workflow(
        workflow_name="governance_test_workflow",
        mode="simulation",
        archive_on_completion=False,
        checkpoint_on_completion=False,
        execution_audit_capability=capability,
    )

    with pytest.raises(RuntimeError, match="already been used"):
        await runtime.facade.run_workflow(
            workflow_name="governance_test_workflow",
            mode="simulation",
            archive_on_completion=False,
            checkpoint_on_completion=False,
            execution_audit_capability=capability,
        )


@pytest.mark.asyncio
async def test_governance_audit_rejects_malformed_persistence_result() -> None:
    audit_service = AsyncMock()
    audit_service.record_governance_evaluation.return_value = (object(),)
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
        automated_decision_audit_service=audit_service,
    )

    with pytest.raises(RuntimeError, match="returned invalid result"):
        await runtime.facade.run_workflow(
            workflow_name="governance_test_workflow",
            mode="simulation",
            archive_on_completion=False,
            checkpoint_on_completion=False,
            execution_audit_capability=await _audit_capability(runtime, audit_service),
        )

    audit_service.record_governance_evaluation.assert_awaited_once()


@pytest.mark.asyncio
async def test_governance_audit_rejects_success_without_durable_write_evidence() -> (
    None
):
    audit_service = AsyncMock()
    audit_service.record_governance_evaluation.return_value = (
        _successful_audit_result_without_durable_write_evidence(),
    )
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
        automated_decision_audit_service=audit_service,
    )

    with pytest.raises(RuntimeError, match="did not persist a record"):
        await runtime.facade.run_workflow(
            workflow_name="governance_test_workflow",
            mode="simulation",
            archive_on_completion=False,
            checkpoint_on_completion=False,
            execution_audit_capability=await _audit_capability(runtime, audit_service),
        )

    audit_service.record_governance_evaluation.assert_awaited_once()


def _successful_audit_result_without_durable_write_evidence() -> (
    AutomatedDecisionAuditPersistenceResult
):
    """Build a malformed boundary result to verify the facade fails closed."""

    result = object.__new__(AutomatedDecisionAuditPersistenceResult)
    object.__setattr__(result, "success", True)
    object.__setattr__(result, "audit_record_id", "governance-audit-1")
    object.__setattr__(result, "records_persisted", 0)
    object.__setattr__(result, "errors", ())
    object.__setattr__(result, "review_task_id", None)
    return result


async def _audit_capability(
    runtime: Any,
    audit_service: AsyncMock | None = None,
) -> WorkflowExecutionAuditCapability:
    service = audit_service or AsyncMock()
    if audit_service is None:
        service.record_governance_evaluation.return_value = ()
        service.record_policy_evaluation.return_value = ()
    authority = classify_risk_authority(workflow_curation_authority_input())
    packet = Mock(spec=DecisionEvidencePacket)
    packet.packet_id = "governance-enforcement-test-packet"
    verified_packet = Mock(spec=DecisionEvidencePacket)
    verified_packet.packet_id = packet.packet_id
    verified_packet.output_id = "governance-enforcement-test"
    verified_packet.schema_version = 1
    verified_packet.authority = authority
    packet_persistence_service = AsyncMock()
    packet_persistence_service.reconstruct_packet.return_value = verified_packet
    execution_service = GovernedWorkflowExecutionService(
        workflow_facade=runtime.facade,
        automated_decision_audit_service=service,
        decision_evidence_packet_persistence_service=packet_persistence_service,
    )
    capability = await execution_service._audit_capability_for_run(
        execution_id="governance-enforcement-test",
        packet=packet,
    )
    assert capability is not None
    return capability


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
