"""Assemble an exact current Evidence command basis from authoritative owner reads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

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
from polaris.domain.configuration import EvidenceRequirementApplicabilityKey
from polaris.domain.decisions import (
    ContestedDecisionLifecycleInterpretation,
    NotYetEffectiveDecisionLifecycleInterpretation,
)
from polaris.domain.evidence.claims import ClaimCatalogVersion
from polaris.domain.evidence.context_versions import BasisScopeKey
from polaris.domain.evidence.corrections import (
    EvidenceInterpretationState,
    EvidenceObservationCorrectionHistory,
    InvalidEvidenceCorrectionHistory,
)
from polaris.domain.evidence.observations import (
    EvidenceBindingId,
    EvidenceFactRef,
    EvidenceSufficiencyAssessmentId,
    EvidenceSupportVersion,
)
from polaris.domain.evidence.sufficiency import (
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
from .reconstruction import (
    EvidenceHistories,
    HistoricalEvidenceItem,
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


class CurrentNoBasisReason(StrEnum):
    MISSING = "missing"
    INCOMPLETE = "incomplete"
    CONTESTED = "contested"
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

    def __post_init__(self) -> None:
        _aware(self.at)
        if type(self.decision) is not DecisionMemoryView:
            raise TypeError("basis requires a versioned DecisionMemoryView")
        if self.decision.decision_id != self.key.decision_id:
            raise ValueError("governing Decision must match the Evidence key")
        if self.target.target != self.key.target:
            raise ValueError("owner target must match the Evidence key")
        if self.context.key != self.key or self.context.at != self.at:
            raise ValueError("context must attest the exact key and T=K")
        if self.support_version != self.sufficiency.support_version:
            raise ValueError("Evidence epoch must match the sufficiency owner read")
        if self.guards.fact_support != self.evidence.fact_support:
            raise ValueError("Evidence ancestry guard must cover all selected support")

    @property
    def claim_catalog_version(self) -> ClaimCatalogVersion | None:
        return (
            None
            if self.guards.claim is None
            else self.guards.claim.membership.catalog_version
        )


type CurrentEvidenceBasisResult = CurrentEvidenceBasis | CurrentEvidenceNoBasis


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

    async def read(
        self, key: BasisScopeKey, *, at: datetime
    ) -> CurrentEvidenceBasisResult:
        if type(key) is not BasisScopeKey:
            raise TypeError("key must be BasisScopeKey")
        _aware(at)
        decision = await self._read_decision(key, at)
        if isinstance(decision, CurrentEvidenceNoBasis):
            return decision
        if isinstance(
            decision.lifecycle_interpretation,
            ContestedDecisionLifecycleInterpretation,
        ):
            return _contested(key, at, "Decision lifecycle is contested")
        if isinstance(
            decision.lifecycle_interpretation,
            NotYetEffectiveDecisionLifecycleInterpretation,
        ):
            return _missing(key, at, "Decision is not yet effective")
        target = await self._targets.read_current(key.target, at=at)
        if not isinstance(target, ResolvedTargetJudgment):
            return _target_failure(key, at, target)
        context = await self._contexts.read_complete_current(key, at=at)
        if isinstance(context, ContextNoBasis):
            return _context_failure(key, at, context)

        requirement_key = await self._read_requirement_key(key, target, context, at)
        if isinstance(requirement_key, CurrentEvidenceNoBasis):
            return requirement_key
        claim = await self._claim_guard(key, at)
        if isinstance(claim, CurrentEvidenceNoBasis):
            return claim
        return await self._assemble(
            key, at, decision, target, context, requirement_key, claim
        )

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
