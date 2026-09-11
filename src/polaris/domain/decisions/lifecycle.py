"""Lifecycle-disposition interpretation of validated, immutable Decision history."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from itertools import combinations
from typing import ClassVar

from .facts import (
    DecisionDeferred,
    DecisionExternallyResolved,
    DecisionInitiated,
    DecisionLifecycleCorrected,
    DecisionLifecycleCorrectionEffect,
    DecisionLifecycleDisposition,
    DecisionLifecycleFact,
    DecisionLifecycleFactId,
    DecisionLifecycleInterpretationContested,
    DecisionLifecycleNotYetEffective,
    DecisionNotKnownAtCutoff,
    DecisionSubstantivelyResolved,
    DecisionWorkPosture,
    DecisionWorkResumed,
    DecisionWorkWithdrawn,
    InvalidDecisionHistory,
    _aware,
)


@dataclass(frozen=True, slots=True)
class NotYetEffectiveDecisionLifecycleInterpretation:
    effective_at: datetime
    known_at: datetime
    kind: ClassVar[str] = "NOT_YET_EFFECTIVE"

    def __post_init__(self) -> None:
        _boundary(self.effective_at, self.known_at)


@dataclass(frozen=True, slots=True)
class DeterminateDecisionLifecycleInterpretation:
    effective_at: datetime
    known_at: datetime
    disposition: DecisionLifecycleDisposition
    support_fact_ids: frozenset[DecisionLifecycleFactId]
    kind: ClassVar[str] = "DETERMINATE"

    def __post_init__(self) -> None:
        _boundary(self.effective_at, self.known_at)
        if type(self.disposition) is not DecisionLifecycleDisposition:
            raise InvalidDecisionHistory("invalid interpreted disposition")
        _support(self.support_fact_ids)


@dataclass(frozen=True, slots=True)
class ContestedDecisionLifecycleInterpretation:
    effective_at: datetime
    known_at: datetime
    support_fact_ids: frozenset[DecisionLifecycleFactId]
    kind: ClassVar[str] = "CONTESTED"

    def __post_init__(self) -> None:
        _boundary(self.effective_at, self.known_at)
        _support(self.support_fact_ids)


DecisionLifecycleInterpretation = (
    NotYetEffectiveDecisionLifecycleInterpretation
    | DeterminateDecisionLifecycleInterpretation
    | ContestedDecisionLifecycleInterpretation
)


def _boundary(effective_at: datetime, known_at: datetime) -> None:
    _aware(effective_at, "effective_at")
    _aware(known_at, "known_at")


def _support(ids: frozenset[DecisionLifecycleFactId]) -> None:
    if (
        type(ids) is not frozenset
        or not ids
        or any(type(identity) is not DecisionLifecycleFactId for identity in ids)
    ):
        raise InvalidDecisionHistory(
            "interpretation needs immutable nonempty fact-ID support"
        )


def _disposition(
    result: DecisionLifecycleInterpretation,
) -> DecisionLifecycleDisposition:
    if isinstance(result, NotYetEffectiveDecisionLifecycleInterpretation):
        raise DecisionLifecycleNotYetEffective(
            "Decision lifecycle is not yet effective"
        )
    if isinstance(result, ContestedDecisionLifecycleInterpretation):
        raise DecisionLifecycleInterpretationContested(
            "Decision lifecycle is contested"
        )
    return result.disposition


@dataclass(frozen=True, slots=True)
class _Branch:
    root: DecisionLifecycleFactId
    root_sequence: int
    disposition: DecisionLifecycleDisposition | None
    effective_at: datetime
    support: frozenset[DecisionLifecycleFactId]
    necessary_withdrawal: bool = False


def _native(fact: DecisionLifecycleFact) -> _Branch:
    if isinstance(fact, DecisionInitiated):
        disposition = DecisionLifecycleDisposition.UNRESOLVED
    elif isinstance(fact, DecisionSubstantivelyResolved):
        disposition = DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED
    else:
        disposition = DecisionLifecycleDisposition.EXTERNALLY_RESOLVED
    meta = fact.metadata
    return _Branch(
        meta.fact_id,
        meta.sequence.value,
        disposition,
        meta.effective_at,
        frozenset({meta.fact_id}),
    )


def _corrected_branch(
    correction: DecisionLifecycleCorrected,
    target: DecisionLifecycleFact,
    prior: _Branch,
    before: dict[DecisionLifecycleFactId, _Branch],
    effective_at: datetime,
) -> _Branch:
    meta = correction.metadata
    if correction.effect is DecisionLifecycleCorrectionEffect.QUALIFY:
        return replace(
            prior,
            disposition=correction.replacement_disposition,
            effective_at=meta.effective_at,
            support=frozenset({meta.fact_id}),
            necessary_withdrawal=False,
        )
    if isinstance(target, DecisionLifecycleCorrected):
        restored = before[target.metadata.fact_id]
        # Preempting a future effect is history, not present explanatory support.
        support = restored.support
        if prior != restored:
            support = support | {meta.fact_id}
        return replace(restored, support=support)
    return replace(
        prior,
        disposition=None,
        support=frozenset({meta.fact_id}),
        necessary_withdrawal=prior.effective_at <= effective_at,
    )


def _branches(
    facts: tuple[DecisionLifecycleFact, ...], effective_at: datetime
) -> list[_Branch]:
    """Resolve ancestry in sequence order and select independent active leaves.

    An inactive ancestor remains traversable. Reverse propagation finds active
    descendants without recursion or an interpreter-depth limit.
    """
    by_id = {f.metadata.fact_id: f for f in facts}
    states: dict[DecisionLifecycleFactId, _Branch] = {}
    before: dict[DecisionLifecycleFactId, _Branch] = {}
    corrections = []
    roots = []
    for fact in facts:
        identity = fact.metadata.fact_id
        if isinstance(fact, DecisionLifecycleCorrected):
            if fact.target_fact_id not in states:
                raise InvalidDecisionHistory(
                    "correction requires known eligible ancestry"
                )
            prior = states[fact.target_fact_id]
            before[identity] = prior
            states[identity] = prior
            if fact.metadata.effective_at <= effective_at:
                states[identity] = _corrected_branch(
                    fact, by_id[fact.target_fact_id], prior, before, effective_at
                )
            corrections.append(fact)
        elif isinstance(
            fact,
            (
                DecisionInitiated,
                DecisionSubstantivelyResolved,
                DecisionExternallyResolved,
            ),
        ):
            states[identity] = _native(fact)
            roots.append(identity)
    descendants: set[DecisionLifecycleFactId] = set()
    leaves = []
    for correction in reversed(corrections):
        identity = correction.metadata.fact_id
        active = correction.metadata.effective_at <= effective_at
        if active and identity not in descendants:
            leaves.append(states[identity])
        if active or identity in descendants:
            descendants.add(correction.target_fact_id)
    leaves.extend(states[root] for root in roots if root not in descendants)
    return [
        b for b in leaves if b.disposition is None or b.effective_at <= effective_at
    ]


def _incompatible(left: _Branch, right: _Branch) -> bool:
    if left.disposition is None and right.disposition is None:
        return False
    if left.root == right.root:
        return (left.disposition, left.effective_at) != (
            right.disposition,
            right.effective_at,
        )
    if left.disposition is None or right.disposition is None:
        return False
    unresolved = DecisionLifecycleDisposition.UNRESOLVED
    if left.disposition is unresolved and right.disposition is unresolved:
        return False
    if left.disposition is not unresolved and right.disposition is not unresolved:
        return (left.disposition, left.effective_at) != (
            right.disposition,
            right.effective_at,
        )
    terminal, pending = (
        (right, left) if left.disposition is unresolved else (left, right)
    )
    return (terminal.effective_at, terminal.root_sequence) < (
        pending.effective_at,
        pending.root_sequence,
    )


def _interpret(
    history: tuple[DecisionLifecycleFact, ...],
    effective_at: datetime,
    known_at: datetime,
) -> DecisionLifecycleInterpretation:
    _boundary(effective_at, known_at)
    if history[0].metadata.recorded_at > known_at:
        raise DecisionNotKnownAtCutoff("Decision initiation is not known at cutoff")
    facts = tuple(f for f in history if f.metadata.recorded_at <= known_at)
    branches = _branches(facts, effective_at)
    positives = [b for b in branches if b.disposition is not None]
    if not positives:
        return NotYetEffectiveDecisionLifecycleInterpretation(effective_at, known_at)
    conflicts: set[DecisionLifecycleFactId] = set()
    for left, right in combinations(branches, 2):
        if _incompatible(left, right):
            conflicts.update(left.support | right.support)
    if conflicts:
        return ContestedDecisionLifecycleInterpretation(
            effective_at, known_at, frozenset(conflicts)
        )
    terminals = [
        b
        for b in positives
        if b.disposition is not DecisionLifecycleDisposition.UNRESOLVED
    ]
    selected = terminals or [
        b for b in positives if b.effective_at == max(p.effective_at for p in positives)
    ]
    support = frozenset(identity for b in selected for identity in b.support)
    support |= frozenset(
        identity
        for b in branches
        if b.disposition is None and b.necessary_withdrawal
        for identity in b.support
    )
    disposition = selected[0].disposition
    assert disposition is not None
    return DeterminateDecisionLifecycleInterpretation(
        effective_at, known_at, disposition, support
    )


def _posture(
    history: tuple[DecisionLifecycleFact, ...],
    result: DecisionLifecycleInterpretation,
) -> DecisionWorkPosture | None:
    if not isinstance(result, DeterminateDecisionLifecycleInterpretation) or (
        result.disposition is not DecisionLifecycleDisposition.UNRESOLVED
    ):
        return None
    postures = {
        DecisionDeferred: DecisionWorkPosture.DEFERRED,
        DecisionWorkWithdrawn: DecisionWorkPosture.WITHDRAWN,
        DecisionWorkResumed: DecisionWorkPosture.ACTIVE,
    }
    applicable = [
        f
        for f in history
        if type(f) in postures
        and f.metadata.recorded_at <= result.known_at
        and f.metadata.effective_at <= result.effective_at
    ]
    if not applicable:
        return DecisionWorkPosture.ACTIVE
    latest = max(
        applicable, key=lambda f: (f.metadata.effective_at, f.metadata.sequence)
    )
    return postures[type(latest)]
