from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from uuid import UUID, uuid4

from polaris.domain.evidence.bindings import EvidenceBinding
from polaris.domain.evidence.observations import EvidenceBindingId

from .binding_contracts import (
    EvidenceBindingCommit,
    EvidenceBindingCommitted,
    EvidenceBindingIdempotencyConflict,
    EvidenceBindingObservationConflict,
    EvidenceBindingReceipt,
    EvidenceBindingReplayed,
    EvidenceBindingResult,
    EvidenceBindingSemanticRequest,
    EvidenceBindingStore,
    EvidenceBindingUnavailable,
    RecordEvidenceBindingCommand,
)
from .contracts import (
    EvidenceIdempotencyConflict,
    EvidencePersistenceUnavailable,
)


class EvidenceBindingObservationReferenceConflict(Exception):
    def __init__(self, observation_id: object) -> None:
        super().__init__(f"Evidence observation does not exist: {observation_id}")
        self.observation_id = observation_id


class EvidenceBindingService:
    def __init__(
        self,
        *,
        store: EvidenceBindingStore,
        now: Callable[[], datetime],
        new_uuid: Callable[[], UUID] = uuid4,
    ) -> None:
        self._store = store
        self._now = now
        self._new_uuid = new_uuid

    async def record(
        self,
        command: RecordEvidenceBindingCommand,
    ) -> EvidenceBindingResult:
        request = EvidenceBindingSemanticRequest.from_command(command)
        receipt = await self._read_receipt(command.operation_id)
        if receipt is not None:
            return _replay(receipt, request, command.operation_id)

        committed_at = self._now()
        _require_aware(committed_at)
        binding = EvidenceBinding(
            binding_id=EvidenceBindingId(self._new_uuid()),
            observation_id=command.observation_id,
            target=command.target,
            scope=command.scope,
            evidence_use=command.evidence_use,
            role=command.role,
            availability=command.availability,
            materially_used=command.materially_used,
            effective_at=command.effective_at,
            recorded_at=committed_at,
            material_qualification=command.material_qualification,
            freshness_authority=command.freshness_authority,
            freshness_basis=command.freshness_basis,
        )
        outcome = await self._store.commit_binding(
            EvidenceBindingCommit(
                operation_id=command.operation_id,
                request=request,
                binding=binding,
                committed_at=committed_at,
            )
        )
        if isinstance(outcome, EvidenceBindingCommitted):
            return outcome.receipt.result
        if isinstance(outcome, EvidenceBindingReplayed):
            return _replay(outcome.receipt, request, command.operation_id)
        if isinstance(outcome, EvidenceBindingIdempotencyConflict):
            raise EvidenceIdempotencyConflict(outcome.operation_id)
        if isinstance(outcome, EvidenceBindingObservationConflict):
            raise EvidenceBindingObservationReferenceConflict(outcome.observation_id)
        if isinstance(outcome, EvidenceBindingUnavailable):
            raise EvidencePersistenceUnavailable(outcome.reason)
        raise AssertionError("EvidenceBindingStore returned an unsupported outcome")

    async def _read_receipt(self, operation_id: object) -> EvidenceBindingReceipt | None:
        try:
            return await self._store.get_binding_receipt(operation_id)  # type: ignore[arg-type]
        except Exception as error:
            if isinstance(error, EvidencePersistenceUnavailable):
                raise
            # Store adapters expose technology-neutral read failure as ordinary
            # exceptions only through their own inward contract.
            from .contracts import EvidenceCommandReadUnavailable

            if isinstance(error, EvidenceCommandReadUnavailable):
                raise EvidencePersistenceUnavailable(str(error)) from error
            raise


def _replay(
    receipt: EvidenceBindingReceipt,
    request: EvidenceBindingSemanticRequest,
    operation_id: object,
) -> EvidenceBindingResult:
    if receipt.request != request or receipt.operation_id != operation_id:
        raise EvidenceIdempotencyConflict(receipt.operation_id)
    return replace(receipt.result, replayed=True)


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("application recording time must be timezone-aware")
