from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import pytest

from polaris.application.evidence import (
    EvidenceIdempotencyConflict,
    EvidenceObservationCommit,
    EvidenceObservationCommitted,
    EvidenceObservationIdempotencyConflict,
    EvidenceObservationReceipt,
    EvidenceObservationReplayed,
    EvidenceObservationResult,
    EvidenceObservationService,
    EvidenceObservationStore,
    EvidenceObservationSuccessionConflict,
    EvidenceSuccessionConflict,
    RecordEvidenceObservationCommand,
)
from polaris.domain.decisions import OperationId
from polaris.domain.evidence import (
    EvidenceObservation,
    EvidenceObservationId,
    EvidenceObservationMaterial,
    EvidenceSourceProvenance,
    EvidenceSubjectReference,
)

OPERATION_ID = UUID("00000000-0000-4000-8000-000000000201")
SECOND_OPERATION_ID = UUID("00000000-0000-4000-8000-000000000202")
OBSERVATION_ID = UUID("00000000-0000-4000-8000-000000000203")
SECOND_OBSERVATION_ID = UUID("00000000-0000-4000-8000-000000000204")
OBSERVED_AT = datetime(2026, 9, 29, 14, 0, tzinfo=UTC)
ACQUIRED_AT = datetime(2026, 9, 29, 14, 1, tzinfo=UTC)
COMMITTED_AT = datetime(2026, 9, 29, 14, 2, tzinfo=UTC)


def _command(operation_id: UUID = OPERATION_ID) -> RecordEvidenceObservationCommand:
    return RecordEvidenceObservationCommand(
        operation_id=OperationId(operation_id),
        source=EvidenceSourceProvenance(
            "fred",
            "series:CPIAUCSL:2026-08",
            "Federal Reserve Bank of St. Louis / source publisher",
        ),
        subject=EvidenceSubjectReference("US:CPI", "2026-08"),
        observed_at=OBSERVED_AT,
        acquired_at=ACQUIRED_AT,
        effective_at=OBSERVED_AT,
        material=EvidenceObservationMaterial(
            retained_representation='{"value": 321.1}'
        ),
    )


class _FakeEvidenceStore(EvidenceObservationStore):
    def __init__(self) -> None:
        self.receipts: dict[OperationId, EvidenceObservationReceipt] = {}
        self.observations: dict[EvidenceObservationId, EvidenceObservation] = {}

    async def get_observation_receipt(
        self, operation_id: OperationId
    ) -> EvidenceObservationReceipt | None:
        return self.receipts.get(operation_id)

    async def commit_observation(
        self, commit: EvidenceObservationCommit
    ) -> (
        EvidenceObservationCommitted
        | EvidenceObservationReplayed
        | EvidenceObservationIdempotencyConflict
        | EvidenceObservationSuccessionConflict
    ):
        prior = self.receipts.get(commit.operation_id)
        if prior is not None:
            if prior.request != commit.request:
                return EvidenceObservationIdempotencyConflict(commit.operation_id)
            return EvidenceObservationReplayed(prior)
        predecessor = commit.observation.supersedes_observation_id
        if predecessor is not None and predecessor not in self.observations:
            return EvidenceObservationSuccessionConflict(predecessor)
        result = EvidenceObservationResult(commit.observation.observation_id)
        receipt = EvidenceObservationReceipt(
            commit.operation_id,
            commit.request,
            result,
        )
        self.observations[commit.observation.observation_id] = commit.observation
        self.receipts[commit.operation_id] = receipt
        return EvidenceObservationCommitted(receipt)

    async def load_observation(
        self, observation_id: EvidenceObservationId
    ) -> EvidenceObservation | None:
        return self.observations.get(observation_id)


def test_application_allocates_observation_identity_before_store_commit() -> None:
    store = _FakeEvidenceStore()
    service = EvidenceObservationService(
        store=store,
        now=lambda: COMMITTED_AT,
        new_uuid=lambda: OBSERVATION_ID,
    )

    result = asyncio.run(service.record(_command()))

    assert result == EvidenceObservationResult(EvidenceObservationId(OBSERVATION_ID))
    assert EvidenceObservationId(OBSERVATION_ID) in store.observations


def test_exact_retry_reuses_committed_observation_identity() -> None:
    store = _FakeEvidenceStore()
    identities = iter((OBSERVATION_ID, SECOND_OBSERVATION_ID))
    service = EvidenceObservationService(
        store=store,
        now=lambda: COMMITTED_AT,
        new_uuid=lambda: next(identities),
    )

    first = asyncio.run(service.record(_command()))
    second = asyncio.run(service.record(_command()))

    assert second == replace(first, replayed=True)
    assert len(store.observations) == 1


def test_changed_semantic_request_reusing_operation_conflicts() -> None:
    store = _FakeEvidenceStore()
    service = EvidenceObservationService(
        store=store,
        now=lambda: COMMITTED_AT,
        new_uuid=lambda: OBSERVATION_ID,
    )
    asyncio.run(service.record(_command()))
    changed = replace(
        _command(),
        material=EvidenceObservationMaterial(
            retained_representation='{"value": 999.0}'
        ),
    )

    with pytest.raises(EvidenceIdempotencyConflict):
        asyncio.run(service.record(changed))


def test_distinct_operation_gets_fresh_identity_for_equivalent_observation() -> None:
    store = _FakeEvidenceStore()
    identities = iter((OBSERVATION_ID, SECOND_OBSERVATION_ID))
    service = EvidenceObservationService(
        store=store,
        now=lambda: COMMITTED_AT,
        new_uuid=lambda: next(identities),
    )

    first = asyncio.run(service.record(_command()))
    second = asyncio.run(service.record(_command(SECOND_OPERATION_ID)))

    assert first.observation_id != second.observation_id
    assert len(store.observations) == 2


def test_supersession_requires_existing_observation_root() -> None:
    missing = EvidenceObservationId(UUID("00000000-0000-4000-8000-000000000205"))
    store = _FakeEvidenceStore()
    service = EvidenceObservationService(
        store=store,
        now=lambda: COMMITTED_AT,
        new_uuid=lambda: OBSERVATION_ID,
    )

    with pytest.raises(EvidenceSuccessionConflict) as raised:
        asyncio.run(
            service.record(replace(_command(), supersedes_observation_id=missing))
        )

    assert raised.value.predecessor_id == missing
