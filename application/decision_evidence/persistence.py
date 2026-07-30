from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import NoReturn, Protocol

from application.decision_evidence.completed_workflow_assembly import (
    calculate_completed_workflow_node_evidence_digest,
)
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunArchive,
    CompletedRunBundle,
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
from core.storage.persistence.serializers import (
    DecisionEvidencePacketPersistenceSerializer,
)
from core.storage.persistence.telemetry import TelemetryTraceRecord
from core.telemetry.emitters.application_service_telemetry import (
    ApplicationServiceTelemetry,
)
from domain.authority import SourceOfTruthCategory
from domain.decision_evidence import (
    DecisionEvidencePacket,
    DecisionEvidencePacketValidationError,
    ReconstructionReference,
    ReconstructionReferenceKind,
    SupportingEvidenceSnapshot,
    UnsupportedMaterialClaimError,
    material_support_snapshots_by_reconstruction_id,
)

logger = logging.getLogger(__name__)


class DecisionEvidencePacketReconstructionError(ValueError):
    """Raised when a persisted packet cannot be safely reconstructed."""


class DecisionEvidencePacketNotFoundError(DecisionEvidencePacketReconstructionError):
    """Raised when no persisted packet audit record exists for an id."""


class MissingDecisionEvidenceSourceError(DecisionEvidencePacketReconstructionError):
    """Raised when a canonical source record referenced by a packet is absent."""


class MissingDecisionEvidenceSnapshotError(DecisionEvidencePacketReconstructionError):
    """Raised when retained material support snapshots are unavailable."""


class TamperedDecisionEvidenceSnapshotError(DecisionEvidencePacketReconstructionError):
    """Raised when retained material support snapshot content is tampered with."""


class StaleDecisionEvidenceSourceError(DecisionEvidencePacketReconstructionError):
    """Raised when a canonical source record no longer matches packet snapshots."""


class SubstitutedDecisionEvidenceSourceError(DecisionEvidencePacketReconstructionError):
    """Raised when a source record belongs to a different evidence context."""


class MalformedDecisionEvidenceReconstructionIdentifierError(
    DecisionEvidencePacketReconstructionError,
):
    """Raised when persisted reconstruction identifiers are malformed."""


class UnsupportedDecisionEvidenceReferenceError(
    DecisionEvidencePacketReconstructionError
):
    """Raised when no canonical validator exists for a reconstruction reference."""


class EvaluationProvenanceRepository(Protocol):
    """Read model needed to verify canonical evaluation provenance sources."""

    async def get_run(self, run_id: str) -> EvaluationRunRecord | None:
        """Load a canonical evaluation run record by id."""

    async def list_metric_results(
        self,
        run_id: str,
    ) -> Sequence[EvaluationMetricResultRecord]:
        """Load canonical metric results attached to an evaluation run."""

    async def list_artifacts(
        self,
        run_id: str,
    ) -> Sequence[EvaluationArtifactRecord]:
        """Load canonical artifacts attached to an evaluation run."""


class RagEvidenceSourceRepository(Protocol):
    """Read model needed to verify canonical RAG retrieval and citation sources."""

    async def get_document(self, document_id: str) -> RagDocumentRecord | None:
        """Load a canonical RAG source document by id."""

    async def get_chunk(self, chunk_id: str) -> RagChunkRecord | None:
        """Load a canonical RAG source chunk by id."""

    async def get_query_log(self, query_id: str) -> RagQueryLogRecord | None:
        """Load a canonical RAG query log by id."""


class TelemetryTraceSourceRepository(Protocol):
    """Read model needed to verify durable trace/correlation references."""

    async def get_trace(self, trace_record_id: str) -> TelemetryTraceRecord | None:
        """Load a durable trace/span record by id."""


@dataclass(frozen=True, slots=True)
class DecisionEvidencePacketPersistenceService:
    """Persist packet references and reconstruct packets from canonical sources."""

    repository: DecisionEvidencePacketPersistenceRepository = field(repr=False)
    completed_run_archive: CompletedRunArchive = field(repr=False)
    evaluation_repository: EvaluationProvenanceRepository | None = field(
        default=None,
        repr=False,
    )
    rag_repository: RagEvidenceSourceRepository | None = field(
        default=None,
        repr=False,
    )
    trace_repository: TelemetryTraceSourceRepository | None = field(
        default=None,
        repr=False,
    )
    telemetry: ApplicationServiceTelemetry | None = field(default=None, repr=False)

    async def persist_packet(
        self,
        packet: DecisionEvidencePacket,
    ) -> DecisionEvidencePacketPersistenceResult:
        """Persist the packet audit record and durable reconstruction identifiers."""

        record = DecisionEvidencePacketPersistenceSerializer.record_from_packet(packet)
        result = await self.repository.persist_packet_record(record)
        if not result.success:
            logger.warning(
                "Decision evidence packet persistence failed.",
                extra={
                    "packet_id": packet.packet_id,
                    "error_count": len(result.errors),
                },
            )
        return result

    async def reconstruct_packet(self, packet_id: str) -> DecisionEvidencePacket:
        """Load a packet record and verify its durable canonical evidence sources."""

        record = await self.repository.get_packet_record(packet_id)
        if record is None:
            error = DecisionEvidencePacketNotFoundError(
                f"decision evidence packet {packet_id!r} was not found."
            )
            logger.warning(
                "Decision evidence packet reconstruction failed.",
                extra={"packet_id": packet_id, "error_type": type(error).__name__},
            )
            await self._emit_reconstruction_failed(
                packet_id=packet_id,
                error=error,
                record=None,
            )
            raise error

        try:
            packet = DecisionEvidencePacketPersistenceSerializer.packet_from_record(
                record
            )
            await self._validate_reconstruction_sources(packet)
        except DecisionEvidencePacketReconstructionError as exc:
            logger.warning(
                "Decision evidence packet reconstruction failed closed.",
                extra={"packet_id": packet_id, "error_type": type(exc).__name__},
                exc_info=True,
            )
            await self._emit_reconstruction_failed(
                packet_id=packet_id,
                error=exc,
                record=record,
            )
            raise
        except (DecisionEvidencePacketValidationError, ValueError) as exc:
            if _is_tampered_snapshot_error(exc):
                reconstruction_error: DecisionEvidencePacketReconstructionError = (
                    TamperedDecisionEvidenceSnapshotError(
                        f"decision evidence packet {packet_id!r} contains a "
                        f"tampered retained support snapshot: {exc}"
                    )
                )
            else:
                reconstruction_error = (
                    MalformedDecisionEvidenceReconstructionIdentifierError(
                        f"decision evidence packet {packet_id!r} contains malformed "
                        f"reconstruction identifiers: {exc}"
                    )
                )
            logger.warning(
                "Decision evidence packet reconstruction identifier was malformed.",
                extra={
                    "packet_id": packet_id,
                    "error_type": type(exc).__name__,
                },
                exc_info=True,
            )
            await self._emit_reconstruction_failed(
                packet_id=packet_id,
                error=reconstruction_error,
                record=record,
            )
            raise reconstruction_error from exc

        return packet

    async def _emit_reconstruction_failed(
        self,
        *,
        packet_id: str,
        error: BaseException,
        record: DecisionEvidencePacketRecord | None,
    ) -> None:
        telemetry = self.telemetry
        if telemetry is None:
            logger.warning(
                "Decision evidence packet reconstruction telemetry is not configured.",
                extra={
                    "packet_id": packet_id,
                    "operation": "decision_evidence_packet_reconstruction",
                    "error_type": type(error).__name__,
                },
            )
            return
        try:
            await telemetry.emit_service_failed(
                "DecisionEvidencePacketPersistenceService",
                "DecisionEvidencePacketReconstruction",
                error=error,
                attributes=_reconstruction_telemetry_attributes(
                    packet_id=packet_id,
                    record=record,
                ),
            )
        except (RuntimeError, OSError) as telemetry_error:
            logger.error(
                "Decision evidence packet telemetry emission failed.",
                extra={
                    "packet_id": packet_id,
                    "operation": "decision_evidence_packet_reconstruction",
                    "error_type": type(error).__name__,
                    "telemetry_error_type": type(telemetry_error).__name__,
                },
                exc_info=True,
            )

    async def _validate_reconstruction_sources(
        self,
        packet: DecisionEvidencePacket,
    ) -> None:
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
                    logger.warning(
                        "Decision evidence reconstruction reference validation failed.",
                        extra={
                            "packet_id": packet.packet_id,
                            "reference_id": reference.reference_id,
                            "reference_kind": reference.kind.value,
                            "record_id": reference.record_id,
                            "source_of_truth": None
                            if reference.source_of_truth is None
                            else reference.source_of_truth.value,
                            "failure_mode": type(exc).__name__,
                        },
                        exc_info=True,
                    )
                    raise
                _validate_retained_material_support_snapshot(
                    snapshot=snapshot,
                    reference=reference,
                )
            except DecisionEvidencePacketReconstructionError as exc:
                logger.warning(
                    "Decision evidence reconstruction reference validation failed.",
                    extra={
                        "packet_id": packet.packet_id,
                        "reference_id": reference.reference_id,
                        "reference_kind": reference.kind.value,
                        "record_id": reference.record_id,
                        "source_of_truth": None
                        if reference.source_of_truth is None
                        else reference.source_of_truth.value,
                        "failure_mode": type(exc).__name__,
                    },
                    exc_info=True,
                )
                raise

    async def _validate_canonical_source_record(
        self,
        reference: ReconstructionReference,
        bundle_cache: dict[tuple[str, str], CompletedRunBundle],
    ) -> None:
        if reference.kind is ReconstructionReferenceKind.COMPLETED_WORKFLOW_RUN:
            await self._validate_completed_workflow_run(reference, bundle_cache)
        elif reference.kind is ReconstructionReferenceKind.WORKFLOW_NODE_OUTPUT:
            await self._validate_workflow_node_output(reference, bundle_cache)
        elif reference.kind is ReconstructionReferenceKind.EVALUATION_RUN:
            await self._validate_evaluation_run(reference)
        elif reference.kind is ReconstructionReferenceKind.EVALUATION_METRIC_RESULT:
            await self._validate_evaluation_metric_result(reference)
        elif reference.kind is ReconstructionReferenceKind.CANONICAL_DOMAIN_RECORD:
            _validate_canonical_domain_record_reference(reference)
        elif reference.kind is ReconstructionReferenceKind.RAG_RETRIEVAL_CONTEXT:
            await self._validate_rag_retrieval_context(reference)
        elif reference.kind is ReconstructionReferenceKind.RAG_CITATION_CONTEXT:
            await self._validate_rag_citation_context(reference)
        elif reference.kind is ReconstructionReferenceKind.TRACE_CONTEXT:
            await self._validate_trace_context(reference)
        elif reference.kind is ReconstructionReferenceKind.LINKED_ARTIFACT:
            await self._validate_linked_artifact(reference)
        else:
            raise UnsupportedDecisionEvidenceReferenceError(
                f"unsupported reconstruction reference kind '{reference.kind.value}'."
            )

    async def _validate_completed_workflow_run(
        self,
        reference: ReconstructionReference,
        bundle_cache: dict[tuple[str, str], CompletedRunBundle],
    ) -> None:
        workflow_name, execution_id = _parse_completed_workflow_run_record_id(reference)
        bundle = await self._load_completed_run_bundle(
            workflow_name,
            execution_id,
            bundle_cache,
        )
        if reference.snapshot_id is None:
            raise MalformedDecisionEvidenceReconstructionIdentifierError(
                "completed workflow run reconstruction reference must include a "
                "snapshot_id."
            )
        if bundle.run.run_id != reference.snapshot_id:
            raise StaleDecisionEvidenceSourceError(
                "completed workflow run evidence is stale for "
                f"'{workflow_name}:{execution_id}'."
            )

    async def _validate_workflow_node_output(
        self,
        reference: ReconstructionReference,
        bundle_cache: dict[tuple[str, str], CompletedRunBundle],
    ) -> None:
        workflow_name, execution_id, node_name = _parse_workflow_node_snapshot_id(
            reference,
        )
        bundle = await self._load_completed_run_bundle(
            workflow_name,
            execution_id,
            bundle_cache,
        )
        node_output = _resolve_node_output(reference, bundle)
        if (
            node_output.run_id != bundle.run.run_id
            or node_output.workflow_name != workflow_name
            or node_output.execution_id != execution_id
            or node_output.node_name != node_name
        ):
            raise SubstitutedDecisionEvidenceSourceError(
                "workflow node output evidence does not belong to completed run "
                f"'{bundle.run.run_id}'."
            )
        if reference.content_digest is None:
            raise MalformedDecisionEvidenceReconstructionIdentifierError(
                "workflow node output reconstruction reference must include a "
                "content digest."
            )
        content_digest = calculate_completed_workflow_node_evidence_digest(
            run=bundle.run,
            node_output=node_output,
        )
        if content_digest != reference.content_digest:
            raise StaleDecisionEvidenceSourceError(
                "workflow node output evidence content digest is stale for "
                f"'{reference.record_id}'."
            )

    async def _validate_evaluation_run(
        self,
        reference: ReconstructionReference,
    ) -> None:
        repository = self.evaluation_repository
        if repository is None:
            raise MissingDecisionEvidenceSourceError(
                "evaluation provenance repository is required to reconstruct "
                f"evaluation run source record '{reference.record_id}'."
            )

        run = await repository.get_run(reference.record_id)
        if run is None:
            raise MissingDecisionEvidenceSourceError(
                f"evaluation run source record '{reference.record_id}' was not found."
            )
        if run.run_id != reference.record_id:
            raise SubstitutedDecisionEvidenceSourceError(
                "evaluation run evidence does not match reconstruction identifier "
                f"'{reference.record_id}'."
            )
        if reference.content_digest is None:
            raise MalformedDecisionEvidenceReconstructionIdentifierError(
                "evaluation run reconstruction reference must include a content digest."
            )

        content_digest = calculate_evaluation_run_evidence_digest(run=run)
        if content_digest != reference.content_digest:
            raise StaleDecisionEvidenceSourceError(
                "evaluation run evidence content digest is stale for "
                f"'{reference.record_id}'."
            )

    async def _validate_evaluation_metric_result(
        self,
        reference: ReconstructionReference,
    ) -> None:
        repository = self.evaluation_repository
        if repository is None:
            raise MissingDecisionEvidenceSourceError(
                "evaluation provenance repository is required to reconstruct "
                f"evaluation metric result source record '{reference.record_id}'."
            )
        if reference.snapshot_id is None:
            raise MalformedDecisionEvidenceReconstructionIdentifierError(
                "evaluation metric result reconstruction reference must include "
                "an evaluation run snapshot_id."
            )

        metric_result = await _load_metric_result(
            repository=repository,
            run_id=reference.snapshot_id,
            metric_result_id=reference.record_id,
        )
        if metric_result.run_id != reference.snapshot_id:
            raise SubstitutedDecisionEvidenceSourceError(
                "evaluation metric result evidence does not belong to evaluation "
                f"run '{reference.snapshot_id}'."
            )
        if reference.content_digest is None:
            raise MalformedDecisionEvidenceReconstructionIdentifierError(
                "evaluation metric result reconstruction reference must include "
                "a content digest."
            )

        content_digest = calculate_evaluation_metric_result_evidence_digest(
            metric_result=metric_result,
        )
        if content_digest != reference.content_digest:
            raise StaleDecisionEvidenceSourceError(
                "evaluation metric result evidence content digest is stale for "
                f"'{reference.record_id}'."
            )

    async def _validate_rag_retrieval_context(
        self,
        reference: ReconstructionReference,
    ) -> None:
        _validate_rag_retrieval_context_reference(reference)
        repository = self.rag_repository
        if repository is None:
            raise MissingDecisionEvidenceSourceError(
                "RAG repository is required to reconstruct retrieval context "
                f"source record '{reference.record_id}'."
            )

        query_log = await repository.get_query_log(reference.snapshot_id or "")
        if query_log is None:
            raise MissingDecisionEvidenceSourceError(
                f"RAG query source record '{reference.snapshot_id}' was not found."
            )
        if query_log.query_id != reference.snapshot_id:
            raise SubstitutedDecisionEvidenceSourceError(
                "RAG retrieval context evidence does not belong to query "
                f"'{reference.snapshot_id}'."
            )

        context_payload = _find_rag_context_payload(
            query_log.metadata,
            context_id=reference.record_id,
        )
        if context_payload is None:
            raise MissingDecisionEvidenceSourceError(
                "RAG retrieval context source record "
                f"'{reference.record_id}' was not retained with query "
                f"'{query_log.query_id}'."
            )

        content_digest = calculate_rag_retrieval_context_evidence_digest(
            context_payload=context_payload,
        )
        if content_digest != reference.content_digest:
            raise StaleDecisionEvidenceSourceError(
                "RAG retrieval context evidence content digest is stale for "
                f"'{reference.record_id}'."
            )

    async def _validate_rag_citation_context(
        self,
        reference: ReconstructionReference,
    ) -> None:
        _validate_rag_citation_context_reference(reference)
        repository = self.rag_repository
        if repository is None:
            raise MissingDecisionEvidenceSourceError(
                "RAG repository is required to reconstruct citation context "
                f"source record '{reference.record_id}'."
            )

        source_identity = _parse_rag_source_record_id(reference.record_id)
        document = await repository.get_document(source_identity.document_id)
        if document is None:
            raise MissingDecisionEvidenceSourceError(
                f"RAG document source record '{source_identity.document_id}' was not "
                "found."
            )
        _validate_rag_document_identity(
            document=document,
            source_identity=source_identity,
            reference=reference,
        )

        chunk: RagChunkRecord | None = None
        if source_identity.chunk_id is not None:
            chunk = await repository.get_chunk(source_identity.chunk_id)
            if chunk is None:
                raise MissingDecisionEvidenceSourceError(
                    f"RAG chunk source record '{source_identity.chunk_id}' was not "
                    "found."
                )
            if chunk.document_id != document.document_id:
                raise SubstitutedDecisionEvidenceSourceError(
                    "RAG citation chunk evidence does not belong to document "
                    f"'{document.document_id}'."
                )

        content_digest = calculate_rag_citation_source_evidence_digest(
            document=document,
            chunk=chunk,
        )
        if content_digest != reference.content_digest:
            raise StaleDecisionEvidenceSourceError(
                "RAG citation context evidence content digest is stale for "
                f"'{reference.record_id}'."
            )

    async def _validate_trace_context(
        self,
        reference: ReconstructionReference,
    ) -> None:
        _validate_trace_context_reference(reference)
        repository = self.trace_repository
        if repository is None:
            raise UnsupportedDecisionEvidenceReferenceError(
                "trace context reconstruction requires a telemetry trace repository "
                f"or a retained snapshot for '{reference.record_id}'."
            )

        trace = await repository.get_trace(reference.record_id)
        if trace is None:
            raise MissingDecisionEvidenceSourceError(
                f"trace context source record '{reference.record_id}' was not found."
            )
        if trace.trace_record_id != reference.record_id:
            raise SubstitutedDecisionEvidenceSourceError(
                "trace context evidence does not match reconstruction identifier "
                f"'{reference.record_id}'."
            )
        if trace.trace_id != reference.snapshot_id:
            raise SubstitutedDecisionEvidenceSourceError(
                "trace context evidence does not belong to trace "
                f"'{reference.snapshot_id}'."
            )

        content_digest = calculate_trace_context_evidence_digest(trace=trace)
        if content_digest != reference.content_digest:
            raise StaleDecisionEvidenceSourceError(
                "trace context evidence content digest is stale for "
                f"'{reference.record_id}'."
            )

    async def _validate_linked_artifact(
        self,
        reference: ReconstructionReference,
    ) -> None:
        _validate_linked_artifact_reference(reference)
        evaluation_artifact = _parse_evaluation_artifact_record_id(reference.record_id)
        if evaluation_artifact is None:
            return

        repository = self.evaluation_repository
        if repository is None:
            raise MissingDecisionEvidenceSourceError(
                "evaluation provenance repository is required to reconstruct "
                f"linked artifact source record '{reference.record_id}'."
            )
        artifact = await _load_evaluation_artifact(
            repository=repository,
            run_id=evaluation_artifact.run_id,
            artifact_id=evaluation_artifact.artifact_id,
        )
        if artifact.run_id != evaluation_artifact.run_id:
            raise SubstitutedDecisionEvidenceSourceError(
                "linked evaluation artifact evidence does not belong to evaluation "
                f"run '{evaluation_artifact.run_id}'."
            )
        if reference.content_digest is not None:
            content_digest = calculate_evaluation_artifact_evidence_digest(
                artifact=artifact,
            )
            if content_digest != reference.content_digest:
                raise StaleDecisionEvidenceSourceError(
                    "linked evaluation artifact evidence content digest is stale "
                    f"for '{reference.record_id}'."
                )

    async def _load_completed_run_bundle(
        self,
        workflow_name: str,
        execution_id: str,
        bundle_cache: dict[tuple[str, str], CompletedRunBundle],
    ) -> CompletedRunBundle:
        cache_key = (workflow_name, execution_id)
        cached = bundle_cache.get(cache_key)
        if cached is not None:
            return cached

        bundle = await self.completed_run_archive.load_archived_run(
            workflow_name,
            execution_id,
        )
        if bundle is None:
            raise MissingDecisionEvidenceSourceError(
                "completed workflow run source record "
                f"'{workflow_name}:{execution_id}' was not found."
            )
        if (
            bundle.run.workflow_name != workflow_name
            or bundle.run.execution_id != execution_id
        ):
            raise SubstitutedDecisionEvidenceSourceError(
                "completed workflow run evidence does not match reconstruction "
                f"identifier '{workflow_name}:{execution_id}'."
            )
        bundle_cache[cache_key] = bundle
        return bundle


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


def _is_tampered_snapshot_error(exc: BaseException) -> bool:
    message = str(exc)
    return "supporting evidence snapshot" in message and "content digest" in message


def calculate_evaluation_run_evidence_digest(
    *,
    run: EvaluationRunRecord,
) -> str:
    """Calculate a stable digest from safe evaluation run provenance fields."""

    return _stable_content_digest(
        {
            "run_id": run.run_id,
            "target_type": _enum_value(run.target_type),
            "status": _enum_value(run.status),
            "evaluator_provider": run.evaluator_provider,
            "evaluator_model": run.evaluator_model,
            "dataset_id": run.dataset_id,
            "case_ids": tuple(run.case_ids),
            "started_at": _datetime_value(run.started_at),
            "completed_at": _datetime_value(run.completed_at),
            "error_message": run.error_message,
        }
    )


def calculate_evaluation_metric_result_evidence_digest(
    *,
    metric_result: EvaluationMetricResultRecord,
) -> str:
    """Calculate a stable digest from safe evaluation metric result fields."""

    return _stable_content_digest(
        {
            "metric_result_id": metric_result.metric_result_id,
            "run_id": metric_result.run_id,
            "case_id": metric_result.case_id,
            "metric_name": metric_result.metric_name,
            "score": metric_result.score,
            "status": _enum_value(metric_result.status),
            "evaluator_provider": metric_result.evaluator_provider,
            "evaluator_model": metric_result.evaluator_model,
            "threshold": metric_result.threshold,
            "threshold_version": metric_result.threshold_version,
            "passed": metric_result.passed,
            "duration_ms": metric_result.duration_ms,
            "error_message": metric_result.error_message,
        }
    )


def calculate_rag_retrieval_context_evidence_digest(
    *,
    context_payload: Mapping[str, object],
) -> str:
    """Calculate a stable digest for a retained canonical RAG context payload."""

    source = _required_mapping(context_payload, "source")
    digest_payload = "|".join(
        (
            _required_string(context_payload, "context_id"),
            _required_string(context_payload, "retrieval_route"),
            _required_string(source, "source_table"),
            _required_string(source, "source_id"),
            _required_string(source, "document_id"),
            _optional_string(source.get("chunk_id")) or "",
            _required_string(context_payload, "text"),
        )
    )
    return hashlib.sha256(digest_payload.encode("utf-8")).hexdigest()


def calculate_rag_citation_source_evidence_digest(
    *,
    document: RagDocumentRecord,
    chunk: RagChunkRecord | None = None,
) -> str:
    """Calculate the RAG citation digest from canonical source document lineage."""

    section_name = _optional_string(document.metadata.get("section_name"))
    if chunk is not None:
        section_name = (
            _optional_string(chunk.metadata.get("section_name")) or section_name
        )
    digest_payload = "|".join(
        (
            document.source_table,
            document.source_id,
            document.source_type,
            document.document_id,
            "" if chunk is None else chunk.chunk_id,
            section_name or "",
            document.generated_at.isoformat(),
        )
    )
    return hashlib.sha256(digest_payload.encode("utf-8")).hexdigest()


def calculate_trace_context_evidence_digest(
    *,
    trace: TelemetryTraceRecord,
) -> str:
    """Calculate a stable digest for durable trace/correlation evidence fields."""

    return _stable_content_digest(
        {
            "trace_record_id": trace.trace_record_id,
            "trace_id": trace.trace_id,
            "span_id": trace.span_id,
            "operation_name": trace.operation_name,
            "source": trace.source,
            "parent_span_id": trace.parent_span_id,
            "started_at": _datetime_value(trace.started_at),
            "ended_at": _datetime_value(trace.ended_at),
            "duration_seconds": trace.duration_seconds,
            "status": trace.status,
            "correlation_id": trace.correlation_id,
            "terminal_event_id": trace.terminal_event_id,
            "exception_type": trace.exception_type,
            "exception_message": trace.exception_message,
        }
    )


def calculate_evaluation_artifact_evidence_digest(
    *,
    artifact: EvaluationArtifactRecord,
) -> str:
    """Calculate a stable digest from safe evaluation artifact identity fields."""

    return _stable_content_digest(
        {
            "artifact_id": artifact.artifact_id,
            "run_id": artifact.run_id,
            "artifact_type": artifact.artifact_type,
            "case_id": artifact.case_id,
            "uri": artifact.uri,
            "payload": artifact.payload,
            "created_at": _datetime_value(artifact.created_at),
        }
    )


async def _load_metric_result(
    *,
    repository: EvaluationProvenanceRepository,
    run_id: str,
    metric_result_id: str,
) -> EvaluationMetricResultRecord:
    metric_results = await repository.list_metric_results(run_id)
    for metric_result in metric_results:
        if metric_result.metric_result_id == metric_result_id:
            return metric_result
    raise MissingDecisionEvidenceSourceError(
        f"evaluation metric result source record '{metric_result_id}' was not found."
    )


async def _load_evaluation_artifact(
    *,
    repository: EvaluationProvenanceRepository,
    run_id: str,
    artifact_id: str,
) -> EvaluationArtifactRecord:
    artifacts = await repository.list_artifacts(run_id)
    for artifact in artifacts:
        if artifact.artifact_id == artifact_id:
            return artifact
    raise MissingDecisionEvidenceSourceError(
        f"evaluation artifact source record '{artifact_id}' was not found."
    )


@dataclass(frozen=True, slots=True)
class _RagSourceRecordIdentity:
    source_table: str | None
    source_id: str | None
    document_id: str
    chunk_id: str | None


@dataclass(frozen=True, slots=True)
class _EvaluationArtifactIdentity:
    run_id: str
    artifact_id: str


def _stable_content_digest(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _enum_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    return value


def _datetime_value(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _find_rag_context_payload(
    metadata: Mapping[str, object],
    *,
    context_id: str,
) -> Mapping[str, object] | None:
    for key in (
        "retrieved_contexts",
        "retrieval_contexts",
        "contexts",
        "citation_contexts",
    ):
        raw_contexts = metadata.get(key)
        if not isinstance(raw_contexts, Sequence) or isinstance(raw_contexts, str):
            continue
        for raw_context in raw_contexts:
            if not isinstance(raw_context, Mapping):
                continue
            raw_context_id = raw_context.get("context_id") or raw_context.get("id")
            if raw_context_id == context_id:
                return raw_context
    return None


def _parse_rag_source_record_id(record_id: str) -> _RagSourceRecordIdentity:
    parts = record_id.split(":")
    if len(parts) == 2 and all(parts):
        return _RagSourceRecordIdentity(
            source_table=None,
            source_id=None,
            document_id=parts[0],
            chunk_id=None if parts[1] == "document" else parts[1],
        )
    if len(parts) < 4 or not all(parts):
        _raise_malformed_rag_source_record_id()

    chunk_or_document = parts[-1]
    if chunk_or_document == "document":
        parsed_document_identity = _parse_rag_document_source_identity(parts)
        if parsed_document_identity is not None:
            return parsed_document_identity

    parsed_chunk_identity = _parse_rag_chunk_source_identity(parts)
    if parsed_chunk_identity is not None:
        return parsed_chunk_identity

    _raise_malformed_rag_source_record_id()


def _parse_rag_document_source_identity(
    parts: Sequence[str],
) -> _RagSourceRecordIdentity | None:
    for document_start_index in _rag_document_start_candidates(
        parts,
        max_index=len(parts) - 2,
    ):
        source_id_parts = parts[1:document_start_index]
        document_id_parts = parts[document_start_index:-1]
        if not source_id_parts or not document_id_parts:
            continue
        return _RagSourceRecordIdentity(
            source_table=parts[0],
            source_id=":".join(source_id_parts),
            document_id=":".join(document_id_parts),
            chunk_id=None,
        )
    return None


def _parse_rag_chunk_source_identity(
    parts: Sequence[str],
) -> _RagSourceRecordIdentity | None:
    if len(parts) == 4:
        return _RagSourceRecordIdentity(
            source_table=parts[0],
            source_id=parts[1],
            document_id=parts[2],
            chunk_id=parts[3],
        )

    if len(parts) >= 6 and parts[-2] == "chunk":
        for document_start_index in _rag_document_start_candidates(
            parts,
            max_index=len(parts) - 4,
        ):
            source_id_parts = parts[1:document_start_index]
            duplicated_document_parts = parts[document_start_index:-2]
            if not source_id_parts or len(duplicated_document_parts) % 2 != 0:
                continue
            document_part_count = len(duplicated_document_parts) // 2
            document_id_parts = duplicated_document_parts[:document_part_count]
            chunk_document_id_parts = duplicated_document_parts[document_part_count:]
            if not document_id_parts or document_id_parts != chunk_document_id_parts:
                continue
            chunk_id_parts = (*chunk_document_id_parts, parts[-2], parts[-1])
            return _RagSourceRecordIdentity(
                source_table=parts[0],
                source_id=":".join(source_id_parts),
                document_id=":".join(document_id_parts),
                chunk_id=":".join(chunk_id_parts),
            )

    for document_start_index in _rag_document_start_candidates(
        parts,
        max_index=len(parts) - 2,
    ):
        source_id_parts = parts[1:document_start_index]
        document_id_parts = parts[document_start_index:-1]
        if not source_id_parts or not document_id_parts:
            continue
        return _RagSourceRecordIdentity(
            source_table=parts[0],
            source_id=":".join(source_id_parts),
            document_id=":".join(document_id_parts),
            chunk_id=parts[-1],
        )
    return None


def _rag_document_start_candidates(
    parts: Sequence[str],
    *,
    max_index: int,
) -> tuple[int, ...]:
    if max_index < 2:
        return ()

    candidates: list[int] = []
    known_document_id_prefixes = {"rag_document", "structured", "web_document"}
    for index in range(2, max_index + 1):
        if parts[index] in known_document_id_prefixes:
            candidates.append(index)

    if not candidates:
        candidates.append(2 if len(parts) == 4 else max_index)
    fallback_indexes = (2, max_index)
    for index in fallback_indexes:
        if 2 <= index <= max_index and index not in candidates:
            candidates.append(index)
    return tuple(candidates)


def _raise_malformed_rag_source_record_id() -> NoReturn:
    raise MalformedDecisionEvidenceReconstructionIdentifierError(
        "RAG citation context reconstruction identifier must be "
        "'<source_table>:<source_id>:<document_id>:<chunk_id|document>'."
    )


def _validate_rag_document_identity(
    *,
    document: RagDocumentRecord,
    source_identity: _RagSourceRecordIdentity,
    reference: ReconstructionReference,
) -> None:
    if document.document_id != source_identity.document_id:
        raise SubstitutedDecisionEvidenceSourceError(
            "RAG citation document evidence does not match reconstruction "
            f"identifier '{reference.record_id}'."
        )
    if source_identity.source_table is not None and (
        document.source_table != source_identity.source_table
        or document.source_id != source_identity.source_id
    ):
        raise SubstitutedDecisionEvidenceSourceError(
            "RAG citation document evidence source lineage does not match "
            f"reconstruction identifier '{reference.record_id}'."
        )


def _parse_evaluation_artifact_record_id(
    record_id: str,
) -> _EvaluationArtifactIdentity | None:
    parts = record_id.split(":")
    if len(parts) != 3 or parts[0] != "evaluation-artifact":
        return None
    if not parts[1] or not parts[2]:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            "evaluation linked artifact reconstruction identifier must be "
            "'evaluation-artifact:<run_id>:<artifact_id>'."
        )
    return _EvaluationArtifactIdentity(run_id=parts[1], artifact_id=parts[2])


def _required_mapping(
    payload: Mapping[str, object],
    key: str,
) -> Mapping[str, object]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            f"RAG context payload must include mapping field '{key}'."
        )
    return value


def _required_string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            f"RAG context payload must include string field '{key}'."
        )
    return value


def _optional_string(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _validate_canonical_domain_record_reference(
    reference: ReconstructionReference,
) -> None:
    _require_source_of_truth(
        reference,
        expected=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
        label="canonical domain record reconstruction reference",
    )


def _validate_rag_retrieval_context_reference(
    reference: ReconstructionReference,
) -> None:
    label = "RAG retrieval context reconstruction reference"
    _require_source_of_truth(
        reference,
        expected=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
        label=label,
    )
    _require_snapshot_id(reference, label=label)
    _require_content_digest(reference, label=label)


def _validate_rag_citation_context_reference(
    reference: ReconstructionReference,
) -> None:
    label = "RAG citation context reconstruction reference"
    _require_source_of_truth(
        reference,
        expected=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
        label=label,
    )
    _require_snapshot_id(reference, label=label)
    _require_content_digest(reference, label=label)


def _validate_trace_context_reference(reference: ReconstructionReference) -> None:
    label = "trace context reconstruction reference"
    _require_source_of_truth(
        reference,
        expected=SourceOfTruthCategory.TELEMETRY,
        label=label,
    )
    _require_snapshot_id(reference, label=label)
    _require_content_digest(reference, label=label)


def _validate_linked_artifact_reference(reference: ReconstructionReference) -> None:
    if reference.source_of_truth is None:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            "linked artifact reconstruction reference must identify its source of "
            "truth."
        )


def _require_source_of_truth(
    reference: ReconstructionReference,
    *,
    expected: SourceOfTruthCategory,
    label: str,
) -> None:
    if reference.source_of_truth is not expected:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            f"{label} must identify {expected.value} as its source of truth."
        )


def _require_snapshot_id(reference: ReconstructionReference, *, label: str) -> None:
    if reference.snapshot_id is None:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            f"{label} must include a snapshot_id."
        )


def _require_content_digest(reference: ReconstructionReference, *, label: str) -> None:
    if reference.content_digest is None:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            f"{label} must include a content digest."
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


def _parse_completed_workflow_run_record_id(
    reference: ReconstructionReference,
) -> tuple[str, str]:
    parts = reference.record_id.split(":")
    if len(parts) != 2 or not all(parts):
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            "completed workflow run reconstruction identifier must be "
            "'<workflow_name>:<execution_id>'."
        )
    return parts[0], parts[1]


def _parse_workflow_node_snapshot_id(
    reference: ReconstructionReference,
) -> tuple[str, str, str]:
    if reference.snapshot_id is None:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            "workflow node output reconstruction reference must include a snapshot_id."
        )
    parts = reference.snapshot_id.split(":")
    if len(parts) != 3 or not all(parts):
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            "workflow node output reconstruction identifier must be "
            "'<workflow_name>:<execution_id>:<node_name>'."
        )
    return parts[0], parts[1], parts[2]


def _resolve_node_output(
    reference: ReconstructionReference,
    bundle: CompletedRunBundle,
) -> CompletedNodeOutputRecord:
    for node_output in bundle.node_outputs:
        if node_output.node_output_id == reference.record_id:
            return node_output
    raise MissingDecisionEvidenceSourceError(
        f"workflow node output source record '{reference.record_id}' was not found."
    )


def _reconstruction_telemetry_attributes(
    *,
    packet_id: str,
    record: DecisionEvidencePacketRecord | None,
) -> dict[str, object]:
    attributes: dict[str, object] = {
        "operation": "decision_evidence_packet_reconstruction",
        "packet_id": packet_id,
    }
    if record is None:
        return attributes

    attributes["output_id"] = record.output_id
    attributes["risk_tier"] = record.risk_tier.value
    retention_metadata = record.retention_metadata
    retention_policy_id = retention_metadata.get("policy_id")
    if isinstance(retention_policy_id, str):
        attributes["retention_policy_id"] = retention_policy_id
    retain_until = retention_metadata.get("retain_until")
    if isinstance(retain_until, str):
        attributes["retain_until"] = retain_until
    legal_hold = retention_metadata.get("legal_hold")
    if isinstance(legal_hold, bool):
        attributes["legal_hold"] = legal_hold
    return attributes


__all__ = [
    "EvaluationProvenanceRepository",
    "RagEvidenceSourceRepository",
    "TelemetryTraceSourceRepository",
    "calculate_evaluation_metric_result_evidence_digest",
    "calculate_evaluation_run_evidence_digest",
    "calculate_evaluation_artifact_evidence_digest",
    "calculate_rag_citation_source_evidence_digest",
    "calculate_rag_retrieval_context_evidence_digest",
    "calculate_trace_context_evidence_digest",
    "DecisionEvidencePacketNotFoundError",
    "DecisionEvidencePacketPersistenceService",
    "DecisionEvidencePacketReconstructionError",
    "MalformedDecisionEvidenceReconstructionIdentifierError",
    "MissingDecisionEvidenceSnapshotError",
    "MissingDecisionEvidenceSourceError",
    "StaleDecisionEvidenceSourceError",
    "SubstitutedDecisionEvidenceSourceError",
    "TamperedDecisionEvidenceSnapshotError",
    "UnsupportedDecisionEvidenceReferenceError",
]
