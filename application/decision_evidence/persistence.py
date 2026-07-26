from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Protocol

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
)
from core.storage.persistence.evaluation import (
    EvaluationMetricResultRecord,
    EvaluationRunRecord,
)
from core.storage.persistence.serializers import (
    DecisionEvidencePacketPersistenceSerializer,
)
from domain.authority import SourceOfTruthCategory
from domain.decision_evidence import (
    DecisionEvidencePacket,
    DecisionEvidencePacketValidationError,
    ReconstructionReference,
    ReconstructionReferenceKind,
)

logger = logging.getLogger(__name__)


class DecisionEvidencePacketReconstructionError(ValueError):
    """Raised when a persisted packet cannot be safely reconstructed."""


class DecisionEvidencePacketNotFoundError(DecisionEvidencePacketReconstructionError):
    """Raised when no persisted packet audit record exists for an id."""


class MissingDecisionEvidenceSourceError(DecisionEvidencePacketReconstructionError):
    """Raised when a canonical source record referenced by a packet is absent."""


class StaleDecisionEvidenceSourceError(DecisionEvidencePacketReconstructionError):
    """Raised when a canonical source record no longer matches packet snapshots."""


class SubstitutedDecisionEvidenceSourceError(DecisionEvidencePacketReconstructionError):
    """Raised when a source record belongs to a different evidence context."""


class MalformedDecisionEvidenceReconstructionIdentifierError(
    DecisionEvidencePacketReconstructionError,
):
    """Raised when persisted reconstruction identifiers are malformed."""


class EvaluationProvenanceRepository(Protocol):
    """Read model needed to verify canonical evaluation provenance sources."""

    async def get_run(self, run_id: str) -> EvaluationRunRecord | None:
        """Load a canonical evaluation run record by id."""

    async def list_metric_results(
        self,
        run_id: str,
    ) -> Sequence[EvaluationMetricResultRecord]:
        """Load canonical metric results attached to an evaluation run."""


@dataclass(frozen=True, slots=True)
class DecisionEvidencePacketPersistenceService:
    """Persist packet references and reconstruct packets from canonical sources."""

    repository: DecisionEvidencePacketPersistenceRepository = field(repr=False)
    completed_run_archive: CompletedRunArchive = field(repr=False)
    evaluation_repository: EvaluationProvenanceRepository | None = field(
        default=None,
        repr=False,
    )

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
            raise
        except (DecisionEvidencePacketValidationError, ValueError) as exc:
            logger.warning(
                "Decision evidence packet reconstruction identifier was malformed.",
                extra={
                    "packet_id": packet_id,
                    "error_type": type(exc).__name__,
                },
                exc_info=True,
            )
            raise MalformedDecisionEvidenceReconstructionIdentifierError(
                f"decision evidence packet {packet_id!r} contains malformed "
                "reconstruction identifiers."
            ) from exc

        return packet

    async def _validate_reconstruction_sources(
        self,
        packet: DecisionEvidencePacket,
    ) -> None:
        bundle_cache: dict[tuple[str, str], CompletedRunBundle] = {}
        for reference in packet.reconstruction_references:
            _validate_source_of_truth(reference)
            if reference.kind is ReconstructionReferenceKind.COMPLETED_WORKFLOW_RUN:
                await self._validate_completed_workflow_run(reference, bundle_cache)
            elif reference.kind is ReconstructionReferenceKind.WORKFLOW_NODE_OUTPUT:
                await self._validate_workflow_node_output(reference, bundle_cache)
            elif reference.kind is ReconstructionReferenceKind.EVALUATION_RUN:
                await self._validate_evaluation_run(reference)
            elif reference.kind is ReconstructionReferenceKind.EVALUATION_METRIC_RESULT:
                await self._validate_evaluation_metric_result(reference)

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


__all__ = [
    "EvaluationProvenanceRepository",
    "calculate_evaluation_metric_result_evidence_digest",
    "calculate_evaluation_run_evidence_digest",
    "DecisionEvidencePacketNotFoundError",
    "DecisionEvidencePacketPersistenceService",
    "DecisionEvidencePacketReconstructionError",
    "MalformedDecisionEvidenceReconstructionIdentifierError",
    "MissingDecisionEvidenceSourceError",
    "StaleDecisionEvidenceSourceError",
    "SubstitutedDecisionEvidenceSourceError",
]
