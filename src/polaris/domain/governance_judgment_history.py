"""Governance-owned correction history for Human Decision Evidence targets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from polaris.domain.actors import KnownActorAttribution
from polaris.domain.evidence.judgment_versions import (
    HumanInvestmentDecisionVersionRef,
    JudgmentRevision,
)
from polaris.domain.evidence.judgments import HumanInvestmentDecisionRef
from polaris.domain.human_investment_decision import HumanInvestmentDecision


class InvalidHumanDecisionTargetHistory(ValueError):
    """A target history has incomplete or contradictory owner ancestry."""


class HumanDecisionTargetNotKnown(ValueError):
    """The root was not committed at the requested knowledge cutoff."""


class HumanDecisionTargetNeedsReevaluation(RuntimeError):
    """Time changed current meaning without a later Governance owner commit."""


class HumanDecisionTargetEffect(StrEnum):
    REVISE = "revise"
    RETRACT = "retract"


class HumanDecisionTargetStatus(StrEnum):
    DETERMINATE = "determinate"
    WITHDRAWN = "withdrawn"
    CONTESTED = "contested"
    NOT_YET_EFFECTIVE = "not_yet_effective"


@dataclass(frozen=True, slots=True)
class HumanDecisionTargetCorrectionDraft:
    """An attributable correction before the store captures its commit boundary."""

    correction_id: UUID
    root: HumanInvestmentDecisionRef
    target: HumanInvestmentDecisionRef | UUID
    attribution: KnownActorAttribution
    basis: str
    effective_at: datetime
    effect: HumanDecisionTargetEffect
    replacement: HumanInvestmentDecision | None = None

    def __post_init__(self) -> None:
        _uuid4(self.correction_id, "correction_id")
        if type(self.root) is not HumanInvestmentDecisionRef:
            raise TypeError("root must be HumanInvestmentDecisionRef")
        if type(self.target) not in (HumanInvestmentDecisionRef, UUID):
            raise TypeError("target must be a root or correction identity")
        if type(self.target) is UUID:
            _uuid4(self.target, "target")
        if type(self.attribution) is not KnownActorAttribution:
            raise TypeError("correction attribution must identify a human actor")
        if not isinstance(self.basis, str) or not self.basis.strip():
            raise ValueError("correction basis must be substantive")
        _aware(self.effective_at, "effective_at")
        if type(self.effect) is not HumanDecisionTargetEffect:
            raise TypeError("correction effect must be closed")
        if (self.effect is HumanDecisionTargetEffect.REVISE) != (
            type(self.replacement) is HumanInvestmentDecision
        ):
            raise ValueError("revision needs one complete replacement assertion")
        if self.replacement is not None and self.replacement.decision_ref != self.root:
            raise ValueError("correction cannot change the Human Decision root")

    def at_boundary(self, committed_at: datetime) -> HumanDecisionTargetCorrection:
        _aware(committed_at, "committed_at")
        return HumanDecisionTargetCorrection(
            self.correction_id,
            self.root,
            self.target,
            self.attribution,
            self.basis.strip(),
            self.effective_at,
            committed_at,
            committed_at,
            self.effect,
            self.replacement,
        )


@dataclass(frozen=True, slots=True)
class HumanDecisionTargetCorrection:
    # duplicate-code: A committed act retains boundary fields that a draft
    # cannot own; sharing the declarations would blur those distinct states.
    # arid: disable
    correction_id: UUID
    root: HumanInvestmentDecisionRef
    target: HumanInvestmentDecisionRef | UUID
    attribution: KnownActorAttribution
    basis: str
    effective_at: datetime
    # arid: enable
    recorded_at: datetime
    known_at: datetime
    effect: HumanDecisionTargetEffect
    replacement: HumanInvestmentDecision | None


@dataclass(frozen=True, slots=True)
class HumanDecisionTargetSelection:
    root: HumanInvestmentDecisionRef
    version: HumanInvestmentDecisionVersionRef
    status: HumanDecisionTargetStatus
    assertions: frozenset[HumanInvestmentDecision]
    support: frozenset[HumanInvestmentDecisionRef | UUID]
    effective_at: datetime
    known_at: datetime

    @property
    def assertion(self) -> HumanInvestmentDecision | None:
        if self.status is HumanDecisionTargetStatus.DETERMINATE:
            return next(iter(self.assertions))
        return None


@dataclass(frozen=True, slots=True)
class _Branch:
    assertion: HumanInvestmentDecision | None
    support: frozenset[HumanInvestmentDecisionRef | UUID]
    withdrawn: bool = False


@dataclass(frozen=True, slots=True)
class HumanDecisionTargetHistory:
    """One root's append-only owner acts and persisted revision sequence."""

    root_assertion: HumanInvestmentDecision
    root_known_at: datetime
    corrections: tuple[HumanDecisionTargetCorrection, ...]
    revisions: tuple[JudgmentRevision, ...]

    @classmethod
    def form(
        cls, assertion: HumanInvestmentDecision, committed_at: datetime
    ) -> HumanDecisionTargetHistory:
        if type(assertion) is not HumanInvestmentDecision:
            raise TypeError("root assertion must be HumanInvestmentDecision")
        _aware(committed_at, "committed_at")
        if assertion.made_at > committed_at:
            raise InvalidHumanDecisionTargetHistory(
                "root cannot be effective after its owner commit"
            )
        return cls(assertion, committed_at, (), (JudgmentRevision(1),))

    def __post_init__(self) -> None:
        if len(self.revisions) != len(self.corrections) + 1:
            raise InvalidHumanDecisionTargetHistory("revision history is incomplete")

    def append(
        self, correction: HumanDecisionTargetCorrection
    ) -> HumanDecisionTargetHistory:
        self._validate_append(correction)
        last_commit = (
            self.corrections[-1].known_at if self.corrections else self.root_known_at
        )
        before = self._select(last_commit, last_commit)
        candidate = HumanDecisionTargetHistory(
            self.root_assertion,
            self.root_known_at,
            (*self.corrections, correction),
            (*self.revisions, self.revisions[-1]),
        )
        after = candidate._select(correction.known_at, correction.known_at)
        changed = (
            before.status,
            before.assertions,
            before.support,
        ) != (after.status, after.assertions, after.support)
        revision = JudgmentRevision(self.revisions[-1].value + int(changed))
        return HumanDecisionTargetHistory(
            self.root_assertion,
            self.root_known_at,
            candidate.corrections,
            (*self.revisions, revision),
        )

    def _validate_append(self, correction: HumanDecisionTargetCorrection) -> None:
        if type(correction) is not HumanDecisionTargetCorrection:
            raise TypeError("correction must be a committed owner act")
        if correction.root != self.root_assertion.decision_ref:
            raise InvalidHumanDecisionTargetHistory("correction changes target root")
        if correction.recorded_at != correction.known_at:
            raise InvalidHumanDecisionTargetHistory(
                "owner knowledge must equal durable commit boundary"
            )
        if correction.known_at < self.root_known_at or (
            self.corrections and correction.known_at < self.corrections[-1].known_at
        ):
            raise InvalidHumanDecisionTargetHistory("owner knowledge is unordered")
        if correction.correction_id in {
            item.correction_id for item in self.corrections
        }:
            raise InvalidHumanDecisionTargetHistory("correction identity is repeated")
        if type(correction.target) is HumanInvestmentDecisionRef:
            if correction.target != correction.root:
                raise InvalidHumanDecisionTargetHistory("wrong root target")
        elif correction.target not in {item.correction_id for item in self.corrections}:
            raise InvalidHumanDecisionTargetHistory("correction ancestry is missing")
        self._validate_replacement(correction)

    def _validate_replacement(self, correction: HumanDecisionTargetCorrection) -> None:
        if correction.effect is HumanDecisionTargetEffect.REVISE:
            replacement = correction.replacement
            if (
                type(replacement) is not HumanInvestmentDecision
                or replacement.decision_ref != correction.root
                or replacement.investment_decision_id
                != self.root_assertion.investment_decision_id
            ):
                raise InvalidHumanDecisionTargetHistory(
                    "replacement must correct the same attributable judgment"
                )
        elif correction.replacement is not None:
            raise InvalidHumanDecisionTargetHistory(
                "retraction cannot supply an assertion"
            )

    def select(
        self, effective_at: datetime, known_at: datetime
    ) -> HumanDecisionTargetSelection:
        selection = self._select(effective_at, known_at)
        if effective_at == known_at:
            known = tuple(
                item for item in self.corrections if item.known_at <= known_at
            )
            last_commit = known[-1].known_at if known else self.root_known_at
            if last_commit < known_at:
                before = self._select(last_commit, last_commit)
                if (
                    before.status,
                    before.assertions,
                    before.support,
                ) != (selection.status, selection.assertions, selection.support):
                    raise HumanDecisionTargetNeedsReevaluation(
                        "current meaning changed after the last Governance commit"
                    )
        return selection

    def _select(
        self, effective_at: datetime, known_at: datetime
    ) -> HumanDecisionTargetSelection:
        _aware(effective_at, "effective_at")
        _aware(known_at, "known_at")
        if known_at < self.root_known_at:
            raise HumanDecisionTargetNotKnown("root not known at cutoff")
        known = tuple(item for item in self.corrections if item.known_at <= known_at)
        active_ids: set[UUID] = set()
        active_items: list[HumanDecisionTargetCorrection] = []
        for item in known:
            if item.effective_at > effective_at:
                continue
            if type(item.target) is UUID and item.target not in active_ids:
                continue
            active_items.append(item)
            active_ids.add(item.correction_id)
        active = tuple(active_items)
        leaves = self._leaves(active)
        assertions = frozenset(
            state.assertion
            for state in leaves
            if state.assertion is not None and state.assertion.made_at <= effective_at
        )
        status = _status(
            assertions,
            leaves,
            effective_at < self.root_assertion.made_at and not active,
        )
        known_count = len(known)
        version = HumanInvestmentDecisionVersionRef(
            self.root_assertion.decision_ref, self.revisions[known_count]
        )
        return HumanDecisionTargetSelection(
            self.root_assertion.decision_ref,
            version,
            status,
            assertions,
            frozenset(ref for state in leaves for ref in state.support),
            effective_at,
            known_at,
        )

    def _leaves(
        self, active: tuple[HumanDecisionTargetCorrection, ...]
    ) -> tuple[_Branch, ...]:
        states: dict[HumanInvestmentDecisionRef | UUID, _Branch] = {
            self.root_assertion.decision_ref: _Branch(
                self.root_assertion,
                frozenset({self.root_assertion.decision_ref}),
            )
        }
        before: dict[UUID, _Branch] = {}
        unresolved = {item.correction_id: item for item in active}
        while unresolved:
            progressed = False
            for identity, item in tuple(unresolved.items()):
                if item.target not in states:
                    continue
                prior = states[item.target]
                before[identity] = prior
                support = prior.support | {item.correction_id, item.target}
                if item.effect is HumanDecisionTargetEffect.REVISE:
                    states[identity] = _Branch(item.replacement, frozenset(support))
                elif type(item.target) is UUID:
                    restored = before[item.target]
                    states[identity] = _Branch(
                        restored.assertion,
                        restored.support | support,
                        restored.withdrawn,
                    )
                else:
                    states[identity] = _Branch(None, frozenset(support), True)
                del unresolved[identity]
                progressed = True
            if not progressed:
                raise InvalidHumanDecisionTargetHistory(
                    "active correction ancestry cannot be resolved"
                )
        targeted = {item.target for item in active}
        return tuple(
            state for identity, state in states.items() if identity not in targeted
        )


def _status(
    assertions: frozenset[HumanInvestmentDecision],
    leaves: tuple[_Branch, ...],
    root_not_yet_effective: bool,
) -> HumanDecisionTargetStatus:
    if root_not_yet_effective:
        return HumanDecisionTargetStatus.NOT_YET_EFFECTIVE
    withdrawn = any(state.withdrawn for state in leaves)
    if len(assertions) > 1 or (assertions and withdrawn):
        return HumanDecisionTargetStatus.CONTESTED
    if assertions:
        return HumanDecisionTargetStatus.DETERMINATE
    if withdrawn:
        return HumanDecisionTargetStatus.WITHDRAWN
    return HumanDecisionTargetStatus.NOT_YET_EFFECTIVE


# duplicate-code: This owner's typed input checks stay local to its target
# history; a cross-owner validator would couple separate domain contracts.
# arid: disable
def _uuid4(value: UUID, field: str) -> None:
    if type(value) is not UUID or value.version != 4:
        raise TypeError(f"{field} must be UUIDv4")


def _aware(value: datetime, field: str) -> None:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


# arid: enable
