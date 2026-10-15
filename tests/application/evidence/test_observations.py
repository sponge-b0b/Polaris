from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from polaris.application.evidence import (
    EvidenceIdempotencyConflict,
    EvidenceObservationCommit,
    EvidenceObservationCommitted,
    EvidenceObservationIdempotencyConflict,
    EvidenceObservationReceipt,
    EvidenceObservationReplayed,
    EvidenceObservationResult,
    EvidenceObservationStore,
    EvidenceObservationSuccessionConflict,
    EvidenceSuccessionConflict,
)
from polaris.domain.decisions import OperationId
from polaris.domain.evidence import EvidenceObservation, EvidenceObservationId
from tests.evidence_support import (
    MISSING_OBSERVATION_ID,
    OBSERVATION_ID,
    SECOND_OBSERVATION_ID,
    SECOND_OPERATION_ID,
    evidence_command,
    evidence_service,
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
    result = asyncio.run(
        evidence_service(store, OBSERVATION_ID).record(evidence_command())
    )

    assert result == EvidenceObservationResult(EvidenceObservationId(OBSERVATION_ID))
    assert EvidenceObservationId(OBSERVATION_ID) in store.observations


def test_exact_retry_reuses_committed_observation_identity() -> None:
    store = _FakeEvidenceStore()
    service = evidence_service(store, OBSERVATION_ID, SECOND_OBSERVATION_ID)

    first = asyncio.run(service.record(evidence_command()))
    second = asyncio.run(service.record(evidence_command()))

    assert second == replace(first, replayed=True)
    assert len(store.observations) == 1


def test_changed_semantic_request_reusing_operation_conflicts() -> None:
    store = _FakeEvidenceStore()
    service = evidence_service(store, OBSERVATION_ID)
    asyncio.run(service.record(evidence_command()))

    with pytest.raises(EvidenceIdempotencyConflict):
        asyncio.run(
            service.record(evidence_command(retained_representation='{"value": 999.0}'))
        )


def test_distinct_operation_gets_fresh_identity_for_equivalent_observation() -> None:
    store = _FakeEvidenceStore()
    service = evidence_service(store, OBSERVATION_ID, SECOND_OBSERVATION_ID)

    first = asyncio.run(service.record(evidence_command()))
    second = asyncio.run(service.record(evidence_command(SECOND_OPERATION_ID)))

    assert first.observation_id != second.observation_id
    assert len(store.observations) == 2


def test_supersession_requires_existing_observation_root() -> None:
    missing = EvidenceObservationId(MISSING_OBSERVATION_ID)
    store = _FakeEvidenceStore()
    service = evidence_service(store, OBSERVATION_ID)

    with pytest.raises(EvidenceSuccessionConflict) as raised:
        asyncio.run(service.record(evidence_command(supersedes=missing)))

    assert raised.value.predecessor_id == missing
