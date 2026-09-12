"""Privileged application coordination for append-only lifecycle correction."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from polaris.domain.actors import KnownActorAttribution
from polaris.domain.decisions import (
    DecisionInitiated,
    DecisionLifecycleCorrectionBasis,
    DecisionLifecycleCorrectionEffect,
    DecisionLifecycleDisposition,
    DecisionLifecycleFactId,
    DecisionMutationContext,
    ExternalResolutionBasis,
    InvalidDecisionBasis,
    InvalidDecisionHistory,
    InvalidDecisionLifecycleCorrection,
    InvalidDecisionTransition,
    InvestmentDecision,
    InvestmentDecisionId,
    TrustedHumanInvestmentDecisionBasis,
    UnsupportedDecisionNeedBasis,
    correct_decision_lifecycle,
)

from .contracts import (
    ConcurrencyConflict,
    DecisionCommandEnvelope,
    InvalidDecisionCommand,
    LifecycleConflict,
)
from .ordinary_work import (
    DecisionCommandState,
    DecisionMutationCommit,
    DecisionMutationKind,
    DecisionMutationPayload,
    DecisionMutationResult,
    DecisionMutationResultKind,
    DecisionMutationSemanticRequest,
    DecisionMutationStore,
    DecisionNotFound,
    LifecycleCorrectionPayload,
    UnsupportedNeedRetractionPayload,
    _expected_version,
    _recording_time,
    _replay,
    _translate_commit_outcome,
)

type ReplacementBasis = (
    TrustedHumanInvestmentDecisionBasis
    | ExternalResolutionBasis
    | UnsupportedDecisionNeedBasis
    | None
)


@dataclass(frozen=True, slots=True)
class RecordDecisionLifecycleCorrectionCommand:
    envelope: DecisionCommandEnvelope
    decision_id: InvestmentDecisionId
    target_fact_id: DecisionLifecycleFactId
    effect: DecisionLifecycleCorrectionEffect
    correction_basis: DecisionLifecycleCorrectionBasis
    replacement_disposition: DecisionLifecycleDisposition | None = None
    replacement_basis: ReplacementBasis = None

    def __post_init__(self) -> None:
        _expected_version(self.envelope, self.decision_id)
        if type(self.target_fact_id) is not DecisionLifecycleFactId:
            raise TypeError("target_fact_id must be DecisionLifecycleFactId")
        if type(self.effect) is not DecisionLifecycleCorrectionEffect:
            raise TypeError("effect must be DecisionLifecycleCorrectionEffect")
        if type(self.correction_basis) is not DecisionLifecycleCorrectionBasis:
            raise InvalidDecisionCommand(
                "lifecycle correction requires DecisionLifecycleCorrectionBasis"
            )
        if self.replacement_disposition is not None and (
            type(self.replacement_disposition) is not DecisionLifecycleDisposition
        ):
            raise TypeError(
                "replacement_disposition must be DecisionLifecycleDisposition or None"
            )
        if self.replacement_basis is not None and not isinstance(
            self.replacement_basis,
            (
                TrustedHumanInvestmentDecisionBasis,
                ExternalResolutionBasis,
                UnsupportedDecisionNeedBasis,
            ),
        ):
            raise TypeError("replacement_basis has an unsupported domain type")


@dataclass(frozen=True, slots=True)
class RetractUnsupportedDecisionNeedCommand:
    envelope: DecisionCommandEnvelope
    decision_id: InvestmentDecisionId
    correction_basis: DecisionLifecycleCorrectionBasis
    unsupported_need_basis: UnsupportedDecisionNeedBasis

    def __post_init__(self) -> None:
        _expected_version(self.envelope, self.decision_id)
        if type(self.correction_basis) is not DecisionLifecycleCorrectionBasis:
            raise InvalidDecisionCommand(
                "unsupported Need retraction requires DecisionLifecycleCorrectionBasis"
            )
        if type(self.unsupported_need_basis) is not UnsupportedDecisionNeedBasis:
            raise InvalidDecisionCommand(
                "unsupported Need retraction requires UnsupportedDecisionNeedBasis"
            )


LifecycleCorrectionCommand = (
    RecordDecisionLifecycleCorrectionCommand | RetractUnsupportedDecisionNeedCommand
)


class DecisionLifecycleCorrectionService:
    """Coordinate privileged correction without adding another lifecycle reducer."""

    def __init__(
        self,
        *,
        store: DecisionMutationStore,
        now: Callable[[], datetime] | None = None,
        new_uuid: Callable[[], UUID] | None = None,
    ) -> None:
        self._store = store
        self._now = now or (lambda: datetime.now(UTC))
        self._new_uuid = new_uuid or uuid4

    async def record_lifecycle_correction(
        self, command: RecordDecisionLifecycleCorrectionCommand
    ) -> DecisionMutationResult:
        return await self._execute(command)

    async def retract_unsupported_decision_need(
        self, command: RetractUnsupportedDecisionNeedCommand
    ) -> DecisionMutationResult:
        return await self._execute(command)

    async def _execute(
        self,
        command: LifecycleCorrectionCommand,
    ) -> DecisionMutationResult:
        request = _semantic_request(command)
        operation_id = command.envelope.operation_id
        prior = await self._store.get_mutation_receipt(operation_id)
        if prior is not None:
            return _replay(prior, request, operation_id)

        recorded_at = _recording_time(self._now())
        state = await self._store.load_decision_for_command(
            command.decision_id,
            known_at=recorded_at,
        )
        if state is None:
            raise DecisionNotFound(command.decision_id)
        if state.decision.version != request.expected_version:
            raise ConcurrencyConflict(
                f"expected Decision version {request.expected_version.value}, "
                f"found {state.decision.version.value}"
            )

        mutation = DecisionMutationContext(
            fact_id=DecisionLifecycleFactId(self._new_uuid()),
            operation_id=operation_id,
            actor_attribution=command.envelope.actor_attribution,
            trigger=command.envelope.trigger,
            effective_at=command.envelope.effective_at,
            recorded_at=recorded_at,
            technical_provenance=command.envelope.technical_provenance,
        )
        decision = _apply_correction(state, command, mutation)
        result = DecisionMutationResult(
            decision_id=decision.decision_id,
            version=decision.version,
            kind=DecisionMutationResultKind.APPLIED,
        )
        outcome = await self._store.commit_mutation(
            DecisionMutationCommit(
                operation_id=operation_id,
                request=request,
                expected_version=request.expected_version,
                expected_history_tail_fact_id=(
                    state.decision.history[-1].metadata.fact_id
                ),
                result=result,
                decision=decision,
            )
        )
        return _translate_commit_outcome(outcome, request, operation_id)


def _apply_correction(
    state: DecisionCommandState,
    command: LifecycleCorrectionCommand,
    mutation: DecisionMutationContext,
) -> InvestmentDecision:
    try:
        if isinstance(command, RecordDecisionLifecycleCorrectionCommand):
            return correct_decision_lifecycle(
                state.decision,
                target_fact_id=command.target_fact_id,
                effect=command.effect,
                correction_basis=command.correction_basis,
                replacement_disposition=command.replacement_disposition,
                replacement_basis=command.replacement_basis,
                mutation=mutation,
                applicability=state.applicability,
            )
        initiation = state.decision.history[0]
        assert isinstance(initiation, DecisionInitiated)
        return correct_decision_lifecycle(
            state.decision,
            target_fact_id=initiation.metadata.fact_id,
            effect=DecisionLifecycleCorrectionEffect.QUALIFY,
            correction_basis=command.correction_basis,
            replacement_disposition=(
                DecisionLifecycleDisposition.NEED_RETRACTED_UNSUPPORTED
            ),
            replacement_basis=command.unsupported_need_basis,
            mutation=mutation,
            applicability=state.applicability,
        )
    except InvalidDecisionBasis as error:
        raise InvalidDecisionCommand(str(error)) from error
    except (
        InvalidDecisionHistory,
        InvalidDecisionLifecycleCorrection,
        InvalidDecisionTransition,
    ) as error:
        raise LifecycleConflict(str(error)) from error


def _semantic_request(
    command: LifecycleCorrectionCommand,
) -> DecisionMutationSemanticRequest:
    expected = _expected_version(command.envelope, command.decision_id)
    payload: DecisionMutationPayload
    if isinstance(command, RecordDecisionLifecycleCorrectionCommand):
        kind = DecisionMutationKind.RECORD_LIFECYCLE_CORRECTION
        payload = LifecycleCorrectionPayload(
            target_fact_id=command.target_fact_id,
            effect=command.effect,
            correction_basis=command.correction_basis,
            replacement_disposition=command.replacement_disposition,
            replacement_basis=command.replacement_basis,
        )
    else:
        kind = DecisionMutationKind.RETRACT_UNSUPPORTED_DECISION_NEED
        payload = UnsupportedNeedRetractionPayload(
            correction_basis=command.correction_basis,
            unsupported_need_basis=command.unsupported_need_basis,
        )
    actor = command.envelope.actor_attribution
    assert type(actor) is KnownActorAttribution
    return DecisionMutationSemanticRequest(
        kind=kind,
        decision_id=command.decision_id,
        actor_attribution=actor,
        trigger=command.envelope.trigger,
        effective_at=command.envelope.effective_at,
        expected_version=expected.version,
        payload=payload,
    )
