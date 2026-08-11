from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest

from application.governance.baseline_runtime_evidence import (
    BaselineRuntimeEvidencePersistenceService,
)
from application.governance.governed_execution_evidence_resolver import (
    CanonicalGovernedExecutionEvidenceLifecycle,
    GovernedExecutionEvidenceResolutionError,
    GovernedExecutionEvidenceResolver,
)
from core.storage.persistence.governed_execution_evidence import (
    GovernedExecutionEvidenceSelection,
)
from core.workflow.models.workflow_graph_definition import WorkflowGraphDefinition
from core.workflow.registry.workflow_registry import WorkflowIdentity, WorkflowRegistry
from domain.authority import RiskTier, classify_risk_authority
from domain.decision_evidence import DecisionEvidencePacket
from domain.governed_execution_evidence import BaselineRuntimeEvidence
from tests.helpers.risk_authority_examples import authority_input_for_tier


class _BaselineRepository:
    def __init__(self) -> None:
        self.records: dict[str, BaselineRuntimeEvidence] = {}

    async def get(self, evidence_id: str) -> BaselineRuntimeEvidence | None:
        return self.records.get(evidence_id)

    async def persist(self, evidence: BaselineRuntimeEvidence) -> None:
        self.records[evidence.evidence_id] = evidence


class _SelectionRepository:
    def __init__(self) -> None:
        self.selections: list[GovernedExecutionEvidenceSelection] = []

    async def create(self, selection: GovernedExecutionEvidenceSelection) -> None:
        self.selections.append(selection)

    async def get(
        self, *, execution_id: str, identity: WorkflowIdentity
    ) -> tuple[GovernedExecutionEvidenceSelection, ...]:
        del identity
        return tuple(
            selection
            for selection in self.selections
            if selection.execution_id == execution_id
        )


def _registry_with_facts(
    risk_tier: RiskTier = RiskTier.BASELINE,
) -> tuple[WorkflowRegistry, str]:
    definition = Mock(spec=WorkflowGraphDefinition)
    definition.workflow_name = "baseline_workflow"
    definition.workflow_description = "Baseline governed workflow."
    definition.to_dict.return_value = {
        "workflow_name": "baseline_workflow",
        "nodes": [{"name": "node"}],
    }
    registry = WorkflowRegistry()
    registry.register(
        cast(WorkflowGraphDefinition, definition),
        risk_authority_contract=classify_risk_authority(
            authority_input_for_tier(risk_tier)
        ),
    )
    return registry, "baseline_workflow"


@pytest.mark.asyncio
async def test_baseline_evidence_is_created_and_reacquired_by_execution() -> None:
    registry, workflow_name = _registry_with_facts()
    baseline_repository = _BaselineRepository()
    selection_repository = _SelectionRepository()
    baseline_service = BaselineRuntimeEvidencePersistenceService(baseline_repository)
    packets = AsyncMock()
    lifecycle = CanonicalGovernedExecutionEvidenceLifecycle(
        workflow_registry=registry,
        selection_repository=selection_repository,
        baseline_evidence_service=baseline_service,
        packet_persistence_service=packets,
    )
    resolver = GovernedExecutionEvidenceResolver(
        workflow_registry=registry,
        selection_repository=selection_repository,
        baseline_evidence_service=baseline_service,
        packet_persistence_service=packets,
    )

    facts = await lifecycle.prepare(
        workflow_name=workflow_name,
        execution_id="execution-one",
    )
    evidence = await resolver.resolve(
        workflow_name=workflow_name,
        execution_id="execution-one",
    )

    assert isinstance(evidence, BaselineRuntimeEvidence)
    assert evidence.workflow_name == facts.identity.workflow_name
    assert evidence.workflow_version == facts.identity.definition_fingerprint
    assert evidence.authority == facts.authority
    assert selection_repository.selections[0].evidence_id == evidence.evidence_id
    assert packets.persist_packet.await_count == 0

    with pytest.raises(GovernedExecutionEvidenceResolutionError):
        await resolver.resolve(
            workflow_name=workflow_name,
            execution_id="execution-two",
        )


@pytest.mark.asyncio
async def test_resolver_fails_closed_for_non_unique_execution_selection() -> None:
    registry, workflow_name = _registry_with_facts()
    baseline_repository = _BaselineRepository()
    selection_repository = _SelectionRepository()
    baseline_service = BaselineRuntimeEvidencePersistenceService(baseline_repository)
    packets = AsyncMock()
    lifecycle = CanonicalGovernedExecutionEvidenceLifecycle(
        workflow_registry=registry,
        selection_repository=selection_repository,
        baseline_evidence_service=baseline_service,
        packet_persistence_service=packets,
    )
    resolver = GovernedExecutionEvidenceResolver(
        workflow_registry=registry,
        selection_repository=selection_repository,
        baseline_evidence_service=baseline_service,
        packet_persistence_service=packets,
    )

    await lifecycle.prepare(workflow_name=workflow_name, execution_id="execution-one")
    selection_repository.selections.append(selection_repository.selections[0])

    with pytest.raises(GovernedExecutionEvidenceResolutionError):
        await resolver.resolve(
            workflow_name=workflow_name,
            execution_id="execution-one",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("risk_tier", [RiskTier.ENHANCED, RiskTier.VIGILANT])
async def test_packet_is_constructed_persisted_and_reacquired(
    risk_tier: RiskTier,
) -> None:
    registry, workflow_name = _registry_with_facts(risk_tier)
    baseline_repository = _BaselineRepository()
    selection_repository = _SelectionRepository()
    baseline_service = BaselineRuntimeEvidencePersistenceService(baseline_repository)
    facts = registry.get_authority_facts(workflow_name)
    packet = Mock(spec=DecisionEvidencePacket)
    packet.packet_id = "packet:execution-one"
    packet.authority = facts.authority
    packets = Mock()
    packets.persist_packet = AsyncMock(return_value=Mock(success=True))
    packets.reconstruct_packet = AsyncMock(return_value=packet)
    factory = AsyncMock(return_value=packet)
    lifecycle = CanonicalGovernedExecutionEvidenceLifecycle(
        workflow_registry=registry,
        selection_repository=selection_repository,
        baseline_evidence_service=baseline_service,
        packet_persistence_service=packets,
        packet_factory=factory,
    )
    resolver = GovernedExecutionEvidenceResolver(
        workflow_registry=registry,
        selection_repository=selection_repository,
        baseline_evidence_service=baseline_service,
        packet_persistence_service=packets,
    )

    await lifecycle.prepare(workflow_name=workflow_name, execution_id="execution-one")
    evidence = await resolver.resolve(
        workflow_name=workflow_name,
        execution_id="execution-one",
    )

    factory.assert_awaited_once_with(facts, "execution-one")
    packets.persist_packet.assert_awaited_once_with(packet)
    packets.reconstruct_packet.assert_awaited_once_with("packet:execution-one")
    assert evidence is packet
    assert selection_repository.selections[0].identity == facts.identity


@pytest.mark.asyncio
async def test_resolver_rejects_substituted_selection_identity() -> None:
    registry, workflow_name = _registry_with_facts()
    baseline_repository = _BaselineRepository()
    selection_repository = _SelectionRepository()
    baseline_service = BaselineRuntimeEvidencePersistenceService(baseline_repository)
    packets = AsyncMock()
    resolver = GovernedExecutionEvidenceResolver(
        workflow_registry=registry,
        selection_repository=selection_repository,
        baseline_evidence_service=baseline_service,
        packet_persistence_service=packets,
    )
    facts = registry.get_authority_facts(workflow_name)
    selection_repository.selections.append(
        GovernedExecutionEvidenceSelection(
            execution_id="execution-one",
            identity=WorkflowIdentity("substituted-workflow", "substituted-version"),
            risk_tier=facts.authority.risk_tier,
            evidence_id="baseline:execution-one",
        )
    )

    with pytest.raises(GovernedExecutionEvidenceResolutionError, match="identity"):
        await resolver.resolve(
            workflow_name=workflow_name,
            execution_id="execution-one",
        )
