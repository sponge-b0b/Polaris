from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from application.decision_evidence import DecisionEvidencePacketPersistenceService
from core.runtime.state.runtime_context import RuntimeContext
from core.storage.persistence.governance_audit import AutomatedDecisionSubject
from core.workflow.execution.workflow_facade import WorkflowFacade
from core.workflow.execution.workflow_runner import WorkflowRunResult
from core.workflow.governance_audit import (
    AutomatedDecisionAuditContext,
    WorkflowExecutionAuditCapability,
    _issue_workflow_execution_audit_capability,
)
from domain.decision_evidence import DecisionEvidencePacket

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
    ) -> None:
        self._workflow_facade = workflow_facade
        self._automated_decision_audit_service = automated_decision_audit_service
        self._decision_evidence_packet_persistence_service = (
            decision_evidence_packet_persistence_service
        )

    async def run_workflow(
        self,
        *,
        workflow_name: str,
        decision_evidence_packet: DecisionEvidencePacket | None,
        execution_id: str | None = None,
        mode: str = "live",
        workflow_inputs: Mapping[str, Any] | None = None,
        simulation_time: datetime | None = None,
        archive_on_completion: bool = True,
        checkpoint_on_completion: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowRunResult:
        capability = await self._audit_capability_for_run(
            execution_id=execution_id,
            packet=decision_evidence_packet,
        )
        return await self._workflow_facade.run_workflow(
            workflow_name=workflow_name,
            execution_id=execution_id,
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
        decision_evidence_packet: DecisionEvidencePacket | None,
        archive_on_completion: bool = True,
        checkpoint_on_completion: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowRunResult:
        capability = await self._audit_capability_for_run(
            execution_id=context.execution_id,
            packet=decision_evidence_packet,
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
        execution_id: str | None,
        packet: DecisionEvidencePacket | None,
    ) -> WorkflowExecutionAuditCapability | None:
        if not self._is_governed():
            return None
        if packet is None:
            raise GovernedWorkflowExecutionEvidenceRequiredError(
                "Governed workflow execution requires a canonical decision evidence "
                "packet."
            )
        verified_packet = (
            await self._decision_evidence_packet_persistence_service.reconstruct_packet(
                packet.packet_id,
            )
        )
        audit_context = AutomatedDecisionAuditContext.from_packet(
            subject=AutomatedDecisionSubject(
                subject_type="workflow",
                subject_id=execution_id or verified_packet.output_id,
            ),
            packet=verified_packet,
        )
        return _issue_workflow_execution_audit_capability(
            service=self._automated_decision_audit_service,
            context=audit_context,
        )

    def _is_governed(self) -> bool:
        return (
            self._workflow_facade.policy_engine is not None
            or self._workflow_facade.governance_engine is not None
        )
