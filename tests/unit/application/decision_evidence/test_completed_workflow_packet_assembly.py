from __future__ import annotations

from datetime import UTC, datetime

import pytest

from application.decision_evidence import (
    CompletedWorkflowEvidencePacketAssembler,
    CompletedWorkflowEvidencePacketAssemblyRequest,
    CompletedWorkflowNodeEvidenceRequirement,
    MissingCompletedWorkflowEvidenceError,
    MissingWorkflowNodeOutputEvidenceError,
    StaleWorkflowEvidenceError,
    SubstitutedWorkflowEvidenceError,
    calculate_completed_workflow_node_evidence_digest,
)
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunArchive,
    CompletedRunBundle,
    CompletedRunRecord,
)
from domain.authority import RiskTier, classify_risk_authority
from domain.decision_evidence import (
    ClaimEvidenceBinding,
    EvidenceReferenceKind,
    EvidenceRetentionRequirement,
    MaterialClaim,
    ReconstructionReferenceKind,
)
from tests.helpers.risk_authority_examples import authority_input_for_tier


@pytest.mark.asyncio
async def test_assembles_packet_from_completed_workflow_node_evidence() -> None:
    bundle = _bundle()
    node_digest = calculate_completed_workflow_node_evidence_digest(
        run=bundle.run,
        node_output=bundle.node_outputs[0],
    )
    assembler = CompletedWorkflowEvidencePacketAssembler(
        completed_run_archive=FakeCompletedRunArchive(bundle),
    )

    packet = await assembler.assemble(
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

    assert packet.risk_tier is RiskTier.ENHANCED
    assert packet.claims[0].evidence.supporting_evidence_ids == ("evidence-synthesis",)
    assert packet.evidence[0].kind is EvidenceReferenceKind.WORKFLOW_NODE_OUTPUT
    assert packet.evidence[0].reconstruction_reference_ids == (
        "evidence-synthesis:completed-run",
        "evidence-synthesis:node-output",
    )
    assert packet.evidence[0].summary == "Persisted strategy synthesis node output."
    assert packet.reconstruction_references[0].kind is (
        ReconstructionReferenceKind.COMPLETED_WORKFLOW_RUN
    )
    assert packet.reconstruction_references[0].record_id == "morning_report:exec-1"
    assert packet.reconstruction_references[0].snapshot_id == "run-1"
    assert packet.reconstruction_references[1].kind is (
        ReconstructionReferenceKind.WORKFLOW_NODE_OUTPUT
    )
    assert packet.reconstruction_references[1].record_id == "node-output-synthesis"
    assert packet.reconstruction_references[1].snapshot_id == (
        "morning_report:exec-1:strategy_synthesis_agent"
    )
    assert packet.reconstruction_references[1].content_digest == node_digest


@pytest.mark.asyncio
@pytest.mark.parametrize("tier", [RiskTier.ENHANCED, RiskTier.VIGILANT])
async def test_enhanced_and_vigilant_assembly_fails_without_completed_run(
    tier: RiskTier,
) -> None:
    assembler = CompletedWorkflowEvidencePacketAssembler(
        completed_run_archive=FakeCompletedRunArchive(None),
    )

    with pytest.raises(
        MissingCompletedWorkflowEvidenceError,
        match="completed workflow run 'morning_report:exec-1' was not found",
    ):
        await assembler.assemble(_request(tier=tier))


@pytest.mark.asyncio
async def test_assembly_fails_when_required_node_output_is_missing() -> None:
    assembler = CompletedWorkflowEvidencePacketAssembler(
        completed_run_archive=FakeCompletedRunArchive(
            _bundle(node_outputs=()),
        ),
    )

    with pytest.raises(
        MissingWorkflowNodeOutputEvidenceError,
        match="node output evidence 'evidence-synthesis' was not found",
    ):
        await assembler.assemble(_request())


@pytest.mark.asyncio
async def test_assembly_rejects_stale_workflow_node_evidence() -> None:
    assembler = CompletedWorkflowEvidencePacketAssembler(
        completed_run_archive=FakeCompletedRunArchive(_bundle()),
    )

    with pytest.raises(
        StaleWorkflowEvidenceError,
        match="content digest mismatch",
    ):
        await assembler.assemble(
            _request(expected_content_digest="stale-digest"),
        )


@pytest.mark.asyncio
async def test_assembly_rejects_substituted_workflow_node_evidence() -> None:
    substituted_node = _node(run_id="other-run")
    assembler = CompletedWorkflowEvidencePacketAssembler(
        completed_run_archive=FakeCompletedRunArchive(
            _bundle(node_outputs=(substituted_node,)),
        ),
    )

    with pytest.raises(
        SubstitutedWorkflowEvidenceError,
        match="does not belong to completed workflow run 'run-1'",
    ):
        await assembler.assemble(_request())


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


def _request(
    *,
    tier: RiskTier = RiskTier.ENHANCED,
    expected_content_digest: str | None = None,
) -> CompletedWorkflowEvidencePacketAssemblyRequest:
    return CompletedWorkflowEvidencePacketAssemblyRequest(
        packet_id="packet-1",
        output_id="strategy-decision-1",
        authority=classify_risk_authority(authority_input_for_tier(tier)),
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
                expected_content_digest=expected_content_digest,
            ),
        ),
        retention=EvidenceRetentionRequirement(
            retain_until="2031-07-25T00:00:00Z",
            policy_id="enhanced-provenance-5y",
        ),
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


def _node(*, run_id: str = "run-1") -> CompletedNodeOutputRecord:
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
        outputs={"decision": {"selected_perspective": "bull"}},
        metadata={"quality_status": "normal"},
        errors_json=(),
        started_at=datetime(2026, 7, 25, 13, 1, tzinfo=UTC),
        completed_at=datetime(2026, 7, 25, 13, 2, tzinfo=UTC),
        duration_seconds=60.0,
    )
