"""Application coordination for Decision renewal and relationship mutations."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Never, Protocol
from uuid import UUID, uuid4

from polaris.domain.actors import KnownActorAttribution
from polaris.domain.decisions import (
    DecisionInitiationContinuity,
    DecisionInitiationDetermination,
    DecisionLifecycleFactId,
    DecisionLifecycleLineageCycle,
    DecisionLifecycleLineageSafetyIndeterminate,
    DecisionMutationContext,
    DecisionNeed,
    DecisionNeedId,
    DecisionRelationshipAdmissionRejected,
    DecisionRelationshipCorrectionBasis,
    DecisionRelationshipCorrectionEffect,
    DecisionRelationshipFactId,
    DecisionRelationshipHistoryFact,
    DecisionRelationshipMutationContext,
    DecisionRelationshipType,
    DecisionScope,
    DecisionSubject,
    DecisionVersion,
    InvalidDecisionRelationshipBasis,
    InvalidDecisionRelationshipHistory,
    InvalidDecisionTransition,
    InvestmentDecision,
    InvestmentDecisionId,
    OperationId,
    RenewedFromRelationshipBasis,
    SupersedesRelationshipBasis,
    TriggerProvenance,
    apply_relationship_command,
    relationship_correction,
    relationship_fact,
    renew_decision,
)

from .contracts import (
    ConcurrencyConflict,
    ContinuityAmbiguous,
    ContinuityCandidateBasis,
    ContinuityConflict,
    ContinuityDetermination,
    ContinuityDeterminationKind,
    DecisionCommandEnvelope,
    DecisionMemoryReader,
    IdempotencyConflict,
    InvalidDecisionCommand,
    PersistenceUnavailable,
    RelationshipConflict,
    RelationshipCycle,
    RelationshipCycleSafetyIndeterminate,
    RelationshipHistoryInvalidOrIncomplete,
)


@dataclass(frozen=True, slots=True)
class RenewalPredecessor:
    decision_id: InvestmentDecisionId
    basis: RenewedFromRelationshipBasis


# duplicate-code: renewal and initiation accept parallel choice inputs but own different
# identity/relationship transactions; sharing a command/base would couple those public
# operations and their validation rules.
# arid: disable
@dataclass(frozen=True, slots=True)
class RenewDecisionCommand:
    envelope: DecisionCommandEnvelope
    need_statement: str
    subject: DecisionSubject
    scope: DecisionScope
    predecessors: tuple[RenewalPredecessor, ...]
    continuity: ContinuityDetermination | None = None

    def __post_init__(self) -> None:
        _known_actor(self.envelope)
        if self.envelope.expected_versions == frozenset():
            raise InvalidDecisionCommand(
                "renewal requires predecessor expected versions"
            )
        if not isinstance(self.need_statement, str) or not self.need_statement.strip():
            raise InvalidDecisionCommand("need_statement must be a non-empty string")
        if type(self.subject) is not DecisionSubject:
            raise TypeError("subject must be DecisionSubject")
        if type(self.scope) is not DecisionScope:
            raise TypeError("scope must be DecisionScope")
        if not self.predecessors:
            raise InvalidDecisionCommand("renewal requires at least one predecessor")
        if len({item.decision_id for item in self.predecessors}) != len(
            self.predecessors
        ):
            raise InvalidDecisionCommand("renewal predecessors must be unique")
        object.__setattr__(self, "need_statement", self.need_statement.strip())


# arid: enable


@dataclass(frozen=True, slots=True)
class SupersessionTarget:
    decision_id: InvestmentDecisionId
    basis: SupersedesRelationshipBasis
    effective_at: datetime

    def __post_init__(self) -> None:
        if type(self.decision_id) is not InvestmentDecisionId:
            raise TypeError("decision_id must be InvestmentDecisionId")
        if type(self.basis) is not SupersedesRelationshipBasis:
            raise TypeError("basis must be SupersedesRelationshipBasis")
        _aware(self.effective_at, "effective_at")


@dataclass(frozen=True, slots=True)
class EstablishSupersessionCommand:
    envelope: DecisionCommandEnvelope
    source_decision_id: InvestmentDecisionId
    targets: tuple[SupersessionTarget, ...]

    def __post_init__(self) -> None:
        _known_actor(self.envelope)
        if type(self.source_decision_id) is not InvestmentDecisionId:
            raise TypeError("source_decision_id must be InvestmentDecisionId")
        if not self.targets:
            raise InvalidDecisionCommand("Supersession requires at least one target")
        if len({item.decision_id for item in self.targets}) != len(self.targets):
            raise InvalidDecisionCommand("Supersession targets must be unique")
        required = {
            self.source_decision_id,
            *(item.decision_id for item in self.targets),
        }
        if set(_expected_versions(self.envelope)) != required:
            raise InvalidDecisionCommand(
                "Supersession requires expected versions for source and every target"
            )


# duplicate-code: relationship correction input and persisted payload intentionally
# carry parallel fields while remaining separate validation and idempotency contracts;
# sharing their model would collapse that boundary.
# arid: disable
@dataclass(frozen=True, slots=True)
class CorrectDecisionRelationshipCommand:
    envelope: DecisionCommandEnvelope
    target_relationship_fact_id: DecisionRelationshipFactId
    effect: DecisionRelationshipCorrectionEffect
    correction_effective_at: datetime
    correction_basis: DecisionRelationshipCorrectionBasis
    replacement_relationship_effective_at: datetime | None = None
    replacement_relationship_basis: (
        RenewedFromRelationshipBasis | SupersedesRelationshipBasis | None
    ) = None

    def __post_init__(self) -> None:
        _known_actor(self.envelope)
        if type(self.target_relationship_fact_id) is not DecisionRelationshipFactId:
            raise TypeError(
                "target_relationship_fact_id must be DecisionRelationshipFactId"
            )
        if type(self.effect) is not DecisionRelationshipCorrectionEffect:
            raise TypeError("effect must be DecisionRelationshipCorrectionEffect")
        _aware(self.correction_effective_at, "correction_effective_at")
        if type(self.correction_basis) is not DecisionRelationshipCorrectionBasis:
            raise TypeError(
                "correction_basis must be DecisionRelationshipCorrectionBasis"
            )
        _expected_versions(self.envelope)


class DecisionRelationshipCommandKind(StrEnum):
    RENEW = "renew"
    ESTABLISH_SUPERSESSION = "establish_supersession"
    CORRECT_RELATIONSHIP = "correct_relationship"


@dataclass(frozen=True, slots=True)
class RenewalPayload:
    need_statement: str
    subject: DecisionSubject
    scope: DecisionScope
    predecessors: tuple[RenewalPredecessor, ...]
    continuity: ContinuityDetermination | None


@dataclass(frozen=True, slots=True)
class SupersessionPayload:
    source_decision_id: InvestmentDecisionId
    targets: tuple[SupersessionTarget, ...]


@dataclass(frozen=True, slots=True)
class RelationshipCorrectionPayload:
    target_relationship_fact_id: DecisionRelationshipFactId
    effect: DecisionRelationshipCorrectionEffect
    correction_effective_at: datetime
    correction_basis: DecisionRelationshipCorrectionBasis
    replacement_relationship_effective_at: datetime | None
    replacement_relationship_basis: (
        RenewedFromRelationshipBasis | SupersedesRelationshipBasis | None
    )


# arid: enable


RelationshipPayload = (
    RenewalPayload | SupersessionPayload | RelationshipCorrectionPayload
)


@dataclass(frozen=True, slots=True)
class DecisionRelationshipSemanticRequest:
    kind: DecisionRelationshipCommandKind
    actor_attribution: KnownActorAttribution
    trigger: TriggerProvenance
    effective_at: datetime
    expected_versions: frozenset[tuple[InvestmentDecisionId, DecisionVersion]]
    payload: RelationshipPayload


@dataclass(frozen=True, slots=True)
class DecisionRelationshipResult:
    relationship_fact_ids: tuple[DecisionRelationshipFactId, ...]
    versioned_decision_ids: frozenset[InvestmentDecisionId]
    new_decision_id: InvestmentDecisionId | None = None
    need_id: DecisionNeedId | None = None
    replayed: bool = False


@dataclass(frozen=True, slots=True)
class DecisionRelationshipReceipt:
    operation_id: OperationId
    request: DecisionRelationshipSemanticRequest
    result: DecisionRelationshipResult


@dataclass(frozen=True, slots=True)
class DecisionRelationshipState:
    history: tuple[DecisionRelationshipHistoryFact, ...]
    decisions: Mapping[InvestmentDecisionId, InvestmentDecision]


@dataclass(frozen=True, slots=True)
class DecisionRelationshipCommit:
    operation_id: OperationId
    request: DecisionRelationshipSemanticRequest
    expected_relationship_history: tuple[DecisionRelationshipHistoryFact, ...]
    expected_versions: frozenset[tuple[InvestmentDecisionId, DecisionVersion]]
    expected_decisions: tuple[InvestmentDecision, ...]
    candidate_basis: ContinuityCandidateBasis | None
    history: tuple[DecisionRelationshipHistoryFact, ...]
    updated_decisions: tuple[InvestmentDecision, ...]
    result: DecisionRelationshipResult


@dataclass(frozen=True, slots=True)
class DecisionRelationshipCommitted:
    receipt: DecisionRelationshipReceipt


@dataclass(frozen=True, slots=True)
class DecisionRelationshipReplayed:
    receipt: DecisionRelationshipReceipt


@dataclass(frozen=True, slots=True)
class DecisionRelationshipIdempotencyConflict:
    operation_id: OperationId


@dataclass(frozen=True, slots=True)
class DecisionRelationshipConcurrencyConflict:
    reason: str


@dataclass(frozen=True, slots=True)
class DecisionRelationshipContinuityConflict:
    candidate_decision_ids: frozenset[InvestmentDecisionId]


@dataclass(frozen=True, slots=True)
class DecisionRelationshipRevalidationConflict:
    reason: str


@dataclass(frozen=True, slots=True)
class DecisionRelationshipUnavailable:
    reason: str


DecisionRelationshipCommitOutcome = (
    DecisionRelationshipCommitted
    | DecisionRelationshipReplayed
    | DecisionRelationshipIdempotencyConflict
    | DecisionRelationshipConcurrencyConflict
    | DecisionRelationshipContinuityConflict
    | DecisionRelationshipRevalidationConflict
    | DecisionRelationshipUnavailable
)


class DecisionRelationshipStore(Protocol):
    async def get_relationship_receipt(
        self, operation_id: OperationId
    ) -> DecisionRelationshipReceipt | None: ...

    async def load_relationship_state(
        self, *, known_at: datetime
    ) -> DecisionRelationshipState: ...

    async def commit_relationship(
        self, commit: DecisionRelationshipCommit
    ) -> DecisionRelationshipCommitOutcome: ...


# duplicate-code: renewal has a continuity/Need transaction distinct from initiation and
# Supersession; retaining its explicit orchestration keeps the different atomic domain
# call and candidate-basis semantics visible.
# arid: disable
class DecisionRelationshipService:
    def __init__(
        self,
        *,
        reader: DecisionMemoryReader,
        store: DecisionRelationshipStore,
        now: Callable[[], datetime] | None = None,
        new_uuid: Callable[[], UUID] | None = None,
    ) -> None:
        self._reader = reader
        self._store = store
        self._now = now or (lambda: datetime.now(UTC))
        self._new_uuid = new_uuid or uuid4

    async def renew(self, command: RenewDecisionCommand) -> DecisionRelationshipResult:
        request = _request(command)
        prior = await self._store.get_relationship_receipt(
            command.envelope.operation_id
        )
        if prior is not None:
            return _replay(prior, request, command.envelope.operation_id)
        recorded_at = _recording_time(self._now())
        state = await self._store.load_relationship_state(known_at=recorded_at)
        candidate_ids = frozenset(
            await self._reader.find_unresolved_continuity_candidates(
                known_at=recorded_at
            )
        )
        candidate_basis = ContinuityCandidateBasis(candidate_ids, recorded_at)
        continuity = _renewal_continuity(command.continuity, candidate_ids, recorded_at)
        predecessor_ids = {item.decision_id for item in command.predecessors}
        decisions = _required_decisions(state, predecessor_ids)
        expected = _expected_versions(command.envelope)
        if set(expected) != predecessor_ids:
            raise InvalidDecisionCommand(
                "renewal requires expected versions for every predecessor and no others"
            )
        _require_versions(decisions, expected)

        decision_id = InvestmentDecisionId(self._new_uuid())
        need_id = DecisionNeedId(self._new_uuid())
        need = DecisionNeed(
            need_id=need_id,
            statement=command.need_statement,
            effective_at=command.envelope.effective_at,
            recorded_at=recorded_at,
            operation_id=command.envelope.operation_id,
            actor_attribution=command.envelope.actor_attribution,
            trigger=command.envelope.trigger,
            technical_provenance=command.envelope.technical_provenance,
        )
        initiation = DecisionMutationContext(
            fact_id=DecisionLifecycleFactId(self._new_uuid()),
            operation_id=command.envelope.operation_id,
            actor_attribution=command.envelope.actor_attribution,
            trigger=command.envelope.trigger,
            effective_at=command.envelope.effective_at,
            recorded_at=recorded_at,
            technical_provenance=command.envelope.technical_provenance,
        )
        facts = tuple(
            relationship_fact(
                source_decision_id=decision_id,
                target_decision_id=item.decision_id,
                relationship_type=DecisionRelationshipType.RENEWED_FROM,
                relationship_effective_at=command.envelope.effective_at,
                relationship_basis=item.basis,
                mutation=_relationship_mutation(
                    command.envelope, recorded_at, self._new_uuid
                ),
            )
            for item in command.predecessors
        )
        try:
            renewal = renew_decision(
                existing_relationship_history=state.history,
                renewal_facts=facts,
                predecessor_decisions=decisions.values(),
                decision_id=decision_id,
                need=need,
                subject=command.subject,
                scope=command.scope,
                continuity=continuity,
                initiation_mutation=initiation,
                expected_versions=expected,
            )
        except _RELATIONSHIP_ERRORS as error:
            _raise_relationship_error(error)
        result = DecisionRelationshipResult(
            tuple(fact.metadata.relationship_fact_id for fact in facts),
            renewal.relationship_result.versioned_decision_ids,
            new_decision_id=decision_id,
            need_id=need_id,
        )
        return await _commit_relationship(
            self._store,
            command.envelope.operation_id,
            request,
            state,
            expected,
            candidate_basis,
            renewal.relationship_result.history,
            renewal.relationship_result.updated_decisions,
            result,
        )

    # arid: enable

    # duplicate-code: Supersession shares transaction mechanics already centralized in
    # _commit_relationship, while its remaining multi-target topology must stay
    # explicit.
    # arid: disable
    async def establish_supersession(
        self, command: EstablishSupersessionCommand
    ) -> DecisionRelationshipResult:
        request = _request(command)
        prior = await self._store.get_relationship_receipt(
            command.envelope.operation_id
        )
        if prior is not None:
            return _replay(prior, request, command.envelope.operation_id)
        recorded_at = _recording_time(self._now())
        state = await self._store.load_relationship_state(known_at=recorded_at)
        ids = {
            command.source_decision_id,
            *(item.decision_id for item in command.targets),
        }
        decisions = _required_decisions(state, ids)
        expected = _expected_versions(command.envelope)
        _require_versions(decisions, expected)
        facts = tuple(
            relationship_fact(
                source_decision_id=command.source_decision_id,
                target_decision_id=item.decision_id,
                relationship_type=DecisionRelationshipType.SUPERSEDES,
                relationship_effective_at=item.effective_at,
                relationship_basis=item.basis,
                mutation=_relationship_mutation(
                    command.envelope, recorded_at, self._new_uuid
                ),
            )
            for item in command.targets
        )
        try:
            applied = apply_relationship_command(
                state.history,
                facts,
                decisions=decisions,
                expected_versions=expected,
                recording_boundary=recorded_at,
            )
        except _RELATIONSHIP_ERRORS as error:
            _raise_relationship_error(error)
        result = DecisionRelationshipResult(
            tuple(fact.metadata.relationship_fact_id for fact in facts),
            applied.versioned_decision_ids,
        )
        return await _commit_relationship(
            self._store,
            command.envelope.operation_id,
            request,
            state,
            expected,
            None,
            applied.history,
            applied.updated_decisions,
            result,
        )

    # arid: enable


# duplicate-code: privileged relationship correction shares the store protocol but not
# ordinary relationship admission semantics; a generic service template would obscure
# that authority boundary.
# arid: disable
class DecisionRelationshipCorrectionService:
    """Privileged append-only relationship correction coordinator."""

    def __init__(
        self,
        *,
        store: DecisionRelationshipStore,
        now: Callable[[], datetime] | None = None,
        new_uuid: Callable[[], UUID] | None = None,
    ) -> None:
        self._store = store
        self._now = now or (lambda: datetime.now(UTC))
        self._new_uuid = new_uuid or uuid4

    async def correct(
        self, command: CorrectDecisionRelationshipCommand
    ) -> DecisionRelationshipResult:
        request = _request(command)
        prior = await self._store.get_relationship_receipt(
            command.envelope.operation_id
        )
        if prior is not None:
            return _replay(prior, request, command.envelope.operation_id)
        recorded_at = _recording_time(self._now())
        state = await self._store.load_relationship_state(known_at=recorded_at)
        expected = _expected_versions(command.envelope)
        correction = relationship_correction(
            target_relationship_fact_id=command.target_relationship_fact_id,
            effect=command.effect,
            correction_effective_at=command.correction_effective_at,
            correction_basis=command.correction_basis,
            replacement_relationship_effective_at=(
                command.replacement_relationship_effective_at
            ),
            replacement_relationship_basis=command.replacement_relationship_basis,
            mutation=_relationship_mutation(
                command.envelope, recorded_at, self._new_uuid
            ),
        )
        try:
            applied = apply_relationship_command(
                state.history,
                (correction,),
                decisions=state.decisions,
                expected_versions=expected,
                recording_boundary=recorded_at,
            )
        except _RELATIONSHIP_ERRORS as error:
            _raise_relationship_error(error)
        result = DecisionRelationshipResult(
            (correction.metadata.relationship_fact_id,),
            applied.versioned_decision_ids,
        )
        return await _commit_relationship(
            self._store,
            command.envelope.operation_id,
            request,
            state,
            expected,
            None,
            applied.history,
            applied.updated_decisions,
            result,
        )


# arid: enable


async def _commit_relationship(
    store: DecisionRelationshipStore,
    operation_id: OperationId,
    request: DecisionRelationshipSemanticRequest,
    state: DecisionRelationshipState,
    expected: Mapping[InvestmentDecisionId, DecisionVersion],
    candidate_basis: ContinuityCandidateBasis | None,
    history: tuple[DecisionRelationshipHistoryFact, ...],
    decisions: tuple[InvestmentDecision, ...],
    result: DecisionRelationshipResult,
) -> DecisionRelationshipResult:
    outcome = await store.commit_relationship(
        DecisionRelationshipCommit(
            operation_id=operation_id,
            request=request,
            expected_relationship_history=state.history,
            expected_versions=frozenset(expected.items()),
            expected_decisions=tuple(
                sorted(
                    (state.decisions[identity] for identity in expected),
                    key=lambda decision: str(decision.decision_id.value),
                )
            ),
            candidate_basis=candidate_basis,
            history=history,
            updated_decisions=decisions,
            result=result,
        )
    )
    if isinstance(outcome, DecisionRelationshipCommitted):
        return outcome.receipt.result
    if isinstance(outcome, DecisionRelationshipReplayed):
        return _replay(outcome.receipt, request, operation_id)
    if isinstance(outcome, DecisionRelationshipIdempotencyConflict):
        raise IdempotencyConflict(outcome.operation_id)
    if isinstance(outcome, DecisionRelationshipConcurrencyConflict):
        raise ConcurrencyConflict(outcome.reason)
    if isinstance(outcome, DecisionRelationshipContinuityConflict):
        raise ContinuityConflict(outcome.candidate_decision_ids)
    if isinstance(outcome, DecisionRelationshipRevalidationConflict):
        raise RelationshipConflict(outcome.reason)
    if isinstance(outcome, DecisionRelationshipUnavailable):
        raise PersistenceUnavailable(outcome.reason)
    raise AssertionError("DecisionRelationshipStore returned unsupported outcome")


_RELATIONSHIP_ERRORS = (
    DecisionRelationshipAdmissionRejected,
    DecisionLifecycleLineageCycle,
    DecisionLifecycleLineageSafetyIndeterminate,
    InvalidDecisionRelationshipBasis,
    InvalidDecisionRelationshipHistory,
    InvalidDecisionTransition,
)


def _raise_relationship_error(error: Exception) -> Never:
    if isinstance(error, DecisionLifecycleLineageCycle):
        raise RelationshipCycle(str(error)) from error
    if isinstance(error, DecisionLifecycleLineageSafetyIndeterminate):
        raise RelationshipCycleSafetyIndeterminate(str(error)) from error
    if isinstance(error, InvalidDecisionRelationshipHistory):
        raise RelationshipHistoryInvalidOrIncomplete(str(error)) from error
    if isinstance(error, InvalidDecisionTransition):
        raise ConcurrencyConflict(str(error)) from error
    raise RelationshipConflict(str(error)) from error


def _known_actor(envelope: DecisionCommandEnvelope) -> None:
    if type(envelope) is not DecisionCommandEnvelope:
        raise TypeError("envelope must be DecisionCommandEnvelope")
    if type(envelope.actor_attribution) is not KnownActorAttribution:
        raise InvalidDecisionCommand(
            "Decision relationship mutation requires known Actor Attribution"
        )


def _expected_versions(
    envelope: DecisionCommandEnvelope,
) -> dict[InvestmentDecisionId, DecisionVersion]:
    _known_actor(envelope)
    values: dict[InvestmentDecisionId, DecisionVersion] = {}
    for item in envelope.expected_versions:
        if item.decision_id in values:
            raise InvalidDecisionCommand(
                "expected_versions cannot contain multiple versions for one Decision"
            )
        values[item.decision_id] = item.version
    return values


def _required_decisions(
    state: DecisionRelationshipState,
    ids: set[InvestmentDecisionId],
) -> dict[InvestmentDecisionId, InvestmentDecision]:
    values: dict[InvestmentDecisionId, InvestmentDecision] = {}
    for identity in ids:
        decision = state.decisions.get(identity)
        if not isinstance(decision, InvestmentDecision):
            raise RelationshipConflict(f"Decision {identity.value} is unavailable")
        values[identity] = decision
    return values


def _require_versions(
    decisions: Mapping[InvestmentDecisionId, InvestmentDecision],
    expected: Mapping[InvestmentDecisionId, DecisionVersion],
) -> None:
    for identity, decision in decisions.items():
        if expected.get(identity) != decision.version:
            raise ConcurrencyConflict(
                f"expected Decision version for {identity.value} does not match"
            )


def _recording_time(value: datetime) -> datetime:
    return _aware(value, "application recording time")


def _aware(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value


def _relationship_mutation(
    envelope: DecisionCommandEnvelope,
    recorded_at: datetime,
    new_uuid: Callable[[], UUID],
) -> DecisionRelationshipMutationContext:
    return DecisionRelationshipMutationContext(
        DecisionRelationshipFactId(new_uuid()),
        envelope.operation_id,
        envelope.actor_attribution,
        envelope.trigger,
        recorded_at,
        envelope.technical_provenance,
    )


def _renewal_continuity(
    requested: ContinuityDetermination | None,
    candidate_ids: frozenset[InvestmentDecisionId],
    known_at: datetime,
) -> DecisionInitiationContinuity:
    if not candidate_ids:
        if (
            requested is not None
            and requested.kind is ContinuityDeterminationKind.CONTINUE_EXISTING
        ):
            raise ContinuityAmbiguous(candidate_ids)
        return DecisionInitiationContinuity(
            determination=DecisionInitiationDetermination.NO_CANDIDATES,
            candidate_decision_ids=(),
            known_at=known_at,
        )
    if (
        requested is None
        or requested.kind is not ContinuityDeterminationKind.CREATE_NEW
        or requested.rationale is None
    ):
        raise ContinuityAmbiguous(candidate_ids)
    return DecisionInitiationContinuity(
        determination=DecisionInitiationDetermination.EXPLICIT_CREATE_NEW,
        candidate_decision_ids=candidate_ids,
        known_at=known_at,
        rationale=requested.rationale,
    )


def _request(
    command: RenewDecisionCommand
    | EstablishSupersessionCommand
    | CorrectDecisionRelationshipCommand,
) -> DecisionRelationshipSemanticRequest:
    envelope = command.envelope
    assert type(envelope.actor_attribution) is KnownActorAttribution
    if isinstance(command, RenewDecisionCommand):
        kind = DecisionRelationshipCommandKind.RENEW
        payload: RelationshipPayload = RenewalPayload(
            command.need_statement,
            command.subject,
            command.scope,
            command.predecessors,
            command.continuity,
        )
    elif isinstance(command, EstablishSupersessionCommand):
        kind = DecisionRelationshipCommandKind.ESTABLISH_SUPERSESSION
        payload = SupersessionPayload(command.source_decision_id, command.targets)
    else:
        kind = DecisionRelationshipCommandKind.CORRECT_RELATIONSHIP
        payload = RelationshipCorrectionPayload(
            command.target_relationship_fact_id,
            command.effect,
            command.correction_effective_at,
            command.correction_basis,
            command.replacement_relationship_effective_at,
            command.replacement_relationship_basis,
        )
    expected = frozenset(_expected_versions(envelope).items())
    return DecisionRelationshipSemanticRequest(
        kind,
        envelope.actor_attribution,
        envelope.trigger,
        envelope.effective_at,
        expected,
        payload,
    )


def _replay(
    receipt: DecisionRelationshipReceipt,
    request: DecisionRelationshipSemanticRequest,
    operation_id: OperationId,
) -> DecisionRelationshipResult:
    if receipt.operation_id != operation_id or receipt.request != request:
        raise IdempotencyConflict(receipt.operation_id)
    return replace(receipt.result, replayed=True)
