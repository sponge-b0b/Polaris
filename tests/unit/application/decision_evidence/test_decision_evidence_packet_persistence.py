from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from typing import cast

import pytest

from application.decision_evidence import (
    CanonicalDomainSourceRecord,
    CompletedWorkflowEvidencePacketAssembler,
    CompletedWorkflowEvidencePacketAssemblyRequest,
    CompletedWorkflowNodeEvidenceRequirement,
    DecisionEvidencePacketNotFoundError,
    DecisionEvidencePacketPersistenceService,
    EvaluationProvenanceRequirement,
    MalformedDecisionEvidenceReconstructionIdentifierError,
    MissingCompletedWorkflowEvidenceError,
    MissingDecisionEvidenceSnapshotError,
    MissingDecisionEvidenceSourceError,
    StaleDecisionEvidenceSourceError,
    SubstitutedDecisionEvidenceSourceError,
    TamperedDecisionEvidenceSnapshotError,
    TamperedDecisionEvidenceSourceError,
    calculate_completed_workflow_node_evidence_digest,
    calculate_evaluation_artifact_evidence_digest,
    calculate_evaluation_metric_result_evidence_digest,
    calculate_evaluation_run_evidence_digest,
    calculate_rag_citation_source_evidence_digest,
    calculate_rag_retrieval_context_evidence_digest,
    calculate_trace_context_evidence_digest,
)
from application.persistence.di import ApplicationPersistenceDIProvider
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
    EvaluationArtifactRecord,
    EvaluationMetricResultRecord,
    EvaluationRunRecord,
)
from core.storage.persistence.rag import (
    RagChunkRecord,
    RagDocumentRecord,
    RagQueryLogRecord,
)
from core.storage.persistence.repositories import (
    PostgresDecisionEvidencePacketRepository,
    PostgresEvaluationPersistenceRepository,
    PostgresRagPersistenceRepository,
    PostgresTelemetryPersistenceRepository,
)
from core.storage.persistence.telemetry import TelemetryTraceRecord
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
    ClaimMaterialityTier,
    DecisionEvidencePacket,
    EvidenceReference,
    EvidenceReferenceKind,
    EvidenceRetentionRequirement,
    MaterialClaim,
    ReconstructionReference,
    ReconstructionReferenceKind,
    SupportingEvidenceSnapshot,
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
    raw_snapshot = repository.records["packet-1"].evidence_references[0][
        "support_snapshot"
    ]
    assert isinstance(raw_snapshot, Mapping)
    redacted_content = raw_snapshot["redacted_content"]
    assert isinstance(redacted_content, str)
    assert '"selected_perspective":"bull"' in redacted_content


@pytest.mark.asyncio
async def test_persists_unresolved_conflicting_evidence_classification() -> None:
    packet = await _packet(bundle=_bundle())
    packet = replace(
        packet,
        claims=(
            replace(
                packet.claims[0],
                evidence=ClaimEvidenceBinding(
                    supporting_evidence_ids=("evidence-synthesis",),
                    conflicting_evidence_ids=("evidence-conflict",),
                    unresolved_conflicting_evidence_ids=("evidence-conflict",),
                ),
            ),
        ),
        evidence=(
            *packet.evidence,
            EvidenceReference(
                evidence_id="evidence-conflict",
                kind=EvidenceReferenceKind.CANONICAL_RECORD,
                reconstruction_reference_ids=("conflict-record",),
                summary="Contrary evidence still unresolved for readiness review.",
                source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
            ),
        ),
        reconstruction_references=(
            *packet.reconstruction_references,
            ReconstructionReference(
                reference_id="conflict-record",
                kind=ReconstructionReferenceKind.CANONICAL_DOMAIN_RECORD,
                record_id="market-snapshot:SPY:2026-07-25",
                source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
                content_digest="digest-conflict-record",
            ),
        ),
    )
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(_bundle()),
        canonical_domain_record_repository=FakeCanonicalDomainRecordRepository(
            records=(
                _canonical_domain_source_record(
                    record_id="market-snapshot:SPY:2026-07-25",
                    content_digest="digest-conflict-record",
                ),
            ),
        ),
    )

    result = await service.persist_packet(packet)
    reconstructed = await service.reconstruct_packet("packet-1")

    assert result.success is True
    raw_claim_evidence = repository.records["packet-1"].claim_audit[0]["evidence"]
    assert isinstance(raw_claim_evidence, Mapping)
    assert raw_claim_evidence["unresolved_conflicting_evidence_ids"] == [
        "evidence-conflict",
    ]
    assert reconstructed == packet
    assert reconstructed.claims[0].evidence.conflicting_evidence_ids == (
        "evidence-conflict",
    )
    assert reconstructed.claims[0].evidence.unresolved_conflicting_evidence_ids == (
        "evidence-conflict",
    )


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
        canonical_domain_record_repository=FakeCanonicalDomainRecordRepository(
            records=(_canonical_domain_source_record(),),
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
async def test_reconstruction_validates_non_workflow_canonical_sources() -> None:
    bundle = _bundle()
    evaluation_run = _evaluation_run()
    metric_result = _metric_result(run_id=evaluation_run.run_id)
    rag_document = _rag_document()
    rag_chunk = _rag_chunk(document_id=rag_document.document_id)
    rag_context_payload = _rag_context_payload(
        rag_document=rag_document, rag_chunk=rag_chunk
    )
    trace = _trace_record()
    artifact = _evaluation_artifact(run_id=evaluation_run.run_id)
    packet = _packet_with_every_reconstruction_kind(
        bundle=bundle,
        evaluation_run=evaluation_run,
        metric_result=metric_result,
        rag_document=rag_document,
        rag_chunk=rag_chunk,
        rag_context_payload=rag_context_payload,
        trace=trace,
        artifact=artifact,
    )
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(bundle),
        evaluation_repository=FakeEvaluationProvenanceRepository(
            runs=(evaluation_run,),
            metric_results=(metric_result,),
            artifacts=(artifact,),
        ),
        rag_repository=FakeRagEvidenceSourceRepository(
            documents=(rag_document,),
            chunks=(rag_chunk,),
            query_logs=(_rag_query_log(context_payload=rag_context_payload),),
        ),
        trace_repository=FakeTelemetryTraceSourceRepository(traces=(trace,)),
        canonical_domain_record_repository=FakeCanonicalDomainRecordRepository(
            records=(_canonical_domain_source_record(),),
        ),
    )

    await service.persist_packet(packet)
    reconstructed = await service.reconstruct_packet("packet-all-reference-kinds")

    assert reconstructed == packet


@pytest.mark.asyncio
async def test_reconstruction_source_verifies_canonical_domain_record() -> None:
    reference = _canonical_domain_record_reference(snapshot_id="record-version-1")
    packet = _canonical_domain_packet(reference=reference)
    canonical_repository = FakeCanonicalDomainRecordRepository(
        records=(
            _canonical_domain_source_record(
                content_digest=reference.content_digest,
                version="record-version-1",
            ),
        ),
    )
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(_bundle()),
        canonical_domain_record_repository=canonical_repository,
    )

    await service.persist_packet(packet)
    reconstructed = await service.reconstruct_packet("packet-canonical-record")

    assert reconstructed == packet
    assert canonical_repository.requested_record_ids == ("strategy-decision-1",)


@pytest.mark.asyncio
async def test_reconstruction_reports_missing_canonical_domain_record() -> None:
    packet = _canonical_domain_packet(
        materiality=ClaimMaterialityTier.CONTEXTUAL,
        support_snapshot=None,
    )
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(_bundle()),
        canonical_domain_record_repository=FakeCanonicalDomainRecordRepository(),
    )
    await service.persist_packet(packet)

    with pytest.raises(
        MissingDecisionEvidenceSourceError,
        match="canonical domain source record 'strategy-decision-1' was not found",
    ):
        await service.reconstruct_packet("packet-canonical-record")


@pytest.mark.asyncio
async def test_reconstruction_reports_stale_canonical_domain_record_version() -> None:
    reference = _canonical_domain_record_reference(snapshot_id="record-version-1")
    packet = _canonical_domain_packet(reference=reference)
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(_bundle()),
        canonical_domain_record_repository=FakeCanonicalDomainRecordRepository(
            records=(
                _canonical_domain_source_record(
                    content_digest=reference.content_digest,
                    version="record-version-2",
                ),
            ),
        ),
    )
    await service.persist_packet(packet)

    with pytest.raises(
        StaleDecisionEvidenceSourceError,
        match="version or snapshot is stale",
    ):
        await service.reconstruct_packet("packet-canonical-record")


@pytest.mark.asyncio
async def test_reconstruction_reports_substituted_canonical_domain_record() -> None:
    packet = _canonical_domain_packet()
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(_bundle()),
        canonical_domain_record_repository=FakeCanonicalDomainRecordRepository(
            records_by_lookup={
                "strategy-decision-1": _canonical_domain_source_record(
                    record_id="strategy-decision-2",
                ),
            },
        ),
    )
    await service.persist_packet(packet)

    with pytest.raises(
        SubstitutedDecisionEvidenceSourceError,
        match="does not match reconstruction identifier",
    ):
        await service.reconstruct_packet("packet-canonical-record")


@pytest.mark.asyncio
async def test_reconstruction_reports_tampered_canonical_domain_record() -> None:
    packet = _canonical_domain_packet()
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(_bundle()),
        canonical_domain_record_repository=FakeCanonicalDomainRecordRepository(
            records=(
                _canonical_domain_source_record(
                    snapshot_payload={
                        "record_id": "strategy-decision-1",
                        "decision": "tampered",
                    },
                ),
            ),
        ),
    )
    await service.persist_packet(packet)

    with pytest.raises(
        TamperedDecisionEvidenceSourceError,
        match="content digest does not match retained source content",
    ):
        await service.reconstruct_packet("packet-canonical-record")


@pytest.mark.asyncio
async def test_reconstruction_reports_canonical_domain_record_digest_mismatch() -> None:
    packet = _canonical_domain_packet()
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(_bundle()),
        canonical_domain_record_repository=FakeCanonicalDomainRecordRepository(
            records=(
                _canonical_domain_source_record(
                    content_digest="digest-canonical-record-v2",
                ),
            ),
        ),
    )
    await service.persist_packet(packet)

    with pytest.raises(
        StaleDecisionEvidenceSourceError,
        match="content digest is stale",
    ):
        await service.reconstruct_packet("packet-canonical-record")


@pytest.mark.asyncio
async def test_reconstruction_allows_canonical_domain_record_snapshot_fallback() -> (
    None
):
    packet = _canonical_domain_packet()
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(_bundle()),
    )
    await service.persist_packet(packet)

    reconstructed = await service.reconstruct_packet("packet-canonical-record")

    assert reconstructed == packet


@pytest.mark.asyncio
async def test_reconstruction_validates_rag_citation_with_canonical_colon_ids() -> None:
    bundle = _bundle()
    evaluation_run = _evaluation_run()
    metric_result = _metric_result(run_id=evaluation_run.run_id)
    document_id = (
        "rag_document:strategy_decisions:strategy_decision:strategy-decision-1"
    )
    rag_document = _rag_document(document_id=document_id)
    rag_chunk = _rag_chunk(
        document_id=rag_document.document_id,
        chunk_id=f"{rag_document.document_id}:chunk:0",
    )
    rag_context_payload = _rag_context_payload(
        rag_document=rag_document, rag_chunk=rag_chunk
    )
    packet = _packet_with_every_reconstruction_kind(
        bundle=bundle,
        evaluation_run=evaluation_run,
        metric_result=metric_result,
        rag_document=rag_document,
        rag_chunk=rag_chunk,
        rag_context_payload=rag_context_payload,
    )
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(bundle),
        evaluation_repository=FakeEvaluationProvenanceRepository(
            runs=(evaluation_run,),
            metric_results=(metric_result,),
        ),
        rag_repository=FakeRagEvidenceSourceRepository(
            documents=(rag_document,),
            chunks=(rag_chunk,),
            query_logs=(_rag_query_log(context_payload=rag_context_payload),),
        ),
    )

    await service.persist_packet(packet)
    reconstructed = await service.reconstruct_packet("packet-all-reference-kinds")

    assert reconstructed == packet


@pytest.mark.asyncio
async def test_reconstruction_falls_back_for_transient_web_rag_citation() -> None:
    bundle = _bundle()
    evaluation_run = _evaluation_run()
    metric_result = _metric_result(run_id=evaluation_run.run_id)
    packet = _packet_with_every_reconstruction_kind(
        bundle=bundle,
        evaluation_run=evaluation_run,
        metric_result=metric_result,
    )
    transient_web_record_id = (
        "external_web:https://example.com/breadth:web_document:web-context:document"
    )
    packet = replace(
        packet,
        reconstruction_references=tuple(
            replace(reference, record_id=transient_web_record_id)
            if reference.kind is ReconstructionReferenceKind.RAG_CITATION_CONTEXT
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
        rag_repository=FakeRagEvidenceSourceRepository(),
    )

    await service.persist_packet(packet)
    reconstructed = await service.reconstruct_packet("packet-all-reference-kinds")

    assert reconstructed == packet


@pytest.mark.asyncio
async def test_reconstruction_reports_stale_rag_retrieval_context() -> None:
    bundle = _bundle()
    evaluation_run = _evaluation_run()
    metric_result = _metric_result(run_id=evaluation_run.run_id)
    rag_document = _rag_document()
    rag_chunk = _rag_chunk(document_id=rag_document.document_id)
    rag_context_payload = _rag_context_payload(
        rag_document=rag_document, rag_chunk=rag_chunk
    )
    stale_context_payload = {**rag_context_payload, "text": "stale retrieved text"}
    packet = _packet_with_every_reconstruction_kind(
        bundle=bundle,
        evaluation_run=evaluation_run,
        metric_result=metric_result,
        rag_document=rag_document,
        rag_chunk=rag_chunk,
        rag_context_payload=rag_context_payload,
    )
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(bundle),
        evaluation_repository=FakeEvaluationProvenanceRepository(
            runs=(evaluation_run,),
            metric_results=(metric_result,),
        ),
        rag_repository=FakeRagEvidenceSourceRepository(
            documents=(rag_document,),
            chunks=(rag_chunk,),
            query_logs=(_rag_query_log(context_payload=stale_context_payload),),
        ),
    )
    await service.persist_packet(packet)

    with pytest.raises(
        StaleDecisionEvidenceSourceError,
        match="RAG retrieval context evidence content digest is stale",
    ):
        await service.reconstruct_packet("packet-all-reference-kinds")


@pytest.mark.asyncio
async def test_reconstruction_reports_substituted_rag_citation_chunk() -> None:
    bundle = _bundle()
    evaluation_run = _evaluation_run()
    metric_result = _metric_result(run_id=evaluation_run.run_id)
    rag_document = _rag_document()
    rag_chunk = _rag_chunk(document_id=rag_document.document_id)
    rag_context_payload = _rag_context_payload(
        rag_document=rag_document, rag_chunk=rag_chunk
    )
    substituted_chunk = _rag_chunk(
        document_id="other-rag-document",
        chunk_id=rag_chunk.chunk_id,
    )
    packet = _packet_with_every_reconstruction_kind(
        bundle=bundle,
        evaluation_run=evaluation_run,
        metric_result=metric_result,
        rag_document=rag_document,
        rag_chunk=rag_chunk,
        rag_context_payload=rag_context_payload,
    )
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(bundle),
        evaluation_repository=FakeEvaluationProvenanceRepository(
            runs=(evaluation_run,),
            metric_results=(metric_result,),
        ),
        rag_repository=FakeRagEvidenceSourceRepository(
            documents=(rag_document,),
            chunks=(substituted_chunk,),
            query_logs=(_rag_query_log(context_payload=rag_context_payload),),
        ),
    )
    await service.persist_packet(packet)

    with pytest.raises(
        SubstitutedDecisionEvidenceSourceError,
        match="RAG citation chunk evidence does not belong",
    ):
        await service.reconstruct_packet("packet-all-reference-kinds")


@pytest.mark.asyncio
async def test_reconstruction_reports_stale_trace_context() -> None:
    bundle = _bundle()
    evaluation_run = _evaluation_run()
    metric_result = _metric_result(run_id=evaluation_run.run_id)
    trace = _trace_record(status="ok")
    stale_trace = _trace_record(status="error")
    packet = _packet_with_every_reconstruction_kind(
        bundle=bundle,
        evaluation_run=evaluation_run,
        metric_result=metric_result,
        trace=trace,
    )
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(bundle),
        evaluation_repository=FakeEvaluationProvenanceRepository(
            runs=(evaluation_run,),
            metric_results=(metric_result,),
        ),
        trace_repository=FakeTelemetryTraceSourceRepository(traces=(stale_trace,)),
    )
    await service.persist_packet(packet)

    with pytest.raises(
        StaleDecisionEvidenceSourceError,
        match="trace context evidence content digest is stale",
    ):
        await service.reconstruct_packet("packet-all-reference-kinds")


@pytest.mark.asyncio
async def test_reconstruction_reports_stale_linked_evaluation_artifact() -> None:
    bundle = _bundle()
    evaluation_run = _evaluation_run()
    metric_result = _metric_result(run_id=evaluation_run.run_id)
    artifact = _evaluation_artifact(run_id=evaluation_run.run_id)
    stale_artifact = _evaluation_artifact(
        run_id=evaluation_run.run_id,
        payload={"summary": "Substituted evaluation artifact content."},
    )
    packet = _packet_with_every_reconstruction_kind(
        bundle=bundle,
        evaluation_run=evaluation_run,
        metric_result=metric_result,
        artifact=artifact,
    )
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(bundle),
        evaluation_repository=FakeEvaluationProvenanceRepository(
            runs=(evaluation_run,),
            metric_results=(metric_result,),
            artifacts=(stale_artifact,),
        ),
    )
    await service.persist_packet(packet)

    with pytest.raises(
        StaleDecisionEvidenceSourceError,
        match="linked evaluation artifact evidence content digest is stale",
    ):
        await service.reconstruct_packet("packet-all-reference-kinds")


@pytest.mark.asyncio
async def test_reconstruction_reports_missing_rag_source_without_snapshot() -> None:
    bundle = _bundle()
    evaluation_run = _evaluation_run()
    metric_result = _metric_result(run_id=evaluation_run.run_id)
    rag_document = _rag_document()
    rag_chunk = _rag_chunk(document_id=rag_document.document_id)
    rag_context_payload = _rag_context_payload(
        rag_document=rag_document, rag_chunk=rag_chunk
    )
    packet = _packet_with_every_reconstruction_kind(
        bundle=bundle,
        evaluation_run=evaluation_run,
        metric_result=metric_result,
        rag_document=rag_document,
        rag_chunk=rag_chunk,
        rag_context_payload=rag_context_payload,
    )
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(bundle),
        evaluation_repository=FakeEvaluationProvenanceRepository(
            runs=(evaluation_run,),
            metric_results=(metric_result,),
        ),
        rag_repository=FakeRagEvidenceSourceRepository(),
        canonical_domain_record_repository=FakeCanonicalDomainRecordRepository(
            records=(_canonical_domain_source_record(),),
        ),
    )
    contextual_packet = replace(
        packet,
        claims=(
            replace(
                packet.claims[0],
                materiality=ClaimMaterialityTier.CONTEXTUAL,
            ),
        ),
    )
    await service.persist_packet(contextual_packet)
    repository.records["packet-all-reference-kinds"] = (
        _record_without_support_snapshots(
            repository.records["packet-all-reference-kinds"],
        )
    )

    with pytest.raises(
        MissingDecisionEvidenceSourceError,
        match="RAG query source record 'rag-query-1' was not found",
    ):
        await service.reconstruct_packet("packet-all-reference-kinds")


@pytest.mark.asyncio
async def test_reconstruction_falls_back_when_evaluation_record_is_missing() -> None:
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

    reconstructed = await service.reconstruct_packet("packet-1")

    assert reconstructed == packet


@pytest.mark.asyncio
async def test_reconstruction_falls_back_when_evaluation_metric_is_missing() -> None:
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

    reconstructed = await service.reconstruct_packet("packet-1")

    assert reconstructed == packet


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
async def test_reconstruction_falls_back_to_retained_material_snapshots() -> None:
    packet = await _packet(bundle=_bundle())
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(None),
    )
    await service.persist_packet(packet)

    reconstructed = await service.reconstruct_packet("packet-1")

    assert reconstructed == packet


@pytest.mark.asyncio
async def test_reconstruction_reports_missing_material_snapshot() -> None:
    packet = await _packet(bundle=_bundle())
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(None),
    )
    await service.persist_packet(packet)
    repository.records["packet-1"] = _record_without_support_snapshots(
        repository.records["packet-1"],
    )

    with pytest.raises(
        MissingDecisionEvidenceSnapshotError,
        match="lacks a retained support snapshot",
    ):
        await service.reconstruct_packet("packet-1")


@pytest.mark.asyncio
async def test_reconstruction_reports_tampered_material_snapshot() -> None:
    packet = await _packet(bundle=_bundle())
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(None),
    )
    await service.persist_packet(packet)
    repository.records["packet-1"] = _record_with_tampered_support_snapshot(
        repository.records["packet-1"],
    )

    with pytest.raises(
        TamperedDecisionEvidenceSnapshotError,
        match="tampered retained support snapshot",
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
        completed_run_archive=FakeCompletedRunArchive(
            _bundle(
                node_outputs=(
                    _node(outputs={"decision": {"selected_perspective": "bear"}}),
                ),
            ),
        ),
        telemetry=ApplicationServiceTelemetry(observability),
    )
    await service.persist_packet(packet)

    with pytest.raises(StaleDecisionEvidenceSourceError):
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
    assert event.payload["error_type"] == "StaleDecisionEvidenceSourceError"


@pytest.mark.asyncio
async def test_persistence_di_reconstruction_failure_emits_telemetry() -> None:
    provider = ApplicationPersistenceDIProvider()
    repository = InMemoryDecisionEvidencePacketRepository()
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)

    service = provider.provide_decision_evidence_packet_persistence_service(
        repository=cast(PostgresDecisionEvidencePacketRepository, repository),
        completed_run_archive=FakeCompletedRunArchive(None),
        rag_repository=cast(
            PostgresRagPersistenceRepository,
            FakeRagEvidenceSourceRepository(),
        ),
        evaluation_repository=cast(
            PostgresEvaluationPersistenceRepository,
            FakeEvaluationProvenanceRepository(),
        ),
        trace_repository=cast(
            PostgresTelemetryPersistenceRepository,
            FakeTelemetryTraceSourceRepository(),
        ),
        application_service_telemetry=ApplicationServiceTelemetry(observability),
    )

    with pytest.raises(DecisionEvidencePacketNotFoundError):
        await service.reconstruct_packet("missing-packet")

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
    assert event.attributes["packet_id"] == "missing-packet"
    assert event.payload["error_type"] == "DecisionEvidencePacketNotFoundError"


@pytest.mark.asyncio
async def test_reconstruction_failure_logs_when_telemetry_dependency_omitted(
    caplog: pytest.LogCaptureFixture,
) -> None:
    repository = InMemoryDecisionEvidencePacketRepository()
    service = DecisionEvidencePacketPersistenceService(
        repository=repository,
        completed_run_archive=FakeCompletedRunArchive(None),
    )

    with caplog.at_level("WARNING"):
        with pytest.raises(DecisionEvidencePacketNotFoundError):
            await service.reconstruct_packet("missing-packet")

    missing_telemetry_logs = [
        record
        for record in caplog.records
        if record.message
        == "Decision evidence packet reconstruction telemetry is not configured."
    ]
    assert len(missing_telemetry_logs) == 1
    assert missing_telemetry_logs[0].packet_id == "missing-packet"
    assert (
        missing_telemetry_logs[0].operation == "decision_evidence_packet_reconstruction"
    )
    assert missing_telemetry_logs[0].error_type == "DecisionEvidencePacketNotFoundError"


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
        completed_run_archive=FakeCompletedRunArchive(
            _bundle(
                node_outputs=(
                    _node(outputs={"decision": {"selected_perspective": "bear"}}),
                ),
            ),
        ),
        telemetry=ApplicationServiceTelemetry(observability),
    )
    await service.persist_packet(packet)

    with caplog.at_level("ERROR"):
        with pytest.raises(StaleDecisionEvidenceSourceError):
            await service.reconstruct_packet("packet-1")

    telemetry_failure_logs = [
        record
        for record in caplog.records
        if record.message == "Decision evidence packet telemetry emission failed."
    ]
    assert len(telemetry_failure_logs) == 1
    assert telemetry_failure_logs[0].exc_info is not None
    assert telemetry_failure_logs[0].error_type == "StaleDecisionEvidenceSourceError"
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


def _record_without_support_snapshots(
    record: DecisionEvidencePacketRecord,
) -> DecisionEvidencePacketRecord:
    return replace(
        record,
        evidence_references=tuple(
            {key: value for key, value in evidence.items() if key != "support_snapshot"}
            for evidence in record.evidence_references
        ),
    )


def _record_with_tampered_support_snapshot(
    record: DecisionEvidencePacketRecord,
) -> DecisionEvidencePacketRecord:
    evidence_references = []
    for evidence in record.evidence_references:
        updated = dict(evidence)
        raw_snapshot = updated["support_snapshot"]
        assert isinstance(raw_snapshot, Mapping)
        snapshot = dict(raw_snapshot)
        snapshot["redacted_content"] = "tampered material support content"
        updated["support_snapshot"] = snapshot
        evidence_references.append(updated)
    return replace(record, evidence_references=tuple(evidence_references))


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


class FakeCanonicalDomainRecordRepository:
    def __init__(
        self,
        *,
        records: tuple[CanonicalDomainSourceRecord, ...] = (),
        records_by_lookup: Mapping[str, CanonicalDomainSourceRecord] | None = None,
    ) -> None:
        self.records = {record.record_id: record for record in records}
        if records_by_lookup is not None:
            self.records.update(records_by_lookup)
        self.requested_record_ids: tuple[str, ...] = ()

    async def get_canonical_domain_record(
        self,
        record_id: str,
    ) -> CanonicalDomainSourceRecord | None:
        self.requested_record_ids = (*self.requested_record_ids, record_id)
        return self.records.get(record_id)


class FakeEvaluationProvenanceRepository:
    def __init__(
        self,
        *,
        runs: tuple[EvaluationRunRecord, ...] = (),
        metric_results: tuple[EvaluationMetricResultRecord, ...] = (),
        artifacts: tuple[EvaluationArtifactRecord, ...] = (),
    ) -> None:
        self.runs = {run.run_id: run for run in runs}
        self.metric_results_by_run: dict[
            str,
            tuple[EvaluationMetricResultRecord, ...],
        ] = {}
        self.artifacts_by_run: dict[str, tuple[EvaluationArtifactRecord, ...]] = {}
        for metric_result in metric_results:
            existing = self.metric_results_by_run.get(metric_result.run_id, ())
            self.metric_results_by_run[metric_result.run_id] = (
                *existing,
                metric_result,
            )
        for artifact in artifacts:
            existing_artifacts = self.artifacts_by_run.get(artifact.run_id, ())
            self.artifacts_by_run[artifact.run_id] = (
                *existing_artifacts,
                artifact,
            )

    async def get_run(self, run_id: str) -> EvaluationRunRecord | None:
        return self.runs.get(run_id)

    async def list_metric_results(
        self,
        run_id: str,
    ) -> tuple[EvaluationMetricResultRecord, ...]:
        return self.metric_results_by_run.get(run_id, ())

    async def list_artifacts(
        self,
        run_id: str,
    ) -> tuple[EvaluationArtifactRecord, ...]:
        return self.artifacts_by_run.get(run_id, ())


class FakeRagEvidenceSourceRepository:
    def __init__(
        self,
        *,
        documents: tuple[RagDocumentRecord, ...] = (),
        chunks: tuple[RagChunkRecord, ...] = (),
        query_logs: tuple[RagQueryLogRecord, ...] = (),
    ) -> None:
        self.documents = {document.document_id: document for document in documents}
        self.chunks = {chunk.chunk_id: chunk for chunk in chunks}
        self.query_logs = {query_log.query_id: query_log for query_log in query_logs}

    async def get_document(self, document_id: str) -> RagDocumentRecord | None:
        return self.documents.get(document_id)

    async def get_chunk(self, chunk_id: str) -> RagChunkRecord | None:
        return self.chunks.get(chunk_id)

    async def get_query_log(self, query_id: str) -> RagQueryLogRecord | None:
        return self.query_logs.get(query_id)


class FakeTelemetryTraceSourceRepository:
    def __init__(
        self,
        *,
        traces: tuple[TelemetryTraceRecord, ...] = (),
    ) -> None:
        self.traces = {trace.trace_record_id: trace for trace in traces}

    async def get_trace(self, trace_record_id: str) -> TelemetryTraceRecord | None:
        return self.traces.get(trace_record_id)


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


def _canonical_domain_record_reference(
    *,
    record_id: str = "strategy-decision-1",
    content_digest: str | None = "digest-canonical-record",
    snapshot_id: str | None = None,
) -> ReconstructionReference:
    return ReconstructionReference(
        reference_id="canonical-record",
        kind=ReconstructionReferenceKind.CANONICAL_DOMAIN_RECORD,
        record_id=record_id,
        source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
        snapshot_id=snapshot_id,
        content_digest=content_digest,
    )


def _canonical_domain_source_record(
    *,
    record_id: str = "strategy-decision-1",
    content_digest: str | None = "digest-canonical-record",
    snapshot_id: str | None = None,
    version: str | None = None,
    source_of_truth: SourceOfTruthCategory = (
        SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD
    ),
    snapshot_payload: Mapping[str, object] | None = None,
) -> CanonicalDomainSourceRecord:
    return CanonicalDomainSourceRecord(
        record_id=record_id,
        source_of_truth=source_of_truth,
        content_digest=content_digest,
        snapshot_id=snapshot_id,
        version=version,
        snapshot_payload=snapshot_payload,
    )


def _canonical_domain_packet(
    *,
    reference: ReconstructionReference | None = None,
    materiality: ClaimMaterialityTier = ClaimMaterialityTier.READINESS_GATING,
    support_snapshot: SupportingEvidenceSnapshot | None = None,
) -> DecisionEvidencePacket:
    reconstruction_reference = reference or _canonical_domain_record_reference()
    if (
        support_snapshot is None
        and materiality is ClaimMaterialityTier.READINESS_GATING
    ):
        support_snapshot = SupportingEvidenceSnapshot(
            snapshot_id="canonical-record:support-snapshot",
            summary="Retained canonical record support snapshot.",
            redacted_content='{"record_id":"strategy-decision-1"}',
            source_label="canonical_record:strategy-decision-1",
        )
    return DecisionEvidencePacket(
        packet_id="packet-canonical-record",
        output_id="strategy-decision-1",
        authority=classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED)),
        claims=(
            MaterialClaim(
                claim_id="claim-canonical-record",
                text="The canonical strategy decision is reconstructable.",
                evidence=ClaimEvidenceBinding(
                    supporting_evidence_ids=("evidence-canonical-record",),
                ),
                materiality=materiality,
            ),
        ),
        evidence=(
            EvidenceReference(
                evidence_id="evidence-canonical-record",
                kind=EvidenceReferenceKind.CANONICAL_RECORD,
                reconstruction_reference_ids=(reconstruction_reference.reference_id,),
                summary="Canonical strategy decision record evidence.",
                source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
                support_snapshot=support_snapshot,
            ),
        ),
        reconstruction_references=(reconstruction_reference,),
        retention=EvidenceRetentionRequirement(
            retain_until="2031-07-25T00:00:00Z",
            policy_id="enhanced-provenance-5y",
        ),
    )


def _packet_with_every_reconstruction_kind(
    *,
    bundle: CompletedRunBundle,
    evaluation_run: EvaluationRunRecord,
    metric_result: EvaluationMetricResultRecord,
    rag_document: RagDocumentRecord | None = None,
    rag_chunk: RagChunkRecord | None = None,
    rag_context_payload: Mapping[str, object] | None = None,
    trace: TelemetryTraceRecord | None = None,
    artifact: EvaluationArtifactRecord | None = None,
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
    rag_retrieval_digest = (
        "digest-rag-context"
        if rag_context_payload is None
        else calculate_rag_retrieval_context_evidence_digest(
            context_payload=rag_context_payload,
        )
    )
    rag_citation_record_id = "rag-document-1:chunk-1"
    rag_citation_digest = "digest-rag-citation"
    if rag_document is not None:
        rag_citation_record_id = ":".join(
            (
                rag_document.source_table,
                rag_document.source_id,
                rag_document.document_id,
                "document" if rag_chunk is None else rag_chunk.chunk_id,
            )
        )
        rag_citation_digest = calculate_rag_citation_source_evidence_digest(
            document=rag_document,
            chunk=rag_chunk,
        )
    trace_digest = (
        "digest-trace-context"
        if trace is None
        else calculate_trace_context_evidence_digest(trace=trace)
    )
    linked_artifact_record_id = "model:gpt-4.1-2026-07-25"
    linked_artifact_digest: str | None = None
    if artifact is not None:
        linked_artifact_record_id = (
            f"evaluation-artifact:{artifact.run_id}:{artifact.artifact_id}"
        )
        linked_artifact_digest = calculate_evaluation_artifact_evidence_digest(
            artifact=artifact,
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
            content_digest=rag_retrieval_digest,
        ),
        ReconstructionReference(
            reference_id="rag-citation",
            kind=ReconstructionReferenceKind.RAG_CITATION_CONTEXT,
            record_id=rag_citation_record_id,
            source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
            snapshot_id="citation-1",
            content_digest=rag_citation_digest,
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
            content_digest=trace_digest,
        ),
        ReconstructionReference(
            reference_id="linked-artifact",
            kind=ReconstructionReferenceKind.LINKED_ARTIFACT,
            record_id=linked_artifact_record_id,
            source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
            content_digest=linked_artifact_digest,
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
                support_snapshot=SupportingEvidenceSnapshot(
                    snapshot_id="evidence-all:support-snapshot",
                    summary="Evidence exercising every canonical reconstruction kind.",
                    redacted_content=(
                        "Retained redacted snapshot covering all reconstruction kinds."
                    ),
                    source_label="canonical_record:strategy-decision-1",
                ),
            ),
        ),
        reconstruction_references=reconstruction_references,
        retention=EvidenceRetentionRequirement(
            retain_until="2031-07-25T00:00:00Z",
            policy_id="enhanced-provenance-5y",
        ),
    )


def _rag_document(
    *,
    document_id: str = "rag-document-1",
    source_id: str = "strategy-decision-1",
    generated_at: datetime = datetime(2026, 7, 25, 13, 8, tzinfo=UTC),
) -> RagDocumentRecord:
    return RagDocumentRecord(
        document_id=document_id,
        source_table="strategy_decisions",
        source_id=source_id,
        source_type="strategy_decision",
        title="Strategy decision evidence",
        content_text="Canonical strategy decision source text.",
        generated_at=generated_at,
    )


def _rag_chunk(
    *,
    document_id: str,
    chunk_id: str = "chunk-1",
) -> RagChunkRecord:
    return RagChunkRecord(
        chunk_id=chunk_id,
        document_id=document_id,
        chunk_index=0,
        chunk_text="Retained redacted snapshot covering all reconstruction kinds.",
        metadata={"section_name": "summary"},
    )


def _rag_context_payload(
    *,
    rag_document: RagDocumentRecord,
    rag_chunk: RagChunkRecord,
) -> dict[str, object]:
    return {
        "context_id": "rag-context-1",
        "retrieval_route": "hybrid",
        "text": rag_chunk.chunk_text,
        "source": {
            "source_table": rag_document.source_table,
            "source_id": rag_document.source_id,
            "source_type": rag_document.source_type,
            "document_id": rag_document.document_id,
            "chunk_id": rag_chunk.chunk_id,
            "section_name": "summary",
            "generated_at": rag_document.generated_at.isoformat(),
        },
    }


def _rag_query_log(
    *,
    context_payload: Mapping[str, object],
) -> RagQueryLogRecord:
    return RagQueryLogRecord(
        query_id="rag-query-1",
        query_text="What evidence supports the strategy decision?",
        retrieval_route="hybrid",
        top_k=5,
        status="succeeded",
        started_at=datetime(2026, 7, 25, 13, 9, tzinfo=UTC),
        context_count=1,
        citation_count=1,
        metadata=cast(JsonObject, {"retrieved_contexts": (context_payload,)}),
    )


def _trace_record(
    *,
    trace_record_id: str = "trace-1:span-1",
    trace_id: str = "trace-1",
    span_id: str = "span-1",
    status: str = "ok",
) -> TelemetryTraceRecord:
    return TelemetryTraceRecord(
        trace_record_id=trace_record_id,
        trace_id=trace_id,
        span_id=span_id,
        operation_name="decision_evidence.reconstruct",
        source="application.decision_evidence",
        started_at=datetime(2026, 7, 25, 13, 10, tzinfo=UTC),
        ended_at=datetime(2026, 7, 25, 13, 10, 1, tzinfo=UTC),
        duration_seconds=1.0,
        status=status,
        correlation_id="correlation-1",
    )


def _evaluation_artifact(
    *,
    run_id: str,
    artifact_id: str = "artifact-1",
    payload: JsonObject | None = None,
) -> EvaluationArtifactRecord:
    return EvaluationArtifactRecord(
        artifact_id=artifact_id,
        run_id=run_id,
        artifact_type="rubric-summary",
        payload=payload or {"summary": "Evaluation artifact summary."},
        created_at=datetime(2026, 7, 25, 13, 11, tzinfo=UTC),
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
