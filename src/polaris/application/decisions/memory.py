from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from polaris.domain.decisions import (
    DecisionApplicability,
    DecisionLifecycleInterpretation,
    DecisionNeed,
    DecisionNotKnownAtCutoff,
    DecisionRelationshipBasisContribution,
    DecisionRelationshipCorrected,
    DecisionRelationshipFact,
    DecisionRelationshipFactId,
    DecisionRelationshipHistoryFact,
    DecisionRelationshipPositiveClaim,
    DecisionRelationshipState,
    DecisionRelationshipType,
    DecisionScope,
    DecisionSubject,
    DecisionVersion,
    DecisionWorkPosture,
    InvalidDecisionHistory,
    InvalidDecisionRelationshipHistory,
    InvestmentDecisionId,
    derive_relationship_applicability,
    interpret_relationship,
    reconstruct_decision,
)
from polaris.domain.decisions.facts import DecisionLifecycleFact

from .contracts import (
    DecisionApplicationError,
    DecisionMemoryReader,
    LifecycleConflict,
    PersistenceUnavailable,
    RelationshipHistoryInvalidOrIncomplete,
)
from .ordinary_work import DecisionNotFound


async def _read[T](awaitable: Awaitable[T]) -> T:
    try:
        return await awaitable
    except DecisionApplicationError:
        raise
    except Exception as error:
        raise PersistenceUnavailable("Decision Memory read is unavailable") from error


class DecisionLineageDirection(StrEnum):
    OUTGOING = "outgoing"
    INCOMING = "incoming"


@dataclass(frozen=True, slots=True)
class DecisionLineageView:
    source_decision_id: InvestmentDecisionId
    target_decision_id: InvestmentDecisionId
    relationship_type: DecisionRelationshipType
    direction: DecisionLineageDirection
    effective_at: datetime
    known_at: datetime
    state: DecisionRelationshipState
    support_fact_ids: frozenset[DecisionRelationshipFactId]
    basis_contributions: frozenset[DecisionRelationshipBasisContribution]
    surviving_positive_claims: frozenset[DecisionRelationshipPositiveClaim]
    history: tuple[DecisionRelationshipHistoryFact, ...]


@dataclass(frozen=True, slots=True)
class DecisionMemoryCurrentState:
    """One coherent persistence-neutral Decision Memory current-read snapshot."""

    lifecycle_facts: tuple[DecisionLifecycleFact, ...]
    version: DecisionVersion
    relationship_history: tuple[DecisionRelationshipHistoryFact, ...]

    def __post_init__(self) -> None:
        if type(self.version) is not DecisionVersion:
            raise TypeError("version must be DecisionVersion")
        if type(self.relationship_history) is not tuple or any(
            not isinstance(
                fact, (DecisionRelationshipFact, DecisionRelationshipCorrected)
            )
            for fact in self.relationship_history
        ):
            raise TypeError(
                "relationship_history must contain Decision relationship facts"
            )


@dataclass(frozen=True, slots=True)
class DecisionMemoryView:
    decision_id: InvestmentDecisionId
    need: DecisionNeed
    subject: DecisionSubject
    scope: DecisionScope
    lifecycle_interpretation: DecisionLifecycleInterpretation
    work_posture: DecisionWorkPosture | None
    applicability: DecisionApplicability
    version: DecisionVersion
    lineage: tuple[DecisionLineageView, ...]


@dataclass(frozen=True, slots=True)
class DecisionMemoryTemporalView:
    decision_id: InvestmentDecisionId
    need: DecisionNeed
    subject: DecisionSubject
    scope: DecisionScope
    lifecycle_interpretation: DecisionLifecycleInterpretation
    work_posture: DecisionWorkPosture | None
    applicability: DecisionApplicability
    lineage: tuple[DecisionLineageView, ...]


@dataclass(frozen=True, slots=True)
class DecisionHistoryView:
    decision_id: InvestmentDecisionId
    known_at: datetime
    lifecycle_facts: tuple[DecisionLifecycleFact, ...]
    relationship_facts: tuple[DecisionRelationshipHistoryFact, ...]


class DecisionMemoryQueryReader(DecisionMemoryReader, Protocol):
    async def load_current_decision_state(
        self,
        decision_id: InvestmentDecisionId,
        *,
        known_at: datetime,
    ) -> DecisionMemoryCurrentState | None:
        """Return lifecycle, version, and relationships from one committed snapshot."""
        ...

    async def load_decision_history(
        self, decision_id: InvestmentDecisionId
    ) -> tuple[DecisionLifecycleFact, ...] | None: ...

    async def load_relationship_history(
        self,
    ) -> tuple[DecisionRelationshipHistoryFact, ...]: ...


class DecisionMemoryService:
    def __init__(
        self,
        *,
        reader: DecisionMemoryQueryReader,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._reader = reader
        self._now = now or (lambda: datetime.now(UTC))

    async def current(self, decision_id: InvestmentDecisionId) -> DecisionMemoryView:
        _decision_id(decision_id)
        boundary = _boundary(self._now(), "now")
        current = await _read(
            self._reader.load_current_decision_state(
                decision_id,
                known_at=boundary,
            )
        )
        if current is None:
            raise DecisionNotFound(decision_id)
        relationship_history = current.relationship_history
        try:
            applicability = derive_relationship_applicability(
                decision_id,
                relationship_history,
                effective_at=boundary,
                known_at=boundary,
            )
            view = reconstruct_decision(
                current.lifecycle_facts,
                observed_at=boundary,
                applicability=applicability,
            )
            if current.version.value < view.version.value:
                raise InvalidDecisionHistory(
                    "current Decision version cannot precede lifecycle history"
                )
            lineage = _lineage(
                relationship_history,
                decision_id=decision_id,
                effective_at=boundary,
                known_at=boundary,
            )
        except InvalidDecisionRelationshipHistory as error:
            raise RelationshipHistoryInvalidOrIncomplete(str(error)) from error
        except DecisionNotKnownAtCutoff as error:
            raise DecisionNotFound(decision_id) from error
        except InvalidDecisionHistory as error:
            raise LifecycleConflict(str(error)) from error
        return DecisionMemoryView(
            decision_id=view.decision_id,
            need=view.need,
            subject=view.subject,
            scope=view.scope,
            lifecycle_interpretation=view.lifecycle_interpretation,
            work_posture=view.work_posture,
            applicability=applicability,
            version=current.version,
            lineage=lineage,
        )

    async def as_known_at(
        self,
        decision_id: InvestmentDecisionId,
        known_at: datetime,
    ) -> DecisionMemoryTemporalView:
        boundary = _boundary(known_at, "known_at")
        return await self.effective_at(
            decision_id,
            boundary,
            known_at=boundary,
        )

    async def effective_at(
        self,
        decision_id: InvestmentDecisionId,
        effective_at: datetime,
        *,
        known_at: datetime,
    ) -> DecisionMemoryTemporalView:
        _decision_id(decision_id)
        effective = _boundary(effective_at, "effective_at")
        known = _boundary(known_at, "known_at")
        lifecycle_history = await self._load_decision_history(decision_id)
        relationship_history = await _read(self._reader.load_relationship_history())
        try:
            known_applicability = derive_relationship_applicability(
                decision_id,
                relationship_history,
                effective_at=known,
                known_at=known,
            )
            decision = reconstruct_decision(
                lifecycle_history,
                observed_at=known,
                applicability=known_applicability,
            )
            applicability = derive_relationship_applicability(
                decision_id,
                relationship_history,
                effective_at=effective,
                known_at=known,
            )
            view = decision.effective_at(
                effective,
                known_at=known,
                applicability=applicability,
            )
            lineage = _lineage(
                relationship_history,
                decision_id=decision_id,
                effective_at=effective,
                known_at=known,
            )
        except InvalidDecisionRelationshipHistory as error:
            raise RelationshipHistoryInvalidOrIncomplete(str(error)) from error
        except DecisionNotKnownAtCutoff as error:
            raise DecisionNotFound(decision_id) from error
        except InvalidDecisionHistory as error:
            raise LifecycleConflict(str(error)) from error
        return DecisionMemoryTemporalView(
            decision_id=view.decision_id,
            need=view.need,
            subject=view.subject,
            scope=view.scope,
            lifecycle_interpretation=view.lifecycle_interpretation,
            work_posture=view.work_posture,
            applicability=applicability,
            lineage=lineage,
        )

    async def history(
        self,
        decision_id: InvestmentDecisionId,
        *,
        known_at: datetime | None = None,
    ) -> DecisionHistoryView:
        _decision_id(decision_id)
        boundary = _boundary(
            self._now() if known_at is None else known_at,
            "known_at",
        )
        lifecycle_history = await self._load_decision_history(decision_id)
        known_lifecycle = tuple(
            fact for fact in lifecycle_history if fact.metadata.recorded_at <= boundary
        )
        if not known_lifecycle:
            raise DecisionNotFound(decision_id)
        relationship_history = await _read(self._reader.load_relationship_history())
        try:
            known_relationships, groups = _grouped_relationship_history(
                relationship_history,
                boundary,
            )
        except InvalidDecisionRelationshipHistory as error:
            raise RelationshipHistoryInvalidOrIncomplete(str(error)) from error
        incident = tuple(
            fact
            for fact in known_relationships
            if _incident(groups[fact.metadata.relationship_fact_id], decision_id)
        )
        return DecisionHistoryView(
            decision_id=decision_id,
            known_at=boundary,
            lifecycle_facts=known_lifecycle,
            relationship_facts=incident,
        )

    async def lineage(
        self,
        decision_id: InvestmentDecisionId,
        *,
        effective_at: datetime | None = None,
        known_at: datetime | None = None,
    ) -> tuple[DecisionLineageView, ...]:
        _decision_id(decision_id)
        known = _boundary(
            self._now() if known_at is None else known_at,
            "known_at",
        )
        effective = _boundary(
            known if effective_at is None else effective_at,
            "effective_at",
        )
        lifecycle_history = await self._load_decision_history(decision_id)
        if not any(fact.metadata.recorded_at <= known for fact in lifecycle_history):
            raise DecisionNotFound(decision_id)
        relationship_history = await _read(self._reader.load_relationship_history())
        try:
            return _lineage(
                relationship_history,
                decision_id=decision_id,
                effective_at=effective,
                known_at=known,
            )
        except InvalidDecisionRelationshipHistory as error:
            raise RelationshipHistoryInvalidOrIncomplete(str(error)) from error

    async def unresolved_continuity_candidates(
        self,
        *,
        known_at: datetime | None = None,
    ) -> tuple[InvestmentDecisionId, ...]:
        boundary = _boundary(
            self._now() if known_at is None else known_at,
            "known_at",
        )
        values = await _read(
            self._reader.find_unresolved_continuity_candidates(known_at=boundary)
        )
        return tuple(sorted(values, key=lambda identity: identity.value.int))

    async def _load_decision_history(
        self,
        decision_id: InvestmentDecisionId,
    ) -> tuple[DecisionLifecycleFact, ...]:
        history = await _read(self._reader.load_decision_history(decision_id))
        if history is None:
            raise DecisionNotFound(decision_id)
        return history


def _decision_id(value: object) -> InvestmentDecisionId:
    if type(value) is not InvestmentDecisionId:
        raise TypeError("decision_id must be InvestmentDecisionId")
    return value


def _boundary(value: object, field: str) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{field} must be timezone-aware")
    return value


RelationshipGroup = tuple[
    InvestmentDecisionId,
    DecisionRelationshipType,
    InvestmentDecisionId,
]


def _index_relationship_history(
    known: tuple[DecisionRelationshipHistoryFact, ...],
) -> tuple[
    dict[DecisionRelationshipFactId, DecisionRelationshipHistoryFact],
    dict[DecisionRelationshipFactId, DecisionRelationshipFactId],
]:
    by_id: dict[DecisionRelationshipFactId, DecisionRelationshipHistoryFact] = {}
    parent: dict[DecisionRelationshipFactId, DecisionRelationshipFactId] = {}
    for fact in known:
        if not isinstance(
            fact, (DecisionRelationshipFact, DecisionRelationshipCorrected)
        ):
            raise InvalidDecisionRelationshipHistory(
                "Decision Memory relationship history contains an unsupported fact"
            )
        identity = fact.metadata.relationship_fact_id
        if identity in by_id:
            raise InvalidDecisionRelationshipHistory(
                "Decision Memory relationship fact identity must be unique"
            )
        by_id[identity] = fact
        if isinstance(fact, DecisionRelationshipCorrected):
            parent[identity] = fact.target_relationship_fact_id
    return by_id, parent


def _validate_relationship_parentage(
    by_id: dict[DecisionRelationshipFactId, DecisionRelationshipHistoryFact],
    parent: dict[DecisionRelationshipFactId, DecisionRelationshipFactId],
) -> None:
    for identity, target_id in parent.items():
        target = by_id.get(target_id)
        if target is None:
            raise InvalidDecisionRelationshipHistory(
                "Decision Memory relationship correction ancestry is unavailable"
            )
        fact = by_id[identity]
        if target.metadata.recorded_at > fact.metadata.recorded_at:
            raise InvalidDecisionRelationshipHistory(
                "Decision Memory correction cannot target later-recorded history"
            )


def _relationship_group(
    identity: DecisionRelationshipFactId,
    by_id: dict[DecisionRelationshipFactId, DecisionRelationshipHistoryFact],
    parent: dict[DecisionRelationshipFactId, DecisionRelationshipFactId],
) -> RelationshipGroup:
    current = identity
    seen: set[DecisionRelationshipFactId] = set()
    while current in parent:
        if current in seen:
            raise InvalidDecisionRelationshipHistory(
                "Decision Memory relationship correction ancestry must be acyclic"
            )
        seen.add(current)
        current = parent[current]
    root = by_id[current]
    if not isinstance(root, DecisionRelationshipFact):
        raise InvalidDecisionRelationshipHistory(
            "Decision Memory correction ancestry must root in a base fact"
        )
    return (
        root.source_decision_id,
        root.relationship_type,
        root.target_decision_id,
    )


def _grouped_relationship_history(
    history: tuple[DecisionRelationshipHistoryFact, ...],
    known_at: datetime,
) -> tuple[
    tuple[DecisionRelationshipHistoryFact, ...],
    dict[DecisionRelationshipFactId, RelationshipGroup],
]:
    known = tuple(fact for fact in history if fact.metadata.recorded_at <= known_at)
    by_id, parent = _index_relationship_history(known)
    _validate_relationship_parentage(by_id, parent)
    groups = {
        identity: _relationship_group(identity, by_id, parent) for identity in by_id
    }
    return known, groups


def _incident(group: RelationshipGroup, decision_id: InvestmentDecisionId) -> bool:
    return decision_id in (group[0], group[2])


def _lineage(
    history: tuple[DecisionRelationshipHistoryFact, ...],
    *,
    decision_id: InvestmentDecisionId,
    effective_at: datetime,
    known_at: datetime,
) -> tuple[DecisionLineageView, ...]:
    known, by_fact = _grouped_relationship_history(history, known_at)
    groups = sorted(
        {group for group in by_fact.values() if _incident(group, decision_id)},
        key=lambda group: (
            group[0].value.int,
            group[1].value,
            group[2].value.int,
        ),
    )
    results = []
    for group in groups:
        interpreted = interpret_relationship(
            known,
            source_decision_id=group[0],
            relationship_type=group[1],
            target_decision_id=group[2],
            effective_at=effective_at,
            known_at=known_at,
        )
        group_history = tuple(
            fact
            for fact in known
            if by_fact[fact.metadata.relationship_fact_id] == group
        )
        results.append(
            DecisionLineageView(
                source_decision_id=interpreted.source_decision_id,
                target_decision_id=interpreted.target_decision_id,
                relationship_type=interpreted.relationship_type,
                direction=(
                    DecisionLineageDirection.OUTGOING
                    if interpreted.source_decision_id == decision_id
                    else DecisionLineageDirection.INCOMING
                ),
                effective_at=interpreted.effective_at,
                known_at=interpreted.known_at,
                state=interpreted.state,
                support_fact_ids=interpreted.support_fact_ids,
                basis_contributions=interpreted.basis_contributions,
                surviving_positive_claims=interpreted.surviving_positive_claims,
                history=group_history,
            )
        )
    return tuple(results)
