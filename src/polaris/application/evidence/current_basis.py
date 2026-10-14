"""Assemble an exact current Evidence command basis from authoritative owner reads."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

from polaris.application.decisions.contracts import (
    LifecycleConflict,
    PersistenceUnavailable,
    RelationshipHistoryInvalidOrIncomplete,
)
from polaris.application.decisions.memory import (
    DecisionMemoryService,
    DecisionMemoryView,
)
from polaris.application.decisions.ordinary_work import DecisionNotFound
from polaris.domain.configuration import (
    EvidenceRequirementApplicabilityKey,
    EvidenceRequirementSetVersionId,
)
from polaris.domain.decisions import (
    ContestedDecisionLifecycleInterpretation,
    DecisionRelationshipState,
    DeterminateDecisionLifecycleInterpretation,
    NotYetEffectiveDecisionLifecycleInterpretation,
)
from polaris.domain.decisions.facts import DecisionVersion
from polaris.domain.evidence.claims import ClaimCatalogVersion
from polaris.domain.evidence.context_versions import (
    BasisScopeKey,
    CanonicalContextVersionRef,
    ContextSelectionGuard,
    DecisionContextVersionRef,
    context_root,
    is_canonical_context_version_ref,
)
from polaris.domain.evidence.corrections import (
    EvidenceInterpretationState,
    EvidenceObservationCorrectionHistory,
    InvalidEvidenceCorrectionHistory,
)
from polaris.domain.evidence.judgment_versions import (
    TargetJudgmentVersionRef,
    is_target_judgment_version_ref,
)
from polaris.domain.evidence.judgments import ClaimSpecificEvidenceScope
from polaris.domain.evidence.observations import (
    EvidenceBindingId,
    EvidenceFactRef,
    EvidenceSufficiencyAssessmentId,
    EvidenceSupportVersion,
    is_evidence_fact_ref,
)
from polaris.domain.evidence.sufficiency import (
    EvidenceBindingUniverseGuard,
    EvidenceCorrectionUniverseGuard,
    EvidenceRequirementAuthorityGuard,
    EvidenceSufficiencyEvaluation,
    InvalidEvidenceSufficiency,
    evaluate_evidence_sufficiency,
    matches_historical_assessment_requirement_version,
)

from .claims import (
    ClaimCatalogMembershipResolver,
    ContestedClaimHistory,
    InvalidClaimHistory,
    ResolvedClaimMembership,
    UnavailableClaimCatalog,
)
from .context_versions import (
    CompleteContextSelection,
    ContextNoBasis,
    ContextNoBasisReason,
    ContextSelectionResolver,
)
from .contracts import EvidenceCommandReadUnavailable
from .judgment_versions import (
    ResolvedTargetJudgment,
    TargetJudgmentContested,
    TargetJudgmentInvalidHistory,
    TargetJudgmentMissing,
    TargetJudgmentResolver,
    TargetJudgmentUnavailable,
    TargetJudgmentWithdrawn,
)
from .owner_meaning import (
    CanonicalContextAbsence,
    CanonicalContextMeaning,
    ClaimMembershipMeaning,
    GoverningDecisionMeaning,
    OwnerMeaningNoBasis,
    OwnerMeaningNoBasisReason,
    OwnerMeaningReader,
    OwnerMeaningResolver,
    OwnerMeaningSubject,
    OwnerMeaningWitness,
    TargetJudgmentMeaning,
)
from .reconstruction import (
    EvidenceHistories,
    HistoricalEvidenceItem,
    StaleEvidenceBasis,
    StaleEvidenceBasisCategory,
)
from .requirements import (
    ContestedEvidenceRequirementAuthority,
    EvidenceRequirementVersionResolver,
    InvalidEvidenceRequirementAuthority,
    MissingEvidenceRequirementAuthority,
    ResolvedEvidenceRequirementVersion,
    UnavailableEvidenceRequirementAuthority,
)
from .sufficiency import (
    EvidenceSufficiencyBasis,
    EvidenceSufficiencyBasisResolution,
    EvidenceSufficiencyInvalidHistory,
)
from .support_epochs import EvidenceSupportEpochReader

if TYPE_CHECKING:
    from polaris.application.decisions.owner_meaning import DecisionOwnerMeaning


class CurrentNoBasisReason(StrEnum):
    # duplicate-code: this query result and the owner-read result have separate
    # public contracts even where their failure words coincide.
    # arid: disable
    MISSING = "missing"
    INCOMPLETE = "incomplete"
    CONTESTED = "contested"
    NOT_YET_EFFECTIVE = "not_yet_effective"
    # arid: enable
    INVALID_HISTORY = "invalid_history"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class CurrentEvidenceNoBasis:
    key: BasisScopeKey
    at: datetime
    reason: CurrentNoBasisReason
    detail: str


@dataclass(frozen=True, slots=True)
class ResolvedRequirementKey:
    """Owner-attested complete applicability coordinates for this Evidence key."""

    key: BasisScopeKey
    at: datetime
    applicability_key: EvidenceRequirementApplicabilityKey

    def __post_init__(self) -> None:
        if (
            self.applicability_key.target != self.key.target
            or self.applicability_key.scope != self.key.scope
            or self.applicability_key.evidence_use is not self.key.use
        ):
            raise ValueError("requirement key must match the exact Evidence basis key")
        _aware(self.at)


class RequirementKeyOwnerReader(Protocol):
    """Resolve applicability from the already captured target and context meaning."""

    async def read_current(
        self,
        key: BasisScopeKey,
        target: ResolvedTargetJudgment,
        context: CompleteContextSelection,
        *,
        at: datetime,
    ) -> ResolvedRequirementKey | CurrentEvidenceNoBasis: ...


class CurrentSufficiencyReader(Protocol):
    async def load_sufficiency_basis(
        self,
        applicability_key: EvidenceRequirementApplicabilityKey,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> EvidenceSufficiencyBasisResolution: ...


class EvidenceHistoryIncomplete(Exception):
    """The Evidence owner cannot attest a complete selected family."""


class EvidenceHistoryInvalid(Exception):
    """The selected Evidence history cannot be interpreted as valid facts."""


class CurrentEvidenceHistoryReader(Protocol):
    """Attest complete scoped binding, assessment and observation ancestry."""

    async def load_scope_histories(
        self, key: BasisScopeKey, *, at: datetime
    ) -> EvidenceHistories: ...


@dataclass(frozen=True, slots=True)
class ClaimMembershipGuard:
    key: BasisScopeKey
    membership: ResolvedClaimMembership


@dataclass(frozen=True, slots=True)
class CurrentEvidenceSelection:
    """Complete visible histories for the exact target/scope/use at T=K."""

    observations: tuple[HistoricalEvidenceItem, ...]
    bindings: tuple[HistoricalEvidenceItem, ...]
    assessments: tuple[HistoricalEvidenceItem, ...]
    current_assessments: tuple[HistoricalEvidenceItem, ...]

    @property
    def fact_support(self) -> frozenset[EvidenceFactRef]:
        return frozenset(
            fact
            for family in (self.observations, self.bindings, self.assessments)
            for item in family
            for fact in item.interpretation.fact_support
        )


@dataclass(frozen=True, slots=True)
class CurrentEvidenceGuards:
    """Typed selected-family and ancestry witnesses scoped by the enclosing key."""

    binding_ids: frozenset[EvidenceBindingId]
    assessment_ids: frozenset[EvidenceSufficiencyAssessmentId]
    fact_support: frozenset[EvidenceFactRef]
    claim: ClaimMembershipGuard | None


@dataclass(frozen=True, slots=True)
class CurrentOwnerMeaning:
    """Verified causes for every positive and selected-or-absent owner dependency."""

    decision: OwnerMeaningWitness
    target: OwnerMeaningWitness
    claim: OwnerMeaningWitness | None
    context: tuple[OwnerMeaningWitness, ...]

    def __post_init__(self) -> None:
        if (
            type(self.decision) is not OwnerMeaningWitness
            or type(self.target) is not OwnerMeaningWitness
            or (self.claim is not None and type(self.claim) is not OwnerMeaningWitness)
            or type(self.context) is not tuple
            or any(type(item) is not OwnerMeaningWitness for item in self.context)
        ):
            raise TypeError("owner meaning requires complete typed witnesses")


@dataclass(frozen=True, slots=True)
class CurrentEvidenceBasis:
    """One command-usable, owner-sourced current basis at explicit T=K."""

    key: BasisScopeKey
    at: datetime
    decision: DecisionMemoryView
    target: ResolvedTargetJudgment
    requirement_key: EvidenceRequirementApplicabilityKey
    sufficiency: EvidenceSufficiencyBasis
    evaluation: EvidenceSufficiencyEvaluation
    context: CompleteContextSelection
    evidence: CurrentEvidenceSelection
    support_version: EvidenceSupportVersion
    guards: CurrentEvidenceGuards
    owner_meaning: CurrentOwnerMeaning

    def __post_init__(self) -> None:
        _aware(self.at)
        self._validate_identity()
        self._validate_guards()
        if not _owner_meaning_matches(
            self.key,
            self.at,
            self.decision,
            self.target,
            self.context,
            self.guards.claim,
            self.owner_meaning,
        ):
            raise ValueError("owner meaning must match current dependencies")

    def _validate_identity(self) -> None:
        if type(self.key) is not BasisScopeKey:
            raise TypeError("basis requires a typed BasisScopeKey")
        if type(self.decision) is not DecisionMemoryView:
            raise TypeError("basis requires a versioned DecisionMemoryView")
        if self.decision.decision_id != self.key.decision_id:
            raise ValueError("governing Decision must match the Evidence key")
        if self.target.target != self.key.target:
            raise ValueError("owner target must match the Evidence key")
        if self.target.effective_at != self.at or self.target.known_at != self.at:
            raise ValueError("target owner result must attest current T=K")
        if self.context.key != self.key or self.context.at != self.at:
            raise ValueError("context must attest the exact key and T=K")
        if (
            self.requirement_key.target != self.key.target
            or self.requirement_key.scope != self.key.scope
            or self.requirement_key.evidence_use is not self.key.use
        ):
            raise ValueError("requirement coordinates must match the exact key")
        if self.support_version != self.sufficiency.support_version:
            raise ValueError("Evidence epoch must match the sufficiency owner read")

    def _validate_guards(self) -> None:
        if self.guards.fact_support != self.evidence.fact_support:
            raise ValueError("Evidence ancestry guard must cover all selected support")
        if self.guards.binding_ids != frozenset(
            item.root.binding_id for item in self.evidence.bindings
        ) or self.guards.assessment_ids != frozenset(
            item.root.assessment_id for item in self.evidence.assessments
        ):
            raise ValueError("Evidence selection guards must cover complete roots")
        if type(self.key.scope) is ClaimSpecificEvidenceScope:
            if (
                self.guards.claim is None
                or self.guards.claim.key != self.key
                or self.guards.claim.membership.target != self.key.target
                or self.guards.claim.membership.claim_id != self.key.scope.claim_id
            ):
                raise ValueError("claim-specific basis requires exact membership guard")
        elif self.guards.claim is not None:
            raise ValueError("judgment-wide basis cannot carry claim membership")

    @property
    def claim_catalog_version(self) -> ClaimCatalogVersion | None:
        return (
            None
            if self.guards.claim is None
            else self.guards.claim.membership.catalog_version
        )


def _witness_at(witness: OwnerMeaningWitness, key: BasisScopeKey, at: datetime) -> bool:
    return (
        type(witness) is OwnerMeaningWitness
        and witness.key == key
        and witness.effective_at == at
        and witness.known_at == at
        and witness.read_at == at
        and witness.cause.complete
    )


def _decision_meaning(view: DecisionMemoryView) -> DecisionOwnerMeaning | None:
    from polaris.application.decisions.owner_meaning import (
        DecisionOwnerMeaning,
        DecisionRelationshipMeaning,
    )

    interpretation = view.lifecycle_interpretation
    if type(interpretation) is not DeterminateDecisionLifecycleInterpretation:
        return None
    lineage = tuple(
        DecisionRelationshipMeaning(
            item.source_decision_id,
            item.target_decision_id,
            item.relationship_type,
            item.direction,
            item.state,
            item.support_fact_ids,
            item.basis_contributions,
            item.surviving_positive_claims,
        )
        for item in view.lineage
        if item.state is DecisionRelationshipState.SUPPORTED
    )
    return DecisionOwnerMeaning(
        view.need,
        view.subject,
        view.scope,
        interpretation.disposition,
        interpretation.support_fact_ids,
        view.work_posture,
        view.applicability,
        lineage,
    )


def _owner_meaning_matches(
    key: BasisScopeKey,
    at: datetime,
    decision: DecisionMemoryView,
    target: ResolvedTargetJudgment,
    context: CompleteContextSelection,
    claim: ClaimMembershipGuard | None,
    meaning: CurrentOwnerMeaning,
) -> bool:
    from polaris.application.decisions.owner_meaning import (
        DecisionMeaningProvenance,
        DecisionRelationshipGuard,
    )

    expected_decision = _decision_meaning(decision)
    decision_proof = meaning.decision
    if (
        expected_decision is None
        or not _witness_at(decision_proof, key, at)
        or decision_proof.subject
        != GoverningDecisionMeaning(
            DecisionContextVersionRef(key.decision_id, decision.version)
        )
        or decision_proof.meaning != expected_decision
        or decision_proof.provenance is not DecisionMeaningProvenance.R2_DECISION_MEMORY
        or DecisionRelationshipGuard(key, expected_decision.lineage)
        not in decision_proof.cause.relationship_guards
    ):
        return False
    target_proof = meaning.target
    if (
        target.target != key.target
        or target.effective_at != at
        or target.known_at != at
        or not _witness_at(target_proof, key, at)
        or target_proof.subject != TargetJudgmentMeaning(target.version)
    ):
        return False
    if claim is None:
        if meaning.claim is not None:
            return False
    else:
        claim_proof = meaning.claim
        if (
            claim_proof is None
            or not _witness_at(claim_proof, key, at)
            or claim_proof.subject
            != ClaimMembershipMeaning(
                key.target,
                claim.membership.claim_id,
                claim.membership.catalog_version,
            )
        ):
            return False
    expected_context: list[OwnerMeaningSubject] = []
    for selection in context.selections:
        if selection.facts:
            expected_context.extend(
                CanonicalContextMeaning(selection.role, fact.reference, selection.guard)
                for fact in selection.facts
            )
        else:
            expected_context.append(
                CanonicalContextAbsence(selection.role, selection.guard)
            )
    return len(meaning.context) == len(expected_context) and all(
        _witness_at(proof, key, at) and proof.subject == subject
        for proof, subject in zip(meaning.context, expected_context, strict=True)
    )


type CurrentEvidenceBasisResult = CurrentEvidenceBasis | CurrentEvidenceNoBasis


class BasisPositiveRole(StrEnum):
    DECISION = "decision"
    TARGET = "target"
    CLAIM = "claim"
    REQUIREMENT = "requirement"
    EVIDENCE_SUPPORT = "evidence_support"
    CONTEXT = "context"


type BasisPositiveReference = (
    DecisionVersion
    | TargetJudgmentVersionRef
    | ClaimCatalogVersion
    | EvidenceRequirementSetVersionId
    | EvidenceRequirementApplicabilityKey
    | EvidenceSupportVersion
    | EvidenceFactRef
    | CanonicalContextVersionRef
)

type PositiveRecorder = Callable[
    [BasisPositiveRole, BasisPositiveReference | None, BasisPositiveReference | None],
    None,
]


@dataclass(frozen=True, slots=True)
class BasisPositiveChange:
    role: BasisPositiveRole
    prior: BasisPositiveReference | None
    fresh: BasisPositiveReference | None

    def __post_init__(self) -> None:
        if type(self.role) is not BasisPositiveRole:
            raise TypeError("positive dependency role must be typed")
        if any(
            value is not None and not _positive_reference_matches(self.role, value)
            for value in (self.prior, self.fresh)
        ):
            raise TypeError("positive reference must match its dependency role")
        if self.role not in (
            BasisPositiveRole.CONTEXT,
            BasisPositiveRole.EVIDENCE_SUPPORT,
        ) and (self.prior is None or self.fresh is None):
            raise ValueError("required owner and authority references cannot be absent")
        if self.prior == self.fresh or (self.prior is None and self.fresh is None):
            raise ValueError("changed reference must have distinct endpoints")


def _positive_reference_matches(
    role: BasisPositiveRole, value: BasisPositiveReference
) -> bool:
    if role is BasisPositiveRole.DECISION:
        return type(value) is DecisionVersion
    if role is BasisPositiveRole.TARGET:
        return is_target_judgment_version_ref(value)
    if role is BasisPositiveRole.CLAIM:
        return type(value) is ClaimCatalogVersion
    if role is BasisPositiveRole.REQUIREMENT:
        return type(value) in (
            EvidenceRequirementSetVersionId,
            EvidenceRequirementApplicabilityKey,
        )
    if role is BasisPositiveRole.EVIDENCE_SUPPORT:
        return type(value) is EvidenceSupportVersion or is_evidence_fact_ref(value)
    return is_canonical_context_version_ref(value)


@dataclass(frozen=True, slots=True)
class BasisOwnerMeaningChange:
    role: BasisPositiveRole
    prior: OwnerMeaningWitness
    fresh: OwnerMeaningWitness

    def __post_init__(self) -> None:
        if (
            type(self.role) is not BasisPositiveRole
            or type(self.prior) is not OwnerMeaningWitness
            or type(self.fresh) is not OwnerMeaningWitness
        ):
            raise TypeError("owner meaning change requires typed witnesses and role")
        if self.role not in (
            BasisPositiveRole.DECISION,
            BasisPositiveRole.TARGET,
            BasisPositiveRole.CLAIM,
            BasisPositiveRole.CONTEXT,
        ):
            raise ValueError("owner meaning change requires an owner role")
        if not all(
            _owner_meaning_role_matches(self.role, witness.subject)
            for witness in (self.prior, self.fresh)
        ):
            raise TypeError("owner meaning subjects must match their dependency role")
        if self.prior.key != self.fresh.key or _owner_subject_identity(
            self.prior.subject
        ) != _owner_subject_identity(self.fresh.subject):
            raise ValueError("meaning change requires one exact owner reference")
        if (self.prior.meaning, self.prior.provenance) == (
            self.fresh.meaning,
            self.fresh.provenance,
        ):
            raise ValueError("owner meaning change requires distinct interpretations")


def _owner_meaning_role_matches(
    role: BasisPositiveRole, subject: OwnerMeaningSubject
) -> bool:
    if role is BasisPositiveRole.DECISION:
        return isinstance(subject, GoverningDecisionMeaning)
    if role is BasisPositiveRole.TARGET:
        return isinstance(subject, TargetJudgmentMeaning)
    if role is BasisPositiveRole.CLAIM:
        return isinstance(subject, ClaimMembershipMeaning)
    return isinstance(subject, (CanonicalContextMeaning, CanonicalContextAbsence))


def _owner_subject_identity(subject: OwnerMeaningSubject) -> tuple[object, ...]:
    if isinstance(subject, GoverningDecisionMeaning):
        return (GoverningDecisionMeaning, subject.reference)
    if isinstance(subject, TargetJudgmentMeaning):
        return (TargetJudgmentMeaning, subject.reference)
    if isinstance(subject, ClaimMembershipMeaning):
        return (
            ClaimMembershipMeaning,
            subject.target,
            subject.claim_id,
            subject.catalog_version,
        )
    if isinstance(subject, CanonicalContextMeaning):
        return (CanonicalContextMeaning, subject.role, subject.reference)
    return (CanonicalContextAbsence, subject.role)


class BasisGuardRole(StrEnum):
    CONTEXT_SELECTION = "context_selection"
    CLAIM_MEMBERSHIP = "claim_membership"
    REQUIREMENT_AUTHORITY = "requirement_authority"
    EVIDENCE_SELECTION = "evidence_selection"
    SUFFICIENCY_BINDINGS = "sufficiency_bindings"
    SUFFICIENCY_CORRECTIONS = "sufficiency_corrections"


@dataclass(frozen=True, slots=True)
class EvidenceSelectionGuard:
    binding_ids: frozenset[EvidenceBindingId]
    assessment_ids: frozenset[EvidenceSufficiencyAssessmentId]
    fact_support: frozenset[EvidenceFactRef]

    @classmethod
    def from_basis(cls, basis: CurrentEvidenceBasis) -> EvidenceSelectionGuard:
        guards = basis.guards
        return cls(guards.binding_ids, guards.assessment_ids, guards.fact_support)


type BasisNegativeGuard = (
    ContextSelectionGuard
    | ClaimMembershipGuard
    | EvidenceSelectionGuard
    | EvidenceBindingUniverseGuard
    | EvidenceCorrectionUniverseGuard
    | EvidenceRequirementAuthorityGuard
)


@dataclass(frozen=True, slots=True)
class BasisGuardBreak:
    role: BasisGuardRole
    prior: BasisNegativeGuard
    fresh: BasisNegativeGuard

    def __post_init__(self) -> None:
        expected = {
            BasisGuardRole.CONTEXT_SELECTION: ContextSelectionGuard,
            BasisGuardRole.CLAIM_MEMBERSHIP: ClaimMembershipGuard,
            BasisGuardRole.REQUIREMENT_AUTHORITY: EvidenceRequirementAuthorityGuard,
            BasisGuardRole.EVIDENCE_SELECTION: EvidenceSelectionGuard,
            BasisGuardRole.SUFFICIENCY_BINDINGS: EvidenceBindingUniverseGuard,
            BasisGuardRole.SUFFICIENCY_CORRECTIONS: EvidenceCorrectionUniverseGuard,
        }
        if type(self.role) is not BasisGuardRole or any(
            type(value) is not expected[self.role] for value in (self.prior, self.fresh)
        ):
            raise TypeError("broken guard must match its typed dependency role")
        if self.prior == self.fresh:
            raise ValueError("broken guard must have distinct endpoints")


def compare_current_evidence_bases(
    prior: CurrentEvidenceBasis, fresh: CurrentEvidenceBasisResult
) -> StaleEvidenceBasis | CurrentEvidenceNoBasis | None:
    """Classify two complete owner-attested reads for the same exact key.

    The caller supplies the fresh trusted T=K. A dependent write separately
    revalidates both owner proofs within its atomic validation boundary.
    """
    _require_comparable_bases(prior, fresh)
    if isinstance(fresh, CurrentEvidenceNoBasis):
        return fresh

    meaning_changes = _owner_meaning_changes(prior, fresh)
    authority_failure = _authority_mismatch(prior, fresh, meaning_changes)
    if authority_failure is not None:
        return authority_failure
    evaluation_failure = _evaluation_failure(prior, fresh)
    if evaluation_failure is not None:
        return evaluation_failure

    changes = _positive_changes(prior, fresh)
    broken = _broken_guards(prior, fresh)
    categories_by_role = {
        BasisPositiveRole.DECISION: StaleEvidenceBasisCategory.DECISION_CHANGED,
        BasisPositiveRole.TARGET: StaleEvidenceBasisCategory.TARGET_CHANGED,
        BasisPositiveRole.CLAIM: StaleEvidenceBasisCategory.CLAIM_CHANGED,
        BasisPositiveRole.REQUIREMENT: StaleEvidenceBasisCategory.REQUIREMENTS_CHANGED,
        BasisPositiveRole.EVIDENCE_SUPPORT: (
            StaleEvidenceBasisCategory.EVIDENCE_SUPPORT_CHANGED
        ),
        BasisPositiveRole.CONTEXT: StaleEvidenceBasisCategory.EVIDENCE_SUPPORT_CHANGED,
    }
    changed_roles = [change.role for change in changes]
    changed_roles.extend(change.role for change in meaning_changes)
    categories = {categories_by_role[role] for role in changed_roles}
    if broken:
        categories.add(StaleEvidenceBasisCategory.NEGATIVE_PREDICATE_BROKEN)
    if _evidence_changed_only_through_time(prior, fresh):
        categories.add(StaleEvidenceBasisCategory.SUPPORT_CHANGED_BY_TIME)
    if not categories and _evidence_result_changed(prior, fresh):
        return _invalid(
            prior.key,
            fresh.at,
            "Evidence meaning changed without an attributable dependency or time cause",
        )
    if not categories:
        return None
    return StaleEvidenceBasis(
        frozenset(categories), tuple(changes), tuple(broken), tuple(meaning_changes)
    )


def _require_comparable_bases(
    prior: CurrentEvidenceBasis, fresh: CurrentEvidenceBasisResult
) -> None:
    if type(prior) is not CurrentEvidenceBasis:
        raise TypeError("prior must be a complete CurrentEvidenceBasis")
    if type(fresh) not in (CurrentEvidenceBasis, CurrentEvidenceNoBasis):
        raise TypeError("fresh must be a typed current-basis result")
    if fresh.key != prior.key or fresh.at < prior.at:
        raise ValueError("fresh result must have the same key and a later T=K")


def _evaluation_failure(
    prior: CurrentEvidenceBasis, fresh: CurrentEvidenceBasis
) -> CurrentEvidenceNoBasis | None:
    for basis in (prior, fresh):
        try:
            expected = evaluate_evidence_sufficiency(
                basis.sufficiency.requirement_version,
                basis.requirement_key,
                basis.sufficiency.interpretations,
                effective_at=basis.at,
                known_at=basis.at,
            )
        except (InvalidEvidenceSufficiency, ValueError) as error:
            return _invalid(prior.key, fresh.at, str(error))
        if basis.evaluation != expected:
            return _invalid(
                prior.key,
                fresh.at,
                "Evidence fitness is not entailed by the attested basis at T=K",
            )
    return None


def _evidence_result_changed(
    prior: CurrentEvidenceBasis, fresh: CurrentEvidenceBasis
) -> bool:
    return (
        prior.evaluation != fresh.evaluation
        or prior.evidence != fresh.evidence
        or prior.sufficiency.interpretations != fresh.sufficiency.interpretations
    )


def _owner_meaning_changes(
    prior: CurrentEvidenceBasis, fresh: CurrentEvidenceBasis
) -> list[BasisOwnerMeaningChange]:
    old = prior.owner_meaning
    new = fresh.owner_meaning
    old_owners: list[tuple[BasisPositiveRole, OwnerMeaningWitness]] = [
        (BasisPositiveRole.DECISION, old.decision),
        (BasisPositiveRole.TARGET, old.target),
    ]
    if old.claim is not None:
        old_owners.append((BasisPositiveRole.CLAIM, old.claim))
    old_owners.extend((BasisPositiveRole.CONTEXT, witness) for witness in old.context)
    new_owners = [new.decision, new.target, *new.context]
    if new.claim is not None:
        new_owners.append(new.claim)
    changes: list[BasisOwnerMeaningChange] = []
    for role, before in old_owners:
        match = next(
            (
                after
                for after in new_owners
                if _owner_subject_identity(before.subject)
                == _owner_subject_identity(after.subject)
            ),
            None,
        )
        if match is not None and (before.meaning, before.provenance) != (
            match.meaning,
            match.provenance,
        ):
            changes.append(BasisOwnerMeaningChange(role, before, match))
    return changes


def _authority_mismatch(
    prior: CurrentEvidenceBasis,
    fresh: CurrentEvidenceBasis,
    meaning_changes: list[BasisOwnerMeaningChange],
) -> CurrentEvidenceNoBasis | None:
    if (
        prior.sufficiency.requirement_version.version_id
        == fresh.sufficiency.requirement_version.version_id
        and prior.sufficiency.requirement_version
        != fresh.sufficiency.requirement_version
    ):
        return _invalid(
            prior.key,
            fresh.at,
            "immutable requirement authority changed without a new version",
        )
    changed_subjects = {
        _owner_subject_identity(change.prior.subject) for change in meaning_changes
    }
    if (
        prior.target.version == fresh.target.version
        and (
            prior.target.assertion != fresh.target.assertion
            or prior.target.correction_support != fresh.target.correction_support
        )
        and _owner_subject_identity(prior.owner_meaning.target.subject)
        not in changed_subjects
    ):
        return _invalid(
            prior.key,
            fresh.at,
            "target owner projection changed without attested meaning",
        )
    for old_selection, new_selection in zip(
        prior.context.selections, fresh.context.selections, strict=True
    ):
        old_facts = {fact.reference: fact for fact in old_selection.facts}
        new_facts = {fact.reference: fact for fact in new_selection.facts}
        if any(
            old_facts[ref] != new_facts[ref]
            and (CanonicalContextMeaning, old_selection.role, ref)
            not in changed_subjects
            for ref in old_facts.keys() & new_facts
        ):
            return _invalid(
                prior.key,
                fresh.at,
                "context owner projection changed without attested meaning",
            )
    if (
        _changed_immutable_roots(
            prior.evidence.observations,
            fresh.evidence.observations,
            lambda root: root.observation_id,
        )
        or _changed_immutable_roots(
            prior.evidence.bindings,
            fresh.evidence.bindings,
            lambda root: root.binding_id,
        )
        or _changed_immutable_roots(
            prior.evidence.assessments,
            fresh.evidence.assessments,
            lambda root: root.assessment_id,
        )
    ):
        return _invalid(
            prior.key,
            fresh.at,
            "immutable Evidence root changed under the same identity",
        )
    if prior.at == fresh.at and (
        meaning_changes
        or (
            prior.support_version == fresh.support_version
            and prior.evidence != fresh.evidence
        )
    ):
        return _invalid(
            prior.key,
            fresh.at,
            "owner meaning changed without a new read boundary",
        )
    return None


def _evidence_changed_only_through_time(
    prior: CurrentEvidenceBasis, fresh: CurrentEvidenceBasis
) -> bool:
    if fresh.at <= prior.at or (
        prior.requirement_key != fresh.requirement_key
        or prior.sufficiency.requirement_version
        != fresh.sufficiency.requirement_version
        or prior.support_version != fresh.support_version
        or prior.guards.binding_ids != fresh.guards.binding_ids
        or prior.guards.assessment_ids != fresh.guards.assessment_ids
        or prior.guards.fact_support != fresh.guards.fact_support
        or prior.sufficiency.guards != fresh.sufficiency.guards
    ):
        return False
    return (
        prior.evaluation != fresh.evaluation
        or prior.sufficiency.interpretations != fresh.sufficiency.interpretations
    )


def _changed_immutable_roots[FactT, IdT](
    prior: tuple[HistoricalEvidenceItem[FactT], ...],
    fresh: tuple[HistoricalEvidenceItem[FactT], ...],
    identity: Callable[[FactT], IdT],
) -> bool:
    old = {identity(item.root): item.root for item in prior}
    new = {identity(item.root): item.root for item in fresh}
    return any(old[key] != new[key] for key in old.keys() & new)


def _positive_changes(
    prior: CurrentEvidenceBasis, fresh: CurrentEvidenceBasis
) -> list[BasisPositiveChange]:
    changes: list[BasisPositiveChange] = []

    def positive(
        role: BasisPositiveRole,
        before: BasisPositiveReference | None,
        after: BasisPositiveReference | None,
    ) -> None:
        if before != after:
            changes.append(BasisPositiveChange(role, before, after))

    positive(
        BasisPositiveRole.DECISION,
        prior.decision.version,
        fresh.decision.version,
    )
    positive(
        BasisPositiveRole.TARGET,
        prior.target.version,
        fresh.target.version,
    )
    positive(
        BasisPositiveRole.CLAIM,
        prior.claim_catalog_version,
        fresh.claim_catalog_version,
    )
    positive(
        BasisPositiveRole.REQUIREMENT,
        prior.sufficiency.requirement_version.version_id,
        fresh.sufficiency.requirement_version.version_id,
    )
    positive(
        BasisPositiveRole.REQUIREMENT,
        prior.requirement_key,
        fresh.requirement_key,
    )
    positive(
        BasisPositiveRole.EVIDENCE_SUPPORT,
        prior.support_version,
        fresh.support_version,
    )
    _compare_context_references(prior, fresh, positive)
    _compare_fact_support(prior, fresh, positive)
    return changes


def _broken_guards(
    prior: CurrentEvidenceBasis, fresh: CurrentEvidenceBasis
) -> list[BasisGuardBreak]:
    broken: list[BasisGuardBreak] = []
    if (
        prior.guards.claim is not None
        and fresh.guards.claim is not None
        and prior.guards.claim != fresh.guards.claim
    ):
        broken.append(
            BasisGuardBreak(
                BasisGuardRole.CLAIM_MEMBERSHIP,
                prior.guards.claim,
                fresh.guards.claim,
            )
        )
    for old_guard, new_guard in zip(
        prior.context.guards, fresh.context.guards, strict=True
    ):
        if old_guard != new_guard:
            broken.append(
                BasisGuardBreak(BasisGuardRole.CONTEXT_SELECTION, old_guard, new_guard)
            )
    if (
        prior.sufficiency.guards.requirement_authority
        != fresh.sufficiency.guards.requirement_authority
    ):
        broken.append(
            BasisGuardBreak(
                BasisGuardRole.REQUIREMENT_AUTHORITY,
                prior.sufficiency.guards.requirement_authority,
                fresh.sufficiency.guards.requirement_authority,
            )
        )
    old_selection = EvidenceSelectionGuard.from_basis(prior)
    new_selection = EvidenceSelectionGuard.from_basis(fresh)
    if old_selection != new_selection:
        broken.append(
            BasisGuardBreak(
                BasisGuardRole.EVIDENCE_SELECTION, old_selection, new_selection
            )
        )
    if prior.sufficiency.guards.bindings != fresh.sufficiency.guards.bindings:
        broken.append(
            BasisGuardBreak(
                BasisGuardRole.SUFFICIENCY_BINDINGS,
                prior.sufficiency.guards.bindings,
                fresh.sufficiency.guards.bindings,
            )
        )
    if prior.sufficiency.guards.corrections != fresh.sufficiency.guards.corrections:
        broken.append(
            BasisGuardBreak(
                BasisGuardRole.SUFFICIENCY_CORRECTIONS,
                prior.sufficiency.guards.corrections,
                fresh.sufficiency.guards.corrections,
            )
        )
    return broken


def _compare_context_references(
    prior: CurrentEvidenceBasis,
    fresh: CurrentEvidenceBasis,
    positive: PositiveRecorder,
) -> None:
    old = {context_root(ref): ref for ref in prior.context.positive_references}
    new = {context_root(ref): ref for ref in fresh.context.positive_references}
    for root in sorted(old.keys() | new.keys(), key=repr):
        positive(
            BasisPositiveRole.CONTEXT,
            old.get(root),
            new.get(root),
        )


def _compare_fact_support(
    prior: CurrentEvidenceBasis,
    fresh: CurrentEvidenceBasis,
    positive: PositiveRecorder,
) -> None:
    old = prior.guards.fact_support
    new = fresh.guards.fact_support
    for ref in sorted(old - new, key=repr):
        positive(
            BasisPositiveRole.EVIDENCE_SUPPORT,
            ref,
            None,
        )
    for ref in sorted(new - old, key=repr):
        positive(
            BasisPositiveRole.EVIDENCE_SUPPORT,
            None,
            ref,
        )


class CurrentEvidenceBasisQuery:
    """Coordinate complete owner reads without issuing versions or absences."""

    def __init__(
        self,
        *,
        decisions: DecisionMemoryService,
        targets: TargetJudgmentResolver,
        contexts: ContextSelectionResolver,
        requirement_keys: RequirementKeyOwnerReader,
        sufficiency: CurrentSufficiencyReader,
        evidence: CurrentEvidenceHistoryReader,
        support_epochs: EvidenceSupportEpochReader,
        claims: ClaimCatalogMembershipResolver,
        requirements: EvidenceRequirementVersionResolver,
        decision_meaning: OwnerMeaningReader,
        target_meaning: OwnerMeaningReader,
        claim_meaning: OwnerMeaningReader,
        context_meaning: OwnerMeaningReader,
    ) -> None:
        self._decisions = decisions
        self._targets = targets
        self._contexts = contexts
        self._requirement_keys = requirement_keys
        self._sufficiency = sufficiency
        self._evidence = evidence
        self._support_epochs = support_epochs
        self._claims = claims
        self._requirements = requirements
        self._decision_meaning = OwnerMeaningResolver(decision_meaning)
        self._target_meaning = OwnerMeaningResolver(target_meaning)
        self._claim_meaning = OwnerMeaningResolver(claim_meaning)
        self._context_meaning = OwnerMeaningResolver(context_meaning)

    async def read(
        self, key: BasisScopeKey, *, at: datetime
    ) -> CurrentEvidenceBasisResult:
        if type(key) is not BasisScopeKey:
            raise TypeError("key must be BasisScopeKey")
        _aware(at)
        decision_read = await self._read_governing_decision(key, at)
        if isinstance(decision_read, CurrentEvidenceNoBasis):
            return decision_read
        decision, decision_proof = decision_read
        target_read = await self._read_target_meaning(key, at)
        if isinstance(target_read, CurrentEvidenceNoBasis):
            return target_read
        target, target_proof = target_read
        context_read = await self._read_context_meaning(key, at)
        if isinstance(context_read, CurrentEvidenceNoBasis):
            return context_read
        context, context_proofs = context_read

        requirement_key = await self._read_requirement_key(key, target, context, at)
        if isinstance(requirement_key, CurrentEvidenceNoBasis):
            return requirement_key
        claim_read = await self._read_claim_meaning(key, at)
        if isinstance(claim_read, CurrentEvidenceNoBasis):
            return claim_read
        claim, claim_proof = claim_read
        owner_meaning = CurrentOwnerMeaning(
            decision_proof, target_proof, claim_proof, context_proofs
        )
        if not _owner_meaning_matches(
            key, at, decision, target, context, claim, owner_meaning
        ):
            return _invalid(key, at, "owner meaning contradicts current dependencies")
        # duplicate-code: passing owner inputs to assembly and constructing the
        # complete result are different boundaries with the same initial fields.
        # arid: disable
        return await self._assemble(
            key,
            at,
            decision,
            target,
            # arid: enable
            context,
            requirement_key,
            claim,
            owner_meaning,
        )

    async def verify_owner_meaning(
        self, basis: CurrentEvidenceBasis, *, validation_at: datetime
    ) -> CurrentEvidenceNoBasis | None:
        """Recheck every prior or fresh owner cause against authoritative history."""
        _aware(validation_at)
        if type(basis) is not CurrentEvidenceBasis:
            raise TypeError("owner verification requires a complete basis")
        witnesses = [
            (self._decision_meaning, basis.owner_meaning.decision),
            (self._target_meaning, basis.owner_meaning.target),
        ]
        if basis.owner_meaning.claim is not None:
            witnesses.append((self._claim_meaning, basis.owner_meaning.claim))
        witnesses.extend(
            (self._context_meaning, witness) for witness in basis.owner_meaning.context
        )
        for resolver, witness in witnesses:
            result = await resolver.verify(witness, validation_at=validation_at)
            if isinstance(result, OwnerMeaningNoBasis):
                return _owner_meaning_failure(basis.key, validation_at, result)
        return None

    async def _read_governing_decision(
        self, key: BasisScopeKey, at: datetime
    ) -> tuple[DecisionMemoryView, OwnerMeaningWitness] | CurrentEvidenceNoBasis:
        decision = await self._read_decision(key, at)
        if isinstance(decision, CurrentEvidenceNoBasis):
            return decision
        proof = await self._read_meaning(
            self._decision_meaning,
            key,
            GoverningDecisionMeaning(
                DecisionContextVersionRef(key.decision_id, decision.version)
            ),
            at,
        )
        if isinstance(proof, CurrentEvidenceNoBasis):
            return proof
        if isinstance(
            decision.lifecycle_interpretation,
            ContestedDecisionLifecycleInterpretation,
        ):
            return _contested(key, at, "Decision lifecycle is contested")
        if isinstance(
            decision.lifecycle_interpretation,
            NotYetEffectiveDecisionLifecycleInterpretation,
        ):
            return _no_basis(
                key,
                at,
                CurrentNoBasisReason.NOT_YET_EFFECTIVE,
                "Decision is not yet effective",
            )
        return decision, proof

    async def _read_target_meaning(
        self, key: BasisScopeKey, at: datetime
    ) -> tuple[ResolvedTargetJudgment, OwnerMeaningWitness] | CurrentEvidenceNoBasis:
        target = await self._targets.read_current(key.target, at=at)
        if not isinstance(target, ResolvedTargetJudgment):
            return _target_failure(key, at, target)
        proof = await self._read_meaning(
            self._target_meaning, key, TargetJudgmentMeaning(target.version), at
        )
        return proof if isinstance(proof, CurrentEvidenceNoBasis) else (target, proof)

    async def _read_context_meaning(
        self, key: BasisScopeKey, at: datetime
    ) -> (
        tuple[CompleteContextSelection, tuple[OwnerMeaningWitness, ...]]
        | CurrentEvidenceNoBasis
    ):
        context = await self._contexts.read_complete_current(key, at=at)
        if isinstance(context, ContextNoBasis):
            return _context_failure(key, at, context)
        proofs = await self._context_meanings(key, context, at)
        return (
            proofs if isinstance(proofs, CurrentEvidenceNoBasis) else (context, proofs)
        )

    async def _read_claim_meaning(
        self, key: BasisScopeKey, at: datetime
    ) -> (
        tuple[ClaimMembershipGuard | None, OwnerMeaningWitness | None]
        | CurrentEvidenceNoBasis
    ):
        claim = await self._claim_guard(key, at)
        if isinstance(claim, CurrentEvidenceNoBasis):
            return claim
        if claim is None:
            return None, None
        proof = await self._read_meaning(
            self._claim_meaning,
            key,
            ClaimMembershipMeaning(
                key.target,
                claim.membership.claim_id,
                claim.membership.catalog_version,
            ),
            at,
        )
        return proof if isinstance(proof, CurrentEvidenceNoBasis) else (claim, proof)

    async def _read_meaning(
        self,
        resolver: OwnerMeaningResolver,
        key: BasisScopeKey,
        subject: OwnerMeaningSubject,
        at: datetime,
    ) -> OwnerMeaningWitness | CurrentEvidenceNoBasis:
        result = await resolver.read_current(key, subject, at=at)
        if isinstance(result, OwnerMeaningNoBasis):
            return _owner_meaning_failure(key, at, result)
        return result

    async def _context_meanings(
        self, key: BasisScopeKey, context: CompleteContextSelection, at: datetime
    ) -> tuple[OwnerMeaningWitness, ...] | CurrentEvidenceNoBasis:
        proofs: list[OwnerMeaningWitness] = []
        for selection in context.selections:
            subjects: tuple[OwnerMeaningSubject, ...] = (
                tuple(
                    CanonicalContextMeaning(
                        selection.role, fact.reference, selection.guard
                    )
                    for fact in selection.facts
                )
                if selection.facts
                else (CanonicalContextAbsence(selection.role, selection.guard),)
            )
            for subject in subjects:
                proof = await self._read_meaning(
                    self._context_meaning, key, subject, at
                )
                if isinstance(proof, CurrentEvidenceNoBasis):
                    return proof
                proofs.append(proof)
        return tuple(proofs)

    async def _read_decision(
        self, key: BasisScopeKey, at: datetime
    ) -> DecisionMemoryView | CurrentEvidenceNoBasis:
        try:
            return await self._decisions.current_at(key.decision_id, at=at)
        except DecisionNotFound:
            return _missing(key, at, "Decision missing")
        except (LifecycleConflict, RelationshipHistoryInvalidOrIncomplete) as error:
            return _invalid(key, at, str(error))
        except PersistenceUnavailable as error:
            return _unavailable(key, at, str(error))

    async def _read_requirement_key(
        self,
        key: BasisScopeKey,
        target: ResolvedTargetJudgment,
        context: CompleteContextSelection,
        at: datetime,
    ) -> EvidenceRequirementApplicabilityKey | CurrentEvidenceNoBasis:
        try:
            requirement_key = await self._requirement_keys.read_current(
                key, target, context, at=at
            )
        except EvidenceCommandReadUnavailable as error:
            return _unavailable(key, at, str(error))
        if isinstance(requirement_key, CurrentEvidenceNoBasis):
            return (
                requirement_key
                if requirement_key.key == key and requirement_key.at == at
                else _invalid(key, at, "requirement owner result mismatch")
            )
        if (
            type(requirement_key) is not ResolvedRequirementKey
            or requirement_key.key != key
            or requirement_key.at != at
        ):
            return _invalid(key, at, "requirement owner result mismatch")
        return requirement_key.applicability_key

    async def _assemble(
        self,
        key: BasisScopeKey,
        at: datetime,
        decision: DecisionMemoryView,
        target: ResolvedTargetJudgment,
        context: CompleteContextSelection,
        requirement_key: EvidenceRequirementApplicabilityKey,
        claim: ClaimMembershipGuard | None,
        owner_meaning: CurrentOwnerMeaning,
    ) -> CurrentEvidenceBasisResult:
        owner_inputs = await self._read_basis_inputs(key, at, requirement_key)
        if isinstance(owner_inputs, CurrentEvidenceNoBasis):
            return owner_inputs
        sufficiency, support_version, histories = owner_inputs
        selected = _select_evidence(histories, key, at)
        if isinstance(selected, CurrentEvidenceNoBasis):
            return selected
        authority_failure = await self._historical_authority(key, at, selected)
        if authority_failure is not None:
            return authority_failure
        if not _coherent_binding_basis(selected, sufficiency, requirement_key):
            return _incomplete(key, at, "interpreted Evidence owner reads disagree")
        try:
            evaluation = evaluate_evidence_sufficiency(
                sufficiency.requirement_version,
                requirement_key,
                sufficiency.interpretations,
                effective_at=at,
                known_at=at,
            )
        except (InvalidEvidenceSufficiency, ValueError) as error:
            return _invalid(key, at, str(error))
        guards = CurrentEvidenceGuards(
            frozenset(item.root.binding_id for item in selected.bindings),
            frozenset(item.root.assessment_id for item in selected.assessments),
            selected.fact_support,
            claim,
        )
        return CurrentEvidenceBasis(
            key,
            at,
            decision,
            target,
            requirement_key,
            sufficiency,
            evaluation,
            context,
            selected,
            support_version,
            guards,
            owner_meaning,
        )

    async def _read_basis_inputs(
        self,
        key: BasisScopeKey,
        at: datetime,
        requirement_key: EvidenceRequirementApplicabilityKey,
    ) -> (
        tuple[EvidenceSufficiencyBasis, EvidenceSupportVersion, EvidenceHistories]
        | CurrentEvidenceNoBasis
    ):
        try:
            sufficiency = await self._sufficiency.load_sufficiency_basis(
                requirement_key, effective_at=at, known_at=at
            )
            if not isinstance(sufficiency, EvidenceSufficiencyBasis):
                return _sufficiency_failure(key, at, sufficiency)
            support_version = await self._support_epochs.load_support_version(
                key.target, key.scope, key.use, effective_at=at, known_at=at
            )
            histories = await self._evidence.load_scope_histories(key, at=at)
        except EvidenceHistoryIncomplete as error:
            return _incomplete(key, at, str(error))
        except EvidenceHistoryInvalid as error:
            return _invalid(key, at, str(error))
        except EvidenceCommandReadUnavailable as error:
            return _unavailable(key, at, str(error))
        if type(support_version) is not EvidenceSupportVersion:
            return _invalid(key, at, "invalid Evidence epoch")
        if sufficiency.support_version != support_version:
            return _incomplete(key, at, "Evidence owner reads disagree on epoch")
        return sufficiency, support_version, histories

    async def _historical_authority(
        self,
        key: BasisScopeKey,
        at: datetime,
        selected: CurrentEvidenceSelection,
    ) -> CurrentEvidenceNoBasis | None:
        from polaris.domain.evidence.judgments import ClaimSpecificEvidenceScope

        if type(key.scope) is ClaimSpecificEvidenceScope:
            for item in selected.bindings:
                membership = await self._claims.resolve(
                    key.target,
                    key.scope.claim_id,
                    effective_at=item.root.effective_at,
                    # The historical and current claim reads use the same owner port
                    # with different cutoffs and independent failure meanings.
                    # arid: disable
                    known_at=item.root.recorded_at,
                )
                if not isinstance(membership, ResolvedClaimMembership):
                    if isinstance(membership, UnavailableClaimCatalog):
                        return _unavailable(key, at, membership.reason)
                    if isinstance(membership, ContestedClaimHistory):
                        return _contested(key, at, membership.reason)
                    return _invalid(
                        # arid: enable
                        key,
                        at,
                        "binding claim was not a historical catalog member",
                    )
                if (
                    membership.target != key.target
                    or membership.claim_id != key.scope.claim_id
                ):
                    return _invalid(key, at, "historical claim owner result mismatch")
        # Historical requirement lookup shares the owner call with reconstruction, while
        # this current basis has its own no-basis result.
        # arid: disable
        for item in selected.assessments:
            root = item.root
            authority = await self._requirements.resolve(
                root.applicability_key,
                effective_at=root.effective_at,
                known_at=root.known_at,
            )
            if not isinstance(authority, ResolvedEvidenceRequirementVersion):
                # arid: enable
                return _sufficiency_failure(key, at, authority)
            version = authority.version
            if not matches_historical_assessment_requirement_version(root, version):
                return _invalid(
                    key, at, "assessment historical requirement authority mismatch"
                )
        return None

    async def _claim_guard(
        self, key: BasisScopeKey, at: datetime
    ) -> ClaimMembershipGuard | CurrentEvidenceNoBasis | None:
        from polaris.domain.evidence.judgments import ClaimSpecificEvidenceScope

        if type(key.scope) is not ClaimSpecificEvidenceScope:
            return None
        membership = await self._claims.resolve(
            key.target, key.scope.claim_id, effective_at=at, known_at=at
        )
        if isinstance(membership, UnavailableClaimCatalog):
            return _unavailable(key, at, membership.reason)
        if isinstance(membership, ContestedClaimHistory):
            return _contested(key, at, membership.reason)
        if isinstance(membership, InvalidClaimHistory):
            return _invalid(key, at, membership.reason)
        if not isinstance(membership, ResolvedClaimMembership):
            return _missing(key, at, "claim is not current")
        if membership.target != key.target or membership.claim_id != key.scope.claim_id:
            return _invalid(key, at, "claim owner result mismatch")
        return ClaimMembershipGuard(key, membership)


def _select_evidence(
    histories: EvidenceHistories, key: BasisScopeKey, at: datetime
) -> CurrentEvidenceSelection | CurrentEvidenceNoBasis:
    if type(histories) is not EvidenceHistories:
        return _invalid(key, at, "invalid Evidence owner result")
    binding_histories = tuple(
        history
        for history in histories.bindings
        if history.root.target == key.target
        and history.root.scope == key.scope
        and history.root.evidence_use is key.use
    )
    assessment_histories = tuple(
        history
        for history in histories.assessments
        if history.root.target == key.target
        and history.root.scope == key.scope
        and history.root.evidence_use is key.use
    )
    try:
        bindings = _visible(binding_histories, at)
        assessments = _visible(assessment_histories, at)
    except InvalidEvidenceCorrectionHistory as error:
        return _invalid(key, at, str(error))
    observation_histories = _observation_ancestry(
        histories.observations, bindings, key, at
    )
    if isinstance(observation_histories, CurrentEvidenceNoBasis):
        return observation_histories
    try:
        observations = _visible(observation_histories, at)
    except InvalidEvidenceCorrectionHistory as error:
        return _invalid(key, at, str(error))
    if len(observations) != len(observation_histories):
        return _incomplete(key, at, "selected observation ancestry is not current")
    for family in (observations, bindings, assessments):
        if any(
            item.interpretation.state is EvidenceInterpretationState.CONTESTED
            for item in family
        ):
            return _contested(key, at, "Evidence interpretation contested")
    invalid = _selection_identity_failure(observations, bindings, assessments, key, at)
    if invalid is not None:
        return invalid
    current = _current_assessments(assessments, key, at)
    if isinstance(current, CurrentEvidenceNoBasis):
        return current
    return CurrentEvidenceSelection(observations, bindings, assessments, current)


def _selection_identity_failure(
    observations: tuple[HistoricalEvidenceItem, ...],
    bindings: tuple[HistoricalEvidenceItem, ...],
    assessments: tuple[HistoricalEvidenceItem, ...],
    key: BasisScopeKey,
    at: datetime,
) -> CurrentEvidenceNoBasis | None:
    binding_ids = [item.root.binding_id for item in bindings]
    assessment_ids = [item.root.assessment_id for item in assessments]
    if len(binding_ids) != len(set(binding_ids)) or len(assessment_ids) != len(
        set(assessment_ids)
    ):
        return _invalid(key, at, "duplicate Evidence root")
    observed = {item.root.observation_id: item for item in observations}
    if any(item.root.observation_id not in observed for item in bindings):
        return _incomplete(key, at, "binding observation not current")
    return None


def _observation_ancestry(
    observations: tuple[EvidenceObservationCorrectionHistory, ...],
    bindings: tuple,
    key: BasisScopeKey,
    at: datetime,
) -> tuple[EvidenceObservationCorrectionHistory, ...] | CurrentEvidenceNoBasis:
    by_id = {history.root.observation_id: history for history in observations}
    if len(by_id) != len(observations):
        return _invalid(key, at, "duplicate observation root")
    needed = {history.root.observation_id for history in bindings}
    frontier = tuple(needed)
    while frontier:
        if needed - by_id.keys():
            return _incomplete(key, at, "observation ancestry missing")
        ancestors = {
            by_id[item].root.supersedes_observation_id
            for item in frontier
            if by_id[item].root.supersedes_observation_id is not None
        } - needed
        needed.update(ancestors)
        frontier = tuple(ancestors)
    for observation_id in needed:
        seen = set()
        cursor = observation_id
        while cursor is not None:
            if cursor in seen:
                return _invalid(key, at, "observation succession cycle")
            seen.add(cursor)
            cursor = by_id[cursor].root.supersedes_observation_id
    return tuple(by_id[item] for item in sorted(needed, key=repr))


def _current_assessments(
    assessments: tuple[HistoricalEvidenceItem, ...],
    key: BasisScopeKey,
    at: datetime,
) -> tuple[HistoricalEvidenceItem, ...] | CurrentEvidenceNoBasis:
    by_id = {item.root.assessment_id: item for item in assessments}
    for item in assessments:
        predecessor = item.root.reassesses_assessment_id
        if predecessor is not None and predecessor not in by_id:
            return _incomplete(key, at, "reassessment ancestry missing")
        seen = {item.root.assessment_id}
        while predecessor is not None:
            if predecessor in seen:
                return _invalid(key, at, "reassessment cycle")
            seen.add(predecessor)
            predecessor = by_id[predecessor].root.reassesses_assessment_id
    superseded = {
        item.root.reassesses_assessment_id
        for item in assessments
        if item.root.reassesses_assessment_id is not None
        and item.interpretation.state is EvidenceInterpretationState.DETERMINATE
    }
    current = tuple(
        item
        for item in assessments
        if item.root.assessment_id not in superseded
        and item.interpretation.state is EvidenceInterpretationState.DETERMINATE
    )
    if len({item.root.applicability_key for item in current}) != len(current):
        return _contested(key, at, "competing current assessments")
    return current


def _visible(histories: tuple, at: datetime) -> tuple[HistoricalEvidenceItem, ...]:
    return tuple(
        HistoricalEvidenceItem(history.root, interpretation)
        for history in histories
        if (interpretation := history.interpret(effective_at=at, known_at=at)).state
        not in (
            EvidenceInterpretationState.NOT_KNOWN,
            EvidenceInterpretationState.NOT_EFFECTIVE,
        )
    )


def _coherent_binding_basis(
    selection: CurrentEvidenceSelection,
    sufficiency: EvidenceSufficiencyBasis,
    key: EvidenceRequirementApplicabilityKey,
) -> bool:
    observations = {item.root.observation_id: item for item in selection.observations}
    expected = {
        item.root.binding_id: (
            item.interpretation.fact_support
            | observations[item.root.observation_id].interpretation.fact_support
        )
        for item in selection.bindings
        if (
            any(
                value.freshness.basis.applicability_key == key
                for value in item.interpretation.assertions
            )
            if item.interpretation.assertions
            else item.root.freshness.basis.applicability_key == key
        )
    }
    actual = {
        value.binding.binding_id: value.fact_support
        for value in sufficiency.interpretations
    }
    return expected == actual


def _target_failure(
    key: BasisScopeKey, at: datetime, result: object
) -> CurrentEvidenceNoBasis:
    if isinstance(result, TargetJudgmentUnavailable):
        return _unavailable(key, at, result.reason)
    if isinstance(result, TargetJudgmentContested):
        return _contested(key, at, result.reason)
    if isinstance(result, TargetJudgmentInvalidHistory):
        return _invalid(key, at, result.reason)
    if isinstance(result, (TargetJudgmentMissing, TargetJudgmentWithdrawn)):
        return _missing(key, at, "target is not current")
    return _invalid(key, at, "invalid target owner result")


def _context_failure(
    key: BasisScopeKey, at: datetime, result: ContextNoBasis
) -> CurrentEvidenceNoBasis:
    reasons = {
        ContextNoBasisReason.MISSING_REQUIRED: CurrentNoBasisReason.MISSING,
        ContextNoBasisReason.INCOMPLETE_MEMBERSHIP: CurrentNoBasisReason.INCOMPLETE,
        ContextNoBasisReason.CONTESTED: CurrentNoBasisReason.CONTESTED,
        ContextNoBasisReason.INVALID_HISTORY: CurrentNoBasisReason.INVALID_HISTORY,
        ContextNoBasisReason.UNAVAILABLE_AUTHORITY: CurrentNoBasisReason.UNAVAILABLE,
    }
    return _no_basis(key, at, reasons[result.reason], result.detail)


def _owner_meaning_failure(
    key: BasisScopeKey, at: datetime, result: OwnerMeaningNoBasis
) -> CurrentEvidenceNoBasis:
    reasons = {
        OwnerMeaningNoBasisReason.MISSING: CurrentNoBasisReason.MISSING,
        OwnerMeaningNoBasisReason.INCOMPLETE: CurrentNoBasisReason.INCOMPLETE,
        OwnerMeaningNoBasisReason.CONTESTED: CurrentNoBasisReason.CONTESTED,
        OwnerMeaningNoBasisReason.NOT_YET_EFFECTIVE: (
            CurrentNoBasisReason.NOT_YET_EFFECTIVE
        ),
        OwnerMeaningNoBasisReason.UNAVAILABLE: CurrentNoBasisReason.UNAVAILABLE,
        OwnerMeaningNoBasisReason.CONTRADICTORY: CurrentNoBasisReason.INVALID_HISTORY,
        OwnerMeaningNoBasisReason.INVALID_HISTORY: CurrentNoBasisReason.INVALID_HISTORY,
    }
    return _no_basis(key, at, reasons[result.reason], result.detail)


def _sufficiency_failure(
    key: BasisScopeKey, at: datetime, result: object
) -> CurrentEvidenceNoBasis:
    if isinstance(result, MissingEvidenceRequirementAuthority):
        return _missing(key, at, "requirement authority missing")
    if isinstance(result, ContestedEvidenceRequirementAuthority):
        return _contested(key, at, "requirement authority contested")
    if isinstance(result, UnavailableEvidenceRequirementAuthority):
        return _unavailable(key, at, result.reason)
    if isinstance(
        result, (InvalidEvidenceRequirementAuthority, EvidenceSufficiencyInvalidHistory)
    ):
        return _invalid(key, at, result.reason)
    return _invalid(key, at, "invalid sufficiency owner result")


def _no_basis(
    key: BasisScopeKey, at: datetime, reason: CurrentNoBasisReason, detail: str
) -> CurrentEvidenceNoBasis:
    return CurrentEvidenceNoBasis(key, at, reason, detail)


def _missing(key: BasisScopeKey, at: datetime, detail: str) -> CurrentEvidenceNoBasis:
    return _no_basis(key, at, CurrentNoBasisReason.MISSING, detail)


def _incomplete(
    key: BasisScopeKey, at: datetime, detail: str
) -> CurrentEvidenceNoBasis:
    return _no_basis(key, at, CurrentNoBasisReason.INCOMPLETE, detail)


def _contested(key: BasisScopeKey, at: datetime, detail: str) -> CurrentEvidenceNoBasis:
    return _no_basis(key, at, CurrentNoBasisReason.CONTESTED, detail)


def _invalid(key: BasisScopeKey, at: datetime, detail: str) -> CurrentEvidenceNoBasis:
    return _no_basis(key, at, CurrentNoBasisReason.INVALID_HISTORY, detail)


def _unavailable(
    key: BasisScopeKey, at: datetime, detail: str
) -> CurrentEvidenceNoBasis:
    return _no_basis(key, at, CurrentNoBasisReason.UNAVAILABLE, detail)


# This public query checks aware time independently of the Decisions domain and retains
# its own error contract.
# arid: disable
def _aware(value: datetime) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError("current Evidence observation instant must be timezone-aware")


# arid: enable
