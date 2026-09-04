from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

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
from core.storage.persistence.telemetry import TelemetryTraceRecord
from domain.authority import SourceOfTruthCategory


class DecisionEvidencePacketReconstructionError(ValueError):
    """Raised when a persisted packet cannot be safely reconstructed."""


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


class TamperedDecisionEvidenceSourceError(DecisionEvidencePacketReconstructionError):
    """Raised when canonical source record content is internally inconsistent."""


@dataclass(frozen=True, slots=True)
class CanonicalDomainSourceRecord:
    """Verifiable identity metadata for a canonical domain source record."""

    record_id: str
    source_of_truth: SourceOfTruthCategory = (
        SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD
    )
    content_digest: str | None = None
    snapshot_id: str | None = None
    version: str | None = None
    snapshot_payload: Mapping[str, object] | None = None


class CanonicalDomainRecordRepository(Protocol):
    """Read model needed to verify generic canonical domain records."""

    async def get_canonical_domain_record(
        self,
        record_id: str,
    ) -> CanonicalDomainSourceRecord | None:
        """Load canonical domain record identity metadata by id."""


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
