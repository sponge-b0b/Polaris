from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, cast

from polaris.domain.actors import ActorAttribution, is_actor_attribution

from .observations import (
    EvidenceBindingId,
    EvidenceCorrectionId,
    EvidenceFactRef,
    EvidenceObservation,
    EvidenceObservationId,
    EvidenceSufficiencyAssessmentId,
)

if TYPE_CHECKING:
    from .bindings import EvidenceBinding
    from .sufficiency import EvidenceSufficiencyAssessment


class InvalidEvidenceCorrection(ValueError):
    pass


class InvalidEvidenceCorrectionHistory(ValueError):
    pass


class EvidenceCorrectionEffect(StrEnum):
    REVISE = "revise"
    RETRACT = "retract"


class EvidenceInterpretationState(StrEnum):
    NOT_KNOWN = "not_known"
    NOT_EFFECTIVE = "not_effective"
    DETERMINATE = "determinate"
    WITHDRAWN = "withdrawn"
    CONTESTED = "contested"


@dataclass(frozen=True, slots=True)
class EvidenceCorrectionBasis:
    reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.reference, str) or not self.reference.strip():
            raise InvalidEvidenceCorrection(
                "Evidence correction basis must be a non-empty reference"
            )
        object.__setattr__(self, "reference", self.reference.strip())


type EvidenceObservationCorrectionTarget = EvidenceObservationId | EvidenceCorrectionId
type EvidenceBindingCorrectionTarget = EvidenceBindingId | EvidenceCorrectionId
type EvidenceAssessmentCorrectionTarget = (
    EvidenceSufficiencyAssessmentId | EvidenceCorrectionId
)


# duplicate-code: each family has a distinct typed root, target, and replacement;
# retaining explicit dataclasses prevents erasing the family contract.
# arid: disable
@dataclass(frozen=True, slots=True)
class EvidenceObservationCorrection:
    correction_id: EvidenceCorrectionId
    root_id: EvidenceObservationId
    target: EvidenceObservationCorrectionTarget
    effect: EvidenceCorrectionEffect
    attribution: ActorAttribution
    basis: EvidenceCorrectionBasis
    effective_at: datetime
    recorded_at: datetime
    replacement: EvidenceObservation | None = None

    def __post_init__(self) -> None:
        _validate_common_correction(self, EvidenceObservationId)
        _validate_replacement(self.effect, self.replacement, EvidenceObservation)
        if (
            self.replacement is not None
            and self.replacement.observation_id != self.root_id
        ):
            raise InvalidEvidenceCorrection(
                "observation replacement must retain its root identity"
            )


@dataclass(frozen=True, slots=True)
class EvidenceBindingCorrection:
    correction_id: EvidenceCorrectionId
    root_id: EvidenceBindingId
    target: EvidenceBindingCorrectionTarget
    effect: EvidenceCorrectionEffect
    attribution: ActorAttribution
    basis: EvidenceCorrectionBasis
    effective_at: datetime
    recorded_at: datetime
    replacement: EvidenceBinding | None = None

    def __post_init__(self) -> None:
        from .bindings import EvidenceBinding

        _validate_common_correction(self, EvidenceBindingId)
        _validate_replacement(self.effect, self.replacement, EvidenceBinding)
        if self.replacement is not None and self.replacement.binding_id != self.root_id:
            raise InvalidEvidenceCorrection(
                "binding replacement must retain its root identity"
            )
        if (
            self.replacement is not None
            and self.replacement.recorded_at > self.recorded_at
        ):
            raise InvalidEvidenceCorrection(
                "binding replacement cannot be recorded after its correction"
            )


@dataclass(frozen=True, slots=True)
class EvidenceAssessmentCorrection:
    correction_id: EvidenceCorrectionId
    root_id: EvidenceSufficiencyAssessmentId
    target: EvidenceAssessmentCorrectionTarget
    effect: EvidenceCorrectionEffect
    attribution: ActorAttribution
    basis: EvidenceCorrectionBasis
    effective_at: datetime
    recorded_at: datetime
    replacement: EvidenceSufficiencyAssessment | None = None

    def __post_init__(self) -> None:
        from .sufficiency import EvidenceSufficiencyAssessment

        _validate_common_correction(self, EvidenceSufficiencyAssessmentId)
        _validate_replacement(
            self.effect, self.replacement, EvidenceSufficiencyAssessment
        )
        if self.replacement is not None:
            if self.replacement.assessment_id != self.root_id:
                raise InvalidEvidenceCorrection(
                    "assessment replacement must retain its root identity"
                )
            if self.replacement.recorded_at > self.recorded_at:
                raise InvalidEvidenceCorrection(
                    "assessment replacement cannot be recorded after its correction"
                )


# arid: enable


type EvidenceCorrection = (
    EvidenceObservationCorrection
    | EvidenceBindingCorrection
    | EvidenceAssessmentCorrection
)


@dataclass(frozen=True, slots=True)
class EvidenceInterpretation[RootT]:
    state: EvidenceInterpretationState
    assertions: frozenset[RootT]
    fact_support: frozenset[EvidenceFactRef]


@dataclass(frozen=True, slots=True)
class _Branch[RootT]:
    assertion: RootT | None
    support: frozenset[EvidenceFactRef]
    withdrawn: bool = False


@dataclass(frozen=True, slots=True)
class EvidenceObservationCorrectionHistory:
    root: EvidenceObservation
    root_recorded_at: datetime
    corrections: tuple[EvidenceObservationCorrection, ...]

    def __post_init__(self) -> None:
        if type(self.root) is not EvidenceObservation:
            raise TypeError("root must be EvidenceObservation")
        _aware(self.root_recorded_at, "root_recorded_at")
        _require_correction_tuple(
            self.corrections,
            EvidenceObservationCorrection,
        )

    def interpret(
        self,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> EvidenceInterpretation[EvidenceObservation]:
        return interpret_evidence_observation(
            self.root,
            root_recorded_at=self.root_recorded_at,
            corrections=self.corrections,
            effective_at=effective_at,
            known_at=known_at,
        )


@dataclass(frozen=True, slots=True)
class EvidenceBindingCorrectionHistory:
    root: EvidenceBinding
    corrections: tuple[EvidenceBindingCorrection, ...]

    def __post_init__(self) -> None:
        from .bindings import EvidenceBinding

        if type(self.root) is not EvidenceBinding:
            raise TypeError("root must be EvidenceBinding")
        _require_correction_tuple(self.corrections, EvidenceBindingCorrection)

    def interpret(
        self, *, effective_at: datetime, known_at: datetime
    ) -> EvidenceInterpretation[EvidenceBinding]:
        # duplicate-code: typed binding and assessment histories independently
        # dispatch to their own interpretation algebra.
        # arid: disable
        return interpret_evidence_binding(
            self.root,
            corrections=self.corrections,
            effective_at=effective_at,
            known_at=known_at,
        )
        # arid: enable


@dataclass(frozen=True, slots=True)
class EvidenceAssessmentCorrectionHistory:
    root: EvidenceSufficiencyAssessment
    corrections: tuple[EvidenceAssessmentCorrection, ...]

    # duplicate-code: each typed history enforces its own root and correction
    # family; sharing the class body would obscure that domain contract.
    # arid: disable
    def __post_init__(self) -> None:
        from .sufficiency import EvidenceSufficiencyAssessment

        if type(self.root) is not EvidenceSufficiencyAssessment:
            raise TypeError("root must be EvidenceSufficiencyAssessment")
        _require_correction_tuple(self.corrections, EvidenceAssessmentCorrection)

    def interpret(
        self, *, effective_at: datetime, known_at: datetime
    ) -> EvidenceInterpretation[EvidenceSufficiencyAssessment]:
        return interpret_evidence_assessment(
            self.root,
            corrections=self.corrections,
            effective_at=effective_at,
            known_at=known_at,
        )

    # arid: enable


def _require_correction_tuple(
    values: object,
    correction_type: type[object],
) -> None:
    if type(values) is not tuple or any(
        type(value) is not correction_type for value in values
    ):
        raise TypeError(f"corrections must be tuple[{correction_type.__name__}, ...]")


def _validate_common_correction(
    correction: EvidenceCorrection,
    root_type: type[object],
) -> None:
    if type(correction.correction_id) is not EvidenceCorrectionId:
        raise TypeError("correction_id must be EvidenceCorrectionId")
    if type(correction.root_id) is not root_type:
        raise TypeError(f"root_id must be {root_type.__name__}")
    if type(correction.target) not in (root_type, EvidenceCorrectionId):
        raise TypeError(f"target must be {root_type.__name__} or EvidenceCorrectionId")
    if correction.target == correction.correction_id:
        raise InvalidEvidenceCorrection("Evidence correction cannot target itself")
    if type(correction.effect) is not EvidenceCorrectionEffect:
        raise TypeError("effect must be EvidenceCorrectionEffect")
    if not is_actor_attribution(correction.attribution):
        raise TypeError("attribution must be an ActorAttribution")
    if type(correction.basis) is not EvidenceCorrectionBasis:
        raise TypeError("basis must be EvidenceCorrectionBasis")
    _aware(correction.effective_at, "effective_at")
    _aware(correction.recorded_at, "recorded_at")


def _validate_replacement(
    effect: EvidenceCorrectionEffect,
    replacement: object,
    replacement_type: type[object],
) -> None:
    if effect is EvidenceCorrectionEffect.REVISE:
        if type(replacement) is not replacement_type:
            raise InvalidEvidenceCorrection(
                "REVISE requires one complete family-specific replacement assertion"
            )
        return
    if replacement is not None:
        raise InvalidEvidenceCorrection("RETRACT cannot carry a replacement assertion")


def _aware(value: object, field: str) -> None:
    # duplicate-code: this validator owns Evidence-specific failure semantics;
    # sharing it with Decisions would couple bounded-context exception contracts.
    # arid: disable
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise InvalidEvidenceCorrection(f"{field} must be timezone-aware")
    # arid: enable


def interpret_evidence_observation(
    root: EvidenceObservation,
    *,
    root_recorded_at: datetime,
    corrections: tuple[EvidenceObservationCorrection, ...],
    effective_at: datetime,
    known_at: datetime,
) -> EvidenceInterpretation[EvidenceObservation]:
    if type(root) is not EvidenceObservation:
        raise TypeError("root must be EvidenceObservation")
    return _interpret(
        root,
        root_id=root.observation_id,
        root_recorded_at=root_recorded_at,
        root_effective_at=root.effective_at or root.observed_at,
        corrections=corrections,
        correction_type=EvidenceObservationCorrection,
        root_type=EvidenceObservationId,
        assertion_effective_at=lambda value: value.effective_at or value.observed_at,
        validate_replacement=lambda _root, _replacement: None,
        effective_at=effective_at,
        known_at=known_at,
    )


def interpret_evidence_binding(
    root: EvidenceBinding,
    *,
    corrections: tuple[EvidenceBindingCorrection, ...],
    effective_at: datetime,
    known_at: datetime,
) -> EvidenceInterpretation[EvidenceBinding]:
    from .bindings import EvidenceBinding

    if type(root) is not EvidenceBinding:
        raise TypeError("root must be EvidenceBinding")
    return _interpret(
        root,
        root_id=root.binding_id,
        root_recorded_at=root.recorded_at,
        root_effective_at=root.effective_at,
        corrections=corrections,
        correction_type=EvidenceBindingCorrection,
        root_type=EvidenceBindingId,
        assertion_effective_at=lambda value: value.effective_at,
        validate_replacement=_validate_binding_replacement,
        effective_at=effective_at,
        known_at=known_at,
    )


def interpret_evidence_assessment(
    root: EvidenceSufficiencyAssessment,
    *,
    corrections: tuple[EvidenceAssessmentCorrection, ...],
    effective_at: datetime,
    known_at: datetime,
) -> EvidenceInterpretation[EvidenceSufficiencyAssessment]:
    from .sufficiency import EvidenceSufficiencyAssessment

    if type(root) is not EvidenceSufficiencyAssessment:
        raise TypeError("root must be EvidenceSufficiencyAssessment")
    return _interpret(
        root,
        root_id=root.assessment_id,
        root_recorded_at=root.recorded_at,
        root_effective_at=root.effective_at,
        corrections=corrections,
        correction_type=EvidenceAssessmentCorrection,
        root_type=EvidenceSufficiencyAssessmentId,
        assertion_effective_at=lambda value: value.effective_at,
        validate_replacement=_validate_assessment_replacement,
        effective_at=effective_at,
        known_at=known_at,
    )


def _validate_assessment_replacement(
    root: EvidenceSufficiencyAssessment,
    replacement: EvidenceSufficiencyAssessment,
) -> None:
    if (
        replacement.assessment_id != root.assessment_id
        or replacement.target != root.target
        or replacement.scope != root.scope
        or replacement.evidence_use is not root.evidence_use
        or replacement.applicability_key != root.applicability_key
        or replacement.requirement_set_id != root.requirement_set_id
        or replacement.requirement_version_id != root.requirement_version_id
        or replacement.effective_at != root.effective_at
        or replacement.known_at != root.known_at
        or replacement.recorded_at != root.recorded_at
        or replacement.reassesses_assessment_id != root.reassesses_assessment_id
    ):
        raise InvalidEvidenceCorrectionHistory(
            "assessment correction must retain its attributable boundary "
            "and exact requirement set/version"
        )


def _validate_binding_replacement(
    root: EvidenceBinding, replacement: EvidenceBinding
) -> None:
    if (
        replacement.observation_id != root.observation_id
        or replacement.target != root.target
        or replacement.scope != root.scope
        or replacement.evidence_use is not root.evidence_use
    ):
        raise InvalidEvidenceCorrectionHistory(
            "binding correction cannot change observation, target, scope, or use"
        )


def _interpret[RootT, CorrectionT: EvidenceCorrection](
    root: RootT,
    *,
    root_id: EvidenceFactRef,
    root_recorded_at: datetime,
    root_effective_at: datetime,
    corrections: tuple[CorrectionT, ...],
    correction_type: type[CorrectionT],
    root_type: type[object],
    assertion_effective_at: Callable[[RootT], datetime],
    validate_replacement: Callable[[RootT, RootT], None],
    effective_at: datetime,
    known_at: datetime,
) -> EvidenceInterpretation[RootT]:
    _aware(root_recorded_at, "root_recorded_at")
    _aware(effective_at, "effective_at")
    _aware(known_at, "known_at")
    if type(corrections) is not tuple or any(
        type(value) is not correction_type for value in corrections
    ):
        raise TypeError(f"corrections must be tuple[{correction_type.__name__}, ...]")
    if root_recorded_at > known_at:
        return EvidenceInterpretation(
            EvidenceInterpretationState.NOT_KNOWN,
            frozenset(),
            frozenset(),
        )
    known = tuple(value for value in corrections if value.recorded_at <= known_at)
    by_id, parent = _history_maps(
        root,
        root_id,
        root_recorded_at,
        known,
        root_type,
        validate_replacement,
    )
    states, _ = _resolve_states(
        root,
        root_id,
        root_effective_at,
        by_id,
        parent,
        effective_at,
    )
    leaves = _leaves(root_id, by_id, parent, states, effective_at)
    return _combine(leaves, assertion_effective_at, effective_at)


def _history_maps[RootT, CorrectionT: EvidenceCorrection](
    root: RootT,
    root_id: EvidenceFactRef,
    root_recorded_at: datetime,
    corrections: tuple[CorrectionT, ...],
    root_type: type[object],
    validate_replacement: Callable[[RootT, RootT], None],
) -> tuple[
    dict[EvidenceCorrectionId, CorrectionT],
    dict[EvidenceCorrectionId, EvidenceFactRef],
]:
    by_id: dict[EvidenceCorrectionId, CorrectionT] = {}
    parent: dict[EvidenceCorrectionId, EvidenceFactRef] = {}
    for correction in corrections:
        _validate_correction_record(
            root,
            root_id,
            root_recorded_at,
            correction,
            root_type,
            validate_replacement,
            by_id,
        )
        by_id[correction.correction_id] = correction
        parent[correction.correction_id] = correction.target
    for target in parent.values():
        if type(target) is EvidenceCorrectionId:
            if target not in by_id:
                raise InvalidEvidenceCorrectionHistory(
                    "Evidence correction requires complete target ancestry"
                )
    _validate_acyclic(parent, root_id)
    for identity, target in parent.items():
        if type(target) is EvidenceCorrectionId:
            if by_id[target].recorded_at > by_id[identity].recorded_at:
                raise InvalidEvidenceCorrectionHistory(
                    "Evidence correction cannot target later-recorded history"
                )
    return by_id, parent


def _validate_correction_record[RootT, CorrectionT: EvidenceCorrection](
    root: RootT,
    root_id: EvidenceFactRef,
    root_recorded_at: datetime,
    correction: CorrectionT,
    root_type: type[object],
    validate_replacement: Callable[[RootT, RootT], None],
    by_id: dict[EvidenceCorrectionId, CorrectionT],
) -> None:
    if correction.correction_id in by_id:
        raise InvalidEvidenceCorrectionHistory(
            "Evidence correction identity must be unique"
        )
    if correction.root_id != root_id:
        raise InvalidEvidenceCorrectionHistory(
            "Evidence correction must remain in one root lineage"
        )
    if type(correction.target) is root_type and correction.target != root_id:
        raise InvalidEvidenceCorrectionHistory(
            "Evidence correction root target must match its lineage root"
        )
    if correction.effect is EvidenceCorrectionEffect.REVISE:
        assert correction.replacement is not None
        validate_replacement(root, cast(RootT, correction.replacement))
    if (
        type(correction.target) is root_type
        and root_recorded_at > correction.recorded_at
    ):
        raise InvalidEvidenceCorrectionHistory(
            "Evidence correction cannot target later-recorded history"
        )


def _validate_acyclic(
    parent: dict[EvidenceCorrectionId, EvidenceFactRef],
    root_id: EvidenceFactRef,
) -> None:
    for identity in parent:
        seen: set[EvidenceFactRef] = {identity}
        current: EvidenceFactRef = identity
        while type(current) is EvidenceCorrectionId:
            if current not in parent:
                raise InvalidEvidenceCorrectionHistory(
                    "Evidence correction ancestry must root in its base fact"
                )
            current = parent[current]
            if current in seen:
                raise InvalidEvidenceCorrectionHistory(
                    "Evidence correction ancestry must be acyclic"
                )
            seen.add(current)
        if current != root_id:
            raise InvalidEvidenceCorrectionHistory(
                "Evidence correction ancestry must root in its base fact"
            )


def _resolve_states[RootT, CorrectionT: EvidenceCorrection](
    root: RootT,
    root_id: EvidenceFactRef,
    root_effective_at: datetime,
    by_id: dict[EvidenceCorrectionId, CorrectionT],
    parent: dict[EvidenceCorrectionId, EvidenceFactRef],
    effective_at: datetime,
) -> tuple[
    dict[EvidenceFactRef, _Branch[RootT]],
    dict[EvidenceCorrectionId, _Branch[RootT]],
]:
    root_support = (
        frozenset({root_id}) if root_effective_at <= effective_at else frozenset()
    )
    states: dict[EvidenceFactRef, _Branch[RootT]] = {
        root_id: _Branch(root, root_support)
    }
    before: dict[EvidenceCorrectionId, _Branch[RootT]] = {}
    # duplicate-code: Evidence and Decision relationships have distinct branch
    # payload/effect algebras; sharing this loop would couple their reducers.
    # arid: disable
    unresolved = set(by_id)
    while unresolved:
        progress = False
        for identity in tuple(unresolved):
            target = parent[identity]
            if target not in states:
                continue
            correction = by_id[identity]
            target_state = states[target]
            before[identity] = target_state
            state = target_state
            if correction.effective_at <= effective_at:
                state = _apply_correction(
                    correction,
                    target,
                    target_state,
                    before,
                )
            states[identity] = state
            unresolved.remove(identity)
            progress = True
        if not progress:
            raise InvalidEvidenceCorrectionHistory(
                "Evidence correction ancestry cannot be resolved"
            )
    # arid: enable
    return states, before


def _apply_correction[RootT](
    correction: EvidenceCorrection,
    target: EvidenceFactRef,
    target_state: _Branch[RootT],
    before: dict[EvidenceCorrectionId, _Branch[RootT]],
) -> _Branch[RootT]:
    support = target_state.support | frozenset[EvidenceFactRef](
        (correction.root_id, correction.target, correction.correction_id)
    )
    if correction.effect is EvidenceCorrectionEffect.REVISE:
        assert correction.replacement is not None
        return _Branch(cast(RootT, correction.replacement), support)
    if type(target) is EvidenceCorrectionId:
        restored = before[target]
        return _Branch(
            restored.assertion,
            restored.support | support,
            restored.withdrawn,
        )
    return _Branch(None, support, withdrawn=True)


def _leaves[RootT, CorrectionT: EvidenceCorrection](
    root_id: EvidenceFactRef,
    by_id: dict[EvidenceCorrectionId, CorrectionT],
    parent: dict[EvidenceCorrectionId, EvidenceFactRef],
    states: dict[EvidenceFactRef, _Branch[RootT]],
    effective_at: datetime,
) -> tuple[_Branch[RootT], ...]:
    active = frozenset(
        identity
        for identity, correction in by_id.items()
        if correction.effective_at <= effective_at
    )
    targeted: set[EvidenceFactRef] = set()
    for identity in active:
        current: EvidenceFactRef = identity
        while type(current) is EvidenceCorrectionId:
            current = parent[current]
            targeted.add(current)
    values: list[_Branch[RootT]] = []
    if root_id not in targeted:
        values.append(states[root_id])
    values.extend(states[identity] for identity in active if identity not in targeted)
    return tuple(values)


def _combine[RootT](
    branches: tuple[_Branch[RootT], ...],
    assertion_effective_at: Callable[[RootT], datetime],
    effective_at: datetime,
) -> EvidenceInterpretation[RootT]:
    positives = [
        branch
        for branch in branches
        if branch.assertion is not None
        and assertion_effective_at(branch.assertion) <= effective_at
    ]
    withdrawals = [branch for branch in branches if branch.withdrawn]
    gaps = [branch for branch in branches if branch not in positives + withdrawals]
    assertions = frozenset(
        branch.assertion for branch in positives if branch.assertion is not None
    )
    support = frozenset(value for branch in branches for value in branch.support)
    if len(assertions) > 1 or bool(assertions and withdrawals):
        state = EvidenceInterpretationState.CONTESTED
    elif assertions:
        state = EvidenceInterpretationState.DETERMINATE
    elif withdrawals and not gaps:
        state = EvidenceInterpretationState.WITHDRAWN
    else:
        state = EvidenceInterpretationState.NOT_EFFECTIVE
    return EvidenceInterpretation(state, assertions, support)


# duplicate-code: the module and public package facade each declare an explicit
# export contract; generating one from the other would hide API ownership.
# arid: disable
__all__ = [
    "EvidenceAssessmentCorrection",
    "EvidenceAssessmentCorrectionHistory",
    "EvidenceAssessmentCorrectionTarget",
    "EvidenceBindingCorrection",
    "EvidenceBindingCorrectionHistory",
    "EvidenceBindingCorrectionTarget",
    "EvidenceCorrection",
    "EvidenceCorrectionBasis",
    "EvidenceCorrectionEffect",
    "EvidenceInterpretation",
    "EvidenceInterpretationState",
    "EvidenceObservationCorrection",
    "EvidenceObservationCorrectionHistory",
    "EvidenceObservationCorrectionTarget",
    "InvalidEvidenceCorrection",
    "InvalidEvidenceCorrectionHistory",
    "interpret_evidence_observation",
    "interpret_evidence_binding",
    "interpret_evidence_assessment",
]
# arid: enable
