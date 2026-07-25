from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from application.decision_evidence import (
    CompletedWorkflowEvidencePacketAssembler,
    CompletedWorkflowEvidencePacketAssemblyRequest,
    CompletedWorkflowNodeEvidenceRequirement,
    DecisionEvidencePacketPersistenceService,
    MalformedDecisionEvidenceReconstructionIdentifierError,
    MissingDecisionEvidenceSourceError,
    StaleDecisionEvidenceSourceError,
    SubstitutedDecisionEvidenceSourceError,
    calculate_completed_workflow_node_evidence_digest,
)
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunArchive,
    CompletedRunBundle,
    CompletedRunRecord,
    JsonObject,
)
from core.storage.persistence.decision_evidence import (
    DecisionEvidencePacketPersistenceRepository,
    DecisionEvidencePacketPersistenceResult,
    DecisionEvidencePacketRecord,
)
from domain.authority import RiskTier, classify_risk_authority
from domain.decision_evidence import (
    ClaimEvidenceBinding,
    DecisionEvidencePacket,
    EvidenceRetentionRequirement,
    MaterialClaim,
    ReconstructionReferenceKind,
)
from tests.helpers.risk_authority_examples import authority_input_for_tier


@pytest.mark.asyncio
async def test_persists_references_and_reconstructs_from_runtime_ids() -> None:
    bundle = _bundle()
    packet = await _packet(bundle=bundle)
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(bundle),
    )

    result = await service.persist_packet(packet)
    reconstructed = await service.reconstruct_packet("packet-1")

    assert result.success is True
    assert reconstructed == packet
    assert repository.records["packet-1"].reconstruction_reference_ids == (
        "evidence-synthesis:completed-run",
        "evidence-synthesis:node-output",
    )
    assert "selected_perspective" not in str(repository.records["packet-1"])


@pytest.mark.asyncio
async def test_reconstruction_reports_missing_canonical_source_record() -> None:
    packet = await _packet(bundle=_bundle())
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(None),
    )
    await service.persist_packet(packet)

    with pytest.raises(
        MissingDecisionEvidenceSourceError, match="morning_report:exec-1"
    ):
        await service.reconstruct_packet("packet-1")


@pytest.mark.asyncio
async def test_reconstruction_reports_stale_workflow_evidence_digest() -> None:
    packet = await _packet(bundle=_bundle())
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(
            _bundle(
                node_outputs=(
                    _node(outputs={"decision": {"selected_perspective": "bear"}}),
                )
            ),
        ),
    )
    await service.persist_packet(packet)

    with pytest.raises(StaleDecisionEvidenceSourceError, match="content digest"):
        await service.reconstruct_packet("packet-1")


@pytest.mark.asyncio
async def test_reconstruction_reports_substituted_workflow_node_evidence() -> None:
    packet = await _packet(bundle=_bundle())
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(
            _bundle(node_outputs=(_node(run_id="other-run"),)),
        ),
    )
    await service.persist_packet(packet)

    with pytest.raises(SubstitutedDecisionEvidenceSourceError, match="does not belong"):
        await service.reconstruct_packet("packet-1")


@pytest.mark.asyncio
async def test_reconstruction_rejects_malformed_completed_run_identifier() -> None:
    packet = await _packet(bundle=_bundle())
    malformed_packet = replace(
        packet,
        reconstruction_references=tuple(
            replace(reference, record_id="malformed-run-id")
            if reference.kind is ReconstructionReferenceKind.COMPLETED_WORKFLOW_RUN
            else reference
            for reference in packet.reconstruction_references
        ),
    )
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(_bundle()),
    )
    await service.persist_packet(malformed_packet)

    with pytest.raises(
        MalformedDecisionEvidenceReconstructionIdentifierError,
        match="completed workflow run",
    ):
        await service.reconstruct_packet("packet-1")


class InMemoryDecisionEvidencePacketRepository(
    DecisionEvidencePacketPersistenceRepository
):
    def __init__(self) -> None:
        self.records: dict[str, DecisionEvidencePacketRecord] = {}

    async def persist_packet_record(
        self,
        record: DecisionEvidencePacketRecord,
    ) -> DecisionEvidencePacketPersistenceResult:
        self.records[record.packet_id] = record
        return DecisionEvidencePacketPersistenceResult.succeeded(record.packet_id)

    async def get_packet_record(
        self,
        packet_id: str,
    ) -> DecisionEvidencePacketRecord | None:
        return self.records.get(packet_id)


class FakeCompletedRunArchive(CompletedRunArchive):
    def __init__(self, bundle: CompletedRunBundle | None) -> None:
        self.bundle = bundle

    async def archive_run(self, bundle: CompletedRunBundle) -> None:
        self.bundle = bundle

    async def load_archived_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> CompletedRunBundle | None:
        if self.bundle is None:
            return None
        if (
            self.bundle.run.workflow_name != workflow_name
            or self.bundle.run.execution_id != execution_id
        ):
            return None
        return self.bundle

    async def list_archived_runs(self, workflow_name: str) -> list[str]:
        if self.bundle is None or self.bundle.run.workflow_name != workflow_name:
            return []
        return [self.bundle.run.execution_id]

    async def delete_archived_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> None:
        self.bundle = None

    async def cleanup_archived_runs(
        self,
        max_age_days: int | None = None,
        max_count: int | None = None,
    ) -> int:
        return 0


async def _packet(*, bundle: CompletedRunBundle) -> DecisionEvidencePacket:
    node_digest = calculate_completed_workflow_node_evidence_digest(
        run=bundle.run,
        node_output=bundle.node_outputs[0],
    )
    assembler = CompletedWorkflowEvidencePacketAssembler(
        completed_run_archive=FakeCompletedRunArchive(bundle),
    )
    return await assembler.assemble(
        CompletedWorkflowEvidencePacketAssemblyRequest(
            packet_id="packet-1",
            output_id="strategy-decision-1",
            authority=classify_risk_authority(
                authority_input_for_tier(RiskTier.ENHANCED),
            ),
            workflow_name="morning_report",
            execution_id="exec-1",
            claims=(
                MaterialClaim(
                    claim_id="claim-1",
                    text="The synthesis selected a bullish strategy posture.",
                    evidence=ClaimEvidenceBinding(
                        supporting_evidence_ids=("evidence-synthesis",),
                    ),
                ),
            ),
            required_node_evidence=(
                CompletedWorkflowNodeEvidenceRequirement(
                    evidence_id="evidence-synthesis",
                    node_name="strategy_synthesis_agent",
                    node_output_id="node-output-synthesis",
                    output_contract="polaris.strategy.synthesis",
                    output_schema_version=1,
                    expected_content_digest=node_digest,
                    summary="Persisted strategy synthesis node output.",
                ),
            ),
            retention=EvidenceRetentionRequirement(
                retain_until="2031-07-25T00:00:00Z",
                policy_id="enhanced-provenance-5y",
            ),
        )
    )


def _bundle(
    *,
    node_outputs: tuple[CompletedNodeOutputRecord, ...] | None = None,
) -> CompletedRunBundle:
    return CompletedRunBundle(
        run=_run(),
        node_outputs=node_outputs if node_outputs is not None else (_node(),),
    )


def _run() -> CompletedRunRecord:
    return CompletedRunRecord(
        run_id="run-1",
        workflow_name="morning_report",
        workflow_id="workflow-1",
        execution_id="exec-1",
        runtime_id="runtime-1",
        status="succeeded",
        success=True,
        context_json={},
        inputs_json={"symbol": "SPY"},
        outputs_json={},
        metadata={},
        errors_json=(),
        started_at=datetime(2026, 7, 25, 13, tzinfo=UTC),
        completed_at=datetime(2026, 7, 25, 13, 5, tzinfo=UTC),
        duration_seconds=300.0,
        node_count=1,
        completed_node_count=1,
        failed_node_count=0,
    )


def _node(
    *,
    run_id: str = "run-1",
    outputs: JsonObject | None = None,
) -> CompletedNodeOutputRecord:
    return CompletedNodeOutputRecord(
        node_output_id="node-output-synthesis",
        run_id=run_id,
        workflow_name="morning_report",
        execution_id="exec-1",
        node_name="strategy_synthesis_agent",
        node_type="strategy",
        output_contract="polaris.strategy.synthesis",
        output_schema_version=1,
        status="succeeded",
        success=True,
        outputs=outputs or {"decision": {"selected_perspective": "bull"}},
        metadata={"quality_status": "normal"},
        errors_json=(),
        started_at=datetime(2026, 7, 25, 13, 1, tzinfo=UTC),
        completed_at=datetime(2026, 7, 25, 13, 2, tzinfo=UTC),
        duration_seconds=60.0,
    )
