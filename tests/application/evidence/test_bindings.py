from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime
from uuid import UUID

import pytest

from polaris.application.evidence import (
    ClaimMembershipResolution,
    EvidenceBindingClaimMembershipRejected,
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
    InvalidClaimReference,
    RecordEvidenceBindingCommand,
    ResolvedClaimMembership,
)
from polaris.domain.decisions import OperationId
from polaris.domain.evidence.bindings import EvidenceBinding
from polaris.domain.evidence.claims import ClaimCatalogVersion
from polaris.domain.evidence.judgments import (
    ClaimId,
    ClaimSpecificEvidenceScope,
    EvidenceJudgmentRef,
    InvestmentRecommendationRef,
)
from polaris.domain.evidence.observations import (
    EvidenceBindingId,
    EvidenceObservationId,
)
from tests.binding_support import (
    BINDING_ID,
    SECOND_BINDING_ID,
    SECOND_BINDING_OPERATION_ID,
    SECOND_TARGET_ID,
    binding_command,
    binding_service,
)
from tests.evidence_support import OBSERVATION_ID

CLAIM_ID = UUID("00000000-0000-4000-8000-000000000421")
SECOND_CLAIM_ID = UUID("00000000-0000-4000-8000-000000000422")


class _ClaimResolver:
    def __init__(self, result: ClaimMembershipResolution) -> None:
        self.result = result

    async def resolve(
        self,
        target: EvidenceJudgmentRef,
        claim_id: ClaimId,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> ClaimMembershipResolution:
        del target, claim_id, effective_at, known_at
        return self.result


def _claim_command_and_resolver() -> tuple[
    RecordEvidenceBindingCommand,
    _ClaimResolver,
]:
    command = binding_command(scope=ClaimSpecificEvidenceScope(ClaimId(CLAIM_ID)))
    return command, _ClaimResolver(
        ResolvedClaimMembership(
            command.target,
            ClaimId(CLAIM_ID),
            ClaimCatalogVersion(1),
        )
    )


def _membership_rejection(
    command: RecordEvidenceBindingCommand,
    resolver: _ClaimResolver,
) -> EvidenceBindingClaimMembershipRejected:
    store = _FakeBindingStore()
    with pytest.raises(EvidenceBindingClaimMembershipRejected) as raised:
        asyncio.run(
            binding_service(store, BINDING_ID, claim_catalog=resolver).record(command)
        )
    assert not store.bindings
    return raised.value


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


def test_changed_target_reusing_operation_conflicts_without_replacing_root() -> None:
    store = _FakeBindingStore()
    service = binding_service(store, BINDING_ID, SECOND_BINDING_ID)

    first = asyncio.run(service.record(binding_command()))

    with pytest.raises(EvidenceIdempotencyConflict):
        asyncio.run(service.record(binding_command(target_id=SECOND_TARGET_ID)))

    assert tuple(store.bindings) == (first.binding_id,)


def test_changed_target_under_distinct_operation_creates_new_root() -> None:
    store = _FakeBindingStore()
    service = binding_service(store, BINDING_ID, SECOND_BINDING_ID)

    first = asyncio.run(service.record(binding_command()))
    second = asyncio.run(
        service.record(
            binding_command(
                SECOND_BINDING_OPERATION_ID,
                target_id=SECOND_TARGET_ID,
            )
        )
    )

    assert first.binding_id != second.binding_id
    assert (
        store.bindings[first.binding_id].target
        != store.bindings[second.binding_id].target
    )


def test_missing_observation_fails_with_typed_reference_conflict() -> None:
    store = _FakeBindingStore(observation_exists=False)

    with pytest.raises(EvidenceBindingObservationReferenceConflict) as raised:
        asyncio.run(binding_service(store, BINDING_ID).record(binding_command()))

    assert raised.value.observation_id == EvidenceObservationId(OBSERVATION_ID)


def test_claim_specific_binding_requires_confirmed_membership() -> None:
    command, resolver = _claim_command_and_resolver()
    store = _FakeBindingStore()

    result = asyncio.run(
        binding_service(store, BINDING_ID, claim_catalog=resolver).record(command)
    )

    assert store.bindings[result.binding_id].scope == command.scope


def test_wrong_target_claim_is_rejected_before_binding_commit() -> None:
    command = binding_command(scope=ClaimSpecificEvidenceScope(ClaimId(CLAIM_ID)))
    resolver = _ClaimResolver(
        InvalidClaimReference(
            InvestmentRecommendationRef(SECOND_TARGET_ID),
            ClaimId(CLAIM_ID),
        )
    )
    rejection = _membership_rejection(command, resolver)

    assert isinstance(rejection.resolution, InvalidClaimReference)


@pytest.mark.parametrize("mismatched_field", ["target", "claim_id"])
def test_contradictory_positive_membership_is_rejected_before_commit(
    mismatched_field: str,
) -> None:
    command = binding_command(scope=ClaimSpecificEvidenceScope(ClaimId(CLAIM_ID)))
    resolver = _ClaimResolver(
        ResolvedClaimMembership(
            (
                InvestmentRecommendationRef(SECOND_TARGET_ID)
                if mismatched_field == "target"
                else command.target
            ),
            (
                ClaimId(SECOND_CLAIM_ID)
                if mismatched_field == "claim_id"
                else ClaimId(CLAIM_ID)
            ),
            ClaimCatalogVersion(1),
        )
    )
    rejection = _membership_rejection(command, resolver)

    assert rejection.resolution == InvalidClaimReference(
        command.target,
        ClaimId(CLAIM_ID),
    )


def test_exact_retry_does_not_revalidate_a_fixed_historical_endpoint() -> None:
    command, resolver = _claim_command_and_resolver()
    service = binding_service(
        _FakeBindingStore(),
        BINDING_ID,
        claim_catalog=resolver,
    )

    first = asyncio.run(service.record(command))
    resolver.result = InvalidClaimReference(command.target, ClaimId(CLAIM_ID))
    replay = asyncio.run(service.record(command))

    assert replay == replace(first, replayed=True)
