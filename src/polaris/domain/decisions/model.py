from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from polaris.domain.actors import (
    ActorAttribution,
    ContestedActorAttribution,
    KnownActorAttribution,
    UnknownActorAttribution,
)
from polaris.domain.portfolio import PortfolioId


class InvestmentDecisionError(ValueError):
    """Base class for Investment Decision semantic failures."""


class InvalidDecisionIdentity(InvestmentDecisionError):
    pass


class InvalidDecisionNeed(InvestmentDecisionError):
    pass


class InvalidDecisionSubject(InvestmentDecisionError):
    pass


class InvalidDecisionScope(InvestmentDecisionError):
    pass


class InvalidDecisionTransition(InvestmentDecisionError):
    pass


class InvalidDecisionHistory(InvestmentDecisionError):
    pass


@dataclass(frozen=True, slots=True)
class DecisionNeedAlreadyGrounded(InvestmentDecisionError):
    need_id: DecisionNeedId
    existing_decision_id: InvestmentDecisionId


@dataclass(frozen=True, slots=True)
class IndependentChoiceRequiresNewDecision(InvestmentDecisionError):
    decision_id: InvestmentDecisionId


def _uuid4(value: object, field: str) -> None:
    if type(value) is not UUID or value.version != 4:
        raise InvalidDecisionIdentity(f"{field} must be UUIDv4")


def _text(value: object, field: str, error: type[InvestmentDecisionError]) -> str:
    if not isinstance(value, str) or not value.strip():
        raise error(f"{field} must be a non-empty string")
    return value.strip()


def _aware(value: object, field: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{field} must be timezone-aware")


def _exact(value: object, expected: type[object], field: str) -> None:
    if type(value) is not expected:
        raise InvalidDecisionIdentity(f"{field} must be {expected.__name__}")


@dataclass(frozen=True, slots=True)
class InvestmentDecisionId:
    value: UUID

    def __post_init__(self) -> None:
        _uuid4(self.value, "InvestmentDecisionId.value")


@dataclass(frozen=True, slots=True)
class DecisionNeedId:
    value: UUID

    def __post_init__(self) -> None:
        _uuid4(self.value, "DecisionNeedId.value")


@dataclass(frozen=True, slots=True)
class DecisionLifecycleFactId:
    value: UUID

    def __post_init__(self) -> None:
        _uuid4(self.value, "DecisionLifecycleFactId.value")


@dataclass(frozen=True, slots=True)
class OperationId:
    value: UUID

    def __post_init__(self) -> None:
        _uuid4(self.value, "OperationId.value")


@dataclass(frozen=True, slots=True, order=True)
class DecisionLifecycleSequence:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value < 1:
            raise ValueError("DecisionLifecycleSequence.value must be >= 1")


@dataclass(frozen=True, slots=True, order=True)
class DecisionVersion:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value < 1:
            raise ValueError("DecisionVersion.value must be >= 1")


@dataclass(frozen=True, slots=True)
class DecisionSubject:
    statement: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "statement",
            _text(self.statement, "DecisionSubject.statement", InvalidDecisionSubject),
        )


class DecisionScopeCompleteness(StrEnum):
    UNRESOLVED = "unresolved"
    ESTABLISHED = "established"


@dataclass(frozen=True, slots=True, init=False)
class DecisionScope:
    portfolio_ids: frozenset[PortfolioId]
    completeness: DecisionScopeCompleteness

    def __init__(
        self,
        portfolio_ids: Iterable[PortfolioId],
        completeness: DecisionScopeCompleteness,
    ) -> None:
        values = tuple(portfolio_ids)
        if any(type(value) is not PortfolioId for value in values):
            raise InvalidDecisionScope("Scope may contain only PortfolioId values")
        if len(values) != len(set(values)):
            raise InvalidDecisionScope("Scope cannot contain duplicate PortfolioIds")
        if not isinstance(completeness, DecisionScopeCompleteness):
            raise InvalidDecisionScope("Scope completeness is invalid")
        canonical = frozenset(values)
        if completeness is DecisionScopeCompleteness.ESTABLISHED and not canonical:
            raise InvalidDecisionScope(
                "Established Decision Scope must contain at least one PortfolioId"
            )
        object.__setattr__(self, "portfolio_ids", canonical)
        object.__setattr__(self, "completeness", completeness)

    @classmethod
    def unresolved(cls, *portfolio_ids: PortfolioId) -> DecisionScope:
        return cls(portfolio_ids, DecisionScopeCompleteness.UNRESOLVED)

    @classmethod
    def established(cls, *portfolio_ids: PortfolioId) -> DecisionScope:
        return cls(portfolio_ids, DecisionScopeCompleteness.ESTABLISHED)


class TriggerKind(StrEnum):
    HUMAN_REQUEST = "human_request"
    ATTENTION = "attention"
    SCHEDULED_REVIEW = "scheduled_review"
    EXTERNAL_OBSERVATION = "external_observation"
    INTERNAL_FOLLOW_UP = "internal_follow_up"


@dataclass(frozen=True, slots=True)
class TriggerProvenance:
    kind: TriggerKind
    reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, TriggerKind):
            raise TypeError("kind must be TriggerKind")
        object.__setattr__(
            self,
            "reference",
            _text(
                self.reference, "TriggerProvenance.reference", InvalidDecisionHistory
            ),
        )


class TechnicalReferenceKind(StrEnum):
    REQUEST = "request"
    WORK_ITEM = "work_item"
    MODEL_INVOCATION = "model_invocation"
    PROVIDER_CALL = "provider_call"
    ADAPTER_SOURCE_CALL = "adapter_source_call"
    TRACE = "trace"


@dataclass(frozen=True, slots=True)
class TechnicalReference:
    kind: TechnicalReferenceKind
    reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, TechnicalReferenceKind):
            raise TypeError("kind must be TechnicalReferenceKind")
        object.__setattr__(
            self,
            "reference",
            _text(
                self.reference, "TechnicalReference.reference", InvalidDecisionHistory
            ),
        )


@dataclass(frozen=True, slots=True, init=False)
class TechnicalProvenance:
    references: frozenset[TechnicalReference]

    def __init__(self, references: Iterable[TechnicalReference] = ()) -> None:
        values = tuple(references)
        if any(type(value) is not TechnicalReference for value in values):
            raise TypeError("TechnicalProvenance requires TechnicalReference values")
        if len(values) != len(set(values)):
            raise ValueError("TechnicalProvenance cannot contain duplicate references")
        object.__setattr__(self, "references", frozenset(values))


EMPTY_TECHNICAL_PROVENANCE = TechnicalProvenance()


def _actor(value: object) -> None:
    if not isinstance(
        value,
        (KnownActorAttribution, UnknownActorAttribution, ContestedActorAttribution),
    ):
        raise TypeError("actor_attribution must be a canonical Actor Attribution value")


def _known_actor(value: object) -> None:
    if type(value) is not KnownActorAttribution:
        raise InvalidDecisionTransition(
            "live Decision mutation requires known Actor Attribution"
        )


@dataclass(frozen=True, slots=True)
class DecisionNeed:
    need_id: DecisionNeedId
    statement: str
    effective_at: datetime
    recorded_at: datetime
    operation_id: OperationId
    actor_attribution: ActorAttribution
    trigger: TriggerProvenance
    technical_provenance: TechnicalProvenance = EMPTY_TECHNICAL_PROVENANCE

    def __post_init__(self) -> None:
        _exact(self.need_id, DecisionNeedId, "need_id")
        object.__setattr__(
            self,
            "statement",
            _text(self.statement, "DecisionNeed.statement", InvalidDecisionNeed),
        )
        _aware(self.effective_at, "DecisionNeed.effective_at")
        _aware(self.recorded_at, "DecisionNeed.recorded_at")
        _exact(self.operation_id, OperationId, "operation_id")
        _actor(self.actor_attribution)
        if type(self.trigger) is not TriggerProvenance:
            raise TypeError("trigger must be TriggerProvenance")
        if type(self.technical_provenance) is not TechnicalProvenance:
            raise TypeError("technical_provenance must be TechnicalProvenance")


class DecisionInitiationDetermination(StrEnum):
    NO_CANDIDATES = "no_candidates"
    EXPLICIT_CREATE_NEW = "explicit_create_new"


@dataclass(frozen=True, slots=True, init=False)
class DecisionInitiationContinuity:
    determination: DecisionInitiationDetermination
    candidate_decision_ids: frozenset[InvestmentDecisionId]
    known_at: datetime
    rationale: str | None

    def __init__(
        self,
        *,
        determination: DecisionInitiationDetermination,
        candidate_decision_ids: Iterable[InvestmentDecisionId],
        known_at: datetime,
        rationale: str | None = None,
    ) -> None:
        candidates = tuple(candidate_decision_ids)
        if not isinstance(determination, DecisionInitiationDetermination):
            raise TypeError("determination must be DecisionInitiationDetermination")
        if any(type(value) is not InvestmentDecisionId for value in candidates):
            raise InvalidDecisionIdentity(
                "candidate_decision_ids must contain InvestmentDecisionId values"
            )
        if len(candidates) != len(set(candidates)):
            raise InvalidDecisionHistory("candidate Decision IDs must be unique")
        _aware(known_at, "DecisionInitiationContinuity.known_at")
        clean = rationale.strip() if isinstance(rationale, str) else rationale
        if rationale is not None and not clean:
            raise InvalidDecisionHistory(
                "Initiation continuity rationale cannot be empty"
            )
        if (
            determination is DecisionInitiationDetermination.NO_CANDIDATES
            and candidates
        ):
            raise InvalidDecisionHistory("NO_CANDIDATES cannot contain candidates")
        if (
            determination is DecisionInitiationDetermination.EXPLICIT_CREATE_NEW
            and candidates
            and clean is None
        ):
            raise InvalidDecisionHistory(
                "EXPLICIT_CREATE_NEW with candidates requires a rationale"
            )
        object.__setattr__(self, "determination", determination)
        object.__setattr__(self, "candidate_decision_ids", frozenset(candidates))
        object.__setattr__(self, "known_at", known_at)
        object.__setattr__(self, "rationale", clean)


class DecisionContinuity(StrEnum):
    SAME_COHERENT_CHOICE = "same_coherent_choice"
    INDEPENDENT_CHOICE = "independent_choice"


@dataclass(frozen=True, slots=True)
class DecisionLifecycleFactMetadata:
    fact_id: DecisionLifecycleFactId
    decision_id: InvestmentDecisionId
    sequence: DecisionLifecycleSequence
    decision_version: DecisionVersion
    operation_id: OperationId
    actor_attribution: ActorAttribution
    trigger: TriggerProvenance
    technical_provenance: TechnicalProvenance
    effective_at: datetime
    recorded_at: datetime


@dataclass(frozen=True, slots=True)
class DecisionInitiated:
    metadata: DecisionLifecycleFactMetadata
    need: DecisionNeed
    subject: DecisionSubject
    scope: DecisionScope
    continuity: DecisionInitiationContinuity


@dataclass(frozen=True, slots=True)
class DecisionSubjectRevised:
    metadata: DecisionLifecycleFactMetadata
    subject: DecisionSubject


@dataclass(frozen=True, slots=True)
class DecisionScopeEstablished:
    metadata: DecisionLifecycleFactMetadata
    scope: DecisionScope


@dataclass(frozen=True, slots=True)
class DecisionScopeRevised:
    metadata: DecisionLifecycleFactMetadata
    scope: DecisionScope


DecisionLifecycleFact = (
    DecisionInitiated
    | DecisionSubjectRevised
    | DecisionScopeEstablished
    | DecisionScopeRevised
)


@dataclass(frozen=True, slots=True, init=False)
class InvestmentDecision:
    _history: tuple[DecisionLifecycleFact, ...]
    _subject: DecisionSubject
    _scope: DecisionScope
    _version: DecisionVersion

    def __init__(self) -> None:
        raise TypeError(
            "InvestmentDecision must be created by domain behavior or "
            "reconstruct_decision"
        )

    @classmethod
    def _from_validated(
        cls,
        history: tuple[DecisionLifecycleFact, ...],
        subject: DecisionSubject,
        scope: DecisionScope,
        version: DecisionVersion,
    ) -> InvestmentDecision:
        instance = object.__new__(cls)
        object.__setattr__(instance, "_history", history)
        object.__setattr__(instance, "_subject", subject)
        object.__setattr__(instance, "_scope", scope)
        object.__setattr__(instance, "_version", version)
        return instance

    @property
    def decision_id(self) -> InvestmentDecisionId:
        return self._history[0].metadata.decision_id

    @property
    def need(self) -> DecisionNeed:
        fact = self._history[0]
        assert isinstance(fact, DecisionInitiated)
        return fact.need

    @property
    def need_id(self) -> DecisionNeedId:
        return self.need.need_id

    @property
    def subject(self) -> DecisionSubject:
        return self._subject

    @property
    def scope(self) -> DecisionScope:
        return self._scope

    @property
    def version(self) -> DecisionVersion:
        return self._version

    @property
    def created_at(self) -> datetime:
        return self._history[0].metadata.recorded_at

    @property
    def history(self) -> tuple[DecisionLifecycleFact, ...]:
        return self._history


@dataclass(frozen=True, slots=True)
class DecisionMutationContext:
    fact_id: DecisionLifecycleFactId
    operation_id: OperationId
    actor_attribution: ActorAttribution
    trigger: TriggerProvenance
    effective_at: datetime
    recorded_at: datetime
    technical_provenance: TechnicalProvenance = EMPTY_TECHNICAL_PROVENANCE

    def __post_init__(self) -> None:
        _exact(self.fact_id, DecisionLifecycleFactId, "fact_id")
        _exact(self.operation_id, OperationId, "operation_id")
        _known_actor(self.actor_attribution)
        if type(self.trigger) is not TriggerProvenance:
            raise TypeError("trigger must be TriggerProvenance")
        if type(self.technical_provenance) is not TechnicalProvenance:
            raise TypeError("technical_provenance must be TechnicalProvenance")
        _aware(self.effective_at, "effective_at")
        _aware(self.recorded_at, "recorded_at")


def _metadata(
    decision: InvestmentDecision | None,
    decision_id: InvestmentDecisionId,
    context: DecisionMutationContext,
) -> DecisionLifecycleFactMetadata:
    sequence = (
        1 if decision is None else decision.history[-1].metadata.sequence.value + 1
    )
    version = 1 if decision is None else decision.version.value + 1
    return DecisionLifecycleFactMetadata(
        context.fact_id,
        decision_id,
        DecisionLifecycleSequence(sequence),
        DecisionVersion(version),
        context.operation_id,
        context.actor_attribution,
        context.trigger,
        context.technical_provenance,
        context.effective_at,
        context.recorded_at,
    )


def _same_choice(decision: InvestmentDecision, continuity: DecisionContinuity) -> None:
    if continuity is DecisionContinuity.INDEPENDENT_CHOICE:
        raise IndependentChoiceRequiresNewDecision(decision.decision_id)
    if continuity is not DecisionContinuity.SAME_COHERENT_CHOICE:
        raise InvalidDecisionTransition("requested change must classify continuity")


def initiate_decision(
    *,
    decision_id: InvestmentDecisionId,
    need: DecisionNeed,
    subject: DecisionSubject,
    scope: DecisionScope,
    continuity: DecisionInitiationContinuity,
    mutation: DecisionMutationContext,
    existing_decision_for_need: InvestmentDecisionId | None = None,
) -> InvestmentDecision:
    _exact(decision_id, InvestmentDecisionId, "decision_id")
    if not isinstance(need, DecisionNeed):
        raise InvalidDecisionNeed("need must be DecisionNeed")
    _known_actor(need.actor_attribution)
    if existing_decision_for_need is not None:
        _exact(
            existing_decision_for_need,
            InvestmentDecisionId,
            "existing_decision_for_need",
        )
        raise DecisionNeedAlreadyGrounded(need.need_id, existing_decision_for_need)
    fact = DecisionInitiated(
        _metadata(None, decision_id, mutation), need, subject, scope, continuity
    )
    return reconstruct_decision((fact,))


def revise_subject(
    decision: InvestmentDecision,
    *,
    subject: DecisionSubject,
    continuity: DecisionContinuity,
    mutation: DecisionMutationContext,
) -> InvestmentDecision:
    if subject == decision.subject:
        return decision
    _same_choice(decision, continuity)
    return reconstruct_decision(
        (
            *decision.history,
            DecisionSubjectRevised(
                _metadata(decision, decision.decision_id, mutation), subject
            ),
        )
    )


def establish_or_revise_scope(
    decision: InvestmentDecision,
    *,
    scope: DecisionScope,
    continuity: DecisionContinuity,
    mutation: DecisionMutationContext,
) -> InvestmentDecision:
    if scope == decision.scope:
        return decision
    _same_choice(decision, continuity)
    if _established_to_unresolved(decision.scope, scope):
        raise InvalidDecisionTransition(
            "Established Decision Scope cannot become unresolved through ordinary "
            "revision"
        )
    meta = _metadata(decision, decision.decision_id, mutation)
    fact: DecisionLifecycleFact
    if _unresolved_to_established(decision.scope, scope):
        fact = DecisionScopeEstablished(meta, scope)
    else:
        fact = DecisionScopeRevised(meta, scope)
    return reconstruct_decision((*decision.history, fact))


def reconstruct_decision(
    history: Iterable[DecisionLifecycleFact],
) -> InvestmentDecision:
    facts = tuple(history)
    initiation = _history_start(facts)
    _validate_metadata(facts, initiation.metadata.decision_id)
    subject, scope = _replay(facts, initiation)
    return InvestmentDecision._from_validated(
        facts, subject, scope, facts[-1].metadata.decision_version
    )


def _history_start(facts: tuple[DecisionLifecycleFact, ...]) -> DecisionInitiated:
    if not facts or type(facts[0]) is not DecisionInitiated:
        raise InvalidDecisionHistory(
            "Decision history must start with DecisionInitiated"
        )
    supported = (
        DecisionInitiated,
        DecisionSubjectRevised,
        DecisionScopeEstablished,
        DecisionScopeRevised,
    )
    if any(not isinstance(fact, supported) for fact in facts):
        raise InvalidDecisionHistory("Decision history contains unsupported fact type")
    initiation = facts[0]
    assert isinstance(initiation, DecisionInitiated)
    return initiation


def _validate_metadata(
    facts: tuple[DecisionLifecycleFact, ...],
    decision_id: InvestmentDecisionId,
) -> None:
    ids: set[DecisionLifecycleFactId] = set()
    previous_version = 0
    for index, fact in enumerate(facts):
        meta = fact.metadata
        _validate_meta_types(meta)
        if meta.decision_id != decision_id:
            raise InvalidDecisionHistory(
                "All lifecycle facts must reference the same Investment Decision"
            )
        if meta.fact_id in ids:
            raise InvalidDecisionHistory("Lifecycle fact IDs must be unique")
        ids.add(meta.fact_id)
        if meta.sequence.value != index + 1:
            raise InvalidDecisionHistory(
                "Lifecycle fact sequence must remain contiguous"
            )
        if index == 0 and meta.decision_version.value != 1:
            raise InvalidDecisionHistory("Decision initiation version must be 1")
        if index and meta.decision_version.value <= previous_version:
            raise InvalidDecisionHistory("Decision versions must strictly increase")
        if index and type(fact) is DecisionInitiated:
            raise InvalidDecisionHistory("Decision history may contain one initiation")
        previous_version = meta.decision_version.value


def _validate_meta_types(meta: object) -> None:
    if type(meta) is not DecisionLifecycleFactMetadata:
        raise InvalidDecisionHistory("fact metadata is invalid")
    _exact(meta.fact_id, DecisionLifecycleFactId, "fact_id")
    _exact(meta.decision_id, InvestmentDecisionId, "decision_id")
    _exact(meta.operation_id, OperationId, "operation_id")
    if type(meta.sequence) is not DecisionLifecycleSequence:
        raise InvalidDecisionHistory("sequence must be DecisionLifecycleSequence")
    if type(meta.decision_version) is not DecisionVersion:
        raise InvalidDecisionHistory("decision_version must be DecisionVersion")
    _actor(meta.actor_attribution)
    if type(meta.trigger) is not TriggerProvenance:
        raise InvalidDecisionHistory("trigger must be TriggerProvenance")
    if type(meta.technical_provenance) is not TechnicalProvenance:
        raise InvalidDecisionHistory("technical_provenance must be TechnicalProvenance")
    _aware(meta.effective_at, "effective_at")
    _aware(meta.recorded_at, "recorded_at")


def _replay(
    facts: tuple[DecisionLifecycleFact, ...],
    initiation: DecisionInitiated,
) -> tuple[DecisionSubject, DecisionScope]:
    _validate_initiation(initiation)
    subject, scope = initiation.subject, initiation.scope
    for fact in facts[1:]:
        if isinstance(fact, DecisionSubjectRevised):
            if type(fact.subject) is not DecisionSubject or fact.subject == subject:
                raise InvalidDecisionHistory("invalid or no-op Subject revision")
            subject = fact.subject
        elif isinstance(fact, DecisionScopeEstablished):
            scope = _replay_establishment(scope, fact)
        elif isinstance(fact, DecisionScopeRevised):
            scope = _replay_scope_revision(scope, fact)
    return subject, scope


def _validate_initiation(fact: DecisionInitiated) -> None:
    if type(fact.need) is not DecisionNeed:
        raise InvalidDecisionHistory("initiation need is invalid")
    if type(fact.subject) is not DecisionSubject:
        raise InvalidDecisionHistory("initiation subject is invalid")
    if type(fact.scope) is not DecisionScope:
        raise InvalidDecisionHistory("initiation scope is invalid")
    if type(fact.continuity) is not DecisionInitiationContinuity:
        raise InvalidDecisionHistory("initiation continuity is invalid")


def _replay_establishment(
    current: DecisionScope, fact: DecisionScopeEstablished
) -> DecisionScope:
    if type(fact.scope) is not DecisionScope:
        raise InvalidDecisionHistory("Scope establishment is invalid")
    if current.completeness is not DecisionScopeCompleteness.UNRESOLVED:
        raise InvalidDecisionHistory("Scope can be established only once")
    if fact.scope.completeness is not DecisionScopeCompleteness.ESTABLISHED:
        raise InvalidDecisionHistory(
            "DecisionScopeEstablished requires ESTABLISHED Scope"
        )
    return fact.scope


def _replay_scope_revision(
    current: DecisionScope, fact: DecisionScopeRevised
) -> DecisionScope:
    if type(fact.scope) is not DecisionScope or fact.scope == current:
        raise InvalidDecisionHistory("invalid or no-op Scope revision")
    if _established_to_unresolved(current, fact.scope):
        raise InvalidDecisionHistory("Established Scope cannot become unresolved")
    if _unresolved_to_established(current, fact.scope):
        raise InvalidDecisionHistory(
            "First Scope establishment must use DecisionScopeEstablished"
        )
    return fact.scope


def _established_to_unresolved(current: DecisionScope, new: DecisionScope) -> bool:
    return (
        current.completeness is DecisionScopeCompleteness.ESTABLISHED
        and new.completeness is DecisionScopeCompleteness.UNRESOLVED
    )


def _unresolved_to_established(current: DecisionScope, new: DecisionScope) -> bool:
    return (
        current.completeness is DecisionScopeCompleteness.UNRESOLVED
        and new.completeness is DecisionScopeCompleteness.ESTABLISHED
    )


@dataclass(frozen=True, slots=True)
class DecisionReconciliationRequired:
    need_id: DecisionNeedId
    decision_ids: frozenset[InvestmentDecisionId]


def find_reconciliation_requirements(
    decisions: Iterable[InvestmentDecision],
) -> tuple[DecisionReconciliationRequired, ...]:
    by_need: dict[DecisionNeedId, set[InvestmentDecisionId]] = {}
    for decision in decisions:
        by_need.setdefault(decision.need_id, set()).add(decision.decision_id)
    conflicts = (
        DecisionReconciliationRequired(need_id, frozenset(ids))
        for need_id, ids in by_need.items()
        if len(ids) > 1
    )
    return tuple(sorted(conflicts, key=lambda item: item.need_id.value.int))
