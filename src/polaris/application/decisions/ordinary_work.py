from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID, uuid4

from polaris.domain.actors import KnownActorAttribution
from polaris.domain.decisions import (
    DecisionApplicability,
    DecisionApplicabilityContested,
    DecisionContinuity,
    DecisionDeferred,
    DecisionLifecycleCorrectionBasis,
    DecisionLifecycleCorrectionEffect,
    DecisionLifecycleDisposition,
    DecisionLifecycleFactId,
    DecisionMutationContext,
    DecisionNotOperative,
    DecisionScope,
    DecisionSubject,
    DecisionVersion,
    DecisionWorkControlBasis,
    ExternalResolutionBasis,
    HumanInvestmentDecisionEffect,
    IndependentChoiceRequiresNewDecision,
    InvalidDecisionBasis,
    InvalidDecisionHistory,
    InvalidDecisionTransition,
    InvestmentDecision,
    InvestmentDecisionId,
    OperationId,
    TriggerProvenance,
    TrustedHumanInvestmentDecisionBasis,
    UnsupportedDecisionNeedBasis,
    defer_decision,
    establish_or_revise_scope,
    externally_resolve_decision,
    resume_decision_work,
    revise_subject,
    substantively_resolve_decision,
    withdraw_decision_work,
)

from .contracts import (
    ConcurrencyConflict,
    DecisionApplicationError,
    DecisionCommandEnvelope,
    DecisionCommandStore,
    ExpectedDecisionVersion,
    IdempotencyConflict,
    InvalidDecisionCommand,
    LifecycleConflict,
    PersistenceUnavailable,
    RelationshipConflict,
)


@dataclass(slots=True)
class ContinuityRequired(DecisionApplicationError):
    decision_id: InvestmentDecisionId


@dataclass(slots=True)
class DecisionNotFound(DecisionApplicationError):
    decision_id: InvestmentDecisionId


class DecisionNonOperative(RelationshipConflict):
    pass


class DecisionOperativeStatusContested(RelationshipConflict):
    pass


class InvalidTrustedBasis(InvalidDecisionCommand):
    pass


def _expected_version(
    envelope: DecisionCommandEnvelope,
    decision_id: InvestmentDecisionId,
) -> ExpectedDecisionVersion:
    if type(envelope) is not DecisionCommandEnvelope:
        raise TypeError("envelope must be DecisionCommandEnvelope")
    if type(decision_id) is not InvestmentDecisionId:
        raise TypeError("decision_id must be InvestmentDecisionId")
    if type(envelope.actor_attribution) is not KnownActorAttribution:
        raise InvalidDecisionCommand(
            "Decision mutation requires known Actor Attribution"
        )
    expected = tuple(envelope.expected_versions)
    if len(expected) != 1 or expected[0].decision_id != decision_id:
        raise InvalidDecisionCommand(
            "Decision mutation requires exactly one expected version "
            "for its target Decision"
        )
    return expected[0]


@dataclass(frozen=True, slots=True)
class ReviseDecisionSubjectCommand:
    envelope: DecisionCommandEnvelope
    decision_id: InvestmentDecisionId
    subject: DecisionSubject
    continuity: DecisionContinuity

    def __post_init__(self) -> None:
        _expected_version(self.envelope, self.decision_id)
        if type(self.subject) is not DecisionSubject:
            raise TypeError("subject must be DecisionSubject")
        if type(self.continuity) is not DecisionContinuity:
            raise TypeError("continuity must be DecisionContinuity")


@dataclass(frozen=True, slots=True)
class EstablishOrReviseDecisionScopeCommand:
    envelope: DecisionCommandEnvelope
    decision_id: InvestmentDecisionId
    scope: DecisionScope
    continuity: DecisionContinuity

    def __post_init__(self) -> None:
        _expected_version(self.envelope, self.decision_id)
        if type(self.scope) is not DecisionScope:
            raise TypeError("scope must be DecisionScope")
        if type(self.continuity) is not DecisionContinuity:
            raise TypeError("continuity must be DecisionContinuity")


@dataclass(frozen=True, slots=True)
class ApplyHumanDeferralCommand:
    envelope: DecisionCommandEnvelope
    decision_id: InvestmentDecisionId
    basis: TrustedHumanInvestmentDecisionBasis

    def __post_init__(self) -> None:
        _expected_version(self.envelope, self.decision_id)
        if type(self.basis) is not TrustedHumanInvestmentDecisionBasis:
            raise InvalidTrustedBasis(
                "Deferral requires a trusted Human Investment Decision basis"
            )
        if self.basis.effect is not HumanInvestmentDecisionEffect.DEFERRING:
            raise InvalidTrustedBasis(
                "Deferral basis must have DEFERRING semantic effect"
            )


@dataclass(frozen=True, slots=True)
class ApplySubstantiveResolutionCommand:
    envelope: DecisionCommandEnvelope
    decision_id: InvestmentDecisionId
    basis: TrustedHumanInvestmentDecisionBasis

    def __post_init__(self) -> None:
        _expected_version(self.envelope, self.decision_id)
        if type(self.basis) is not TrustedHumanInvestmentDecisionBasis:
            raise InvalidTrustedBasis(
                "Substantive resolution requires a trusted Human Investment "
                "Decision basis"
            )
        if (
            self.basis.effect
            is not HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING
        ):
            raise InvalidTrustedBasis(
                "Substantive resolution basis must have "
                "SUBSTANTIVELY_RESOLVING semantic effect"
            )


@dataclass(frozen=True, slots=True)
class ApplyExternalResolutionCommand:
    envelope: DecisionCommandEnvelope
    decision_id: InvestmentDecisionId
    basis: ExternalResolutionBasis

    def __post_init__(self) -> None:
        _expected_version(self.envelope, self.decision_id)
        if type(self.basis) is not ExternalResolutionBasis:
            raise InvalidDecisionCommand(
                "External Resolution requires an ExternalResolutionBasis"
            )


@dataclass(frozen=True, slots=True)
class WithdrawDecisionWorkCommand:
    envelope: DecisionCommandEnvelope
    decision_id: InvestmentDecisionId
    basis: DecisionWorkControlBasis

    def __post_init__(self) -> None:
        _expected_version(self.envelope, self.decision_id)
        if type(self.basis) is not DecisionWorkControlBasis:
            raise InvalidDecisionCommand(
                "work withdrawal requires a DecisionWorkControlBasis"
            )


@dataclass(frozen=True, slots=True)
class ResumeDecisionWorkCommand:
    envelope: DecisionCommandEnvelope
    decision_id: InvestmentDecisionId
    basis: DecisionWorkControlBasis
    continuity: DecisionContinuity

    def __post_init__(self) -> None:
        _expected_version(self.envelope, self.decision_id)
        if type(self.basis) is not DecisionWorkControlBasis:
            raise InvalidDecisionCommand(
                "work resumption requires a DecisionWorkControlBasis"
            )
        if type(self.continuity) is not DecisionContinuity:
            raise TypeError("continuity must be DecisionContinuity")


ExistingDecisionCommand = (
    ReviseDecisionSubjectCommand
    | EstablishOrReviseDecisionScopeCommand
    | ApplyHumanDeferralCommand
    | ApplySubstantiveResolutionCommand
    | ApplyExternalResolutionCommand
    | WithdrawDecisionWorkCommand
    | ResumeDecisionWorkCommand
)


class DecisionMutationKind(StrEnum):
    REVISE_SUBJECT = "revise_subject"
    ESTABLISH_OR_REVISE_SCOPE = "establish_or_revise_scope"
    APPLY_HUMAN_DEFERRAL = "apply_human_deferral"
    APPLY_SUBSTANTIVE_RESOLUTION = "apply_substantive_resolution"
    APPLY_EXTERNAL_RESOLUTION = "apply_external_resolution"
    WITHDRAW_WORK = "withdraw_work"
    RESUME_WORK = "resume_work"
    RECORD_LIFECYCLE_CORRECTION = "record_lifecycle_correction"
    RETRACT_UNSUPPORTED_DECISION_NEED = "retract_unsupported_decision_need"


@dataclass(frozen=True, slots=True)
class SubjectRevisionPayload:
    subject: DecisionSubject
    continuity: DecisionContinuity


@dataclass(frozen=True, slots=True)
class ScopeMutationPayload:
    scope: DecisionScope
    continuity: DecisionContinuity


@dataclass(frozen=True, slots=True)
class HumanDeferralPayload:
    basis: TrustedHumanInvestmentDecisionBasis


@dataclass(frozen=True, slots=True)
class SubstantiveResolutionPayload:
    basis: TrustedHumanInvestmentDecisionBasis


@dataclass(frozen=True, slots=True)
class ExternalResolutionPayload:
    basis: ExternalResolutionBasis


@dataclass(frozen=True, slots=True)
class WorkWithdrawalPayload:
    basis: DecisionWorkControlBasis


@dataclass(frozen=True, slots=True)
class WorkResumptionPayload:
    basis: DecisionWorkControlBasis
    continuity: DecisionContinuity


@dataclass(frozen=True, slots=True)
class LifecycleCorrectionPayload:
    target_fact_id: DecisionLifecycleFactId
    effect: DecisionLifecycleCorrectionEffect
    correction_basis: DecisionLifecycleCorrectionBasis
    replacement_disposition: DecisionLifecycleDisposition | None
    replacement_basis: (
        TrustedHumanInvestmentDecisionBasis
        | ExternalResolutionBasis
        | UnsupportedDecisionNeedBasis
        | None
    )


@dataclass(frozen=True, slots=True)
class UnsupportedNeedRetractionPayload:
    correction_basis: DecisionLifecycleCorrectionBasis
    unsupported_need_basis: UnsupportedDecisionNeedBasis


DecisionMutationPayload = (
    SubjectRevisionPayload
    | ScopeMutationPayload
    | HumanDeferralPayload
    | SubstantiveResolutionPayload
    | ExternalResolutionPayload
    | WorkWithdrawalPayload
    | WorkResumptionPayload
    | LifecycleCorrectionPayload
    | UnsupportedNeedRetractionPayload
)


@dataclass(frozen=True, slots=True)
class DecisionMutationSemanticRequest:
    kind: DecisionMutationKind
    decision_id: InvestmentDecisionId
    actor_attribution: KnownActorAttribution
    trigger: TriggerProvenance
    effective_at: datetime
    expected_version: DecisionVersion
    payload: DecisionMutationPayload


class DecisionMutationResultKind(StrEnum):
    APPLIED = "applied"
    NO_OP = "no_op"


@dataclass(frozen=True, slots=True)
class DecisionMutationResult:
    decision_id: InvestmentDecisionId
    version: DecisionVersion
    kind: DecisionMutationResultKind
    replayed: bool = False


@dataclass(frozen=True, slots=True)
class DecisionMutationReceipt:
    operation_id: OperationId
    request: DecisionMutationSemanticRequest
    result: DecisionMutationResult


@dataclass(frozen=True, slots=True)
class DecisionCommandState:
    decision: InvestmentDecision
    applicability: DecisionApplicability


@dataclass(frozen=True, slots=True)
class DecisionMutationCommit:
    operation_id: OperationId
    request: DecisionMutationSemanticRequest
    expected_version: DecisionVersion
    expected_history_tail_fact_id: DecisionLifecycleFactId
    result: DecisionMutationResult
    decision: InvestmentDecision


@dataclass(frozen=True, slots=True)
class DecisionMutationCommitted:
    receipt: DecisionMutationReceipt


@dataclass(frozen=True, slots=True)
class DecisionMutationReplayed:
    receipt: DecisionMutationReceipt


@dataclass(frozen=True, slots=True)
class DecisionMutationIdempotencyConflict:
    operation_id: OperationId


@dataclass(frozen=True, slots=True)
class DecisionMutationConcurrencyConflict:
    decision_id: InvestmentDecisionId


@dataclass(frozen=True, slots=True)
class DecisionMutationUnavailable:
    reason: str


DecisionMutationCommitOutcome = (
    DecisionMutationCommitted
    | DecisionMutationReplayed
    | DecisionMutationIdempotencyConflict
    | DecisionMutationConcurrencyConflict
    | DecisionMutationUnavailable
)


class DecisionMutationStore(DecisionCommandStore, Protocol):
    async def get_mutation_receipt(
        self, operation_id: OperationId
    ) -> DecisionMutationReceipt | None: ...

    async def load_decision_for_command(
        self,
        decision_id: InvestmentDecisionId,
        *,
        known_at: datetime,
    ) -> DecisionCommandState | None: ...

    async def commit_mutation(
        self, commit: DecisionMutationCommit
    ) -> DecisionMutationCommitOutcome: ...


class DecisionOrdinaryWorkService:
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

    async def revise_subject(
        self, command: ReviseDecisionSubjectCommand
    ) -> DecisionMutationResult:
        return await self._execute(
            command,
            lambda state, mutation: revise_subject(
                state.decision,
                subject=command.subject,
                continuity=command.continuity,
                applicability=state.applicability,
                mutation=mutation,
            ),
        )

    async def establish_or_revise_scope(
        self, command: EstablishOrReviseDecisionScopeCommand
    ) -> DecisionMutationResult:
        return await self._execute(
            command,
            lambda state, mutation: establish_or_revise_scope(
                state.decision,
                scope=command.scope,
                continuity=command.continuity,
                applicability=state.applicability,
                mutation=mutation,
            ),
        )

    async def apply_human_deferral(
        self, command: ApplyHumanDeferralCommand
    ) -> DecisionMutationResult:
        return await self._execute(
            command,
            lambda state, mutation: self._defer(state, command, mutation),
        )

    async def apply_substantive_resolution(
        self, command: ApplySubstantiveResolutionCommand
    ) -> DecisionMutationResult:
        return await self._execute(
            command,
            lambda state, mutation: self._substantively_resolve(
                state,
                command,
                mutation,
            ),
        )

    async def apply_external_resolution(
        self, command: ApplyExternalResolutionCommand
    ) -> DecisionMutationResult:
        return await self._execute(
            command,
            lambda state, mutation: self._externally_resolve(
                state,
                command,
                mutation,
            ),
        )

    async def withdraw_work(
        self, command: WithdrawDecisionWorkCommand
    ) -> DecisionMutationResult:
        return await self._execute(
            command,
            lambda state, mutation: withdraw_decision_work(
                state.decision,
                basis=command.basis,
                applicability=state.applicability,
                mutation=mutation,
            ),
        )

    async def resume_work(
        self, command: ResumeDecisionWorkCommand
    ) -> DecisionMutationResult:
        return await self._execute(
            command,
            lambda state, mutation: resume_decision_work(
                state.decision,
                basis=command.basis,
                continuity=command.continuity,
                applicability=state.applicability,
                mutation=mutation,
            ),
        )

    async def _execute(
        self,
        command: ExistingDecisionCommand,
        apply: Callable[
            [DecisionCommandState, DecisionMutationContext],
            InvestmentDecision,
        ],
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

        _require_ordinary_work_admission(state)

        mutation = DecisionMutationContext(
            fact_id=DecisionLifecycleFactId(self._new_uuid()),
            operation_id=operation_id,
            actor_attribution=command.envelope.actor_attribution,
            trigger=command.envelope.trigger,
            effective_at=command.envelope.effective_at,
            recorded_at=recorded_at,
            technical_provenance=command.envelope.technical_provenance,
        )

        decision = _apply_transition(apply, state, mutation)

        result = DecisionMutationResult(
            decision_id=decision.decision_id,
            version=decision.version,
            kind=(
                DecisionMutationResultKind.NO_OP
                if decision.history == state.decision.history
                else DecisionMutationResultKind.APPLIED
            ),
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

    @staticmethod
    def _substantively_resolve(
        state: DecisionCommandState,
        command: ApplySubstantiveResolutionCommand,
        mutation: DecisionMutationContext,
    ) -> InvestmentDecision:
        _require_forward_resolution_order(state, mutation.effective_at)
        return substantively_resolve_decision(
            state.decision,
            basis=command.basis,
            applicability=state.applicability,
            mutation=mutation,
        )

    @staticmethod
    def _externally_resolve(
        state: DecisionCommandState,
        command: ApplyExternalResolutionCommand,
        mutation: DecisionMutationContext,
    ) -> InvestmentDecision:
        _require_forward_resolution_order(state, mutation.effective_at)
        return externally_resolve_decision(
            state.decision,
            basis=command.basis,
            mutation=mutation,
        )

    @staticmethod
    def _defer(
        state: DecisionCommandState,
        command: ApplyHumanDeferralCommand,
        mutation: DecisionMutationContext,
    ) -> InvestmentDecision:
        if any(
            isinstance(fact, DecisionDeferred) and fact.basis == command.basis
            for fact in state.decision.history
        ):
            raise InvalidDecisionCommand(
                "re-Deferral requires a new trusted Human Investment Decision basis"
            )
        return defer_decision(
            state.decision,
            basis=command.basis,
            applicability=state.applicability,
            mutation=mutation,
        )


def _require_forward_resolution_order(
    state: DecisionCommandState,
    effective_at: datetime,
) -> None:
    if any(
        fact.metadata.effective_at > effective_at for fact in state.decision.history
    ):
        raise LifecycleConflict(
            "late historical resolution requires append-only lifecycle correction"
        )


def _require_ordinary_work_admission(state: DecisionCommandState) -> None:
    if state.decision.disposition is not DecisionLifecycleDisposition.UNRESOLVED:
        raise LifecycleConflict("resolved Decision cannot receive ordinary work")
    if state.applicability is DecisionApplicability.CONTESTED:
        raise DecisionOperativeStatusContested(
            "ordinary Decision work requires determinate operative applicability"
        )
    if state.applicability is DecisionApplicability.NON_OPERATIVE:
        raise DecisionNonOperative("ordinary Decision work requires operative status")
    if state.applicability is not DecisionApplicability.OPERATIVE:
        raise RelationshipConflict("Decision applicability is invalid")


def _apply_transition(
    apply: Callable[
        [DecisionCommandState, DecisionMutationContext],
        InvestmentDecision,
    ],
    state: DecisionCommandState,
    mutation: DecisionMutationContext,
) -> InvestmentDecision:
    try:
        return apply(state, mutation)
    except IndependentChoiceRequiresNewDecision as error:
        raise ContinuityRequired(error.decision_id) from error
    except DecisionApplicabilityContested as error:
        raise DecisionOperativeStatusContested(str(error)) from error
    except DecisionNotOperative as error:
        raise DecisionNonOperative(str(error)) from error
    except InvalidDecisionBasis as error:
        raise InvalidTrustedBasis(str(error)) from error
    except (InvalidDecisionTransition, InvalidDecisionHistory) as error:
        raise LifecycleConflict(str(error)) from error


def _translate_commit_outcome(
    outcome: DecisionMutationCommitOutcome,
    request: DecisionMutationSemanticRequest,
    operation_id: OperationId,
) -> DecisionMutationResult:
    if isinstance(outcome, DecisionMutationCommitted):
        return outcome.receipt.result
    if isinstance(outcome, DecisionMutationReplayed):
        return _replay(outcome.receipt, request, operation_id)
    if isinstance(outcome, DecisionMutationIdempotencyConflict):
        raise IdempotencyConflict(outcome.operation_id)
    if isinstance(outcome, DecisionMutationConcurrencyConflict):
        raise ConcurrencyConflict(
            f"Decision {outcome.decision_id.value} changed before commit"
        )
    if isinstance(outcome, DecisionMutationUnavailable):
        raise PersistenceUnavailable(outcome.reason)
    raise AssertionError("Decision store returned an unsupported mutation outcome")


def _recording_time(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("application recording time must be timezone-aware")
    return value


def _semantic_request(
    command: ExistingDecisionCommand,
) -> DecisionMutationSemanticRequest:
    expected = _expected_version(command.envelope, command.decision_id)
    if isinstance(command, ReviseDecisionSubjectCommand):
        kind = DecisionMutationKind.REVISE_SUBJECT
        payload: DecisionMutationPayload = SubjectRevisionPayload(
            command.subject,
            command.continuity,
        )
    elif isinstance(command, EstablishOrReviseDecisionScopeCommand):
        kind = DecisionMutationKind.ESTABLISH_OR_REVISE_SCOPE
        payload = ScopeMutationPayload(command.scope, command.continuity)
    elif isinstance(command, ApplyHumanDeferralCommand):
        kind = DecisionMutationKind.APPLY_HUMAN_DEFERRAL
        payload = HumanDeferralPayload(command.basis)
    elif isinstance(command, ApplySubstantiveResolutionCommand):
        kind = DecisionMutationKind.APPLY_SUBSTANTIVE_RESOLUTION
        payload = SubstantiveResolutionPayload(command.basis)
    elif isinstance(command, ApplyExternalResolutionCommand):
        kind = DecisionMutationKind.APPLY_EXTERNAL_RESOLUTION
        payload = ExternalResolutionPayload(command.basis)
    elif isinstance(command, WithdrawDecisionWorkCommand):
        kind = DecisionMutationKind.WITHDRAW_WORK
        payload = WorkWithdrawalPayload(command.basis)
    else:
        kind = DecisionMutationKind.RESUME_WORK
        payload = WorkResumptionPayload(command.basis, command.continuity)

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


def _replay(
    receipt: DecisionMutationReceipt,
    request: DecisionMutationSemanticRequest,
    operation_id: OperationId,
) -> DecisionMutationResult:
    if receipt.request != request or receipt.operation_id != operation_id:
        raise IdempotencyConflict(receipt.operation_id)
    return replace(receipt.result, replayed=True)
