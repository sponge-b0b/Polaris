from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from application.decision_evidence import (
    CompletedWorkflowEvidencePacketAssembler,
    CompletedWorkflowEvidencePacketAssemblyRequest,
    CompletedWorkflowNodeEvidenceRequirement,
    DecisionEvidencePacketPersistenceService,
    EvaluationProvenanceRequirement,
    MalformedDecisionEvidenceReconstructionIdentifierError,
    MissingCompletedWorkflowEvidenceError,
    MissingDecisionEvidenceSourceError,
    StaleDecisionEvidenceSourceError,
    SubstitutedDecisionEvidenceSourceError,
    calculate_completed_workflow_node_evidence_digest,
    calculate_evaluation_metric_result_evidence_digest,
    calculate_evaluation_run_evidence_digest,
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
from core.storage.persistence.evaluation import (
    EvaluationMetricResultRecord,
    EvaluationRunRecord,
)
from core.telemetry.collectors.telemetry_collector import TelemetryCollector
from core.telemetry.emitters.application_service_telemetry import (
    ApplicationServiceTelemetry,
)
from core.telemetry.metrics.metrics_store import MetricsStore
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from domain.authority import RiskTier, SourceOfTruthCategory, classify_risk_authority
from domain.decision_evidence import (
    ClaimEvidenceBinding,
    DecisionEvidencePacket,
    EvidenceReference,
    EvidenceReferenceKind,
    EvidenceRetentionRequirement,
    MaterialClaim,
    ReconstructionReference,
    ReconstructionReferenceKind,
)
from domain.evaluation import EvaluationStatus, EvaluationTargetType
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
async def test_reconstruction_validates_evaluation_provenance_references() -> None:
    bundle = _bundle()
    evaluation_run = _evaluation_run()
    metric_result = _metric_result(run_id=evaluation_run.run_id)
    packet = await _packet(
        bundle=bundle,
        evaluation_run=evaluation_run,
        metric_result=metric_result,
    )
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(bundle),
        evaluation_repository=FakeEvaluationProvenanceRepository(
            runs=(evaluation_run,),
            metric_results=(metric_result,),
        ),
    )

    result = await service.persist_packet(packet)
    reconstructed = await service.reconstruct_packet("packet-1")

    assert result.success is True
    assert reconstructed == packet
    assert {
        reference.kind for reference in reconstructed.reconstruction_references
    } >= {
        ReconstructionReferenceKind.EVALUATION_RUN,
        ReconstructionReferenceKind.EVALUATION_METRIC_RESULT,
        ReconstructionReferenceKind.LINKED_ARTIFACT,
    }


@pytest.mark.asyncio
async def test_reconstruction_accepts_all_canonical_reference_kinds() -> None:
    bundle = _bundle()
    evaluation_run = _evaluation_run()
    metric_result = _metric_result(run_id=evaluation_run.run_id)
    packet = _packet_with_every_reconstruction_kind(
        bundle=bundle,
        evaluation_run=evaluation_run,
        metric_result=metric_result,
    )
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(bundle),
        evaluation_repository=FakeEvaluationProvenanceRepository(
            runs=(evaluation_run,),
            metric_results=(metric_result,),
        ),
    )

    await service.persist_packet(packet)
    reconstructed = await service.reconstruct_packet("packet-all-reference-kinds")

    assert reconstructed == packet
    reconstructed_kinds = tuple(
        reference.kind for reference in reconstructed.reconstruction_references
    )
    assert reconstructed_kinds == (
        ReconstructionReferenceKind.COMPLETED_WORKFLOW_RUN,
        ReconstructionReferenceKind.WORKFLOW_NODE_OUTPUT,
        ReconstructionReferenceKind.CANONICAL_DOMAIN_RECORD,
        ReconstructionReferenceKind.RAG_RETRIEVAL_CONTEXT,
        ReconstructionReferenceKind.RAG_CITATION_CONTEXT,
        ReconstructionReferenceKind.EVALUATION_RUN,
        ReconstructionReferenceKind.EVALUATION_METRIC_RESULT,
        ReconstructionReferenceKind.TRACE_CONTEXT,
        ReconstructionReferenceKind.LINKED_ARTIFACT,
    )


@pytest.mark.asyncio
async def test_reconstruction_reports_malformed_rag_context_reference() -> None:
    bundle = _bundle()
    evaluation_run = _evaluation_run()
    metric_result = _metric_result(run_id=evaluation_run.run_id)
    packet = _packet_with_every_reconstruction_kind(
        bundle=bundle,
        evaluation_run=evaluation_run,
        metric_result=metric_result,
    )
    malformed_packet = replace(
        packet,
        reconstruction_references=tuple(
            replace(reference, content_digest=None)
            if reference.kind is ReconstructionReferenceKind.RAG_RETRIEVAL_CONTEXT
            else reference
            for reference in packet.reconstruction_references
        ),
    )
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(bundle),
        evaluation_repository=FakeEvaluationProvenanceRepository(
            runs=(evaluation_run,),
            metric_results=(metric_result,),
        ),
    )
    await service.persist_packet(malformed_packet)

    with pytest.raises(
        MalformedDecisionEvidenceReconstructionIdentifierError,
        match="RAG retrieval context reconstruction reference",
    ):
        await service.reconstruct_packet("packet-all-reference-kinds")


@pytest.mark.asyncio
async def test_reconstruction_reports_missing_evaluation_record() -> None:
    bundle = _bundle()
    evaluation_run = _evaluation_run()
    metric_result = _metric_result(run_id=evaluation_run.run_id)
    packet = await _packet(
        bundle=bundle,
        evaluation_run=evaluation_run,
        metric_result=metric_result,
    )
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(bundle),
        evaluation_repository=FakeEvaluationProvenanceRepository(),
    )
    await service.persist_packet(packet)

    with pytest.raises(
        MissingDecisionEvidenceSourceError,
        match="evaluation run source record 'evaluation-run-1' was not found",
    ):
        await service.reconstruct_packet("packet-1")


@pytest.mark.asyncio
async def test_reconstruction_reports_missing_evaluation_metric_record() -> None:
    bundle = _bundle()
    evaluation_run = _evaluation_run()
    metric_result = _metric_result(run_id=evaluation_run.run_id)
    packet = await _packet(
        bundle=bundle,
        evaluation_run=evaluation_run,
        metric_result=metric_result,
    )
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(bundle),
        evaluation_repository=FakeEvaluationProvenanceRepository(
            runs=(evaluation_run,),
        ),
    )
    await service.persist_packet(packet)

    with pytest.raises(
        MissingDecisionEvidenceSourceError,
        match="evaluation metric result source record 'metric-result-1' was not found",
    ):
        await service.reconstruct_packet("packet-1")


@pytest.mark.asyncio
async def test_reconstruction_reports_stale_evaluation_reference() -> None:
    bundle = _bundle()
    evaluation_run = _evaluation_run(status=EvaluationStatus.PASSED)
    metric_result = _metric_result(run_id=evaluation_run.run_id)
    packet = await _packet(
        bundle=bundle,
        evaluation_run=evaluation_run,
        metric_result=metric_result,
    )
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(bundle),
        evaluation_repository=FakeEvaluationProvenanceRepository(
            runs=(_evaluation_run(status=EvaluationStatus.FAILED),),
            metric_results=(metric_result,),
        ),
    )
    await service.persist_packet(packet)

    with pytest.raises(
        StaleDecisionEvidenceSourceError,
        match="evaluation run evidence content digest is stale",
    ):
        await service.reconstruct_packet("packet-1")


@pytest.mark.asyncio
async def test_reconstruction_reports_stale_evaluation_metric_reference() -> None:
    bundle = _bundle()
    evaluation_run = _evaluation_run()
    metric_result = _metric_result(run_id=evaluation_run.run_id, score=0.92)
    packet = await _packet(
        bundle=bundle,
        evaluation_run=evaluation_run,
        metric_result=metric_result,
    )
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(bundle),
        evaluation_repository=FakeEvaluationProvenanceRepository(
            runs=(evaluation_run,),
            metric_results=(_metric_result(run_id=evaluation_run.run_id, score=0.81),),
        ),
    )
    await service.persist_packet(packet)

    with pytest.raises(
        StaleDecisionEvidenceSourceError,
        match="evaluation metric result evidence content digest is stale",
    ):
        await service.reconstruct_packet("packet-1")


@pytest.mark.asyncio
async def test_persistence_redacts_sensitive_evaluation_provenance_metadata() -> None:
    bundle = _bundle()
    evaluation_run = _evaluation_run()
    metric_result = _metric_result(run_id=evaluation_run.run_id)
    packet = await _packet(
        bundle=bundle,
        evaluation_run=evaluation_run,
        metric_result=metric_result,
        sensitive_metadata={
            "prompt_body": "SECRET PROMPT BODY",
            "hidden_chain_of_thought": "SECRET REASONING TRACE",
            "retrieval_context": "SECRET CONTEXT BODY",
        },
    )
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(bundle),
        evaluation_repository=FakeEvaluationProvenanceRepository(
            runs=(evaluation_run,),
            metric_results=(metric_result,),
        ),
    )

    await service.persist_packet(packet)

    assert "SECRET" not in str(repository.records["packet-1"])
    assert "hidden_chain_of_thought" not in str(repository.records["packet-1"])


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


@pytest.mark.asyncio
async def test_reconstruction_rejects_missing_retention_metadata() -> None:
    packet = await _packet(bundle=_bundle())
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(_bundle()),
    )
    await service.persist_packet(packet)
    repository.records["packet-1"] = replace(
        repository.records["packet-1"],
        retention_metadata={},
    )

    with pytest.raises(
        MalformedDecisionEvidenceReconstructionIdentifierError,
        match="retention metadata",
    ):
        await service.reconstruct_packet("packet-1")


@pytest.mark.asyncio
async def test_reconstruction_failure_emits_canonical_telemetry() -> None:
    packet = await _packet(bundle=_bundle())
    repository = InMemoryDecisionEvidencePacketRepository()
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(None),
        telemetry=ApplicationServiceTelemetry(observability),
    )
    await service.persist_packet(packet)

    with pytest.raises(MissingDecisionEvidenceSourceError):
        await service.reconstruct_packet("packet-1")

    failure_events = [
        event
        for event in sink.events
        if event.event_type == "application.service.failed"
    ]
    assert len(failure_events) == 1
    event = failure_events[0]
    assert (
        event.attributes["service_name"] == "DecisionEvidencePacketPersistenceService"
    )
    assert event.attributes["request_name"] == "DecisionEvidencePacketReconstruction"
    assert event.attributes["operation"] == "decision_evidence_packet_reconstruction"
    assert event.attributes["packet_id"] == "packet-1"
    assert event.attributes["risk_tier"] == "enhanced"
    assert event.attributes["retention_policy_id"] == "enhanced-provenance-5y"
    assert event.payload["error_type"] == "MissingDecisionEvidenceSourceError"


@pytest.mark.asyncio
async def test_reconstruction_telemetry_failures_do_not_replace_domain_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    packet = await _packet(bundle=_bundle())
    repository = InMemoryDecisionEvidencePacketRepository()
    observability = ObservabilityManager(
        collector=TelemetryCollector(
            sinks=(FailingTelemetrySink(),),
            fail_fast=True,
            metrics_store=MetricsStore(),
        ),
    )
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(None),
        telemetry=ApplicationServiceTelemetry(observability),
    )
    await service.persist_packet(packet)

    with caplog.at_level("ERROR"):
        with pytest.raises(MissingDecisionEvidenceSourceError):
            await service.reconstruct_packet("packet-1")

    telemetry_failure_logs = [
        record
        for record in caplog.records
        if record.message == "Decision evidence packet telemetry emission failed."
    ]
    assert len(telemetry_failure_logs) == 1
    assert telemetry_failure_logs[0].exc_info is not None
    assert telemetry_failure_logs[0].error_type == "MissingDecisionEvidenceSourceError"
    assert telemetry_failure_logs[0].telemetry_error_type == "RuntimeError"


@pytest.mark.asyncio
async def test_packet_assembly_failure_emits_canonical_telemetry() -> None:
    bundle = _bundle()
    request = _assembly_request(bundle=bundle)
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    assembler = CompletedWorkflowEvidencePacketAssembler(
        completed_run_archive=FakeCompletedRunArchive(None),
        telemetry=ApplicationServiceTelemetry(observability),
    )

    with pytest.raises(MissingCompletedWorkflowEvidenceError):
        await assembler.assemble(request)

    failure_events = [
        event
        for event in sink.events
        if event.event_type == "application.service.failed"
    ]
    assert len(failure_events) == 1
    event = failure_events[0]
    assert event.attributes["service_name"] == (
        "CompletedWorkflowEvidencePacketAssembler"
    )
    assert event.attributes["request_name"] == (
        "CompletedWorkflowEvidencePacketAssembly"
    )
    assert event.attributes["operation"] == "decision_evidence_packet_assembly"
    assert event.attributes["packet_id"] == "packet-1"
    assert event.attributes["workflow_name"] == "morning_report"
    assert event.attributes["execution_id"] == "exec-1"
    assert event.attributes["risk_tier"] == "enhanced"
    assert event.attributes["retention_policy_id"] == "enhanced-provenance-5y"
    assert event.payload["error_type"] == "MissingCompletedWorkflowEvidenceError"


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


class FakeEvaluationProvenanceRepository:
    def __init__(
        self,
        *,
        runs: tuple[EvaluationRunRecord, ...] = (),
        metric_results: tuple[EvaluationMetricResultRecord, ...] = (),
    ) -> None:
        self.runs = {run.run_id: run for run in runs}
        self.metric_results_by_run: dict[
            str,
            tuple[EvaluationMetricResultRecord, ...],
        ] = {}
        for metric_result in metric_results:
            existing = self.metric_results_by_run.get(metric_result.run_id, ())
            self.metric_results_by_run[metric_result.run_id] = (
                *existing,
                metric_result,
            )

    async def get_run(self, run_id: str) -> EvaluationRunRecord | None:
        return self.runs.get(run_id)

    async def list_metric_results(
        self,
        run_id: str,
    ) -> tuple[EvaluationMetricResultRecord, ...]:
        return self.metric_results_by_run.get(run_id, ())


class FailingTelemetrySink:
    async def emit(self, event: object) -> None:
        raise RuntimeError("telemetry sink unavailable")


async def _packet(
    *,
    bundle: CompletedRunBundle,
    evaluation_run: EvaluationRunRecord | None = None,
    metric_result: EvaluationMetricResultRecord | None = None,
    sensitive_metadata: dict[str, object] | None = None,
) -> DecisionEvidencePacket:
    assembler = CompletedWorkflowEvidencePacketAssembler(
        completed_run_archive=FakeCompletedRunArchive(bundle),
    )
    return await assembler.assemble(
        _assembly_request(
            bundle=bundle,
            evaluation_run=evaluation_run,
            metric_result=metric_result,
            sensitive_metadata=sensitive_metadata,
        )
    )


def _assembly_request(
    *,
    bundle: CompletedRunBundle,
    evaluation_run: EvaluationRunRecord | None = None,
    metric_result: EvaluationMetricResultRecord | None = None,
    sensitive_metadata: dict[str, object] | None = None,
) -> CompletedWorkflowEvidencePacketAssemblyRequest:
    node_digest = calculate_completed_workflow_node_evidence_digest(
        run=bundle.run,
        node_output=bundle.node_outputs[0],
    )
    supporting_evidence_ids = ["evidence-synthesis"]
    evaluation_provenance: tuple[EvaluationProvenanceRequirement, ...] = ()
    if evaluation_run is not None and metric_result is not None:
        supporting_evidence_ids.append("evidence-evaluation")
        evaluation_provenance = (
            EvaluationProvenanceRequirement(
                evidence_id="evidence-evaluation",
                evaluation_run_id=evaluation_run.run_id,
                evaluation_run_digest=calculate_evaluation_run_evidence_digest(
                    run=evaluation_run,
                ),
                metric_result_ids=(metric_result.metric_result_id,),
                metric_result_digests={
                    metric_result.metric_result_id: (
                        calculate_evaluation_metric_result_evidence_digest(
                            metric_result=metric_result,
                        )
                    )
                },
                model_version=evaluation_run.evaluator_model,
                profile_version="strategy-evaluation-profile-v1",
                prompt_version="strategy-evaluation-prompt-v2",
                rubric_version="strategy-evaluation-rubric-v1",
                dataset_id=evaluation_run.dataset_id,
                dataset_version="2026-07-25",
                metric_versions={
                    metric_result.metric_name: (
                        metric_result.threshold_version or "faithfulness-threshold-v1"
                    )
                },
                evaluation_result_version="evaluation-result-schema-v1",
                summary="Canonical evaluator provenance for the output.",
                sensitive_metadata=sensitive_metadata or {},
            ),
        )
    return CompletedWorkflowEvidencePacketAssemblyRequest(
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
                    supporting_evidence_ids=tuple(supporting_evidence_ids),
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
        evaluation_provenance=evaluation_provenance,
    )


def _packet_with_every_reconstruction_kind(
    *,
    bundle: CompletedRunBundle,
    evaluation_run: EvaluationRunRecord,
    metric_result: EvaluationMetricResultRecord,
) -> DecisionEvidencePacket:
    node_output = bundle.node_outputs[0]
    node_digest = calculate_completed_workflow_node_evidence_digest(
        run=bundle.run,
        node_output=node_output,
    )
    evaluation_run_digest = calculate_evaluation_run_evidence_digest(run=evaluation_run)
    metric_digest = calculate_evaluation_metric_result_evidence_digest(
        metric_result=metric_result,
    )
    reconstruction_references = (
        ReconstructionReference(
            reference_id="completed-run",
            kind=ReconstructionReferenceKind.COMPLETED_WORKFLOW_RUN,
            record_id="morning_report:exec-1",
            source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
            snapshot_id=bundle.run.run_id,
        ),
        ReconstructionReference(
            reference_id="workflow-node",
            kind=ReconstructionReferenceKind.WORKFLOW_NODE_OUTPUT,
            record_id=node_output.node_output_id,
            source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
            snapshot_id="morning_report:exec-1:strategy_synthesis_agent",
            content_digest=node_digest,
        ),
        ReconstructionReference(
            reference_id="canonical-record",
            kind=ReconstructionReferenceKind.CANONICAL_DOMAIN_RECORD,
            record_id="strategy-decision-1",
            source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
            content_digest="digest-canonical-record",
        ),
        ReconstructionReference(
            reference_id="rag-retrieval",
            kind=ReconstructionReferenceKind.RAG_RETRIEVAL_CONTEXT,
            record_id="rag-context-1",
            source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
            snapshot_id="rag-query-1",
            content_digest="digest-rag-context",
        ),
        ReconstructionReference(
            reference_id="rag-citation",
            kind=ReconstructionReferenceKind.RAG_CITATION_CONTEXT,
            record_id="rag-document-1:chunk-1",
            source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
            snapshot_id="citation-1",
            content_digest="digest-rag-citation",
        ),
        ReconstructionReference(
            reference_id="evaluation-run",
            kind=ReconstructionReferenceKind.EVALUATION_RUN,
            record_id=evaluation_run.run_id,
            source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
            content_digest=evaluation_run_digest,
        ),
        ReconstructionReference(
            reference_id="evaluation-metric",
            kind=ReconstructionReferenceKind.EVALUATION_METRIC_RESULT,
            record_id=metric_result.metric_result_id,
            source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
            snapshot_id=evaluation_run.run_id,
            content_digest=metric_digest,
        ),
        ReconstructionReference(
            reference_id="trace-context",
            kind=ReconstructionReferenceKind.TRACE_CONTEXT,
            record_id="trace-1:span-1",
            source_of_truth=SourceOfTruthCategory.TELEMETRY,
            snapshot_id="trace-1",
            content_digest="digest-trace-context",
        ),
        ReconstructionReference(
            reference_id="linked-artifact",
            kind=ReconstructionReferenceKind.LINKED_ARTIFACT,
            record_id="model:gpt-4.1-2026-07-25",
            source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
        ),
    )
    return DecisionEvidencePacket(
        packet_id="packet-all-reference-kinds",
        output_id="strategy-decision-1",
        authority=classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED)),
        claims=(
            MaterialClaim(
                claim_id="claim-1",
                text="The synthesis selected a supported strategy posture.",
                evidence=ClaimEvidenceBinding(
                    supporting_evidence_ids=("evidence-all",),
                ),
            ),
        ),
        evidence=(
            EvidenceReference(
                evidence_id="evidence-all",
                kind=EvidenceReferenceKind.CANONICAL_RECORD,
                reconstruction_reference_ids=tuple(
                    reference.reference_id for reference in reconstruction_references
                ),
                summary="Evidence exercising every canonical reconstruction kind.",
                source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
            ),
        ),
        reconstruction_references=reconstruction_references,
        retention=EvidenceRetentionRequirement(
            retain_until="2031-07-25T00:00:00Z",
            policy_id="enhanced-provenance-5y",
        ),
    )


def _evaluation_run(
    *,
    status: EvaluationStatus = EvaluationStatus.PASSED,
    evaluator_model: str = "gpt-4.1-2026-07-25",
    dataset_id: str = "dataset-strategy-synthesis",
) -> EvaluationRunRecord:
    return EvaluationRunRecord(
        run_id="evaluation-run-1",
        target_type=EvaluationTargetType.STRATEGY_SYNTHESIS,
        status=status,
        evaluator_provider="openai",
        evaluator_model=evaluator_model,
        dataset_id=dataset_id,
        case_ids=("case-1",),
        started_at=datetime(2026, 7, 25, 13, 6, tzinfo=UTC),
        completed_at=datetime(2026, 7, 25, 13, 7, tzinfo=UTC),
    )


def _metric_result(
    *,
    run_id: str,
    metric_result_id: str = "metric-result-1",
    score: float = 0.92,
) -> EvaluationMetricResultRecord:
    return EvaluationMetricResultRecord(
        metric_result_id=metric_result_id,
        run_id=run_id,
        case_id="case-1",
        metric_name="faithfulness",
        score=score,
        status=EvaluationStatus.PASSED,
        evaluator_provider="openai",
        evaluator_model="gpt-4.1-2026-07-25",
        threshold=0.8,
        threshold_version="faithfulness-threshold-v1",
        passed=True,
        reason="The final answer remains grounded in persisted evidence.",
        duration_ms=125.0,
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
