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
from domain.governed_execution_evidence import BaselineRuntimeEvidence
from tests.helpers.risk_authority_examples import authority_input_for_tier


class _BaselineRepository:
    def __init__(self) -> None:
        self.records: dict[str, BaselineRuntimeEvidence] = {}

    async def get(self, evidence_id: str) -> BaselineRuntimeEvidence | None:
        return self.records.get(evidence_id)

    async def persist(
        self,
        evidence: BaselineRuntimeEvidence,
        *,
        commit: bool = True,
    ) -> None:
        del commit
        self.records[evidence.evidence_id] = evidence

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class _SelectionRepository:
    def __init__(self) -> None:
        self.selections: list[GovernedExecutionEvidenceSelection] = []

    async def create(
        self,
        selection: GovernedExecutionEvidenceSelection,
        *,
        commit: bool = True,
    ) -> None:
        del commit
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


class _FailingSelectionRepository(_SelectionRepository):
    async def create(
        self,
        selection: GovernedExecutionEvidenceSelection,
        *,
        commit: bool = True,
    ) -> None:
        del selection, commit
        raise RuntimeError("selection write unavailable")


class _RollbackTrackingBaselineRepository(_BaselineRepository):
    def __init__(self) -> None:
        super().__init__()
        self.rollback_count = 0

    async def rollback(self) -> None:
        self.rollback_count += 1
        self.records.clear()


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
async def test_invocation_rejects_output_evidence_tiers_before_claims_exist(
    risk_tier: RiskTier,
) -> None:
    registry, workflow_name = _registry_with_facts(risk_tier)
    baseline_repository = _BaselineRepository()
    selection_repository = _SelectionRepository()
    baseline_service = BaselineRuntimeEvidencePersistenceService(baseline_repository)
    packets = Mock()
    lifecycle = CanonicalGovernedExecutionEvidenceLifecycle(
        workflow_registry=registry,
        selection_repository=selection_repository,
        baseline_evidence_service=baseline_service,
        packet_persistence_service=packets,
    )

    with pytest.raises(
        GovernedExecutionEvidenceResolutionError,
        match="output boundary",
    ):
        await lifecycle.prepare(
            workflow_name=workflow_name,
            execution_id="execution-one",
        )

    assert selection_repository.selections == []


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


@pytest.mark.asyncio
async def test_resolver_rejects_baseline_evidence_from_another_execution() -> None:
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
    facts = registry.get_authority_facts(workflow_name)
    baseline_repository.records["baseline:execution-one"] = (
        BaselineRuntimeEvidence.create(
            evidence_id="baseline:execution-one",
            authority=facts.authority,
            workflow_name=facts.identity.workflow_name,
            workflow_version=facts.identity.definition_fingerprint,
            execution_id="execution-two",
        )
    )

    with pytest.raises(GovernedExecutionEvidenceResolutionError, match="Baseline"):
        await resolver.resolve(
            workflow_name=workflow_name,
            execution_id="execution-one",
        )


@pytest.mark.asyncio
async def test_invocation_rolls_back_baseline_evidence_when_selection_write_fails() -> (
    None
):
    registry, workflow_name = _registry_with_facts()
    baseline_repository = _RollbackTrackingBaselineRepository()
    baseline_service = BaselineRuntimeEvidencePersistenceService(baseline_repository)
    lifecycle = CanonicalGovernedExecutionEvidenceLifecycle(
        workflow_registry=registry,
        selection_repository=_FailingSelectionRepository(),
        baseline_evidence_service=baseline_service,
        packet_persistence_service=AsyncMock(),
    )

    with pytest.raises(
        GovernedExecutionEvidenceResolutionError,
        match="persistence did not complete",
    ):
        await lifecycle.prepare(
            workflow_name=workflow_name,
            execution_id="execution-one",
        )

    assert baseline_repository.rollback_count == 1
    assert baseline_repository.records == {}
