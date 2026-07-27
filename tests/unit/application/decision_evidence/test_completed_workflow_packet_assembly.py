from __future__ import annotations

from datetime import UTC, datetime

import pytest

from application.decision_evidence import (
    CompletedWorkflowEvidencePacketAssembler,
    CompletedWorkflowEvidencePacketAssemblyRequest,
    CompletedWorkflowNodeEvidenceRequirement,
    EvaluationProvenanceRequirement,
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
    JsonObject,
)
from core.telemetry.collectors.telemetry_collector import TelemetryCollector
from core.telemetry.emitters.application_service_telemetry import (
    ApplicationServiceTelemetry,
)
from core.telemetry.metrics.metrics_store import MetricsStore
from core.telemetry.observability.observability_manager import ObservabilityManager
from domain.authority import RiskTier, classify_risk_authority
from domain.decision_evidence import (
    ClaimEvidenceBinding,
    DecisionEvidencePacketValidationError,
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
    support_snapshot = packet.evidence[0].support_snapshot
    assert support_snapshot is not None
    assert support_snapshot.snapshot_id == "evidence-synthesis:support-snapshot"
    assert support_snapshot.source_label == "workflow_node_output:node-output-synthesis"
    assert '"selected_perspective":"bull"' in support_snapshot.redacted_content
    assert "run-1" in support_snapshot.redacted_content
    assert support_snapshot.content_digest is not None
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
async def test_assembly_includes_redacted_evaluation_provenance_references() -> None:
    bundle = _bundle()
    assembler = CompletedWorkflowEvidencePacketAssembler(
        completed_run_archive=FakeCompletedRunArchive(bundle),
    )

    packet = await assembler.assemble(
        _request(
            supporting_evidence_ids=("evidence-synthesis", "evidence-evaluation"),
            evaluation_provenance=(
                EvaluationProvenanceRequirement(
                    evidence_id="evidence-evaluation",
                    evaluation_run_id="evaluation-run-1",
                    evaluation_run_digest="evaluation-run-digest-1",
                    metric_result_ids=("metric-result-1",),
                    metric_result_digests={"metric-result-1": "metric-result-digest-1"},
                    model_version="gpt-4.1-2026-07-25",
                    profile_version="strategy-evaluation-profile-v1",
                    prompt_version="strategy-evaluation-prompt-v2",
                    rubric_version="strategy-evaluation-rubric-v1",
                    dataset_id="dataset-strategy-synthesis",
                    dataset_version="2026-07-25",
                    metric_versions={"faithfulness": "faithfulness-v1"},
                    evaluation_result_version="evaluation-result-schema-v1",
                    summary="Canonical evaluator provenance for the output.",
                    sensitive_metadata={
                        "prompt_body": "SECRET PROMPT BODY",
                        "hidden_chain_of_thought": "SECRET REASONING TRACE",
                        "retrieval_context": "SECRET CONTEXT BODY",
                    },
                ),
            ),
        )
    )

    evidence_by_id = {evidence.evidence_id: evidence for evidence in packet.evidence}
    evaluation_evidence = evidence_by_id["evidence-evaluation"]
    assert evaluation_evidence.kind is EvidenceReferenceKind.EVALUATION_RUN
    assert evaluation_evidence.support_snapshot is not None
    assert evaluation_evidence.support_snapshot.snapshot_id == (
        "evidence-evaluation:support-snapshot"
    )
    assert "evaluation-run-1" in evaluation_evidence.support_snapshot.redacted_content
    assert "SECRET" not in evaluation_evidence.support_snapshot.redacted_content
    assert "hidden_chain_of_thought" not in (
        evaluation_evidence.support_snapshot.redacted_content
    )
    assert evaluation_evidence.reconstruction_reference_ids == (
        "evidence-evaluation:evaluation-run",
        "evidence-evaluation:metric-result:metric-result-1",
        "evidence-evaluation:model-version",
        "evidence-evaluation:profile-version",
        "evidence-evaluation:prompt-version",
        "evidence-evaluation:rubric-version",
        "evidence-evaluation:dataset-version",
        "evidence-evaluation:metric-version:0",
        "evidence-evaluation:evaluation-result-version",
    )

    references_by_id = {
        reference.reference_id: reference
        for reference in packet.reconstruction_references
    }
    assert references_by_id["evidence-evaluation:evaluation-run"].kind is (
        ReconstructionReferenceKind.EVALUATION_RUN
    )
    assert references_by_id["evidence-evaluation:evaluation-run"].record_id == (
        "evaluation-run-1"
    )
    assert (
        references_by_id["evidence-evaluation:metric-result:metric-result-1"].kind
        is ReconstructionReferenceKind.EVALUATION_METRIC_RESULT
    )
    assert (
        references_by_id[
            "evidence-evaluation:metric-result:metric-result-1"
        ].snapshot_id
        == "evaluation-run-1"
    )
    assert {
        reference.record_id
        for reference in packet.reconstruction_references
        if reference.kind is ReconstructionReferenceKind.LINKED_ARTIFACT
    } == {
        "model:gpt-4.1-2026-07-25",
        "profile:strategy-evaluation-profile-v1",
        "prompt:strategy-evaluation-prompt-v2",
        "rubric:strategy-evaluation-rubric-v1",
        "dataset:dataset-strategy-synthesis:2026-07-25",
        "metric:faithfulness:faithfulness-v1",
        "evaluation-result:evaluation-result-schema-v1",
    }
    assert "SECRET" not in str(packet)
    assert "hidden_chain_of_thought" not in str(packet)


@pytest.mark.asyncio
async def test_assembly_rejects_reasoning_trace_snapshot_content() -> None:
    assembler = CompletedWorkflowEvidencePacketAssembler(
        completed_run_archive=FakeCompletedRunArchive(
            _bundle(
                node_outputs=(
                    _node(outputs={"hidden_chain_of_thought": "private reasoning"}),
                ),
            ),
        ),
    )

    with pytest.raises(
        DecisionEvidencePacketValidationError,
        match="unsafe snapshot content marker 'hidden_chain_of_thought'",
    ):
        await assembler.assemble(_request())


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
async def test_assembly_telemetry_failures_do_not_replace_domain_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    observability = ObservabilityManager(
        collector=TelemetryCollector(
            sinks=(FailingTelemetrySink(),),
            fail_fast=True,
            metrics_store=MetricsStore(),
        ),
    )
    assembler = CompletedWorkflowEvidencePacketAssembler(
        completed_run_archive=FakeCompletedRunArchive(None),
        telemetry=ApplicationServiceTelemetry(observability),
    )

    with caplog.at_level("ERROR"):
        with pytest.raises(MissingCompletedWorkflowEvidenceError):
            await assembler.assemble(_request())

    telemetry_failure_logs = [
        record
        for record in caplog.records
        if record.message == "Decision evidence packet telemetry emission failed."
    ]
    assert len(telemetry_failure_logs) == 1
    assert telemetry_failure_logs[0].exc_info is not None
    assert telemetry_failure_logs[0].error_type == (
        "MissingCompletedWorkflowEvidenceError"
    )
    assert telemetry_failure_logs[0].telemetry_error_type == "RuntimeError"


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


class FailingTelemetrySink:
    async def emit(self, event: object) -> None:
        raise RuntimeError("telemetry sink unavailable")


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
    supporting_evidence_ids: tuple[str, ...] = ("evidence-synthesis",),
    evaluation_provenance: tuple[EvaluationProvenanceRequirement, ...] = (),
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
                    supporting_evidence_ids=supporting_evidence_ids,
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
        evaluation_provenance=evaluation_provenance,
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
    metadata: JsonObject | None = None,
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
        outputs=(
            outputs
            if outputs is not None
            else {"decision": {"selected_perspective": "bull"}}
        ),
        metadata=metadata if metadata is not None else {"quality_status": "normal"},
        errors_json=(),
        started_at=datetime(2026, 7, 25, 13, 1, tzinfo=UTC),
        completed_at=datetime(2026, 7, 25, 13, 2, tzinfo=UTC),
        duration_seconds=60.0,
    )
