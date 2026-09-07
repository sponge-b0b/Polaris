from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Iterable


class InvestmentDecisionError(Exception):
    """Base class for explicit Investment Decision semantic failures."""


@dataclass(frozen=True, slots=True)
class InvalidDecisionIdentity(InvestmentDecisionError):
    field: str
    expected_type: str

    def __str__(self) -> str:
        return f"{self.field} must be {self.expected_type}"


@dataclass(frozen=True, slots=True)
class InvalidDecisionScope(InvestmentDecisionError):
    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class DecisionNeedAlreadyGrounded(InvestmentDecisionError):
    need_id: DecisionNeedId
    existing_decision_id: InvestmentDecisionId

    def __str__(self) -> str:
        return (
            f"Decision Need {self.need_id.value!r} is already grounded by "
            f"Investment Decision {self.existing_decision_id.value!r}"
        )


@dataclass(frozen=True, slots=True)
class IndependentChoiceRequiresNewDecision(InvestmentDecisionError):
    decision_id: InvestmentDecisionId

    def __str__(self) -> str:
        return (
            f"Independent choice cannot refine Investment Decision "
            f"{self.decision_id.value!r}; create a new Decision Need and Decision"
        )


@dataclass(frozen=True, slots=True)
class InvalidDecisionHistory(InvestmentDecisionError):
    reason: str

    def __str__(self) -> str:
        return self.reason


def _require_text(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class InvestmentDecisionId:
    value: str

    def __post_init__(self) -> None:
        _require_text(self.value, "InvestmentDecisionId.value")


@dataclass(frozen=True, slots=True)
class DecisionNeedId:
    value: str

    def __post_init__(self) -> None:
        _require_text(self.value, "DecisionNeedId.value")


@dataclass(frozen=True, slots=True)
class OperationId:
    value: str

    def __post_init__(self) -> None:
        _require_text(self.value, "OperationId.value")


@dataclass(frozen=True, slots=True)
class PortfolioRef:
    value: str

    def __post_init__(self) -> None:
        _require_text(self.value, "PortfolioRef.value")


@dataclass(frozen=True, slots=True)
class DecisionSubject:
    meaning: str

    def __post_init__(self) -> None:
        _require_text(self.meaning, "DecisionSubject.meaning")


class ScopeCompleteness(StrEnum):
    UNRESOLVED = "unresolved"
    ESTABLISHED = "established"


@dataclass(frozen=True, slots=True)
class DecisionScope:
    portfolios: tuple[PortfolioRef, ...]
    completeness: ScopeCompleteness

    def __post_init__(self) -> None:
        if not isinstance(self.portfolios, tuple):
            raise InvalidDecisionScope("Scope Portfolios must be an immutable tuple")
        if not isinstance(self.completeness, ScopeCompleteness):
            raise InvalidDecisionScope("Scope completeness is invalid")
        if any(
            not isinstance(portfolio, PortfolioRef) for portfolio in self.portfolios
        ):
            raise InvalidDecisionScope("Scope may contain only Portfolio references")
        if len(set(self.portfolios)) != len(self.portfolios):
            raise InvalidDecisionScope("Scope cannot contain duplicate Portfolios")
        if self.completeness is ScopeCompleteness.ESTABLISHED and not self.portfolios:
            raise InvalidDecisionScope(
                "Established Decision Scope must contain at least one Portfolio"
            )

    @classmethod
    def unresolved(cls, *portfolios: PortfolioRef) -> DecisionScope:
        return cls(tuple(portfolios), ScopeCompleteness.UNRESOLVED)

    @classmethod
    def established(cls, *portfolios: PortfolioRef) -> DecisionScope:
        return cls(tuple(portfolios), ScopeCompleteness.ESTABLISHED)


@dataclass(frozen=True, slots=True)
class ActorAttribution:
    kind: str
    identifier: str

    def __post_init__(self) -> None:
        _require_text(self.kind, "ActorAttribution.kind")
        _require_text(self.identifier, "ActorAttribution.identifier")


@dataclass(frozen=True, slots=True)
class TriggerProvenance:
    kind: str
    identifier: str

    def __post_init__(self) -> None:
        _require_text(self.kind, "TriggerProvenance.kind")
        _require_text(self.identifier, "TriggerProvenance.identifier")


@dataclass(frozen=True, slots=True)
class TechnicalReference:
    kind: str
    identifier: str

    def __post_init__(self) -> None:
        _require_text(self.kind, "TechnicalReference.kind")
        _require_text(self.identifier, "TechnicalReference.identifier")


@dataclass(frozen=True, slots=True)
class TechnicalProvenance:
    references: tuple[TechnicalReference, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.references, tuple):
            raise ValueError(
                "Technical provenance references must be an immutable tuple"
            )
        if any(
            not isinstance(reference, TechnicalReference)
            for reference in self.references
        ):
            raise ValueError("Technical provenance requires TechnicalReference values")


@dataclass(frozen=True, slots=True)
class BusinessBasis:
    kind: str
    identifier: str

    def __post_init__(self) -> None:
        _require_text(self.kind, "BusinessBasis.kind")
        _require_text(self.identifier, "BusinessBasis.identifier")


@dataclass(frozen=True, slots=True)
class BusinessReference:
    kind: str
    identifier: str

    def __post_init__(self) -> None:
        _require_text(self.kind, "BusinessReference.kind")
        _require_text(self.identifier, "BusinessReference.identifier")


@dataclass(frozen=True, slots=True)
class FactMetadata:
    effective_at: datetime
    recorded_at: datetime
    recorded_sequence: int
    operation_id: OperationId
    actor: ActorAttribution
    trigger: TriggerProvenance | None = None
    technical: TechnicalProvenance = TechnicalProvenance()
    business_basis: BusinessBasis | None = None
    business_reference: BusinessReference | None = None

    def __post_init__(self) -> None:
        if self.effective_at.tzinfo is None or self.effective_at.utcoffset() is None:
            raise ValueError("effective_at must be timezone-aware")
        if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() is None:
            raise ValueError("recorded_at must be timezone-aware")
        if self.recorded_sequence < 0:
            raise ValueError("recorded_sequence must be non-negative")
        if not isinstance(self.operation_id, OperationId):
            raise InvalidDecisionIdentity("operation_id", "OperationId")
        if not isinstance(self.actor, ActorAttribution):
            raise ValueError("actor must be ActorAttribution")
        if self.trigger is not None and not isinstance(self.trigger, TriggerProvenance):
            raise ValueError("trigger must be TriggerProvenance or None")
        if not isinstance(self.technical, TechnicalProvenance):
            raise ValueError("technical must be TechnicalProvenance")
        if self.business_basis is not None and not isinstance(
            self.business_basis, BusinessBasis
        ):
            raise ValueError("business_basis must be BusinessBasis or None")
        if self.business_reference is not None and not isinstance(
            self.business_reference, BusinessReference
        ):
            raise ValueError("business_reference must be BusinessReference or None")


@dataclass(frozen=True, slots=True)
class DecisionInitiated:
    decision_id: InvestmentDecisionId
    need_id: DecisionNeedId
    subject: DecisionSubject
    scope: DecisionScope
    metadata: FactMetadata

    def __post_init__(self) -> None:
        _require_identity(self.decision_id, InvestmentDecisionId, "decision_id")
        _require_identity(self.need_id, DecisionNeedId, "need_id")
        if not isinstance(self.subject, DecisionSubject):
            raise ValueError("subject must be DecisionSubject")
        if not isinstance(self.scope, DecisionScope):
            raise InvalidDecisionScope("scope must be DecisionScope")
        if not isinstance(self.metadata, FactMetadata):
            raise ValueError("metadata must be FactMetadata")


@dataclass(frozen=True, slots=True)
class DecisionSubjectRefined:
    decision_id: InvestmentDecisionId
    subject: DecisionSubject
    metadata: FactMetadata

    def __post_init__(self) -> None:
        _require_identity(self.decision_id, InvestmentDecisionId, "decision_id")
        if not isinstance(self.subject, DecisionSubject):
            raise ValueError("subject must be DecisionSubject")
        if not isinstance(self.metadata, FactMetadata):
            raise ValueError("metadata must be FactMetadata")


@dataclass(frozen=True, slots=True)
class DecisionScopeRefined:
    decision_id: InvestmentDecisionId
    scope: DecisionScope
    metadata: FactMetadata

    def __post_init__(self) -> None:
        _require_identity(self.decision_id, InvestmentDecisionId, "decision_id")
        if not isinstance(self.scope, DecisionScope):
            raise InvalidDecisionScope("scope must be DecisionScope")
        if not isinstance(self.metadata, FactMetadata):
            raise ValueError("metadata must be FactMetadata")


DecisionFact = DecisionInitiated | DecisionSubjectRefined | DecisionScopeRefined


class DecisionContinuity(StrEnum):
    SAME_COHERENT_CHOICE = "same_coherent_choice"
    INDEPENDENT_CHOICE = "independent_choice"


@dataclass(frozen=True, slots=True)
class InvestmentDecision:
    facts: tuple[DecisionFact, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.facts, tuple):
            raise InvalidDecisionHistory("Decision facts must be an immutable tuple")
        if not self.facts or not isinstance(self.facts[0], DecisionInitiated):
            raise InvalidDecisionHistory("Decision history must start with initiation")

        decision_id = self.facts[0].decision_id
        previous_sequence = -1
        for fact in self.facts:
            if fact.decision_id != decision_id:
                raise InvalidDecisionHistory(
                    "All Decision facts must reference the same Decision identity"
                )
            if fact.metadata.recorded_sequence <= previous_sequence:
                raise InvalidDecisionHistory(
                    "Decision facts must have strictly increasing recorded sequence"
                )
            previous_sequence = fact.metadata.recorded_sequence

    @property
    def _initiation(self) -> DecisionInitiated:
        initiation = self.facts[0]
        assert isinstance(initiation, DecisionInitiated)
        return initiation

    @property
    def decision_id(self) -> InvestmentDecisionId:
        return self._initiation.decision_id

    @property
    def need_id(self) -> DecisionNeedId:
        return self._initiation.need_id

    @property
    def subject(self) -> DecisionSubject:
        for fact in reversed(self.facts):
            if isinstance(fact, (DecisionInitiated, DecisionSubjectRefined)):
                return fact.subject
        raise AssertionError("validated Decision history has no Subject")

    @property
    def scope(self) -> DecisionScope:
        for fact in reversed(self.facts):
            if isinstance(fact, (DecisionInitiated, DecisionScopeRefined)):
                return fact.scope
        raise AssertionError("validated Decision history has no Scope")


def _require_identity(value: object, expected: type[object], field: str) -> None:
    if type(value) is not expected:
        raise InvalidDecisionIdentity(field, expected.__name__)


def _append_fact(
    decision: InvestmentDecision,
    fact: DecisionFact,
) -> InvestmentDecision:
    return InvestmentDecision((*decision.facts, fact))


def _require_same_choice(
    decision: InvestmentDecision,
    continuity: DecisionContinuity,
) -> None:
    if continuity is DecisionContinuity.INDEPENDENT_CHOICE:
        raise IndependentChoiceRequiresNewDecision(decision.decision_id)
    if continuity is not DecisionContinuity.SAME_COHERENT_CHOICE:
        raise ValueError("continuity must explicitly classify the requested change")


def initiate_decision(
    *,
    decision_id: InvestmentDecisionId,
    need_id: DecisionNeedId,
    subject: DecisionSubject,
    scope: DecisionScope,
    metadata: FactMetadata,
    existing_decision_for_need: InvestmentDecisionId | None = None,
) -> InvestmentDecision:
    _require_identity(decision_id, InvestmentDecisionId, "decision_id")
    _require_identity(need_id, DecisionNeedId, "need_id")
    if not isinstance(subject, DecisionSubject):
        raise ValueError("subject must be DecisionSubject")
    if not isinstance(scope, DecisionScope):
        raise InvalidDecisionScope("scope must be DecisionScope")
    if not isinstance(metadata, FactMetadata):
        raise ValueError("metadata must be FactMetadata")
    if existing_decision_for_need is not None:
        _require_identity(
            existing_decision_for_need,
            InvestmentDecisionId,
            "existing_decision_for_need",
        )
        raise DecisionNeedAlreadyGrounded(need_id, existing_decision_for_need)

    return InvestmentDecision(
        (DecisionInitiated(decision_id, need_id, subject, scope, metadata),)
    )


def refine_subject(
    decision: InvestmentDecision,
    *,
    subject: DecisionSubject,
    continuity: DecisionContinuity,
    metadata: FactMetadata,
) -> InvestmentDecision:
    _require_same_choice(decision, continuity)
    if not isinstance(subject, DecisionSubject):
        raise ValueError("subject must be DecisionSubject")
    if not isinstance(metadata, FactMetadata):
        raise ValueError("metadata must be FactMetadata")
    return _append_fact(
        decision,
        DecisionSubjectRefined(decision.decision_id, subject, metadata),
    )


def refine_scope(
    decision: InvestmentDecision,
    *,
    scope: DecisionScope,
    continuity: DecisionContinuity,
    metadata: FactMetadata,
) -> InvestmentDecision:
    _require_same_choice(decision, continuity)
    if not isinstance(scope, DecisionScope):
        raise InvalidDecisionScope("scope must be DecisionScope")
    if not isinstance(metadata, FactMetadata):
        raise ValueError("metadata must be FactMetadata")
    return _append_fact(
        decision,
        DecisionScopeRefined(decision.decision_id, scope, metadata),
    )


@dataclass(frozen=True, slots=True)
class DecisionReconciliationRequired:
    need_id: DecisionNeedId
    decision_ids: tuple[InvestmentDecisionId, ...]


def find_reconciliation_requirements(
    decisions: Iterable[InvestmentDecision],
) -> tuple[DecisionReconciliationRequired, ...]:
    by_need: dict[DecisionNeedId, list[InvestmentDecisionId]] = {}
    for decision in decisions:
        by_need.setdefault(decision.need_id, []).append(decision.decision_id)

    conflicts = []
    for need_id, decision_ids in by_need.items():
        unique_ids = tuple(
            sorted(set(decision_ids), key=lambda decision_id: decision_id.value)
        )
        if len(unique_ids) > 1:
            conflicts.append(DecisionReconciliationRequired(need_id, unique_ids))

    return tuple(sorted(conflicts, key=lambda conflict: conflict.need_id.value))
