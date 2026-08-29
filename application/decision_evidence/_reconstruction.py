from __future__ import annotations

import logging
from dataclasses import dataclass

from application.decision_evidence._reconstruction_contracts import (
    CanonicalDomainRecordRepository,
    DecisionEvidencePacketReconstructionError,
    EvaluationProvenanceRepository,
    MalformedDecisionEvidenceReconstructionIdentifierError,
    MissingDecisionEvidenceSnapshotError,
    MissingDecisionEvidenceSourceError,
    RagEvidenceSourceRepository,
    TelemetryTraceSourceRepository,
    UnsupportedDecisionEvidenceReferenceError,
)
from application.decision_evidence._reconstruction_domain import (
    validate_canonical_domain_record,
)
from application.decision_evidence._reconstruction_evaluation import (
    validate_evaluation_metric_result,
    validate_evaluation_run,
    validate_linked_artifact,
)
from application.decision_evidence._reconstruction_rag import (
    validate_rag_citation_context,
    validate_rag_retrieval_context,
)
from application.decision_evidence._reconstruction_trace import validate_trace_context
from application.decision_evidence._reconstruction_workflow import (
    validate_completed_workflow_run,
    validate_workflow_node_output,
)
from core.storage.persistence.completed_run_archive import (
    CompletedRunArchive,
    CompletedRunBundle,
)
from domain.authority import SourceOfTruthCategory
from domain.decision_evidence import (
    DecisionEvidencePacket,
    ReconstructionReference,
    ReconstructionReferenceKind,
    SupportingEvidenceSnapshot,
    UnsupportedMaterialClaimError,
    material_support_snapshots_by_reconstruction_id,
)

logger = logging.getLogger("application.decision_evidence.persistence")


@dataclass(frozen=True, slots=True)
class ReconstructionSourceValidator:
    completed_run_archive: CompletedRunArchive
    evaluation_repository: EvaluationProvenanceRepository | None = None
    rag_repository: RagEvidenceSourceRepository | None = None
    trace_repository: TelemetryTraceSourceRepository | None = None
    canonical_domain_record_repository: CanonicalDomainRecordRepository | None = None

    async def validate(self, packet: DecisionEvidencePacket) -> None:
        bundle_cache: dict[tuple[str, str], CompletedRunBundle] = {}
        material_snapshots = _material_support_snapshots(packet)
        for reference in packet.reconstruction_references:
            _validate_source_of_truth(reference)
            try:
                await self._validate_canonical_source_record(reference, bundle_cache)
            except (
                MissingDecisionEvidenceSourceError,
                UnsupportedDecisionEvidenceReferenceError,
            ) as exc:
                snapshot = material_snapshots.get(reference.reference_id)
                if snapshot is None:
                    _log_reference_validation_failure(
                        packet=packet,
                        reference=reference,
                        error=exc,
                    )
                    raise
                _validate_retained_material_support_snapshot(
                    snapshot=snapshot,
                    reference=reference,
                )
            except DecisionEvidencePacketReconstructionError as exc:
                _log_reference_validation_failure(
                    packet=packet,
                    reference=reference,
                    error=exc,
                )
                raise

    async def _validate_canonical_source_record(
        self,
        reference: ReconstructionReference,
        bundle_cache: dict[tuple[str, str], CompletedRunBundle],
    ) -> None:
        if reference.kind is ReconstructionReferenceKind.COMPLETED_WORKFLOW_RUN:
            await validate_completed_workflow_run(
                archive=self.completed_run_archive,
                reference=reference,
                bundle_cache=bundle_cache,
            )
        elif reference.kind is ReconstructionReferenceKind.WORKFLOW_NODE_OUTPUT:
            await validate_workflow_node_output(
                archive=self.completed_run_archive,
                reference=reference,
                bundle_cache=bundle_cache,
            )
        elif reference.kind is ReconstructionReferenceKind.EVALUATION_RUN:
            await validate_evaluation_run(
                repository=self.evaluation_repository,
                reference=reference,
            )
        elif reference.kind is ReconstructionReferenceKind.EVALUATION_METRIC_RESULT:
            await validate_evaluation_metric_result(
                repository=self.evaluation_repository,
                reference=reference,
            )
        elif reference.kind is ReconstructionReferenceKind.CANONICAL_DOMAIN_RECORD:
            await validate_canonical_domain_record(
                repository=self.canonical_domain_record_repository,
                reference=reference,
            )
        elif reference.kind is ReconstructionReferenceKind.RAG_RETRIEVAL_CONTEXT:
            await validate_rag_retrieval_context(
                repository=self.rag_repository,
                reference=reference,
            )
        elif reference.kind is ReconstructionReferenceKind.RAG_CITATION_CONTEXT:
            await validate_rag_citation_context(
                repository=self.rag_repository,
                reference=reference,
            )
        elif reference.kind is ReconstructionReferenceKind.TRACE_CONTEXT:
            await validate_trace_context(
                repository=self.trace_repository,
                reference=reference,
            )
        elif reference.kind is ReconstructionReferenceKind.LINKED_ARTIFACT:
            await validate_linked_artifact(
                repository=self.evaluation_repository,
                reference=reference,
            )
        else:
            raise UnsupportedDecisionEvidenceReferenceError(
                f"unsupported reconstruction reference kind '{reference.kind.value}'."
            )


def _log_reference_validation_failure(
    *,
    packet: DecisionEvidencePacket,
    reference: ReconstructionReference,
    error: DecisionEvidencePacketReconstructionError,
) -> None:
    logger.warning(
        "Decision evidence reconstruction reference validation failed.",
        extra={
            "packet_id": packet.packet_id,
            "reference_id": reference.reference_id,
            "reference_kind": reference.kind.value,
            "record_id": reference.record_id,
            "source_of_truth": (
                None
                if reference.source_of_truth is None
                else reference.source_of_truth.value
            ),
            "failure_mode": type(error).__name__,
        },
        exc_info=True,
    )


def _material_support_snapshots(
    packet: DecisionEvidencePacket,
) -> dict[str, SupportingEvidenceSnapshot]:
    try:
        return material_support_snapshots_by_reconstruction_id(packet)
    except UnsupportedMaterialClaimError as exc:
        raise MissingDecisionEvidenceSnapshotError(str(exc)) from exc


def _validate_retained_material_support_snapshot(
    *,
    snapshot: SupportingEvidenceSnapshot,
    reference: ReconstructionReference,
) -> None:
    if snapshot.content_digest is None:
        raise MissingDecisionEvidenceSnapshotError(
            "material support snapshot "
            f"'{snapshot.snapshot_id}' for reference '{reference.reference_id}' "
            "does not include a content digest."
        )


def _validate_source_of_truth(reference: ReconstructionReference) -> None:
    if reference.kind in {
        ReconstructionReferenceKind.COMPLETED_WORKFLOW_RUN,
        ReconstructionReferenceKind.WORKFLOW_NODE_OUTPUT,
    }:
        if reference.source_of_truth is not SourceOfTruthCategory.RUNTIME_EVIDENCE:
            raise MalformedDecisionEvidenceReconstructionIdentifierError(
                "workflow reconstruction references must identify runtime "
                "evidence as their source of truth."
            )
        return

    if reference.kind in {
        ReconstructionReferenceKind.EVALUATION_RUN,
        ReconstructionReferenceKind.EVALUATION_METRIC_RESULT,
    }:
        if (
            reference.source_of_truth
            is not SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD
        ):
            raise MalformedDecisionEvidenceReconstructionIdentifierError(
                "evaluation reconstruction references must identify canonical "
                "domain records as their source of truth."
            )
        return

    if reference.source_of_truth in {
        SourceOfTruthCategory.DERIVED_PROJECTION,
        SourceOfTruthCategory.PRESENTATION_OUTPUT,
        SourceOfTruthCategory.EXTERNAL_TRANSPORT_PAYLOAD,
    }:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            "derived projections, presentation outputs, and external transport "
            "payloads cannot be authoritative reconstruction sources."
        )
