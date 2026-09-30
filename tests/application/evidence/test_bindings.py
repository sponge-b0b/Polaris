from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from polaris.application.evidence import (
    EvidenceBindingCommit,
    EvidenceBindingCommitOutcome,
    EvidenceBindingCommitted,
    EvidenceBindingIdempotencyConflict,
    EvidenceBindingObservationConflict,
    EvidenceBindingObservationReferenceConflict,
    EvidenceBindingReceipt,
    EvidenceBindingReplayed,
    EvidenceBindingResult,
    EvidenceBindingStore,
    EvidenceIdempotencyConflict,
)
from polaris.domain.decisions import OperationId
from polaris.domain.evidence.bindings import EvidenceBinding
from polaris.domain.evidence.observations import (
    EvidenceBindingId,
    EvidenceObservationId,
)
from tests.binding_support import (
    BINDING_ID,
    SECOND_BINDING_ID,
    SECOND_BINDING_OPERATION_ID,
    binding_command,
    binding_service,
)
from tests.evidence_support import OBSERVATION_ID


class _FakeBindingStore(EvidenceBindingStore):
    def __init__(self, *, observation_exists: bool = True) -> None:
        self.receipts: dict[OperationId, EvidenceBindingReceipt] = {}
        self.bindings: dict[EvidenceBindingId, EvidenceBinding] = {}
        self.observation_exists = observation_exists

    # duplicate-code: this in-memory binding fake is an independent application
    # falsifier; sharing another aggregate's fake would couple test state machines.
    # arid: disable
    async def get_binding_receipt(
        self,
        operation_id: OperationId,
    ) -> EvidenceBindingReceipt | None:
        return self.receipts.get(operation_id)

    # arid: enable

    async def commit_binding(
        self,
        commit: EvidenceBindingCommit,
    ) -> EvidenceBindingCommitOutcome:
        # duplicate-code: fake replay behavior mirrors the inward binding port
        # without depending on production SQL or the observation fake.
        # arid: disable
        prior = self.receipts.get(commit.operation_id)
        if prior is not None:
            if prior.request != commit.request:
                return EvidenceBindingIdempotencyConflict(commit.operation_id)
            return EvidenceBindingReplayed(prior)
        # arid: enable
        if not self.observation_exists:
            return EvidenceBindingObservationConflict(commit.binding.observation_id)
        result = EvidenceBindingResult(commit.binding.binding_id)
        receipt = EvidenceBindingReceipt(commit.operation_id, commit.request, result)
        self.bindings[commit.binding.binding_id] = commit.binding
        self.receipts[commit.operation_id] = receipt
        return EvidenceBindingCommitted(receipt)

    async def load_binding(
        self,
        binding_id: EvidenceBindingId,
    ) -> EvidenceBinding | None:
        return self.bindings.get(binding_id)


def test_application_allocates_binding_identity_before_commit() -> None:
    store = _FakeBindingStore()
    result = asyncio.run(binding_service(store, BINDING_ID).record(binding_command()))

    assert result.binding_id == EvidenceBindingId(BINDING_ID)
    assert EvidenceBindingId(BINDING_ID) in store.bindings


def test_exact_retry_reuses_committed_binding_identity() -> None:
    store = _FakeBindingStore()
    service = binding_service(store, BINDING_ID, SECOND_BINDING_ID)

    first = asyncio.run(service.record(binding_command()))
    second = asyncio.run(service.record(binding_command()))

    assert second == replace(first, replayed=True)
    assert len(store.bindings) == 1


def test_changed_semantic_request_reusing_operation_conflicts() -> None:
    store = _FakeBindingStore()
    service = binding_service(store, BINDING_ID)
    asyncio.run(service.record(binding_command()))

    with pytest.raises(EvidenceIdempotencyConflict):
        asyncio.run(
            service.record(
                replace(
                    binding_command(),
                    materially_used=False,
                )
            )
        )


def test_distinct_operation_preserves_equivalent_binding_as_distinct_act() -> None:
    store = _FakeBindingStore()
    service = binding_service(store, BINDING_ID, SECOND_BINDING_ID)

    first = asyncio.run(service.record(binding_command()))
    second = asyncio.run(service.record(binding_command(SECOND_BINDING_OPERATION_ID)))

    assert first.binding_id != second.binding_id
    assert len(store.bindings) == 2


def test_missing_observation_fails_with_typed_reference_conflict() -> None:
    store = _FakeBindingStore(observation_exists=False)

    with pytest.raises(EvidenceBindingObservationReferenceConflict) as raised:
        asyncio.run(binding_service(store, BINDING_ID).record(binding_command()))

    assert raised.value.observation_id == EvidenceObservationId(OBSERVATION_ID)
