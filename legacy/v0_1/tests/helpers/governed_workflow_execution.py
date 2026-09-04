from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock

from application.governance import GovernedWorkflowExecutionService
from core.storage.persistence.governance_audit import (
    AutomatedDecisionAuditPersistenceResult,
)
from core.workflow.execution.workflow_facade import WorkflowFacade
from domain.authority import RiskTier, classify_risk_authority
from domain.governed_execution_evidence import BaselineRuntimeEvidence
from tests.helpers.risk_authority_examples import authority_input_for_tier


@dataclass(frozen=True, slots=True)
class GovernedWorkflowExecutionHarness:
    execution_service: GovernedWorkflowExecutionService
    audit_service: AsyncMock
    evidence_lifecycle: AsyncMock
    evidence_resolver: AsyncMock


def governed_workflow_execution_harness(
    workflow_facade: WorkflowFacade,
) -> GovernedWorkflowExecutionHarness:
    persisted = AutomatedDecisionAuditPersistenceResult.succeeded(
        "governed-workflow-test-audit",
        records_persisted=1,
    )
    audit_service = AsyncMock()
    audit_service.record_governance_evaluation.return_value = (persisted,)
    audit_service.record_policy_evaluation.return_value = (persisted,)

    evidence_lifecycle = AsyncMock()
    evidence_lifecycle.prepare.return_value = None
    evidence_resolver = AsyncMock()
    authority = classify_risk_authority(authority_input_for_tier(RiskTier.BASELINE))

    async def resolve_evidence(
        *,
        workflow_name: str,
        execution_id: str,
    ) -> BaselineRuntimeEvidence:
        return BaselineRuntimeEvidence.create(
            evidence_id=f"baseline:{execution_id}",
            authority=authority,
            workflow_name=workflow_name,
            workflow_version="test-governed-workflow",
            execution_id=execution_id,
        )

    evidence_resolver.resolve.side_effect = resolve_evidence

    return GovernedWorkflowExecutionHarness(
        execution_service=GovernedWorkflowExecutionService(
            workflow_facade=workflow_facade,
            automated_decision_audit_service=audit_service,
            decision_evidence_packet_persistence_service=AsyncMock(),
            evidence_lifecycle=evidence_lifecycle,
            evidence_resolver=evidence_resolver,
        ),
        audit_service=audit_service,
        evidence_lifecycle=evidence_lifecycle,
        evidence_resolver=evidence_resolver,
    )
