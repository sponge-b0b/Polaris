from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import uuid4

from application.decision_evidence import DecisionEvidencePacketPersistenceService
from application.governance.baseline_runtime_evidence import (
    BaselineRuntimeEvidencePersistenceService,
)
from application.governance.governed_execution_evidence_resolver import (
    CanonicalGovernedExecutionEvidenceLifecycle,
    GovernedExecutionEvidenceResolver,
)
from core.runtime.state.runtime_context import RuntimeContext
from core.storage.persistence.governance_audit import AutomatedDecisionSubject
from core.workflow.execution.workflow_facade import WorkflowFacade
from core.workflow.execution.workflow_runner import WorkflowRunResult
from core.workflow.governance_audit import (
    AutomatedDecisionAuditContext,
    WorkflowExecutionAuditCapability,
    _issue_workflow_execution_audit_capability,
)
from domain.governed_execution_evidence import BaselineRuntimeEvidence

from .automated_decision_audit import AutomatedDecisionAuditService


class GovernedWorkflowExecutionEvidenceRequiredError(RuntimeError):
    """Raised when governed workflow execution lacks canonical decision evidence."""


class GovernedWorkflowExecutionService:
    """Request-scoped composition boundary for governed workflow execution."""

    def __init__(
        self,
        *,
        workflow_facade: WorkflowFacade,
        automated_decision_audit_service: AutomatedDecisionAuditService,
        decision_evidence_packet_persistence_service: (
            DecisionEvidencePacketPersistenceService
        ),
        baseline_runtime_evidence_persistence_service: (
            BaselineRuntimeEvidencePersistenceService | None
        ) = None,
        evidence_lifecycle: CanonicalGovernedExecutionEvidenceLifecycle | None = None,
        evidence_resolver: GovernedExecutionEvidenceResolver | None = None,
    ) -> None:
        self._workflow_facade = workflow_facade
        self._automated_decision_audit_service = automated_decision_audit_service
        self._decision_evidence_packet_persistence_service = (
            decision_evidence_packet_persistence_service
        )
        self._baseline_runtime_evidence_persistence_service = (
            baseline_runtime_evidence_persistence_service
        )
        self._evidence_lifecycle = evidence_lifecycle
        self._evidence_resolver = evidence_resolver

    async def run_workflow(
        self,
        *,
        workflow_name: str,
        mode: str = "live",
        workflow_inputs: Mapping[str, Any] | None = None,
        simulation_time: datetime | None = None,
        archive_on_completion: bool = True,
        checkpoint_on_completion: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowRunResult:
        correlation_id = f"governed-{uuid4().hex}"
        capability = await self._audit_capability_for_run(
            workflow_name=workflow_name,
            execution_id=correlation_id,
        )
        return await self._workflow_facade.run_workflow(
            workflow_name=workflow_name,
            execution_id=correlation_id,
            mode=mode,
            workflow_inputs=workflow_inputs,
            simulation_time=simulation_time,
            archive_on_completion=archive_on_completion,
            checkpoint_on_completion=checkpoint_on_completion,
            metadata=metadata,
            execution_audit_capability=capability,
        )

    async def run_from_context(
        self,
        *,
        workflow_name: str,
        context: RuntimeContext,
        archive_on_completion: bool = True,
        checkpoint_on_completion: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowRunResult:
        capability = await self._audit_capability_for_run(
            workflow_name=workflow_name,
            execution_id=context.execution_id,
            prepare_evidence=False,
        )
        return await self._workflow_facade.run_from_context(
            workflow_name=workflow_name,
            context=context,
            archive_on_completion=archive_on_completion,
            checkpoint_on_completion=checkpoint_on_completion,
            metadata=metadata,
            execution_audit_capability=capability,
        )

    async def _audit_capability_for_run(
        self,
        *,
        workflow_name: str,
        execution_id: str | None,
        prepare_evidence: bool = True,
    ) -> WorkflowExecutionAuditCapability | None:
        if not self._is_governed():
            return None
        if self._evidence_lifecycle is None or self._evidence_resolver is None:
            raise GovernedWorkflowExecutionEvidenceRequiredError(
                "Canonical governed-evidence lifecycle is not configured."
            )
        if execution_id is None:
            raise GovernedWorkflowExecutionEvidenceRequiredError(
                "Governed workflow execution requires an execution correlation."
            )
        if prepare_evidence:
            await self._evidence_lifecycle.prepare(
                workflow_name=workflow_name,
                execution_id=execution_id,
            )
        evidence = await self._evidence_resolver.resolve(
            workflow_name=workflow_name,
            execution_id=execution_id,
        )
        if isinstance(evidence, BaselineRuntimeEvidence):
            audit_context = (
                AutomatedDecisionAuditContext.from_baseline_runtime_evidence(
                    subject=AutomatedDecisionSubject(
                        subject_type="workflow",
                        subject_id=execution_id,
                    ),
                    evidence=evidence,
                )
            )
        else:
            audit_context = AutomatedDecisionAuditContext.from_packet(
                subject=AutomatedDecisionSubject(
                    subject_type="workflow",
                    subject_id=execution_id,
                ),
                packet=evidence,
            )
        return _issue_workflow_execution_audit_capability(
            service=self._automated_decision_audit_service,
            context=audit_context,
            evidence=evidence,
        )

    def _is_governed(self) -> bool:
        return (
            self._workflow_facade.policy_engine is not None
            or self._workflow_facade.governance_engine is not None
        )
