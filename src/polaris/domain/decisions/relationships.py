"""Typed Investment Decision relationship facts, interpretation, and commands."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from polaris.domain.actors import ActorAttribution

from .facts import (
    DecisionApplicability,
    DecisionInitiationContinuity,
    DecisionLifecycleDisposition,
    DecisionMutationContext,
    DecisionNeed,
    DecisionNotOperative,
    DecisionScope,
    DecisionSubject,
    DecisionVersion,
    InvalidDecisionBasis,
    InvalidDecisionHistory,
    InvalidDecisionTransition,
    InvestmentDecisionError,
    InvestmentDecisionId,
    OperationId,
    TechnicalProvenance,
    TriggerProvenance,
    _actor,
    _aware,
    _exact,
    _known_actor,
    _uuid4,
    _validate_provenance,
)
from .model import InvestmentDecision, initiate_decision


class InvalidDecisionRelationshipHistory(InvalidDecisionHistory):
    pass


class InvalidDecisionRelationshipBasis(InvalidDecisionBasis):
    pass


class DecisionRelationshipAdmissionRejected(InvalidDecisionTransition):
    pass


class DecisionLifecycleLineageCycle(DecisionRelationshipAdmissionRejected):
    """Supported lifecycle-lineage edges contain a definite directed cycle."""


class DecisionLifecycleLineageSafetyIndeterminate(
    DecisionRelationshipAdmissionRejected
):
    """A cycle is possible only with contested surviving positive edges."""


class DecisionRelationshipNotKnownAtCutoff(InvestmentDecisionError):
    pass


class DecisionRelationshipReplayConflict(InvestmentDecisionError):
    pass


class DecisionRelationshipDeterminismRequired(InvalidDecisionTransition):
    pass


@dataclass(frozen=True, slots=True)
class DecisionRelationshipFactId:
    value: UUID

    def __post_init__(self) -> None:
        _uuid4(self.value, "DecisionRelationshipFactId.value")


class DecisionRelationshipType(StrEnum):
    RENEWED_FROM = "renewed_from"
    SUPERSEDES = "supersedes"


class DecisionRelationshipCorrectionEffect(StrEnum):
    QUALIFY = "qualify"
    DISCONFIRM = "disconfirm"


class DecisionRelationshipState(StrEnum):
    SUPPORTED = "SUPPORTED"
    CONTESTED = "CONTESTED"
    WITHDRAWN = "WITHDRAWN"
    NOT_EFFECTIVE = "NOT_EFFECTIVE"


class DecisionRelationshipBasisRole(StrEnum):
    RELATIONSHIP = "relationship"
    CORRECTION = "correction"


def _basis_references(values: Iterable[str], field: str) -> frozenset[str]:
    raw = tuple(values)
    if not raw:
        raise InvalidDecisionRelationshipBasis(
            f"{field} requires at least one reference"
        )
    if any(not isinstance(value, str) or not value.strip() for value in raw):
        raise InvalidDecisionRelationshipBasis(
            f"{field} references must be non-empty strings"
        )
    clean = tuple(value.strip() for value in raw)
    if len(clean) != len(set(clean)):
        raise InvalidDecisionRelationshipBasis(f"{field} references must be unique")
    return frozenset(clean)


# duplicate-code: these purpose-specific basis types intentionally remain distinct
# domain values; sharing a base class would couple renewal, supersession, and correction
# semantics after their common validation is already centralized.
# arid: disable
@dataclass(frozen=True, slots=True, init=False)
class RenewedFromRelationshipBasis:
    references: frozenset[str]

    def __init__(self, references: Iterable[str]) -> None:
        object.__setattr__(
            self,
            "references",
            _basis_references(references, "RenewedFromRelationshipBasis"),
        )


@dataclass(frozen=True, slots=True, init=False)
class SupersedesRelationshipBasis:
    references: frozenset[str]

    def __init__(self, references: Iterable[str]) -> None:
        object.__setattr__(
            self,
            "references",
            _basis_references(references, "SupersedesRelationshipBasis"),
        )


@dataclass(frozen=True, slots=True, init=False)
class DecisionRelationshipCorrectionBasis:
    references: frozenset[str]

    def __init__(self, references: Iterable[str]) -> None:
        object.__setattr__(
            self,
            "references",
            _basis_references(references, "DecisionRelationshipCorrectionBasis"),
        )


# arid: enable


DecisionRelationshipBasis = RenewedFromRelationshipBasis | SupersedesRelationshipBasis


def _validate_relationship_context(
    operation_id: object,
    actor_attribution: object,
    trigger: object,
    technical_provenance: object,
    recorded_at: object,
    *,
    require_known_actor: bool,
) -> None:
    _exact(operation_id, OperationId, "operation_id")
    if require_known_actor:
        _known_actor(actor_attribution)
    else:
        _actor(actor_attribution)
    _validate_provenance(trigger, technical_provenance)
    _aware(recorded_at, "recorded_at")


@dataclass(frozen=True, slots=True)
class DecisionRelationshipMutationContext:
    fact_id: DecisionRelationshipFactId
    operation_id: OperationId
    actor_attribution: ActorAttribution
    trigger: TriggerProvenance
    recorded_at: datetime
    technical_provenance: TechnicalProvenance = TechnicalProvenance()

    def __post_init__(self) -> None:
        _exact(self.fact_id, DecisionRelationshipFactId, "fact_id")
        _validate_relationship_context(
            self.operation_id,
            self.actor_attribution,
            self.trigger,
            self.technical_provenance,
            self.recorded_at,
            require_known_actor=True,
        )


@dataclass(frozen=True, slots=True)
class DecisionRelationshipFactMetadata:
    relationship_fact_id: DecisionRelationshipFactId
    operation_id: OperationId
    # duplicate-code: lifecycle and relationship fact metadata deliberately remain
    # separate typed envelopes even though both carry the same attribution/provenance
    # tail and validation forwarding shape.
    # arid: disable
    actor_attribution: ActorAttribution
    trigger: TriggerProvenance
    technical_provenance: TechnicalProvenance
    recorded_at: datetime

    def __post_init__(self) -> None:
        _exact(
            self.relationship_fact_id,
            DecisionRelationshipFactId,
            "relationship_fact_id",
        )
        _validate_relationship_context(
            self.operation_id,
            self.actor_attribution,
            self.trigger,
            self.technical_provenance,
            self.recorded_at,
            require_known_actor=False,
        )

    # arid: enable


@dataclass(frozen=True, slots=True)
class DecisionRelationshipFact:
    metadata: DecisionRelationshipFactMetadata
    source_decision_id: InvestmentDecisionId
    target_decision_id: InvestmentDecisionId
    relationship_type: DecisionRelationshipType
    relationship_effective_at: datetime
    relationship_basis: DecisionRelationshipBasis

    def __post_init__(self) -> None:
        if type(self.metadata) is not DecisionRelationshipFactMetadata:
            raise InvalidDecisionRelationshipHistory("invalid relationship metadata")
        _exact(self.source_decision_id, InvestmentDecisionId, "source_decision_id")
        _exact(self.target_decision_id, InvestmentDecisionId, "target_decision_id")
        if self.source_decision_id == self.target_decision_id:
            raise DecisionLifecycleLineageCycle(
                "Decision relationship source and target must differ"
            )
        if type(self.relationship_type) is not DecisionRelationshipType:
            raise InvalidDecisionRelationshipHistory("invalid relationship type")
        _aware(self.relationship_effective_at, "relationship_effective_at")
        _require_relationship_basis(self.relationship_type, self.relationship_basis)


@dataclass(frozen=True, slots=True)
class DecisionRelationshipCorrected:
    metadata: DecisionRelationshipFactMetadata
    target_relationship_fact_id: DecisionRelationshipFactId
    effect: DecisionRelationshipCorrectionEffect
    correction_effective_at: datetime
    correction_basis: DecisionRelationshipCorrectionBasis
    replacement_relationship_effective_at: datetime | None = None
    replacement_relationship_basis: DecisionRelationshipBasis | None = None

    def __post_init__(self) -> None:
        if type(self.metadata) is not DecisionRelationshipFactMetadata:
            raise InvalidDecisionRelationshipHistory("invalid relationship metadata")
        _exact(
            self.target_relationship_fact_id,
            DecisionRelationshipFactId,
            "target_relationship_fact_id",
        )
        if type(self.effect) is not DecisionRelationshipCorrectionEffect:
            raise InvalidDecisionRelationshipHistory(
                "invalid relationship correction effect"
            )
        _aware(self.correction_effective_at, "correction_effective_at")
        if type(self.correction_basis) is not DecisionRelationshipCorrectionBasis:
            raise InvalidDecisionRelationshipBasis(
                "relationship correction requires its own correction basis"
            )
        if self.effect is DecisionRelationshipCorrectionEffect.DISCONFIRM:
            if (
                self.replacement_relationship_effective_at is not None
                or self.replacement_relationship_basis is not None
            ):
                raise InvalidDecisionRelationshipHistory(
                    "DISCONFIRM has no replacement relationship claim"
                )
        else:
            if self.replacement_relationship_effective_at is None:
                raise InvalidDecisionRelationshipHistory(
                    "QUALIFY requires replacement relationship effective time"
                )
            _aware(
                self.replacement_relationship_effective_at,
                "replacement_relationship_effective_at",
            )
            if not isinstance(
                self.replacement_relationship_basis,
                (RenewedFromRelationshipBasis, SupersedesRelationshipBasis),
            ):
                raise InvalidDecisionRelationshipBasis(
                    "QUALIFY requires a separate purpose-specific replacement basis"
                )


DecisionRelationshipHistoryFact = (
    DecisionRelationshipFact | DecisionRelationshipCorrected
)


@dataclass(frozen=True, slots=True)
class DecisionRelationshipBasisContribution:
    relationship_fact_id: DecisionRelationshipFactId
    role: DecisionRelationshipBasisRole
    basis: DecisionRelationshipBasis | DecisionRelationshipCorrectionBasis


@dataclass(frozen=True, slots=True)
class DecisionRelationshipPositiveClaim:
    relationship_effective_at: datetime
    support_fact_ids: frozenset[DecisionRelationshipFactId]
    basis_contributions: frozenset[DecisionRelationshipBasisContribution]


@dataclass(frozen=True, slots=True)
class DecisionRelationshipInterpretation:
    source_decision_id: InvestmentDecisionId
    relationship_type: DecisionRelationshipType
    target_decision_id: InvestmentDecisionId
    effective_at: datetime
    known_at: datetime
    state: DecisionRelationshipState
    support_fact_ids: frozenset[DecisionRelationshipFactId]
    basis_contributions: frozenset[DecisionRelationshipBasisContribution]
    surviving_positive_claims: frozenset[DecisionRelationshipPositiveClaim]

    def __post_init__(self) -> None:
        _aware(self.effective_at, "effective_at")
        _aware(self.known_at, "known_at")
        if type(self.state) is not DecisionRelationshipState:
            raise InvalidDecisionRelationshipHistory("invalid relationship state")


@dataclass(frozen=True, slots=True)
class DecisionRelationshipProtectionRequirements:
    """Commit must protect the complete known history, including absent edges.

    Endpoint versions and the touched groups/ancestry below are not an exhaustive
    read set. Revalidate lifecycle lineage over the authoritative complete final
    relationship history at recording_boundary, including non-endpoint paths and
    future-only facts that may not advance any endpoint version.
    """

    endpoint_decision_ids: frozenset[InvestmentDecisionId]
    lifecycle_history_decision_ids: frozenset[InvestmentDecisionId]
    correction_ancestry_fact_ids: frozenset[DecisionRelationshipFactId]
    relationship_groups: frozenset[
        tuple[InvestmentDecisionId, DecisionRelationshipType, InvestmentDecisionId]
    ]
    recording_boundary: datetime
    requires_complete_relationship_history: bool = True
    requires_graph_revalidation: bool = True
    requires_absence_revalidation: bool = True


@dataclass(frozen=True, slots=True)
class DecisionRelationshipCommandResult:
    history: tuple[DecisionRelationshipHistoryFact, ...]
    updated_decisions: tuple[InvestmentDecision, ...]
    versioned_decision_ids: frozenset[InvestmentDecisionId]
    protection_requirements: DecisionRelationshipProtectionRequirements

    def decision(self, decision_id: InvestmentDecisionId) -> InvestmentDecision:
        for decision in self.updated_decisions:
            if decision.decision_id == decision_id:
                return decision
        raise KeyError(decision_id)


@dataclass(frozen=True, slots=True)
class DecisionRenewalResult:
    decision: InvestmentDecision
    relationship_result: DecisionRelationshipCommandResult


def _metadata(
    context: DecisionRelationshipMutationContext,
) -> DecisionRelationshipFactMetadata:
    return DecisionRelationshipFactMetadata(
        context.fact_id,
        context.operation_id,
        context.actor_attribution,
        context.trigger,
        context.technical_provenance,
        context.recorded_at,
    )


def relationship_fact(
    *,
    source_decision_id: InvestmentDecisionId,
    target_decision_id: InvestmentDecisionId,
    relationship_type: DecisionRelationshipType,
    relationship_effective_at: datetime,
    relationship_basis: DecisionRelationshipBasis,
    mutation: DecisionRelationshipMutationContext,
) -> DecisionRelationshipFact:
    return DecisionRelationshipFact(
        _metadata(mutation),
        source_decision_id,
        target_decision_id,
        relationship_type,
        relationship_effective_at,
        relationship_basis,
    )


def relationship_correction(
    *,
    target_relationship_fact_id: DecisionRelationshipFactId,
    effect: DecisionRelationshipCorrectionEffect,
    correction_effective_at: datetime,
    correction_basis: DecisionRelationshipCorrectionBasis,
    mutation: DecisionRelationshipMutationContext,
    replacement_relationship_effective_at: datetime | None = None,
    replacement_relationship_basis: DecisionRelationshipBasis | None = None,
) -> DecisionRelationshipCorrected:
    return DecisionRelationshipCorrected(
        _metadata(mutation),
        target_relationship_fact_id,
        effect,
        correction_effective_at,
        correction_basis,
        replacement_relationship_effective_at,
        replacement_relationship_basis,
    )


def _require_relationship_basis(
    relationship_type: DecisionRelationshipType,
    basis: object,
) -> None:
    expected = {
        DecisionRelationshipType.RENEWED_FROM: RenewedFromRelationshipBasis,
        DecisionRelationshipType.SUPERSEDES: SupersedesRelationshipBasis,
    }[relationship_type]
    if type(basis) is not expected:
        raise InvalidDecisionRelationshipBasis(
            f"{relationship_type.value} requires {expected.__name__}"
        )


@dataclass(frozen=True, slots=True)
class _Branch:
    root_id: DecisionRelationshipFactId
    claim_effective_at: datetime | None
    support: frozenset[DecisionRelationshipFactId]
    bases: frozenset[DecisionRelationshipBasisContribution]
    withdrawn: bool = False


def _relationship_contribution(
    fact: DecisionRelationshipFact,
) -> DecisionRelationshipBasisContribution:
    return DecisionRelationshipBasisContribution(
        fact.metadata.relationship_fact_id,
        DecisionRelationshipBasisRole.RELATIONSHIP,
        fact.relationship_basis,
    )


def _correction_contributions(
    fact: DecisionRelationshipCorrected,
    *,
    include_relationship: bool,
) -> frozenset[DecisionRelationshipBasisContribution]:
    values = {
        DecisionRelationshipBasisContribution(
            fact.metadata.relationship_fact_id,
            DecisionRelationshipBasisRole.CORRECTION,
            fact.correction_basis,
        )
    }
    if include_relationship:
        assert fact.replacement_relationship_basis is not None
        values.add(
            DecisionRelationshipBasisContribution(
                fact.metadata.relationship_fact_id,
                DecisionRelationshipBasisRole.RELATIONSHIP,
                fact.replacement_relationship_basis,
            )
        )
    return frozenset(values)


def _native_branch(fact: DecisionRelationshipFact, effective_at: datetime) -> _Branch:
    effective = fact.relationship_effective_at <= effective_at
    return _Branch(
        fact.metadata.relationship_fact_id,
        fact.relationship_effective_at,
        frozenset({fact.metadata.relationship_fact_id}) if effective else frozenset(),
        frozenset({_relationship_contribution(fact)}) if effective else frozenset(),
    )


def _material_branch(branch: _Branch, effective_at: datetime) -> tuple[object, ...]:
    if branch.claim_effective_at is not None:
        if branch.claim_effective_at > effective_at:
            return ("gap", branch.support, branch.bases)
        return ("positive", branch.claim_effective_at, branch.support, branch.bases)
    if branch.withdrawn:
        return ("withdrawn", branch.support, branch.bases)
    return ("gap", branch.support, branch.bases)


def _apply_qualify(
    correction: DecisionRelationshipCorrected,
    target_state: _Branch,
    effective_at: datetime,
) -> _Branch:
    assert correction.replacement_relationship_effective_at is not None
    replacement_effective = correction.replacement_relationship_effective_at
    target_material = _material_branch(target_state, effective_at)
    include = (
        replacement_effective <= effective_at
        or target_material[0] != "gap"
        or (len(target_material) > 1 and bool(target_material[1]))
    )
    if not include:
        return _Branch(
            target_state.root_id, replacement_effective, frozenset(), frozenset()
        )
    return _Branch(
        target_state.root_id,
        replacement_effective,
        frozenset({correction.metadata.relationship_fact_id}),
        _correction_contributions(
            correction,
            include_relationship=replacement_effective <= effective_at,
        ),
    )


def _restore_correction(
    correction: DecisionRelationshipCorrected,
    target: DecisionRelationshipCorrected,
    target_state: _Branch,
    before: Mapping[DecisionRelationshipFactId, _Branch],
    effective_at: datetime,
) -> _Branch:
    restored = before[target.metadata.relationship_fact_id]
    if _material_branch(target_state, effective_at) == _material_branch(
        restored, effective_at
    ):
        return restored
    return _Branch(
        restored.root_id,
        restored.claim_effective_at,
        restored.support | {correction.metadata.relationship_fact_id},
        restored.bases
        | _correction_contributions(correction, include_relationship=False),
        restored.withdrawn,
    )


def _withdraw_base(
    correction: DecisionRelationshipCorrected,
    target: DecisionRelationshipFact,
    target_state: _Branch,
    effective_at: datetime,
) -> _Branch:
    necessary = target.relationship_effective_at <= effective_at
    if not necessary:
        return _Branch(target_state.root_id, None, frozenset(), frozenset())
    return _Branch(
        target_state.root_id,
        None,
        frozenset({correction.metadata.relationship_fact_id}),
        _correction_contributions(correction, include_relationship=False),
        withdrawn=True,
    )


def _apply_correction(
    correction: DecisionRelationshipCorrected,
    target: DecisionRelationshipHistoryFact,
    target_state: _Branch,
    before: Mapping[DecisionRelationshipFactId, _Branch],
    effective_at: datetime,
) -> _Branch:
    if correction.effect is DecisionRelationshipCorrectionEffect.QUALIFY:
        return _apply_qualify(correction, target_state, effective_at)
    if isinstance(target, DecisionRelationshipCorrected):
        return _restore_correction(
            correction, target, target_state, before, effective_at
        )
    return _withdraw_base(correction, target, target_state, effective_at)


def _index_history(
    history: tuple[DecisionRelationshipHistoryFact, ...],
) -> tuple[
    dict[DecisionRelationshipFactId, DecisionRelationshipHistoryFact],
    dict[DecisionRelationshipFactId, DecisionRelationshipFactId],
]:
    by_id: dict[DecisionRelationshipFactId, DecisionRelationshipHistoryFact] = {}
    parent: dict[DecisionRelationshipFactId, DecisionRelationshipFactId] = {}
    for fact in history:
        identity = fact.metadata.relationship_fact_id
        if identity in by_id:
            raise InvalidDecisionRelationshipHistory(
                "relationship fact identity must be globally unique"
            )
        by_id[identity] = fact
        if isinstance(fact, DecisionRelationshipCorrected):
            parent[identity] = fact.target_relationship_fact_id
    return by_id, parent


def _validate_parent_targets(
    by_id: Mapping[DecisionRelationshipFactId, DecisionRelationshipHistoryFact],
    parent: Mapping[DecisionRelationshipFactId, DecisionRelationshipFactId],
) -> None:
    for identity, target_id in parent.items():
        if target_id not in by_id:
            raise InvalidDecisionRelationshipHistory(
                "relationship correction requires complete target ancestry"
            )
        target = by_id[target_id]
        fact = by_id[identity]
        assert isinstance(fact, DecisionRelationshipCorrected)
        if target.metadata.recorded_at > fact.metadata.recorded_at:
            raise InvalidDecisionRelationshipHistory(
                "relationship correction cannot target later-recorded history"
            )


def _validate_ancestry(
    by_id: Mapping[DecisionRelationshipFactId, DecisionRelationshipHistoryFact],
    parent: Mapping[DecisionRelationshipFactId, DecisionRelationshipFactId],
) -> None:
    for identity in parent:
        seen = {identity}
        current = identity
        while current in parent:
            current = parent[current]
            if current in seen:
                raise InvalidDecisionRelationshipHistory(
                    "relationship correction ancestry must be acyclic"
                )
            seen.add(current)
        if not isinstance(by_id[current], DecisionRelationshipFact):
            raise InvalidDecisionRelationshipHistory(
                "relationship correction ancestry must root in a base fact"
            )


def _validate_correction_basis_roles(
    by_id: Mapping[DecisionRelationshipFactId, DecisionRelationshipHistoryFact],
    parent: Mapping[DecisionRelationshipFactId, DecisionRelationshipFactId],
) -> None:
    for identity in parent:
        fact = by_id[identity]
        if not isinstance(fact, DecisionRelationshipCorrected):
            continue
        if fact.effect is not DecisionRelationshipCorrectionEffect.QUALIFY:
            continue
        root = by_id[_root_id(identity, parent)]
        assert isinstance(root, DecisionRelationshipFact)
        _require_relationship_basis(
            root.relationship_type,
            fact.replacement_relationship_basis,
        )


def _history_maps(
    history: tuple[DecisionRelationshipHistoryFact, ...],
) -> tuple[
    dict[DecisionRelationshipFactId, DecisionRelationshipHistoryFact],
    dict[DecisionRelationshipFactId, DecisionRelationshipFactId],
]:
    by_id, parent = _index_history(history)
    _validate_parent_targets(by_id, parent)
    _validate_ancestry(by_id, parent)
    _validate_correction_basis_roles(by_id, parent)
    return by_id, parent


def _root_id(
    identity: DecisionRelationshipFactId,
    parent: Mapping[DecisionRelationshipFactId, DecisionRelationshipFactId],
) -> DecisionRelationshipFactId:
    while identity in parent:
        identity = parent[identity]
    return identity


def _resolve_branch_states(
    by_id: Mapping[DecisionRelationshipFactId, DecisionRelationshipHistoryFact],
    effective_at: datetime,
) -> dict[DecisionRelationshipFactId, _Branch]:
    states: dict[DecisionRelationshipFactId, _Branch] = {}
    before: dict[DecisionRelationshipFactId, _Branch] = {}
    unresolved = set(by_id)
    while unresolved:
        progress = False
        for identity in tuple(unresolved):
            fact = by_id[identity]
            if isinstance(fact, DecisionRelationshipFact):
                states[identity] = _native_branch(fact, effective_at)
            elif fact.target_relationship_fact_id in states:
                target = by_id[fact.target_relationship_fact_id]
                target_state = states[fact.target_relationship_fact_id]
                before[identity] = target_state
                states[identity] = target_state
                if fact.correction_effective_at <= effective_at:
                    states[identity] = _apply_correction(
                        fact, target, target_state, before, effective_at
                    )
            else:
                continue
            unresolved.remove(identity)
            progress = True
        if not progress:
            raise InvalidDecisionRelationshipHistory(
                "relationship correction ancestry cannot be resolved"
            )
    return states


def _active_correction_ids(
    history: tuple[DecisionRelationshipHistoryFact, ...],
    effective_at: datetime,
) -> frozenset[DecisionRelationshipFactId]:
    return frozenset(
        fact.metadata.relationship_fact_id
        for fact in history
        if isinstance(fact, DecisionRelationshipCorrected)
        and fact.correction_effective_at <= effective_at
    )


def _active_descendant_targets(
    active_ids: Iterable[DecisionRelationshipFactId],
    parent: Mapping[DecisionRelationshipFactId, DecisionRelationshipFactId],
) -> frozenset[DecisionRelationshipFactId]:
    values: set[DecisionRelationshipFactId] = set()
    for identity in active_ids:
        current = identity
        while current in parent:
            current = parent[current]
            values.add(current)
    return frozenset(values)


def _collect_branch_leaves(
    by_id: Mapping[DecisionRelationshipFactId, DecisionRelationshipHistoryFact],
    parent: Mapping[DecisionRelationshipFactId, DecisionRelationshipFactId],
    states: Mapping[DecisionRelationshipFactId, _Branch],
    active_ids: frozenset[DecisionRelationshipFactId],
    descendant_targets: frozenset[DecisionRelationshipFactId],
) -> dict[DecisionRelationshipFactId, list[_Branch]]:
    leaves: dict[DecisionRelationshipFactId, list[_Branch]] = {}
    for identity, fact in by_id.items():
        root = _root_id(identity, parent)
        if isinstance(fact, DecisionRelationshipCorrected):
            if identity not in active_ids or identity in descendant_targets:
                continue
        elif identity in descendant_targets:
            continue
        leaves.setdefault(root, []).append(states[identity])
    return leaves


def _branch_leaves(
    history: tuple[DecisionRelationshipHistoryFact, ...],
    effective_at: datetime,
) -> dict[DecisionRelationshipFactId, list[_Branch]]:
    by_id, parent = _history_maps(history)
    states = _resolve_branch_states(by_id, effective_at)
    active_ids = _active_correction_ids(history, effective_at)
    descendant_targets = _active_descendant_targets(active_ids, parent)
    return _collect_branch_leaves(by_id, parent, states, active_ids, descendant_targets)


@dataclass(frozen=True, slots=True)
class _RootResult:
    state: DecisionRelationshipState
    support: frozenset[DecisionRelationshipFactId]
    bases: frozenset[DecisionRelationshipBasisContribution]
    positives: frozenset[DecisionRelationshipPositiveClaim]


def _claim(branch: _Branch) -> DecisionRelationshipPositiveClaim:
    assert branch.claim_effective_at is not None
    return DecisionRelationshipPositiveClaim(
        branch.claim_effective_at, branch.support, branch.bases
    )


def _coalesced_claims(
    claims: Iterable[DecisionRelationshipPositiveClaim],
) -> frozenset[DecisionRelationshipPositiveClaim]:
    grouped: dict[
        datetime,
        tuple[
            set[DecisionRelationshipFactId],
            set[DecisionRelationshipBasisContribution],
        ],
    ] = {}
    for claim in claims:
        support, bases = grouped.setdefault(
            claim.relationship_effective_at, (set(), set())
        )
        support.update(claim.support_fact_ids)
        bases.update(claim.basis_contributions)
    return frozenset(
        DecisionRelationshipPositiveClaim(instant, frozenset(support), frozenset(bases))
        for instant, (support, bases) in grouped.items()
    )


def _partition_root_branches(
    branches: Iterable[_Branch],
    effective_at: datetime,
) -> tuple[list[_Branch], list[_Branch], list[_Branch]]:
    positives: list[_Branch] = []
    withdrawals: list[_Branch] = []
    gaps: list[_Branch] = []
    for branch in branches:
        if (
            branch.claim_effective_at is not None
            and branch.claim_effective_at <= effective_at
        ):
            positives.append(branch)
        elif branch.withdrawn:
            withdrawals.append(branch)
        else:
            gaps.append(branch)
    return positives, withdrawals, gaps


def _root_state(
    positives: list[_Branch],
    withdrawals: list[_Branch],
    gaps: list[_Branch],
) -> DecisionRelationshipState:
    positive_instants = {branch.claim_effective_at for branch in positives}
    if len(positive_instants) > 1 or bool(positives and withdrawals):
        return DecisionRelationshipState.CONTESTED
    if positives:
        return DecisionRelationshipState.SUPPORTED
    if withdrawals and not gaps:
        return DecisionRelationshipState.WITHDRAWN
    return DecisionRelationshipState.NOT_EFFECTIVE


def _root_result(branches: list[_Branch], effective_at: datetime) -> _RootResult:
    positives, withdrawals, gaps = _partition_root_branches(branches, effective_at)
    support = frozenset(identity for branch in branches for identity in branch.support)
    bases = frozenset(value for branch in branches for value in branch.bases)
    positive_claims = _coalesced_claims(_claim(branch) for branch in positives)
    return _RootResult(
        _root_state(positives, withdrawals, gaps),
        support,
        bases,
        positive_claims,
    )


def _relationship_roots(
    history: Iterable[DecisionRelationshipHistoryFact],
    *,
    source_decision_id: InvestmentDecisionId,
    relationship_type: DecisionRelationshipType,
    target_decision_id: InvestmentDecisionId,
) -> tuple[DecisionRelationshipFact, ...]:
    return tuple(
        fact
        for fact in history
        if isinstance(fact, DecisionRelationshipFact)
        and fact.source_decision_id == source_decision_id
        and fact.relationship_type is relationship_type
        and fact.target_decision_id == target_decision_id
    )


def _combined_relationship_state(
    results: Iterable[_RootResult],
) -> DecisionRelationshipState:
    values = tuple(results)
    if any(result.state is DecisionRelationshipState.CONTESTED for result in values):
        return DecisionRelationshipState.CONTESTED
    positives = tuple(claim for result in values for claim in result.positives)
    if len({claim.relationship_effective_at for claim in positives}) > 1:
        return DecisionRelationshipState.CONTESTED
    if positives:
        return DecisionRelationshipState.SUPPORTED
    if all(result.state is DecisionRelationshipState.WITHDRAWN for result in values):
        return DecisionRelationshipState.WITHDRAWN
    return DecisionRelationshipState.NOT_EFFECTIVE


def _known_relationship_history(
    history: Iterable[DecisionRelationshipHistoryFact],
    known_at: datetime,
) -> tuple[DecisionRelationshipHistoryFact, ...]:
    return tuple(fact for fact in history if fact.metadata.recorded_at <= known_at)


def _relationship_root_results(
    roots: Iterable[DecisionRelationshipFact],
    history: tuple[DecisionRelationshipHistoryFact, ...],
    effective_at: datetime,
) -> tuple[_RootResult, ...]:
    leaves = _branch_leaves(history, effective_at)
    return tuple(
        _root_result(leaves[fact.metadata.relationship_fact_id], effective_at)
        for fact in roots
    )


def interpret_relationship(
    history: Iterable[DecisionRelationshipHistoryFact],
    *,
    source_decision_id: InvestmentDecisionId,
    relationship_type: DecisionRelationshipType,
    target_decision_id: InvestmentDecisionId,
    effective_at: datetime,
    known_at: datetime,
) -> DecisionRelationshipInterpretation:
    _exact(source_decision_id, InvestmentDecisionId, "source_decision_id")
    _exact(target_decision_id, InvestmentDecisionId, "target_decision_id")
    if type(relationship_type) is not DecisionRelationshipType:
        raise InvalidDecisionRelationshipHistory("invalid relationship type")
    _aware(effective_at, "effective_at")
    _aware(known_at, "known_at")
    known = _known_relationship_history(history, known_at)
    _history_maps(known)
    roots = _relationship_roots(
        known,
        source_decision_id=source_decision_id,
        relationship_type=relationship_type,
        target_decision_id=target_decision_id,
    )
    if not roots:
        raise DecisionRelationshipNotKnownAtCutoff(
            "relationship group is not known at cutoff"
        )
    results = _relationship_root_results(roots, known, effective_at)
    support = frozenset(identity for result in results for identity in result.support)
    bases = frozenset(value for result in results for value in result.bases)
    positives = _coalesced_claims(
        claim for result in results for claim in result.positives
    )
    return DecisionRelationshipInterpretation(
        source_decision_id,
        relationship_type,
        target_decision_id,
        effective_at,
        known_at,
        _combined_relationship_state(results),
        support,
        bases,
        positives,
    )


def _lineage_effective_boundaries(
    history: tuple[DecisionRelationshipHistoryFact, ...],
) -> list[datetime]:
    boundaries = set()
    for fact in history:
        if isinstance(fact, DecisionRelationshipFact):
            boundaries.add(fact.relationship_effective_at)
        else:
            boundaries.add(fact.correction_effective_at)
            if fact.replacement_relationship_effective_at is not None:
                boundaries.add(fact.replacement_relationship_effective_at)
    return sorted(boundaries)


def _lineage_has_cycle(
    interpretations: Iterable[DecisionRelationshipInterpretation],
) -> bool:
    # Parallel relationship types/claims share reachability, not domain meaning.
    outgoing: dict[InvestmentDecisionId, set[InvestmentDecisionId]] = {}
    incoming: dict[InvestmentDecisionId, int] = {}
    for result in interpretations:
        source, target = result.source_decision_id, result.target_decision_id
        targets = outgoing.setdefault(source, set())
        incoming.setdefault(source, 0)
        if target not in targets:
            targets.add(target)
            incoming[target] = incoming.get(target, 0) + 1
    ready = deque(identity for identity, count in incoming.items() if count == 0)
    removed = 0
    while ready:
        identity = ready.popleft()
        removed += 1
        for target in outgoing.get(identity, ()):
            incoming[target] -= 1
            if incoming[target] == 0:
                ready.append(target)
    return removed != len(incoming)


def validate_decision_lifecycle_lineage(
    history: Iterable[DecisionRelationshipHistoryFact],
    *,
    known_at: datetime,
) -> None:
    """Certify the complete known historical and future lifecycle-lineage graph.

    Supply the complete proposed final relationship history, never just incident
    edges or a current-time projection. The combined relationship interpreter owns
    correction/support semantics. Before the first effective boundary there are
    no positive edges; between consecutive boundaries interpretation is constant,
    and the last boundary covers the unbounded final interval.

    Success is conditional on this input history and knowledge boundary. Application
    and persistence must protect/revalidate that predicate (including future facts,
    non-endpoint paths and absence) through commit; endpoint CAS cannot replace it.
    This rule applies only to the RENEWED_FROM/SUPERSEDES fact contract. A future
    purpose-specific context fact owns its own historical-target boundary and does
    not enter lifecycle-lineage validation by merely being retrieved or referenced.
    """
    _aware(known_at, "known_at")
    facts = tuple(history)
    if any(
        type(fact) not in {DecisionRelationshipFact, DecisionRelationshipCorrected}
        for fact in facts
    ):
        raise InvalidDecisionRelationshipHistory(
            "lifecycle lineage requires typed relationship facts/corrections"
        )
    known = _known_relationship_history(facts, known_at)
    _history_maps(known)
    groups = {
        (fact.source_decision_id, fact.relationship_type, fact.target_decision_id)
        for fact in known
        if isinstance(fact, DecisionRelationshipFact)
    }
    for boundary in _lineage_effective_boundaries(known):
        supported = []
        possible = []
        for source, kind, target in groups:
            result = interpret_relationship(
                known,
                source_decision_id=source,
                relationship_type=kind,
                target_decision_id=target,
                effective_at=boundary,
                known_at=known_at,
            )
            if result.state is DecisionRelationshipState.SUPPORTED:
                supported.append(result)
            elif (
                result.state is DecisionRelationshipState.CONTESTED
                and result.surviving_positive_claims
            ):
                possible.append(result)
        detail = f"effective_at={boundary.isoformat()}, known_at={known_at.isoformat()}"
        if _lineage_has_cycle(supported):
            raise DecisionLifecycleLineageCycle(detail)
        if _lineage_has_cycle((*supported, *possible)):
            raise DecisionLifecycleLineageSafetyIndeterminate(detail)


def _group_for_fact(
    identity: DecisionRelationshipFactId,
    by_id: Mapping[DecisionRelationshipFactId, DecisionRelationshipHistoryFact],
    parent: Mapping[DecisionRelationshipFactId, DecisionRelationshipFactId],
) -> tuple[InvestmentDecisionId, DecisionRelationshipType, InvestmentDecisionId]:
    root = by_id[_root_id(identity, parent)]
    assert isinstance(root, DecisionRelationshipFact)
    return root.source_decision_id, root.relationship_type, root.target_decision_id


def _eligible_endpoint(
    decision: InvestmentDecision,
    *,
    claim_effective_at: datetime,
    known_at: datetime,
) -> DecisionLifecycleDisposition:
    try:
        view = decision.effective_at(
            claim_effective_at,
            known_at=known_at,
            applicability=DecisionApplicability.OPERATIVE,
        )
        disposition = view.disposition
    except InvestmentDecisionError as error:
        raise DecisionRelationshipAdmissionRejected(
            "positive relationship endpoint lifecycle is not determinate/eligible"
        ) from error
    if disposition not in {
        DecisionLifecycleDisposition.UNRESOLVED,
        DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED,
        DecisionLifecycleDisposition.EXTERNALLY_RESOLVED,
    }:
        raise DecisionRelationshipAdmissionRejected(
            "positive relationship endpoint lifecycle is ineligible"
        )
    return disposition


def _validate_positive_admission(
    *,
    source: InvestmentDecision,
    target: InvestmentDecision,
    relationship_type: DecisionRelationshipType,
    claim_effective_at: datetime,
    known_at: datetime,
) -> None:
    _eligible_endpoint(source, claim_effective_at=claim_effective_at, known_at=known_at)
    _eligible_endpoint(target, claim_effective_at=claim_effective_at, known_at=known_at)
    if relationship_type is DecisionRelationshipType.RENEWED_FROM:
        if source.need_id == target.need_id:
            raise DecisionRelationshipAdmissionRejected(
                "RENEWED_FROM source requires its own new Decision Need"
            )
        episode_start = source.need.effective_at
        if claim_effective_at < episode_start:
            raise DecisionRelationshipAdmissionRejected(
                "RENEWED_FROM cannot predate the new Decision episode"
            )
        for instant in (episode_start, claim_effective_at):
            disposition = _eligible_endpoint(
                target, claim_effective_at=instant, known_at=known_at
            )
            if disposition not in {
                DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED,
                DecisionLifecycleDisposition.EXTERNALLY_RESOLVED,
            }:
                raise DecisionRelationshipAdmissionRejected(
                    "renewal predecessor must be resolved at episode start "
                    "and relationship effective time"
                )


def _protected_entry(
    history: tuple[DecisionRelationshipHistoryFact, ...],
    group: tuple[InvestmentDecisionId, DecisionRelationshipType, InvestmentDecisionId],
    boundary: datetime,
) -> object:
    try:
        result = interpret_relationship(
            history,
            source_decision_id=group[0],
            relationship_type=group[1],
            target_decision_id=group[2],
            effective_at=boundary,
            known_at=boundary,
        )
    except DecisionRelationshipNotKnownAtCutoff:
        return None
    if (
        result.state is DecisionRelationshipState.NOT_EFFECTIVE
        and not result.support_fact_ids
    ):
        return None
    return (
        result.state,
        result.surviving_positive_claims,
        result.support_fact_ids,
        result.basis_contributions,
    )


def _with_version(
    decision: InvestmentDecision, version: DecisionVersion
) -> InvestmentDecision:
    return InvestmentDecision._from_validated(
        decision._history,
        decision._subject,
        decision._scope,
        version,
        decision.lifecycle_interpretation,
        decision._applicability,
        decision._work_posture,
    )


def _validate_command_envelope(
    before: tuple[DecisionRelationshipHistoryFact, ...],
    proposed: tuple[DecisionRelationshipHistoryFact, ...],
    recording_boundary: datetime,
) -> None:
    if any(fact.metadata.recorded_at > recording_boundary for fact in before):
        raise InvalidDecisionRelationshipHistory(
            "recording boundary cannot precede committed relationship history"
        )
    if not proposed:
        raise InvalidDecisionRelationshipHistory(
            "relationship command requires at least one attributable fact"
        )
    if any(fact.metadata.recorded_at != recording_boundary for fact in proposed):
        raise InvalidDecisionRelationshipHistory(
            "all facts in one relationship command require the trusted "
            "recording boundary"
        )
    if len({fact.metadata.operation_id for fact in proposed}) != 1:
        raise InvalidDecisionRelationshipHistory(
            "one atomic relationship command requires one OperationId"
        )
    for fact in proposed:
        try:
            _known_actor(fact.metadata.actor_attribution)
        except InvalidDecisionTransition as error:
            raise DecisionRelationshipAdmissionRejected(
                "live relationship command requires known Actor Attribution"
            ) from error


def _require_endpoint(
    decisions: Mapping[InvestmentDecisionId, InvestmentDecision],
    identity: InvestmentDecisionId,
) -> InvestmentDecision:
    decision = decisions.get(identity)
    if not isinstance(decision, InvestmentDecision) or decision.decision_id != identity:
        raise DecisionRelationshipAdmissionRejected(
            "relationship command requires authoritative history for the exact "
            "endpoint Decision identity"
        )
    return decision


def _validate_correction_admission(
    fact: DecisionRelationshipCorrected,
    *,
    proposed_ids: frozenset[DecisionRelationshipFactId],
    post_by_id: Mapping[DecisionRelationshipFactId, DecisionRelationshipHistoryFact],
    post_parent: Mapping[DecisionRelationshipFactId, DecisionRelationshipFactId],
    decisions: Mapping[InvestmentDecisionId, InvestmentDecision],
    recording_boundary: datetime,
) -> None:
    target = post_by_id[fact.target_relationship_fact_id]
    if fact.target_relationship_fact_id in proposed_ids and (
        target.metadata.operation_id != fact.metadata.operation_id
    ):
        raise InvalidDecisionRelationshipHistory(
            "same-command correction ancestry must share OperationId"
        )
    if fact.effect is not DecisionRelationshipCorrectionEffect.QUALIFY:
        return
    group = _group_for_fact(fact.metadata.relationship_fact_id, post_by_id, post_parent)
    _require_relationship_basis(group[1], fact.replacement_relationship_basis)
    assert fact.replacement_relationship_effective_at is not None
    _validate_positive_admission(
        source=_require_endpoint(decisions, group[0]),
        target=_require_endpoint(decisions, group[2]),
        relationship_type=group[1],
        claim_effective_at=fact.replacement_relationship_effective_at,
        known_at=recording_boundary,
    )


def _validate_base_admission(
    fact: DecisionRelationshipFact,
    *,
    decisions: Mapping[InvestmentDecisionId, InvestmentDecision],
    recording_boundary: datetime,
) -> None:
    _validate_positive_admission(
        source=_require_endpoint(decisions, fact.source_decision_id),
        target=_require_endpoint(decisions, fact.target_decision_id),
        relationship_type=fact.relationship_type,
        claim_effective_at=fact.relationship_effective_at,
        known_at=recording_boundary,
    )


def _validate_proposed_admission(
    proposed: tuple[DecisionRelationshipHistoryFact, ...],
    *,
    post_by_id: Mapping[DecisionRelationshipFactId, DecisionRelationshipHistoryFact],
    post_parent: Mapping[DecisionRelationshipFactId, DecisionRelationshipFactId],
    decisions: Mapping[InvestmentDecisionId, InvestmentDecision],
    recording_boundary: datetime,
) -> None:
    proposed_ids = frozenset(fact.metadata.relationship_fact_id for fact in proposed)
    for fact in proposed:
        if isinstance(fact, DecisionRelationshipCorrected):
            _validate_correction_admission(
                fact,
                proposed_ids=proposed_ids,
                post_by_id=post_by_id,
                post_parent=post_parent,
                decisions=decisions,
                recording_boundary=recording_boundary,
            )
        else:
            _validate_base_admission(
                fact,
                decisions=decisions,
                recording_boundary=recording_boundary,
            )


def _changed_groups(
    proposed: tuple[DecisionRelationshipHistoryFact, ...],
    by_id: Mapping[DecisionRelationshipFactId, DecisionRelationshipHistoryFact],
    parent: Mapping[DecisionRelationshipFactId, DecisionRelationshipFactId],
) -> frozenset[
    tuple[InvestmentDecisionId, DecisionRelationshipType, InvestmentDecisionId]
]:
    return frozenset(
        _group_for_fact(fact.metadata.relationship_fact_id, by_id, parent)
        for fact in proposed
    )


def _touched_decisions(
    groups: Iterable[
        tuple[InvestmentDecisionId, DecisionRelationshipType, InvestmentDecisionId]
    ],
) -> frozenset[InvestmentDecisionId]:
    return frozenset(identity for group in groups for identity in (group[0], group[2]))


def _same_command_lifecycle_increment(
    decision: InvestmentDecision,
    *,
    expected: DecisionVersion,
    operation_id: OperationId,
    recording_boundary: datetime,
) -> bool:
    if decision.version != DecisionVersion(expected.value + 1):
        return False
    if not decision.history:
        return False
    metadata = decision.history[-1].metadata
    return (
        metadata.operation_id == operation_id
        and metadata.recorded_at == recording_boundary
        and metadata.decision_version == decision.version
    )


def _same_command_new_decision(
    decision: InvestmentDecision,
    *,
    operation_id: OperationId,
    recording_boundary: datetime,
) -> bool:
    if decision.version != DecisionVersion(1) or not decision._history:
        return False
    metadata = decision._history[0].metadata
    return (
        metadata.operation_id == operation_id
        and metadata.recorded_at == recording_boundary
        and metadata.decision_version == DecisionVersion(1)
    )


def _validate_touched_versions(
    touched: frozenset[InvestmentDecisionId],
    *,
    new_ids: frozenset[InvestmentDecisionId],
    decisions: Mapping[InvestmentDecisionId, InvestmentDecision],
    expected_versions: Mapping[InvestmentDecisionId, DecisionVersion],
    operation_id: OperationId,
    recording_boundary: datetime,
) -> frozenset[InvestmentDecisionId]:
    if not new_ids <= touched:
        raise InvalidDecisionRelationshipHistory(
            "new_decision_ids must be directly touched by this command"
        )
    already_versioned: set[InvestmentDecisionId] = set()
    for identity in touched:
        decision = _require_endpoint(decisions, identity)
        if identity in new_ids:
            if not _same_command_new_decision(
                decision,
                operation_id=operation_id,
                recording_boundary=recording_boundary,
            ):
                raise InvalidDecisionRelationshipHistory(
                    "new Decision must be established by this atomic command "
                    "at DecisionVersion 1"
                )
            continue
        expected = expected_versions.get(identity)
        if type(expected) is not DecisionVersion:
            raise InvalidDecisionTransition(
                "expected endpoint versions are required for touched existing Decisions"
            )
        if expected == decision.version:
            continue
        if _same_command_lifecycle_increment(
            decision,
            expected=expected,
            operation_id=operation_id,
            recording_boundary=recording_boundary,
        ):
            already_versioned.add(identity)
            continue
        raise InvalidDecisionTransition("expected DecisionVersion does not match")
    return frozenset(already_versioned)


def _relationship_version_changes(
    before: tuple[DecisionRelationshipHistoryFact, ...],
    post: tuple[DecisionRelationshipHistoryFact, ...],
    groups: frozenset[
        tuple[InvestmentDecisionId, DecisionRelationshipType, InvestmentDecisionId]
    ],
    recording_boundary: datetime,
) -> frozenset[InvestmentDecisionId]:
    changed: set[InvestmentDecisionId] = set()
    for group in groups:
        if _protected_entry(before, group, recording_boundary) == _protected_entry(
            post, group, recording_boundary
        ):
            continue
        changed.update((group[0], group[2]))
    return frozenset(changed)


def _updated_decisions(
    touched: frozenset[InvestmentDecisionId],
    *,
    new_ids: frozenset[InvestmentDecisionId],
    already_versioned: frozenset[InvestmentDecisionId],
    version_changes: frozenset[InvestmentDecisionId],
    decisions: Mapping[InvestmentDecisionId, InvestmentDecision],
) -> tuple[tuple[InvestmentDecision, ...], frozenset[InvestmentDecisionId]]:
    updated: list[InvestmentDecision] = []
    versioned: set[InvestmentDecisionId] = set(already_versioned)
    for identity in touched:
        decision = decisions[identity]
        if (
            identity in new_ids
            or identity in already_versioned
            or identity not in version_changes
        ):
            updated.append(decision)
            continue
        updated.append(
            _with_version(decision, DecisionVersion(decision.version.value + 1))
        )
        versioned.add(identity)
    return (
        tuple(sorted(updated, key=lambda item: str(item.decision_id.value))),
        frozenset(versioned),
    )


def _correction_ancestry(
    proposed: tuple[DecisionRelationshipHistoryFact, ...],
    parent: Mapping[DecisionRelationshipFactId, DecisionRelationshipFactId],
) -> frozenset[DecisionRelationshipFactId]:
    return frozenset(
        identity
        for fact in proposed
        if isinstance(fact, DecisionRelationshipCorrected)
        for identity in _ancestry_ids(fact.metadata.relationship_fact_id, parent)
    )


def apply_relationship_command(
    existing_history: Iterable[DecisionRelationshipHistoryFact],
    proposed_facts: Iterable[DecisionRelationshipHistoryFact],
    *,
    decisions: Mapping[InvestmentDecisionId, InvestmentDecision],
    expected_versions: Mapping[InvestmentDecisionId, DecisionVersion],
    recording_boundary: datetime,
    new_decision_ids: Iterable[InvestmentDecisionId] = (),
) -> DecisionRelationshipCommandResult:
    """Validate one indivisible relationship command and return only final state.

    Application/persistence owns receipt replay, transactional locking, and commit.
    Returned protection requirements identify predicates endpoint CAS cannot protect.
    existing_history must include the complete relationship timeline known at the
    trusted recording boundary. No tentative prefix is an admission result.
    """
    _aware(recording_boundary, "recording_boundary")
    before = tuple(existing_history)
    proposed = tuple(proposed_facts)
    _validate_command_envelope(before, proposed, recording_boundary)
    _history_maps(before)
    post = (*before, *proposed)
    post_by_id, post_parent = _history_maps(post)
    # duplicate-code: this aggregate admission boundary intentionally forwards the same
    # command context used by per-fact admission; another forwarding wrapper would add
    # no domain behavior and obscure the two validation phases.
    # arid: disable
    _validate_proposed_admission(
        proposed,
        post_by_id=post_by_id,
        post_parent=post_parent,
        decisions=decisions,
        recording_boundary=recording_boundary,
    )
    # arid: enable
    validate_decision_lifecycle_lineage(post, known_at=recording_boundary)
    groups = _changed_groups(proposed, post_by_id, post_parent)
    touched = _touched_decisions(groups)
    new_ids = frozenset(new_decision_ids)
    operation_id = proposed[0].metadata.operation_id
    already_versioned = _validate_touched_versions(
        touched,
        new_ids=new_ids,
        decisions=decisions,
        expected_versions=expected_versions,
        operation_id=operation_id,
        recording_boundary=recording_boundary,
    )
    version_changes = _relationship_version_changes(
        before, post, groups, recording_boundary
    )
    updated, versioned = _updated_decisions(
        touched,
        new_ids=new_ids,
        already_versioned=already_versioned,
        version_changes=version_changes,
        decisions=decisions,
    )
    requirements = DecisionRelationshipProtectionRequirements(
        touched,
        touched,
        _correction_ancestry(proposed, post_parent),
        groups,
        recording_boundary,
    )
    return DecisionRelationshipCommandResult(post, updated, versioned, requirements)


def _ancestry_ids(
    identity: DecisionRelationshipFactId,
    parent: Mapping[DecisionRelationshipFactId, DecisionRelationshipFactId],
) -> frozenset[DecisionRelationshipFactId]:
    values = set()
    while identity in parent:
        identity = parent[identity]
        values.add(identity)
    return frozenset(values)


def derive_relationship_applicability(
    decision_id: InvestmentDecisionId,
    history: Iterable[DecisionRelationshipHistoryFact],
    *,
    effective_at: datetime,
    known_at: datetime,
) -> DecisionApplicability:
    """Derive current operative applicability from incoming Supersession groups."""
    _exact(decision_id, InvestmentDecisionId, "decision_id")
    _aware(effective_at, "effective_at")
    _aware(known_at, "known_at")
    facts = tuple(history)
    groups = {
        (fact.source_decision_id, fact.target_decision_id)
        for fact in facts
        if isinstance(fact, DecisionRelationshipFact)
        and fact.relationship_type is DecisionRelationshipType.SUPERSEDES
        and fact.target_decision_id == decision_id
        and fact.metadata.recorded_at <= known_at
    }
    states = []
    for source_id, target_id in groups:
        result = interpret_relationship(
            facts,
            source_decision_id=source_id,
            relationship_type=DecisionRelationshipType.SUPERSEDES,
            target_decision_id=target_id,
            effective_at=effective_at,
            known_at=known_at,
        )
        states.append(result.state)
    if DecisionRelationshipState.CONTESTED in states:
        return DecisionApplicability.CONTESTED
    if DecisionRelationshipState.SUPPORTED in states:
        return DecisionApplicability.NON_OPERATIVE
    return DecisionApplicability.OPERATIVE


def require_determinate_relationship_applicability(
    applicability: DecisionApplicability,
) -> None:
    if applicability is DecisionApplicability.CONTESTED:
        raise DecisionRelationshipDeterminismRequired(
            "ordinary work requires determinate relationship applicability"
        )
    if applicability is DecisionApplicability.NON_OPERATIVE:
        raise DecisionNotOperative(
            "ordinary work is prohibited for a non-operative Decision"
        )
    if applicability is not DecisionApplicability.OPERATIVE:
        raise InvalidDecisionTransition("Decision applicability is invalid")


def reconcile_relationship_replay(
    *,
    operation_id: OperationId,
    stored_operation_id: OperationId,
    semantic_request_matches: bool,
) -> bool:
    """Return True for exact replay; Application/persistence returns its receipt."""
    _exact(operation_id, OperationId, "operation_id")
    _exact(stored_operation_id, OperationId, "stored_operation_id")
    if operation_id != stored_operation_id:
        return False
    if semantic_request_matches is not True:
        raise DecisionRelationshipReplayConflict(
            "same OperationId reused for a different relationship request"
        )
    return True


def _renewal_predecessor_map(
    predecessors: tuple[InvestmentDecision, ...],
) -> dict[InvestmentDecisionId, InvestmentDecision]:
    values = {item.decision_id: item for item in predecessors}
    if len(values) != len(predecessors):
        raise InvalidDecisionRelationshipHistory(
            "renewal predecessors must be unique Decisions"
        )
    return values


def _validate_renewal_facts(
    facts: tuple[DecisionRelationshipFact, ...],
    *,
    decision_id: InvestmentDecisionId,
    predecessor_ids: frozenset[InvestmentDecisionId],
    initiation_mutation: DecisionMutationContext,
) -> None:
    if any(
        fact.relationship_type is not DecisionRelationshipType.RENEWED_FROM
        or fact.source_decision_id != decision_id
        or fact.target_decision_id not in predecessor_ids
        for fact in facts
    ):
        raise DecisionRelationshipAdmissionRejected(
            "renewal facts must link the new Decision to supplied predecessors"
        )
    if {fact.target_decision_id for fact in facts} != predecessor_ids:
        raise DecisionRelationshipAdmissionRejected(
            "every supplied renewal predecessor requires an explicit relationship fact"
        )
    if any(
        fact.metadata.operation_id != initiation_mutation.operation_id
        or fact.metadata.recorded_at != initiation_mutation.recorded_at
        for fact in facts
    ):
        raise InvalidDecisionRelationshipHistory(
            "renewal initiation and relationship facts must share one atomic "
            "command boundary"
        )


def renew_decision(
    *,
    existing_relationship_history: Iterable[DecisionRelationshipHistoryFact],
    renewal_facts: Iterable[DecisionRelationshipFact],
    predecessor_decisions: Iterable[InvestmentDecision],
    decision_id: InvestmentDecisionId,
    need: DecisionNeed,
    subject: DecisionSubject,
    scope: DecisionScope,
    continuity: DecisionInitiationContinuity,
    initiation_mutation: DecisionMutationContext,
    expected_versions: Mapping[InvestmentDecisionId, DecisionVersion],
    existing_decision_for_need: InvestmentDecisionId | None = None,
) -> DecisionRenewalResult:
    """Create one new Decision episode and validate all renewal links atomically."""
    facts = tuple(renewal_facts)
    predecessors = tuple(predecessor_decisions)
    if not facts or not predecessors:
        raise DecisionRelationshipAdmissionRejected(
            "renewal requires at least one causal predecessor"
        )
    decision = initiate_decision(
        decision_id=decision_id,
        need=need,
        subject=subject,
        scope=scope,
        continuity=continuity,
        mutation=initiation_mutation,
        existing_decision_for_need=existing_decision_for_need,
    )
    predecessor_by_id = _renewal_predecessor_map(predecessors)
    _validate_renewal_facts(
        facts,
        decision_id=decision_id,
        predecessor_ids=frozenset(predecessor_by_id),
        initiation_mutation=initiation_mutation,
    )
    decisions = {decision.decision_id: decision, **predecessor_by_id}
    result = apply_relationship_command(
        existing_relationship_history,
        facts,
        decisions=decisions,
        expected_versions=expected_versions,
        recording_boundary=initiation_mutation.recorded_at,
        new_decision_ids={decision.decision_id},
    )
    return DecisionRenewalResult(result.decision(decision.decision_id), result)
