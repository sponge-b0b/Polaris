from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from polaris.domain.decisions import (
    DecisionInitiationContinuity,
    DecisionInitiationDetermination,
    DecisionLifecycleFactId,
    DecisionMutationContext,
    DecisionNeed,
    DecisionNeedId,
    InvestmentDecisionId,
    OperationId,
    initiate_decision,
)

from .contracts import (
    ContinuityAmbiguous,
    ContinuityCandidateBasis,
    ContinuityConflict,
    ContinuityDetermination,
    ContinuityDeterminationKind,
    DecisionCommandStore,
    DecisionMemoryReader,
    DecisionNeedGroundingConflict,
    IdempotencyConflict,
    InitiateDecisionCommand,
    InitiationCommit,
    InitiationCommitted,
    InitiationContinuityConflict,
    InitiationIdempotencyConflict,
    InitiationNeedAlreadyGrounded,
    InitiationReceipt,
    InitiationReplayed,
    InitiationResult,
    InitiationResultKind,
    InitiationSemanticRequest,
    InitiationUnavailable,
    InvalidDecisionCommand,
    PersistenceUnavailable,
)


class DecisionInitiationService:
    def __init__(
        self,
        *,
        reader: DecisionMemoryReader,
        store: DecisionCommandStore,
        now: Callable[[], datetime] | None = None,
        new_uuid: Callable[[], UUID] | None = None,
    ) -> None:
        self._reader = reader
        self._store = store
        self._now = now or (lambda: datetime.now(UTC))
        self._new_uuid = new_uuid or uuid4

    async def initiate(self, command: InitiateDecisionCommand) -> InitiationResult:
        request = InitiationSemanticRequest.from_command(command)
        if request.expected_versions:
            raise InvalidDecisionCommand(
                "new Decision initiation cannot carry expected existing-Decision "
                "versions"
            )

        prior = await self._store.get_initiation_receipt(command.envelope.operation_id)
        if prior is not None:
            return _replay(prior, request, command.envelope.operation_id)

        recorded_at = _recording_time(self._now())
        candidate_ids = frozenset(
            await self._reader.find_unresolved_continuity_candidates(
                known_at=recorded_at
            )
        )
        basis = ContinuityCandidateBasis(candidate_ids, recorded_at)
        determination = _resolve_determination(command.continuity, basis)

        if determination.kind is ContinuityDeterminationKind.CONTINUE_EXISTING:
            assert determination.decision_id is not None
            result = InitiationResult(
                decision_id=determination.decision_id,
                need_id=None,
                kind=InitiationResultKind.CONTINUED,
            )
            decision = None
        else:
            decision_id = InvestmentDecisionId(self._new_uuid())
            need_id = DecisionNeedId(self._new_uuid())
            fact_id = DecisionLifecycleFactId(self._new_uuid())
            continuity = _domain_continuity(basis, determination)
            envelope = command.envelope
            need = DecisionNeed(
                need_id=need_id,
                statement=command.need_statement,
                effective_at=envelope.effective_at,
                recorded_at=recorded_at,
                operation_id=envelope.operation_id,
                actor_attribution=envelope.actor_attribution,
                trigger=envelope.trigger,
                technical_provenance=envelope.technical_provenance,
            )
            decision = initiate_decision(
                decision_id=decision_id,
                need=need,
                subject=command.subject,
                scope=command.scope,
                continuity=continuity,
                mutation=DecisionMutationContext(
                    fact_id=fact_id,
                    operation_id=envelope.operation_id,
                    actor_attribution=envelope.actor_attribution,
                    trigger=envelope.trigger,
                    effective_at=envelope.effective_at,
                    recorded_at=recorded_at,
                    technical_provenance=envelope.technical_provenance,
                ),
            )
            result = InitiationResult(
                decision_id=decision_id,
                need_id=need_id,
                kind=InitiationResultKind.CREATED,
            )

        outcome = await self._store.commit_initiation(
            InitiationCommit(
                operation_id=command.envelope.operation_id,
                request=request,
                candidate_basis=basis,
                result=result,
                decision=decision,
            )
        )
        if isinstance(outcome, InitiationCommitted):
            return outcome.receipt.result
        if isinstance(outcome, InitiationReplayed):
            return _replay(outcome.receipt, request, command.envelope.operation_id)
        if isinstance(outcome, InitiationIdempotencyConflict):
            raise IdempotencyConflict(outcome.operation_id)
        if isinstance(outcome, InitiationContinuityConflict):
            raise ContinuityConflict(outcome.candidate_decision_ids)
        if isinstance(outcome, InitiationNeedAlreadyGrounded):
            raise DecisionNeedGroundingConflict(outcome.existing_decision_id)
        if isinstance(outcome, InitiationUnavailable):
            raise PersistenceUnavailable(outcome.reason)
        raise AssertionError("DecisionCommandStore returned an unsupported outcome")


def _recording_time(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("application recording time must be timezone-aware")
    return value


def _resolve_determination(
    requested: ContinuityDetermination | None,
    basis: ContinuityCandidateBasis,
) -> ContinuityDetermination:
    candidates = basis.candidate_decision_ids
    if not candidates:
        if (
            requested is None
            or requested.kind is ContinuityDeterminationKind.CREATE_NEW
        ):
            return ContinuityDetermination.create_new()
        raise ContinuityAmbiguous(candidates)

    if requested is None:
        raise ContinuityAmbiguous(candidates)
    if requested.kind is ContinuityDeterminationKind.CONTINUE_EXISTING:
        if requested.decision_id not in candidates:
            raise ContinuityAmbiguous(candidates)
        return requested
    if requested.rationale is None:
        raise ContinuityAmbiguous(candidates)
    return requested


def _domain_continuity(
    basis: ContinuityCandidateBasis,
    determination: ContinuityDetermination,
) -> DecisionInitiationContinuity:
    if not basis.candidate_decision_ids:
        return DecisionInitiationContinuity(
            determination=DecisionInitiationDetermination.NO_CANDIDATES,
            candidate_decision_ids=(),
            known_at=basis.known_at,
        )
    assert determination.rationale is not None
    return DecisionInitiationContinuity(
        determination=DecisionInitiationDetermination.EXPLICIT_CREATE_NEW,
        candidate_decision_ids=basis.candidate_decision_ids,
        known_at=basis.known_at,
        rationale=determination.rationale,
    )


def _replay(
    receipt: InitiationReceipt,
    request: InitiationSemanticRequest,
    operation_id: OperationId,
) -> InitiationResult:
    if receipt.request != request or receipt.operation_id != operation_id:
        raise IdempotencyConflict(receipt.operation_id)
    return replace(receipt.result, replayed=True)
