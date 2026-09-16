"""Privileged application coordination for append-only lifecycle correction."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

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
    DecisionCommandEnvelope,
    InvalidDecisionCommand,
    LifecycleConflict,
)
from .ordinary_work import (
    DecisionCommandState,
    DecisionMutationKind,
    DecisionMutationPayload,
    DecisionMutationResult,
    DecisionMutationSemanticRequest,
    DecisionMutationStore,
    LifecycleCorrectionPayload,
    UnsupportedNeedRetractionPayload,
    _execute_mutation,
    _expected_version,
    _mutation_request,
)

# duplicate-code: correction commands and persisted mutation payloads carry parallel
# fields but remain distinct input and receipt contracts; sharing a model would collapse
# validation ownership across the transaction boundary.
# arid: disable
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


# arid: enable


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

    # duplicate-code: this privileged service intentionally forwards through the shared
    # transaction executor without inheriting ordinary-work admission semantics.
    # arid: disable
    async def _execute(
        self,
        command: LifecycleCorrectionCommand,
    ) -> DecisionMutationResult:
        return await _execute_mutation(
            store=self._store,
            command=command,
            request=_semantic_request(command),
            now=self._now,
            new_uuid=self._new_uuid,
            apply=lambda state, mutation: _apply_correction(state, command, mutation),
        )

    # arid: enable


# duplicate-code: the two correction branches keep their different target and
# replacement semantics explicit around the same canonical domain reducer; another
# generic argument builder would obscure the privileged command distinction.
# arid: disable
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


# arid: enable


def _semantic_request(
    command: LifecycleCorrectionCommand,
) -> DecisionMutationSemanticRequest:
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
    return _mutation_request(command, kind, payload)
