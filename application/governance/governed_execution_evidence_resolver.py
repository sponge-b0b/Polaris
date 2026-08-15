"""Canonical production and request-scoped resolution of governed evidence."""

from __future__ import annotations

from dataclasses import dataclass

from application.decision_evidence import DecisionEvidencePacketPersistenceService
from application.governance.baseline_runtime_evidence import (
    BaselineRuntimeEvidencePersistenceService,
)
from core.storage.persistence.governed_execution_evidence import (
    GovernedExecutionEvidenceSelection,
    GovernedExecutionEvidenceSelectionConflictError,
    GovernedExecutionEvidenceSelectionRepository,
)
from core.workflow.registry.workflow_registry import (
    WorkflowAuthorityFacts,
    WorkflowRegistry,
)
from domain.authority import RiskTier
from domain.governed_execution_evidence import (
    BaselineRuntimeEvidence,
    GovernedExecutionEvidence,
)


class GovernedExecutionEvidenceResolutionError(RuntimeError):
    """Raised when the canonical governed-evidence lifecycle cannot be proven."""


@dataclass(frozen=True, slots=True)
class CanonicalGovernedExecutionEvidenceLifecycle:
    """Only production owner for tier-specific evidence and its selection."""

    workflow_registry: WorkflowRegistry
    selection_repository: GovernedExecutionEvidenceSelectionRepository
    baseline_evidence_service: BaselineRuntimeEvidencePersistenceService
    packet_persistence_service: DecisionEvidencePacketPersistenceService

    async def prepare(
        self, *, workflow_name: str, execution_id: str
    ) -> WorkflowAuthorityFacts:
        try:
            facts = self.workflow_registry.get_authority_facts(workflow_name)
        except KeyError as exc:
            raise GovernedExecutionEvidenceResolutionError(
                "Workflow has no registered governed authority facts."
            ) from exc
        try:
            evidence_id = await self._persist_baseline_evidence(
                facts=facts,
                execution_id=execution_id,
            )
            await self.selection_repository.create(
                GovernedExecutionEvidenceSelection(
                    execution_id=execution_id,
                    identity=facts.identity,
                    risk_tier=facts.authority.risk_tier,
                    evidence_id=evidence_id,
                ),
                commit=False,
            )
            await self.baseline_evidence_service.commit()
        except GovernedExecutionEvidenceSelectionConflictError as exc:
            await self.baseline_evidence_service.rollback()
            raise GovernedExecutionEvidenceResolutionError(
                "Durable governed-evidence selection is not unique."
            ) from exc
        except GovernedExecutionEvidenceResolutionError:
            await self.baseline_evidence_service.rollback()
            raise
        except Exception as exc:
            await self.baseline_evidence_service.rollback()
            raise GovernedExecutionEvidenceResolutionError(
                "Durable governed-evidence persistence did not complete."
            ) from exc
        return facts

    async def _persist_baseline_evidence(
        self, *, facts: WorkflowAuthorityFacts, execution_id: str
    ) -> str:
        if facts.authority.risk_tier is RiskTier.BASELINE:
            evidence = BaselineRuntimeEvidence.create(
                evidence_id=f"baseline:{execution_id}",
                authority=facts.authority,
                workflow_name=facts.identity.workflow_name,
                workflow_version=facts.identity.definition_fingerprint,
                execution_id=execution_id,
            )
            await self.baseline_evidence_service.persist(evidence, commit=False)
            return evidence.evidence_id

        raise GovernedExecutionEvidenceResolutionError(
            "Only Baseline workflows acquire invocation evidence; Enhanced and "
            "Vigilant packets belong to their claim-bearing output boundary."
        )


@dataclass(frozen=True, slots=True)
class GovernedExecutionEvidenceResolver:
    """Re-acquires and validates the sole durable selection before evaluation."""

    workflow_registry: WorkflowRegistry
    selection_repository: GovernedExecutionEvidenceSelectionRepository
    baseline_evidence_service: BaselineRuntimeEvidencePersistenceService
    packet_persistence_service: DecisionEvidencePacketPersistenceService

    async def resolve(
        self, *, workflow_name: str, execution_id: str
    ) -> GovernedExecutionEvidence:
        try:
            facts = self.workflow_registry.get_authority_facts(workflow_name)
        except KeyError as exc:
            raise GovernedExecutionEvidenceResolutionError(
                "Workflow has no registered governed authority facts."
            ) from exc
        selections = await self.selection_repository.get(
            execution_id=execution_id,
            identity=facts.identity,
        )
        if len(selections) != 1:
            raise GovernedExecutionEvidenceResolutionError(
                "Expected exactly one durable governed-evidence selection."
            )
        selection = selections[0]
        if selection.identity != facts.identity:
            raise GovernedExecutionEvidenceResolutionError(
                "Durable governed-evidence selection identity does not match "
                "registry authority facts."
            )
        if selection.risk_tier is not facts.authority.risk_tier:
            raise GovernedExecutionEvidenceResolutionError(
                "Durable governed-evidence selection tier does not match "
                "authority facts."
            )
        if selection.risk_tier is RiskTier.BASELINE:
            evidence = await self.baseline_evidence_service.reconstruct(
                selection.evidence_id
            )
            self._validate_baseline(evidence, facts, execution_id)
            return evidence
        if selection.risk_tier not in {RiskTier.ENHANCED, RiskTier.VIGILANT}:
            raise GovernedExecutionEvidenceResolutionError(
                "Prohibited workflows cannot resolve governed-execution evidence."
            )
        packet = await self.packet_persistence_service.reconstruct_packet(
            selection.evidence_id
        )
        if packet.authority != facts.authority:
            raise GovernedExecutionEvidenceResolutionError(
                "Reconstructed packet authority does not match registry "
                "authority facts."
            )
        return packet

    @staticmethod
    def _validate_baseline(
        evidence: BaselineRuntimeEvidence,
        facts: WorkflowAuthorityFacts,
        execution_id: str,
    ) -> None:
        if (
            evidence.authority != facts.authority
            or evidence.workflow_name != facts.identity.workflow_name
            or evidence.workflow_version != facts.identity.definition_fingerprint
            or evidence.execution_id != execution_id
        ):
            raise GovernedExecutionEvidenceResolutionError(
                "Reconstructed Baseline evidence does not match registry "
                "authority facts."
            )
