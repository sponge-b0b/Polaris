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
    DecisionMemoryTemporalView,
)
from polaris.application.decisions.ordinary_work import DecisionNotFound
from polaris.domain.decisions import (
    ContestedDecisionLifecycleInterpretation,
    InvestmentDecisionId,
    NotYetEffectiveDecisionLifecycleInterpretation,
)
from polaris.domain.evidence import (
    ClaimCatalogVersion,
    ClaimId,
    ClaimSpecificEvidenceScope,
    EvidenceAssessmentCorrectionHistory,
    EvidenceBindingCorrectionHistory,
    EvidenceInterpretation,
    EvidenceInterpretationState,
    EvidenceJudgmentRef,
    EvidenceObservationCorrectionHistory,
    EvidenceUse,
    is_evidence_judgment_ref,
)
from polaris.domain.evidence.bindings import EvidenceBinding
from polaris.domain.evidence.corrections import InvalidEvidenceCorrectionHistory
from polaris.domain.evidence.observations import EvidenceObservation
from polaris.domain.evidence.sufficiency import (
    EvidenceSufficiencyAssessment,
    matches_historical_assessment_requirement_version,
)

from .claims import (
    ClaimCatalogMembershipResolver,
    ClaimNotCurrent,
    ClaimNotKnownAtCutoff,
    ClaimNotYetEffective,
    ClaimTargetNotKnownAtCutoff,
    ClaimTargetNotYetEffective,
    ContestedClaimHistory,
    InvalidClaimHistory,
    InvalidClaimReference,
    ResolvedClaimMembership,
    UnavailableClaimCatalog,
)
from .contracts import EvidenceCommandReadUnavailable
from .requirements import (
    ContestedEvidenceRequirementAuthority,
    EvidenceRequirementVersionResolver,
    InvalidEvidenceRequirementAuthority,
    ResolvedEvidenceRequirementVersion,
    UnavailableEvidenceRequirementAuthority,
)


# duplicate-code: this Application input guard owns ValueError semantics; sharing
# a Decisions-domain validator would couple independent public boundaries.
# arid: disable
def _aware(value: object, field: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{field} must be timezone-aware")


# arid: enable


@dataclass(frozen=True, slots=True)
class HistoricalEvidenceRequest:
    decision_id: InvestmentDecisionId
    target: EvidenceJudgmentRef
    effective_at: datetime
    known_at: datetime

    def __post_init__(self) -> None:
        if type(self.decision_id) is not InvestmentDecisionId:
            raise TypeError("decision_id must be InvestmentDecisionId")
        if not is_evidence_judgment_ref(self.target):
            raise TypeError("target must be an EvidenceJudgmentRef")
        _aware(self.effective_at, "effective_at")
        _aware(self.known_at, "known_at")


@dataclass(frozen=True, slots=True)
class TargetContext[TargetFactT]:
    """Target-owned canonical fact and its Decision association at one `(T,K)`."""

    decision_id: InvestmentDecisionId
    target: EvidenceJudgmentRef
    fact: TargetFactT


@dataclass(frozen=True, slots=True)
class TargetNotKnown:
    pass


@dataclass(frozen=True, slots=True)
class TargetNotEffective:
    pass


@dataclass(frozen=True, slots=True)
class TargetInvalidReference:
    reason: str


@dataclass(frozen=True, slots=True)
class TargetContextIncomplete:
    reason: str


@dataclass(frozen=True, slots=True)
class TargetContextContested:
    reason: str


@dataclass(frozen=True, slots=True)
class TargetContextUnavailable:
    reason: str


type TargetContextResolution[TargetFactT] = (
    TargetContext[TargetFactT]
    | TargetNotKnown
    | TargetNotEffective
    | TargetInvalidReference
    | TargetContextIncomplete
    | TargetContextContested
    | TargetContextUnavailable
)


class HistoricalTargetReader[TargetFactT](Protocol):
    async def load_target_context(
        self, target: EvidenceJudgmentRef, *, effective_at: datetime, known_at: datetime
    ) -> TargetContextResolution[TargetFactT]: ...


@dataclass(frozen=True, slots=True)
class EvidenceHistories:
    """Complete target-root history, including corrections recorded after the cutoff."""

    observations: tuple[EvidenceObservationCorrectionHistory, ...]
    bindings: tuple[EvidenceBindingCorrectionHistory, ...]
    assessments: tuple[EvidenceAssessmentCorrectionHistory, ...]


class HistoricalEvidenceReader(Protocol):
    async def load_target_histories(
        self, target: EvidenceJudgmentRef
    ) -> EvidenceHistories:
        """Return all target roots and their referenced observation histories."""
        ...


class _CorrectionHistory[FactT](Protocol):
    @property
    def root(self) -> FactT: ...

    def interpret(
        self, *, effective_at: datetime, known_at: datetime
    ) -> EvidenceInterpretation[FactT]: ...


@dataclass(frozen=True, slots=True)
class HistoricalEvidenceItem[FactT]:
    root: FactT
    interpretation: EvidenceInterpretation[FactT]


@dataclass(frozen=True, slots=True)
class HistoricalDecisionContext[TargetFactT]:
    decision: DecisionMemoryTemporalView
    target: TargetContext[TargetFactT]


@dataclass(frozen=True, slots=True)
class HistoricalEvidenceView[TargetFactT]:
    request: HistoricalEvidenceRequest
    context: HistoricalDecisionContext[TargetFactT]
    observations: tuple[HistoricalEvidenceItem[EvidenceObservation], ...]
    judgment_time_bindings: tuple[HistoricalEvidenceItem[EvidenceBinding], ...]
    current_support_bindings: tuple[HistoricalEvidenceItem[EvidenceBinding], ...]
    retrospective_later_bindings: tuple[HistoricalEvidenceItem[EvidenceBinding], ...]
    reconstruction_only_bindings: tuple[HistoricalEvidenceItem[EvidenceBinding], ...]
    assessments: tuple[HistoricalEvidenceItem[EvidenceSufficiencyAssessment], ...]
    current_assessments: tuple[
        HistoricalEvidenceItem[EvidenceSufficiencyAssessment], ...
    ]


@dataclass(frozen=True, slots=True)
class CompleteReconstruction[TargetFactT]:
    view: HistoricalEvidenceView[TargetFactT]


@dataclass(frozen=True, slots=True)
class IncompleteReconstruction[TargetFactT]:
    reasons: tuple[str, ...]
    safe_partial: HistoricalEvidenceView[TargetFactT] | None = None


@dataclass(frozen=True, slots=True)
class ContestedReconstruction[TargetFactT]:
    reasons: tuple[str, ...]
    safe_partial: HistoricalEvidenceView[TargetFactT] | None = None


class ReconstructionSubject(StrEnum):
    DECISION = "decision"
    TARGET = "target"
    CLAIM = "claim"
    CONTEXT = "context"


@dataclass(frozen=True, slots=True)
class ReconstructionNotKnown:
    subject: ReconstructionSubject


@dataclass(frozen=True, slots=True)
class ReconstructionInvalidReference:
    reason: str


@dataclass(frozen=True, slots=True)
class ReconstructionNotEffective:
    subject: ReconstructionSubject


@dataclass(frozen=True, slots=True)
class ReconstructionInvalidHistory:
    reason: str


@dataclass(frozen=True, slots=True)
class ReconstructionUnavailable:
    reason: str


def _claim_resolution_identity_status(
    resolution: object,
    target: EvidenceJudgmentRef,
    claim_id: ClaimId,
) -> ReconstructionInvalidReference | ReconstructionInvalidHistory | None:
    if not isinstance(
        resolution,
        (
            ResolvedClaimMembership,
            ClaimTargetNotKnownAtCutoff,
            ClaimNotKnownAtCutoff,
            ClaimTargetNotYetEffective,
            ClaimNotYetEffective,
            ClaimNotCurrent,
            InvalidClaimReference,
            ContestedClaimHistory,
            InvalidClaimHistory,
            UnavailableClaimCatalog,
        ),
    ):
        return ReconstructionInvalidHistory("unsupported claim membership result")
    if resolution.target != target:
        return ReconstructionInvalidReference("claim result has a different target")
    if (
        isinstance(
            resolution,
            (
                ResolvedClaimMembership,
                ClaimNotKnownAtCutoff,
                ClaimNotYetEffective,
                ClaimNotCurrent,
                InvalidClaimReference,
            ),
        )
        and resolution.claim_id != claim_id
    ):
        return ReconstructionInvalidReference("claim result has a different Claim ID")
    if isinstance(resolution, ResolvedClaimMembership) and (
        type(resolution.catalog_version) is not ClaimCatalogVersion
    ):
        return ReconstructionInvalidReference("claim result has an invalid version")
    return None


class StaleEvidenceBasisCategory(StrEnum):
    DECISION_CHANGED = "decision_changed"
    TARGET_CHANGED = "target_changed"
    CLAIM_CHANGED = "claim_changed"
    REQUIREMENTS_CHANGED = "requirements_changed"
    EVIDENCE_SUPPORT_CHANGED = "evidence_support_changed"
    NEGATIVE_PREDICATE_BROKEN = "negative_predicate_broken"
    SUPPORT_CHANGED_BY_TIME = "support_changed_by_time"


@dataclass(frozen=True, slots=True)
class StaleEvidenceBasis:
    categories: frozenset[StaleEvidenceBasisCategory]

    def __post_init__(self) -> None:
        if not self.categories or any(
            type(value) is not StaleEvidenceBasisCategory for value in self.categories
        ):
            raise ValueError("stale Evidence basis requires typed mismatch categories")


type HistoricalReconstructionResult[TargetFactT] = (
    CompleteReconstruction[TargetFactT]
    | IncompleteReconstruction[TargetFactT]
    | ContestedReconstruction[TargetFactT]
    | ReconstructionNotKnown
    | ReconstructionInvalidReference
    | ReconstructionNotEffective
    | ReconstructionInvalidHistory
    | ReconstructionUnavailable
)

type EvidenceReconstructionResult[TargetFactT] = (
    HistoricalReconstructionResult[TargetFactT] | StaleEvidenceBasis
)


class HistoricalEvidenceQuery[TargetFactT]:
    """Compose owner facts and Evidence history without revising historical proof."""

    def __init__(
        self,
        *,
        decisions: DecisionMemoryService,
        targets: HistoricalTargetReader[TargetFactT],
        evidence: HistoricalEvidenceReader,
        claims: ClaimCatalogMembershipResolver,
        requirements: EvidenceRequirementVersionResolver,
    ) -> None:
        self._decisions = decisions
        self._targets = targets
        self._evidence = evidence
        self._claims = claims
        self._requirements = requirements

    async def reconstruct(
        self, request: HistoricalEvidenceRequest
    ) -> HistoricalReconstructionResult[TargetFactT]:
        if type(request) is not HistoricalEvidenceRequest:
            raise TypeError("request must be HistoricalEvidenceRequest")
        decision = await self._load_decision(request)
        if not isinstance(decision, DecisionMemoryTemporalView):
            return decision
        if isinstance(
            decision.lifecycle_interpretation,
            NotYetEffectiveDecisionLifecycleInterpretation,
        ):
            return ReconstructionNotEffective(ReconstructionSubject.DECISION)
        if isinstance(
            decision.lifecycle_interpretation,
            ContestedDecisionLifecycleInterpretation,
        ):
            return ContestedReconstruction(("Decision lifecycle is contested",))
        target = await self._load_target(request)
        if not isinstance(target, TargetContext):
            return target
        if target.decision_id != request.decision_id or target.target != request.target:
            return ReconstructionInvalidReference(
                "target does not belong to the requested Decision"
            )
        try:
            histories = await self._evidence.load_target_histories(request.target)
        except EvidenceCommandReadUnavailable as error:
            return ReconstructionUnavailable(str(error))
        try:
            return await self._compose(
                request, HistoricalDecisionContext(decision, target), histories
            )
        except InvalidEvidenceCorrectionHistory as error:
            return ReconstructionInvalidHistory(str(error))

    async def _load_decision(
        self, request: HistoricalEvidenceRequest
    ) -> (
        DecisionMemoryTemporalView
        | ReconstructionNotKnown
        | ReconstructionInvalidHistory
        | ReconstructionUnavailable
    ):
        try:
            return await self._decisions.effective_at(
                request.decision_id, request.effective_at, known_at=request.known_at
            )
        except DecisionNotFound:
            return ReconstructionNotKnown(ReconstructionSubject.DECISION)
        except (LifecycleConflict, RelationshipHistoryInvalidOrIncomplete) as error:
            return ReconstructionInvalidHistory(str(error))
        except PersistenceUnavailable as error:
            return ReconstructionUnavailable(str(error))

    async def _load_target(
        self, request: HistoricalEvidenceRequest
    ) -> (
        TargetContext[TargetFactT]
        | ReconstructionNotKnown
        | ReconstructionNotEffective
        | ReconstructionInvalidReference
        | IncompleteReconstruction[TargetFactT]
        | ContestedReconstruction[TargetFactT]
        | ReconstructionUnavailable
    ):
        target = await self._targets.load_target_context(
            request.target, effective_at=request.effective_at, known_at=request.known_at
        )
        if isinstance(target, TargetNotKnown):
            return ReconstructionNotKnown(ReconstructionSubject.TARGET)
        if isinstance(target, TargetNotEffective):
            return ReconstructionNotEffective(ReconstructionSubject.TARGET)
        if isinstance(target, TargetInvalidReference):
            return ReconstructionInvalidReference(target.reason)
        if isinstance(target, TargetContextIncomplete):
            return IncompleteReconstruction((target.reason,))
        if isinstance(target, TargetContextContested):
            return ContestedReconstruction((target.reason,))
        if isinstance(target, TargetContextUnavailable):
            return ReconstructionUnavailable(target.reason)
        return target

    async def _compose(
        self,
        request: HistoricalEvidenceRequest,
        context: HistoricalDecisionContext[TargetFactT],
        histories: EvidenceHistories,
    ) -> HistoricalReconstructionResult[TargetFactT]:
        bindings = self._visible(histories.bindings, request)
        observation_ids = {item.root.observation_id for item in bindings}
        observations = tuple(
            item
            for item in self._visible(histories.observations, request)
            if item.root.observation_id in observation_ids
        )
        assessments = self._visible(histories.assessments, request)
        judgment_time = tuple(
            item
            for item in bindings
            if item.root.evidence_use
            in (EvidenceUse.JUDGMENT_BASIS, EvidenceUse.CHALLENGE_BASIS)
        )
        current_support = tuple(
            item
            for item in bindings
            if item.root.evidence_use is EvidenceUse.CURRENT_SUPPORT_CHECK
        )
        retrospective = tuple(
            item
            for item in bindings
            if item.root.evidence_use is EvidenceUse.RETROSPECTIVE_LATER_EVIDENCE
        )
        reconstruction_only = tuple(
            item
            for item in bindings
            if item.root.evidence_use is EvidenceUse.RECONSTRUCTION_ONLY
        )
        binding_status = await self._binding_status(bindings, observations)
        if isinstance(
            binding_status,
            (
                ReconstructionUnavailable,
                ReconstructionInvalidHistory,
                ReconstructionInvalidReference,
                ReconstructionNotKnown,
                ReconstructionNotEffective,
            ),
        ):
            return binding_status
        assessment_status = await self._assessment_status(assessments)
        if isinstance(
            assessment_status, (ReconstructionUnavailable, ReconstructionInvalidHistory)
        ):
            return assessment_status
        incomplete, contested = binding_status
        assessment_incomplete, assessment_contested, current_assessments = (
            assessment_status
        )
        view = HistoricalEvidenceView(
            request,
            context,
            observations,
            judgment_time,
            current_support,
            retrospective,
            reconstruction_only,
            assessments,
            current_assessments,
        )
        incomplete.extend(assessment_incomplete)
        contested.extend(assessment_contested)
        contested.extend(
            "observation correction branches conflict"
            for item in observations
            if item.interpretation.state is EvidenceInterpretationState.CONTESTED
        )
        if contested:
            return ContestedReconstruction(tuple(dict.fromkeys(contested)), view)
        if incomplete:
            return IncompleteReconstruction(tuple(dict.fromkeys(incomplete)), view)
        return CompleteReconstruction(view)

    @staticmethod
    def _visible[FactT](
        histories: tuple[_CorrectionHistory[FactT], ...],
        request: HistoricalEvidenceRequest,
    ) -> tuple[HistoricalEvidenceItem[FactT], ...]:
        return tuple(
            HistoricalEvidenceItem(history.root, interpretation)
            for history in histories
            if (
                interpretation := history.interpret(
                    effective_at=request.effective_at, known_at=request.known_at
                )
            ).state
            is not EvidenceInterpretationState.NOT_KNOWN
        )

    async def _binding_status(
        self,
        bindings: tuple[HistoricalEvidenceItem[EvidenceBinding], ...],
        observations: tuple[HistoricalEvidenceItem[EvidenceObservation], ...],
    ) -> (
        tuple[list[str], list[str]]
        | ReconstructionUnavailable
        | ReconstructionInvalidHistory
        | ReconstructionInvalidReference
        | ReconstructionNotKnown
        | ReconstructionNotEffective
    ):
        incomplete: list[str] = []
        contested: list[str] = []
        observed = {item.root.observation_id: item for item in observations}
        for item in bindings:
            observation = observed.get(item.root.observation_id)
            if observation is None:
                incomplete.append("binding references a missing observation history")
            elif observation.interpretation.state in (
                EvidenceInterpretationState.NOT_EFFECTIVE,
                EvidenceInterpretationState.WITHDRAWN,
            ):
                incomplete.append("binding observation has no effective assertion")
            if item.interpretation.state is EvidenceInterpretationState.CONTESTED:
                contested.append("binding correction branches conflict")
            for assertion in item.interpretation.assertions:
                claim_status = await self._claim_status(assertion, item.root)
                if isinstance(claim_status, ContestedReconstruction):
                    contested.extend(claim_status.reasons)
                elif claim_status is not None:
                    return claim_status
        return incomplete, contested

    async def _claim_status(
        self, assertion: EvidenceBinding, root: EvidenceBinding
    ) -> (
        ContestedReconstruction[TargetFactT]
        | ReconstructionUnavailable
        | ReconstructionInvalidHistory
        | ReconstructionInvalidReference
        | ReconstructionNotKnown
        | ReconstructionNotEffective
        | None
    ):
        if type(assertion.scope) is not ClaimSpecificEvidenceScope:
            return None
        membership = await self._claims.resolve(
            assertion.target,
            assertion.scope.claim_id,
            effective_at=root.effective_at,
            known_at=root.recorded_at,
        )
        identity_status = _claim_resolution_identity_status(
            membership, assertion.target, assertion.scope.claim_id
        )
        if identity_status is not None:
            return identity_status
        if isinstance(membership, ContestedClaimHistory):
            return ContestedReconstruction(("binding claim history is contested",))
        if isinstance(membership, UnavailableClaimCatalog):
            return ReconstructionUnavailable(membership.reason)
        if isinstance(membership, InvalidClaimHistory):
            return ReconstructionInvalidHistory(membership.reason)
        if isinstance(membership, (ClaimTargetNotKnownAtCutoff, ClaimNotKnownAtCutoff)):
            subject = (
                ReconstructionSubject.TARGET
                if isinstance(membership, ClaimTargetNotKnownAtCutoff)
                else ReconstructionSubject.CLAIM
            )
            return ReconstructionNotKnown(subject)
        if isinstance(membership, (ClaimTargetNotYetEffective, ClaimNotYetEffective)):
            subject = (
                ReconstructionSubject.TARGET
                if isinstance(membership, ClaimTargetNotYetEffective)
                else ReconstructionSubject.CLAIM
            )
            return ReconstructionNotEffective(subject)
        if not isinstance(membership, ResolvedClaimMembership):
            return ReconstructionInvalidReference(
                "binding claim was not a member at its historical boundary"
            )
        return None

    async def _assessment_status(
        self,
        assessments: tuple[HistoricalEvidenceItem[EvidenceSufficiencyAssessment], ...],
    ) -> (
        tuple[
            list[str],
            list[str],
            tuple[HistoricalEvidenceItem[EvidenceSufficiencyAssessment], ...],
        ]
        | ReconstructionUnavailable
        | ReconstructionInvalidHistory
    ):
        incomplete: list[str] = []
        contested: list[str] = []
        by_id = {item.root.assessment_id: item for item in assessments}
        if len(by_id) != len(assessments):
            return ReconstructionInvalidHistory("duplicate assessment root identity")
        for item in assessments:
            root = item.root
            lineage_status = self._reassessment_status(item, by_id)
            if isinstance(lineage_status, ReconstructionInvalidHistory):
                return lineage_status
            if lineage_status is not None:
                incomplete.append(lineage_status)
            if item.interpretation.state is EvidenceInterpretationState.CONTESTED:
                contested.append("assessment correction branches conflict")
            authority_status = await self._requirement_status(root)
            if isinstance(
                authority_status,
                (ReconstructionUnavailable, ReconstructionInvalidHistory),
            ):
                return authority_status
            if isinstance(authority_status, ContestedReconstruction):
                contested.extend(authority_status.reasons)
            if isinstance(authority_status, IncompleteReconstruction):
                incomplete.extend(authority_status.reasons)
        live = tuple(
            item
            for item in assessments
            if item.interpretation.state
            in (
                EvidenceInterpretationState.DETERMINATE,
                EvidenceInterpretationState.CONTESTED,
            )
        )
        superseded = {
            item.root.reassesses_assessment_id
            for item in live
            if item.root.reassesses_assessment_id is not None
        }
        current = tuple(
            item for item in live if item.root.assessment_id not in superseded
        )
        keys = [item.root.applicability_key for item in current]
        if len(keys) != len(set(keys)):
            contested.append("competing current assessment roots")
        return incomplete, contested, current

    async def _requirement_status(
        self, root: EvidenceSufficiencyAssessment
    ) -> (
        ReconstructionUnavailable
        | ReconstructionInvalidHistory
        | ContestedReconstruction[TargetFactT]
        | IncompleteReconstruction[TargetFactT]
        | None
    ):
        authority = await self._requirements.resolve(
            root.applicability_key,
            effective_at=root.effective_at,
            known_at=root.known_at,
        )
        if isinstance(authority, UnavailableEvidenceRequirementAuthority):
            return ReconstructionUnavailable(authority.reason)
        if isinstance(authority, InvalidEvidenceRequirementAuthority):
            return ReconstructionInvalidHistory(authority.reason)
        if isinstance(authority, ContestedEvidenceRequirementAuthority):
            return ContestedReconstruction(
                ("assessment requirement authority is contested",)
            )
        if not isinstance(authority, ResolvedEvidenceRequirementVersion):
            return IncompleteReconstruction(
                ("assessment requirement authority is missing",)
            )
        version = authority.version
        if not matches_historical_assessment_requirement_version(root, version):
            return ReconstructionInvalidHistory(
                "assessment does not retain its historical requirement version"
            )
        return None

    @staticmethod
    def _reassessment_status(
        item: HistoricalEvidenceItem[EvidenceSufficiencyAssessment],
        by_id: dict[object, HistoricalEvidenceItem[EvidenceSufficiencyAssessment]],
    ) -> ReconstructionInvalidHistory | str | None:
        predecessor_id = item.root.reassesses_assessment_id
        if predecessor_id is not None:
            predecessor = by_id.get(predecessor_id)
            if predecessor is None:
                return "assessment reassessment predecessor is missing"
            if predecessor.root.applicability_key != item.root.applicability_key:
                return ReconstructionInvalidHistory(
                    "assessment reassessment predecessor has a different scope"
                )
        if HistoricalEvidenceQuery._reassessment_cycle(item, by_id):
            return ReconstructionInvalidHistory("assessment reassessment cycle")
        return None

    @staticmethod
    def _reassessment_cycle(
        item: HistoricalEvidenceItem[EvidenceSufficiencyAssessment],
        by_id: dict[object, HistoricalEvidenceItem[EvidenceSufficiencyAssessment]],
    ) -> bool:
        seen = {item.root.assessment_id}
        predecessor = item.root.reassesses_assessment_id
        while predecessor is not None and predecessor in by_id:
            if predecessor in seen:
                return True
            seen.add(predecessor)
            predecessor = by_id[predecessor].root.reassesses_assessment_id
        return False
