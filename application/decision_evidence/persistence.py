from __future__ import annotations

import logging
from dataclasses import dataclass, field

from application.decision_evidence._reconstruction import (
    CanonicalDomainRecordRepository,
    CanonicalDomainSourceRecord,
    DecisionEvidencePacketReconstructionError,
    EvaluationProvenanceRepository,
    MalformedDecisionEvidenceReconstructionIdentifierError,
    MissingDecisionEvidenceSnapshotError,
    MissingDecisionEvidenceSourceError,
    RagEvidenceSourceRepository,
    ReconstructionSourceValidator,
    StaleDecisionEvidenceSourceError,
    SubstitutedDecisionEvidenceSourceError,
    TamperedDecisionEvidenceSnapshotError,
    TamperedDecisionEvidenceSourceError,
    TelemetryTraceSourceRepository,
    UnsupportedDecisionEvidenceReferenceError,
    calculate_evaluation_artifact_evidence_digest,
    calculate_evaluation_metric_result_evidence_digest,
    calculate_evaluation_run_evidence_digest,
    calculate_rag_citation_source_evidence_digest,
    calculate_rag_retrieval_context_evidence_digest,
    calculate_trace_context_evidence_digest,
)
from core.storage.persistence.completed_run_archive import CompletedRunArchive
from core.storage.persistence.decision_evidence import (
    DecisionEvidencePacketPersistenceRepository,
    DecisionEvidencePacketPersistenceResult,
    DecisionEvidencePacketRecord,
)
from core.storage.persistence.serializers import (
    DecisionEvidencePacketPersistenceSerializer,
)
from core.telemetry.emitters.application_service_telemetry import (
    ApplicationServiceTelemetry,
)
from domain.decision_evidence import (
    DecisionEvidencePacket,
    DecisionEvidencePacketValidationError,
)

logger = logging.getLogger(__name__)


class DecisionEvidencePacketNotFoundError(DecisionEvidencePacketReconstructionError):
    """Raised when no persisted packet audit record exists for an id."""


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
    canonical_domain_record_repository: CanonicalDomainRecordRepository | None = field(
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

        record = await self._load_packet_record(packet_id)
        try:
            packet = self._deserialize_packet(record)
            await self._validate_reconstruction_sources(packet)
        except DecisionEvidencePacketReconstructionError as exc:
            await self._report_reconstruction_failure(
                packet_id=packet_id,
                error=exc,
                record=record,
                message="Decision evidence packet reconstruction failed closed.",
                logged_error=exc,
            )
            raise
        except (DecisionEvidencePacketValidationError, ValueError) as exc:
            reconstruction_error = _normalize_reconstruction_validation_error(
                packet_id=packet_id,
                error=exc,
            )
            await self._report_reconstruction_failure(
                packet_id=packet_id,
                error=reconstruction_error,
                record=record,
                message=(
                    "Decision evidence packet reconstruction identifier was malformed."
                ),
                logged_error=exc,
            )
            raise reconstruction_error from exc

        return packet

    async def _load_packet_record(
        self,
        packet_id: str,
    ) -> DecisionEvidencePacketRecord:
        record = await self.repository.get_packet_record(packet_id)
        if record is not None:
            return record

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

    def _deserialize_packet(
        self,
        record: DecisionEvidencePacketRecord,
    ) -> DecisionEvidencePacket:
        return DecisionEvidencePacketPersistenceSerializer.packet_from_record(record)

    async def _validate_reconstruction_sources(
        self,
        packet: DecisionEvidencePacket,
    ) -> None:
        validator = ReconstructionSourceValidator(
            completed_run_archive=self.completed_run_archive,
            evaluation_repository=self.evaluation_repository,
            rag_repository=self.rag_repository,
            trace_repository=self.trace_repository,
            canonical_domain_record_repository=self.canonical_domain_record_repository,
        )
        await validator.validate(packet)

    async def _report_reconstruction_failure(
        self,
        *,
        packet_id: str,
        error: DecisionEvidencePacketReconstructionError,
        record: DecisionEvidencePacketRecord,
        message: str,
        logged_error: BaseException,
    ) -> None:
        logger.warning(
            message,
            extra={
                "packet_id": packet_id,
                "error_type": type(logged_error).__name__,
            },
            exc_info=True,
        )
        await self._emit_reconstruction_failed(
            packet_id=packet_id,
            error=error,
            record=record,
        )

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


def _normalize_reconstruction_validation_error(
    *,
    packet_id: str,
    error: DecisionEvidencePacketValidationError | ValueError,
) -> DecisionEvidencePacketReconstructionError:
    if _is_tampered_snapshot_error(error):
        return TamperedDecisionEvidenceSnapshotError(
            f"decision evidence packet {packet_id!r} contains a "
            f"tampered retained support snapshot: {error}"
        )
    return MalformedDecisionEvidenceReconstructionIdentifierError(
        f"decision evidence packet {packet_id!r} contains malformed "
        f"reconstruction identifiers: {error}"
    )


def _is_tampered_snapshot_error(exc: BaseException) -> bool:
    message = str(exc)
    return "supporting evidence snapshot" in message and "content digest" in message


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
    "TamperedDecisionEvidenceSourceError",
    "UnsupportedDecisionEvidenceReferenceError",
    "CanonicalDomainRecordRepository",
    "CanonicalDomainSourceRecord",
]
