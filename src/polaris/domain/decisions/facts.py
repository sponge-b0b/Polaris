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


class InvalidDecisionBasis(InvestmentDecisionError):
    pass


class DecisionNotOperative(InvalidDecisionTransition):
    pass


class DecisionApplicabilityContested(InvalidDecisionTransition):
    pass


class DecisionNotKnownAtCutoff(InvestmentDecisionError):
    pass


class DecisionLifecycleNotYetEffective(InvalidDecisionTransition):
    pass


class DecisionLifecycleInterpretationContested(InvalidDecisionTransition):
    pass


class InvalidDecisionLifecycleCorrection(InvalidDecisionHistory):
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


def _history_reference(value: object, field: str) -> str:
    return _text(value, field, InvalidDecisionHistory)


def _basis_reference(value: object, field: str) -> str:
    return _text(value, field, InvalidDecisionBasis)


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
            _history_reference(self.reference, "TriggerProvenance.reference"),
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
            _history_reference(self.reference, "TechnicalReference.reference"),
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


def _validate_provenance(
    trigger: object,
    technical_provenance: object,
) -> None:
    if type(trigger) is not TriggerProvenance:
        raise TypeError("trigger must be TriggerProvenance")
    if type(technical_provenance) is not TechnicalProvenance:
        raise TypeError("technical_provenance must be TechnicalProvenance")


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
        _validate_provenance(self.trigger, self.technical_provenance)


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


class DecisionLifecycleDisposition(StrEnum):
    UNRESOLVED = "unresolved"
    SUBSTANTIVELY_RESOLVED = "substantively_resolved"
    EXTERNALLY_RESOLVED = "externally_resolved"
    NEED_RETRACTED_UNSUPPORTED = "need_retracted_unsupported"


class DecisionWorkPosture(StrEnum):
    ACTIVE = "active"
    DEFERRED = "deferred"
    WITHDRAWN = "withdrawn"


class DecisionApplicability(StrEnum):
    OPERATIVE = "operative"
    NON_OPERATIVE = "non_operative"
    CONTESTED = "contested"


class HumanInvestmentDecisionEffect(StrEnum):
    DEFERRING = "deferring"
    SUBSTANTIVELY_RESOLVING = "substantively_resolving"


@dataclass(frozen=True, slots=True)
class TrustedHumanInvestmentDecisionBasis:
    decision_reference: str
    effect: HumanInvestmentDecisionEffect

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "decision_reference",
            _basis_reference(
                self.decision_reference,
                "TrustedHumanInvestmentDecisionBasis.decision_reference",
            ),
        )
        if not isinstance(self.effect, HumanInvestmentDecisionEffect):
            raise InvalidDecisionBasis(
                "Trusted Human Investment Decision effect is invalid"
            )


# duplicate-code: these simple basis values share normalization but remain separate
# purpose-specific domain types; a common base would weaken their type distinction
# without removing any duplicated behavior.
# arid: disable
@dataclass(frozen=True, slots=True)
class DecisionWorkControlBasis:
    reference: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reference",
            _basis_reference(self.reference, "DecisionWorkControlBasis.reference"),
        )


@dataclass(frozen=True, slots=True)
class ExternalResolutionBasis:
    reference: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reference",
            _basis_reference(self.reference, "ExternalResolutionBasis.reference"),
        )


# arid: enable


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


@dataclass(frozen=True, slots=True)
class DecisionDeferred:
    metadata: DecisionLifecycleFactMetadata
    basis: TrustedHumanInvestmentDecisionBasis


@dataclass(frozen=True, slots=True)
class DecisionWorkWithdrawn:
    metadata: DecisionLifecycleFactMetadata
    basis: DecisionWorkControlBasis


@dataclass(frozen=True, slots=True)
class DecisionWorkResumed:
    metadata: DecisionLifecycleFactMetadata
    basis: DecisionWorkControlBasis


@dataclass(frozen=True, slots=True)
class DecisionSubstantivelyResolved:
    metadata: DecisionLifecycleFactMetadata
    basis: TrustedHumanInvestmentDecisionBasis


@dataclass(frozen=True, slots=True)
class DecisionExternallyResolved:
    metadata: DecisionLifecycleFactMetadata
    basis: ExternalResolutionBasis


class DecisionLifecycleCorrectionEffect(StrEnum):
    QUALIFY = "qualify"
    DISCONFIRM = "disconfirm"


# duplicate-code: correction and unsupported-Need bases are intentionally distinct
# semantic evidence types; both already reuse the shared basis-reference validator, so
# inheritance would only couple their identities.
# arid: disable
@dataclass(frozen=True, slots=True)
class DecisionLifecycleCorrectionBasis:
    reference: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reference",
            _basis_reference(
                self.reference,
                "DecisionLifecycleCorrectionBasis.reference",
            ),
        )


@dataclass(frozen=True, slots=True)
class UnsupportedDecisionNeedBasis:
    reference: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reference",
            _basis_reference(self.reference, "UnsupportedDecisionNeedBasis.reference"),
        )


# arid: enable


@dataclass(frozen=True, slots=True)
class DecisionLifecycleCorrected:
    metadata: DecisionLifecycleFactMetadata
    target_fact_id: DecisionLifecycleFactId
    effect: DecisionLifecycleCorrectionEffect
    correction_basis: DecisionLifecycleCorrectionBasis
    replacement_disposition: DecisionLifecycleDisposition | None = None
    replacement_basis: (
        TrustedHumanInvestmentDecisionBasis
        | ExternalResolutionBasis
        | UnsupportedDecisionNeedBasis
        | None
    ) = None

    def __post_init__(self) -> None:
        _exact(self.target_fact_id, DecisionLifecycleFactId, "target_fact_id")
        if type(self.correction_basis) is not DecisionLifecycleCorrectionBasis:
            raise InvalidDecisionBasis("correction requires its own correction basis")
        if self.effect is DecisionLifecycleCorrectionEffect.DISCONFIRM:
            if (
                self.replacement_disposition is not None
                or self.replacement_basis is not None
            ):
                raise InvalidDecisionLifecycleCorrection(
                    "DISCONFIRM has no replacement"
                )
        elif self.effect is DecisionLifecycleCorrectionEffect.QUALIFY:
            _validate_replacement(self)
        else:
            raise InvalidDecisionLifecycleCorrection("invalid correction effect")


def _validate_replacement(fact: DecisionLifecycleCorrected) -> None:
    support_types = {
        DecisionLifecycleDisposition.UNRESOLVED: type(None),
        DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED: (
            TrustedHumanInvestmentDecisionBasis
        ),
        DecisionLifecycleDisposition.EXTERNALLY_RESOLVED: ExternalResolutionBasis,
        DecisionLifecycleDisposition.NEED_RETRACTED_UNSUPPORTED: (
            UnsupportedDecisionNeedBasis
        ),
    }
    if type(fact.replacement_disposition) is not DecisionLifecycleDisposition:
        raise InvalidDecisionLifecycleCorrection("QUALIFY requires a disposition")
    if type(fact.replacement_basis) is not support_types[fact.replacement_disposition]:
        raise InvalidDecisionBasis("replacement basis must match its disposition")
    if isinstance(fact.replacement_basis, TrustedHumanInvestmentDecisionBasis) and (
        fact.replacement_basis.effect
        is not HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING
    ):
        raise InvalidDecisionBasis("replacement human basis must substantively resolve")


DecisionLifecycleFact = (
    DecisionInitiated
    | DecisionSubjectRevised
    | DecisionScopeEstablished
    | DecisionScopeRevised
    | DecisionDeferred
    | DecisionWorkWithdrawn
    | DecisionWorkResumed
    | DecisionSubstantivelyResolved
    | DecisionExternallyResolved
    | DecisionLifecycleCorrected
)


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
        _validate_provenance(self.trigger, self.technical_provenance)
        _aware(self.effective_at, "effective_at")
        _aware(self.recorded_at, "recorded_at")
