from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from polaris.domain.decisions import OperationId
from polaris.domain.evidence import EvidenceObservation, EvidenceObservationId

from .contracts import (
    EvidenceCommandReadUnavailable,
    EvidenceIdempotencyConflict,
    EvidenceObservationCommit,
    EvidenceObservationCommitted,
    EvidenceObservationIdempotencyConflict,
    EvidenceObservationReceipt,
    EvidenceObservationReplayed,
    EvidenceObservationResult,
    EvidenceObservationSemanticRequest,
    EvidenceObservationStore,
    EvidenceObservationSuccessionConflict,
    EvidenceObservationUnavailable,
    EvidencePersistenceUnavailable,
    EvidenceSuccessionConflict,
    RecordEvidenceObservationCommand,
    require_aware_recording_time,
    require_exact_replay,
)


class EvidenceObservationService:
    def __init__(
        self,
        *,
        store: EvidenceObservationStore,
        now: Callable[[], datetime] | None = None,
        new_uuid: Callable[[], UUID] | None = None,
    ) -> None:
        self._store = store
        self._now = now or (lambda: datetime.now(UTC))
        self._new_uuid = new_uuid or uuid4

    async def record(
        self, command: RecordEvidenceObservationCommand
    ) -> EvidenceObservationResult:
        request = EvidenceObservationSemanticRequest.from_command(command)
        prior = await _read_receipt(self._store, command.operation_id)
        if prior is not None:
            return _replay(prior, request, command.operation_id)

        observation = EvidenceObservation(
            observation_id=EvidenceObservationId(self._new_uuid()),
            source=request.source,
            subject=request.subject,
            observed_at=request.observed_at,
            acquired_at=request.acquired_at,
            material=request.material,
            effective_at=request.effective_at,
            supersedes_observation_id=request.supersedes_observation_id,
        )
        committed_at = self._now()
        require_aware_recording_time(committed_at)

        outcome = await self._store.commit_observation(
            EvidenceObservationCommit(
                operation_id=command.operation_id,
                request=request,
                observation=observation,
                committed_at=committed_at,
            )
        )
        if isinstance(outcome, EvidenceObservationCommitted):
            return outcome.receipt.result
        if isinstance(outcome, EvidenceObservationReplayed):
            return _replay(outcome.receipt, request, command.operation_id)
        if isinstance(outcome, EvidenceObservationIdempotencyConflict):
            raise EvidenceIdempotencyConflict(outcome.operation_id)
        if isinstance(outcome, EvidenceObservationSuccessionConflict):
            raise EvidenceSuccessionConflict(outcome.predecessor_id)
        if isinstance(outcome, EvidenceObservationUnavailable):
            raise EvidencePersistenceUnavailable(outcome.reason)
        raise AssertionError("EvidenceObservationStore returned an unsupported outcome")


async def _read_receipt(
    store: EvidenceObservationStore,
    operation_id: OperationId,
) -> EvidenceObservationReceipt | None:
    try:
        return await store.get_observation_receipt(operation_id)
    except EvidenceCommandReadUnavailable as error:
        raise EvidencePersistenceUnavailable(str(error)) from error


def _replay(
    receipt: EvidenceObservationReceipt,
    request: EvidenceObservationSemanticRequest,
    operation_id: OperationId,
) -> EvidenceObservationResult:
    require_exact_replay(
        receipt_operation_id=receipt.operation_id,
        receipt_request=receipt.request,
        operation_id=operation_id,
        request=request,
    )
    return EvidenceObservationResult(
        observation_id=receipt.result.observation_id,
        replayed=True,
    )
