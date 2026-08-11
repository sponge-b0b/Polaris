"""Canonical production and request-scoped resolution of governed evidence."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
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
from domain.decision_evidence import DecisionEvidencePacket
from domain.governed_execution_evidence import (
    BaselineRuntimeEvidence,
    GovernedExecutionEvidence,
)


class GovernedExecutionEvidenceResolutionError(RuntimeError):
    """Raised when the canonical governed-evidence lifecycle cannot be proven."""


type DecisionEvidencePacketFactory = Callable[
    [WorkflowAuthorityFacts, str], Awaitable[DecisionEvidencePacket]
]


@dataclass(frozen=True, slots=True)
class CanonicalGovernedExecutionEvidenceLifecycle:
    """Only production owner for tier-specific evidence and its selection."""

    workflow_registry: WorkflowRegistry
    selection_repository: GovernedExecutionEvidenceSelectionRepository
    baseline_evidence_service: BaselineRuntimeEvidencePersistenceService
    packet_persistence_service: DecisionEvidencePacketPersistenceService
    packet_factory: DecisionEvidencePacketFactory | None = None

    async def prepare(
        self, *, workflow_name: str, execution_id: str
    ) -> WorkflowAuthorityFacts:
        try:
            facts = self.workflow_registry.get_authority_facts(workflow_name)
        except KeyError as exc:
            raise GovernedExecutionEvidenceResolutionError(
                "Workflow has no registered governed authority facts."
            ) from exc
        evidence_id = await self._persist_tier_evidence(
            facts=facts,
            execution_id=execution_id,
        )
        try:
            await self.selection_repository.create(
                GovernedExecutionEvidenceSelection(
                    execution_id=execution_id,
                    identity=facts.identity,
                    risk_tier=facts.authority.risk_tier,
                    evidence_id=evidence_id,
                )
            )
        except GovernedExecutionEvidenceSelectionConflictError as exc:
            raise GovernedExecutionEvidenceResolutionError(
                "Durable governed-evidence selection is not unique."
            ) from exc
        return facts

    async def _persist_tier_evidence(
        self, *, facts: WorkflowAuthorityFacts, execution_id: str
    ) -> str:
        if facts.authority.risk_tier is RiskTier.BASELINE:
            evidence = BaselineRuntimeEvidence.create(
                evidence_id=f"baseline:{execution_id}",
                authority=facts.authority,
                workflow_name=facts.identity.workflow_name,
                workflow_version=facts.identity.definition_fingerprint,
            )
            await self.baseline_evidence_service.persist(evidence)
            return evidence.evidence_id

        if facts.authority.risk_tier not in {
            RiskTier.ENHANCED,
            RiskTier.VIGILANT,
        }:
            raise GovernedExecutionEvidenceResolutionError(
                "Prohibited workflows cannot acquire governed-execution evidence."
            )

        if self.packet_factory is None:
            raise GovernedExecutionEvidenceResolutionError(
                "No canonical decision-evidence packet factory is configured."
            )
        packet = await self.packet_factory(facts, execution_id)
        if packet.authority != facts.authority:
            raise GovernedExecutionEvidenceResolutionError(
                "Canonical packet authority does not match registry authority facts."
            )
        result = await self.packet_persistence_service.persist_packet(packet)
        if not result.success:
            raise GovernedExecutionEvidenceResolutionError(
                "Canonical decision-evidence packet was not durably persisted."
            )
        return packet.packet_id


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
            self._validate_baseline(evidence, facts)
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
        evidence: BaselineRuntimeEvidence, facts: WorkflowAuthorityFacts
    ) -> None:
        if (
            evidence.authority != facts.authority
            or evidence.workflow_name != facts.identity.workflow_name
            or evidence.workflow_version != facts.identity.definition_fingerprint
        ):
            raise GovernedExecutionEvidenceResolutionError(
                "Reconstructed Baseline evidence does not match registry "
                "authority facts."
            )
